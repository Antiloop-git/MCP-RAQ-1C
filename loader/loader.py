"""Streamlit UI для загрузки и индексации метаданных 1С в Qdrant."""

import httpx
import streamlit as st

from config import (
    DEFAULT_COLLECTION,
    PARSER_SERVICE_URL,
    EMBEDDING_SERVICE_URL,
    QDRANT_HOST,
    QDRANT_PORT,
    ROW_BATCH_SIZE,
)
from indexer import QdrantIndexer, BslIndexer, DEFAULT_CODE_COLLECTION


st.set_page_config(page_title="MCP RAQ 1C — Loader", layout="wide")
st.title("MCP RAQ 1C — Загрузка метаданных")


def check_service(url: str, name: str) -> bool:
    try:
        resp = httpx.get(f"{url}/health", timeout=5.0)
        return resp.status_code == 200
    except Exception:
        return False


def check_qdrant() -> bool:
    try:
        resp = httpx.get(f"http://{QDRANT_HOST}:{QDRANT_PORT}/healthz", timeout=5.0)
        return resp.status_code == 200
    except Exception:
        return False


# --- Статус сервисов ---
st.subheader("Статус сервисов")
col1, col2, col3 = st.columns(3)

parser_ok = check_service(PARSER_SERVICE_URL, "Parser")
embeddings_ok = check_service(EMBEDDING_SERVICE_URL, "Embeddings")
qdrant_ok = check_qdrant()

col1.metric("Parser", "OK" if parser_ok else "Недоступен")
col2.metric("Embeddings", "OK" if embeddings_ok else "Недоступен")
col3.metric("Qdrant", "OK" if qdrant_ok else "Недоступен")

all_ok = parser_ok and embeddings_ok and qdrant_ok

# ============================================================
# Вкладки
# ============================================================
tab_meta, tab_bsl = st.tabs(["🗂️ Метаданные", "📝 BSL-код"])

with tab_meta:
    # --- Настройки ---
    st.subheader("Настройки индексации")
    col_a, col_b = st.columns(2)

    collection_name = col_a.text_input("Имя коллекции", value=DEFAULT_COLLECTION)
    config_name = col_b.text_input("Имя конфигурации", value="MY_CONFIG")

    # --- Путь к XML-выгрузке ---
    current_config_path = ""
    if parser_ok:
        try:
            path_resp = httpx.get(f"{PARSER_SERVICE_URL}/config-path", timeout=5.0)
            if path_resp.status_code == 200:
                current_config_path = path_resp.json().get("config_path", "")
        except Exception:
            pass

    config_path = st.text_input(
        "Путь к XML-выгрузке конфигурации (внутри контейнера parser)",
        value=current_config_path,
        help="Путь к папке с XML-файлами конфигурации 1С внутри контейнера parser. "
        "По умолчанию: /app/configuration/Prod. "
        "Для использования другой папки примонтируйте её в docker-compose.yml "
        "в секции parser → volumes.",
    )

    if parser_ok and config_path and config_path != current_config_path:
        if st.button("Применить путь", key="apply_path"):
            try:
                reload_resp = httpx.post(
                    f"{PARSER_SERVICE_URL}/reload",
                    params={"config_path": config_path},
                    timeout=120.0,
                )
                if reload_resp.status_code == 200:
                    data = reload_resp.json()
                    st.success(
                        f"Путь изменён: `{config_path}`. "
                        f"Загружено {data['total_objects']} объектов."
                    )
                    st.rerun()
                else:
                    st.error(f"Ошибка: {reload_resp.text}")
            except Exception as e:
                st.error(f"Ошибка смены пути: {e}")

    # --- Статистика парсера ---
    if parser_ok:
        try:
            stats_resp = httpx.get(f"{PARSER_SERVICE_URL}/stats", timeout=30.0)
            if stats_resp.status_code == 200:
                stats = stats_resp.json()
                total = sum(stats.values())
                st.info(f"Объектов в конфигурации: **{total}** ({', '.join(f'{k}: {v}' for k, v in stats.items())})")
        except Exception:
            pass

    # --- Статистика Qdrant ---
    if qdrant_ok:
        try:
            from qdrant_client import QdrantClient
            qc = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
            collections = [c.name for c in qc.get_collections().collections]
            if collections:
                st.info(f"Коллекции в Qdrant: {', '.join(collections)}")
            if collection_name in collections:
                info = qc.get_collection(collection_name)
                st.warning(
                    f"Коллекция `{collection_name}` уже существует ({info.points_count} points). "
                    "При индексации она будет пересоздана."
                )
            qc.close()
        except Exception:
            pass

    # --- Кнопка индексации ---
    st.divider()
    st.subheader("🗂️ Индексация метаданных в Qdrant")
    st.caption(f"Парсит XML-выгрузку конфигурации, строит эмбеддинги и пишет в коллекцию `{collection_name}`. От 1 до 30 минут.")

    if not all_ok:
        st.error("Все сервисы должны быть доступны для индексации.")

    if st.button("✅ Индексировать метаданные", disabled=not all_ok, type="primary", key="index_meta"):
        progress_bar = st.progress(0, text="Загрузка объектов из парсера...")
        status_text = st.empty()

        status_text.text("Получение объектов из парсера...")
        try:
            resp = httpx.get(f"{PARSER_SERVICE_URL}/parse/all", timeout=120.0)
            resp.raise_for_status()
            objects = resp.json()
        except Exception as e:
            st.error(f"Ошибка получения данных из парсера: {e}")
            st.stop()

        total = len(objects)
        st.info(f"Получено {total} объектов. Начинаем индексацию...")

        status_text.text("Создание коллекции в Qdrant...")
        indexer = QdrantIndexer()
        try:
            indexer.create_collection(collection_name)
        except Exception as e:
            st.error(f"Ошибка создания коллекции: {e}")
            indexer.close()
            st.stop()

        def update_progress(indexed: int, total: int):
            pct = indexed / total if total > 0 else 0
            progress_bar.progress(pct, text=f"Проиндексировано: {indexed}/{total}")

        status_text.text("Индексация...")
        try:
            stats = indexer.index_objects(
                objects=objects,
                collection_name=collection_name,
                config_name=config_name,
                progress_callback=update_progress,
            )
        except Exception as e:
            st.error(f"Ошибка индексации: {e}")
            indexer.close()
            st.stop()

        indexer.close()
        progress_bar.progress(1.0, text="Готово!")
        status_text.empty()
        st.success(
            f"Индексация завершена.\n\n"
            f"- Всего объектов: {stats.total_objects}\n"
            f"- Проиндексировано: {stats.indexed}\n"
            f"- Ошибок: {stats.errors}"
        )


with tab_bsl:
    st.subheader("Индексация BSL-кода конфигурации")
    st.markdown(
        "Индексирует файлы модулей (`.bsl`) в Qdrant, разбивая каждый файл на чанки "
        "по процедурам/функциям. Позволяет MCP-агенту искать логику бизнес-процессов по коду."
    )

    bsl_col_a, bsl_col_b = st.columns(2)
    bsl_modules_dir = bsl_col_a.text_input(
        "Путь к папке с .bsl файлами",
        value="/app/modules",
        help="Путь внутри контейнера loader. Примонтируйте папку parsed_metadata/modules "
             "через docker-compose.yml → loader → volumes.",
    )
    bsl_collection = bsl_col_b.text_input(
        "Коллекция для BSL-кода",
        value=DEFAULT_CODE_COLLECTION,
        help="Имя коллекции Qdrant для индекса BSL.",
    )

    if qdrant_ok and embeddings_ok:
        try:
            from qdrant_client import QdrantClient as _QC
            _qc = _QC(host=QDRANT_HOST, port=QDRANT_PORT)
            _cols = [c.name for c in _qc.get_collections().collections]
            if bsl_collection in _cols:
                _info = _qc.get_collection(bsl_collection)
                st.warning(
                    f"Коллекция `{bsl_collection}` уже существует ({_info.points_count} чанков). "
                    "При индексации она будет пересоздана."
                )
            _qc.close()
        except Exception:
            pass
    else:
        st.error("Для индексации BSL нужны Qdrant + Embeddings.")

    bsl_disabled = not (qdrant_ok and embeddings_ok)
    if st.button(
        "✅ Индексировать BSL-код",
        disabled=bsl_disabled,
        type="primary",
        key="index_bsl",
        help=f"Читает .bsl файлы из `{bsl_modules_dir}`, разбивает на чанки и сохраняет в `{bsl_collection}`. От 5 до 60 минут.",
    ):
        bsl_progress = st.progress(0, text="Сбор .bsl файлов...")
        bsl_status = st.empty()

        bsl_indexer = BslIndexer()
        try:
            bsl_indexer.create_collection(bsl_collection)
        except Exception as e:
            st.error(f"Ошибка создания коллекции: {e}")
            bsl_indexer.close()
            st.stop()

        def bsl_progress_cb(files_done: int, total_files: int):
            pct = files_done / total_files if total_files > 0 else 0
            bsl_progress.progress(pct, text=f"Файлов: {files_done}/{total_files}")

        bsl_status.text("Индексация...")
        try:
            bsl_stats = bsl_indexer.index_directory(
                modules_dir=bsl_modules_dir,
                collection_name=bsl_collection,
                progress_callback=bsl_progress_cb,
            )
        except Exception as e:
            st.error(f"Ошибка индексации BSL: {e}")
            bsl_indexer.close()
            st.stop()

        bsl_indexer.close()
        bsl_progress.progress(1.0, text="Готово!")
        bsl_status.empty()
        st.success(
            f"Индексация BSL завершена.\n\n"
            f"- Файлов: {bsl_stats.total_files}\n"
            f"- Чанков: {bsl_stats.total_chunks}\n"
            f"- Проиндексировано: {bsl_stats.indexed}\n"
            f"- Ошибок: {bsl_stats.errors}"
        )
