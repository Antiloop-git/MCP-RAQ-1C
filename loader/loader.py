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
from indexer import (
    QdrantIndexer,
    BslIndexer,
    ContentIndexer,
    DEFAULT_CODE_COLLECTION,
    DEFAULT_HELP_COLLECTION,
    DEFAULT_BSP_COLLECTION,
    DEFAULT_TEMPLATES_COLLECTION,
)


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


def show_collection_status(col_name: str) -> None:
    """Показывает статус коллекции Qdrant: количество точек или 'не создана'."""
    if not qdrant_ok:
        return
    try:
        from qdrant_client import QdrantClient as _QC2
        _qc2 = _QC2(host=QDRANT_HOST, port=QDRANT_PORT)
        _cols2 = [c.name for c in _qc2.get_collections().collections]
        if col_name in _cols2:
            _info2 = _qc2.get_collection(col_name)
            st.success(f"Коллекция `{col_name}`: **{_info2.points_count}** точек проиндексировано.")
        else:
            st.info(f"Коллекция `{col_name}` ещё не создана.")
        _qc2.close()
    except Exception:
        pass

# ============================================================
# Вкладки
# ============================================================
tab_meta, tab_bsl, tab_help, tab_bsp, tab_tpl = st.tabs([
    "🗂️ Метаданные", "📝 BSL-код", "📚 Справка платформы", "📖 Справка БСП", "🧩 Шаблоны кода",
])

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


# ============================================================
# Вкладка: Справка платформы (#15)
# ============================================================
with tab_help:
    st.subheader("Индексация справки платформы 1С:Предприятие")
    st.markdown(
        "Парсит HBK-файл (zip-архив с HTML-документацией платформы 1С) и индексирует "
        "в Qdrant. Позволяет MCP-агенту искать по документации платформы."
    )

    help_collection = st.text_input(
        "Коллекция для справки платформы",
        value=DEFAULT_HELP_COLLECTION,
        key="help_collection",
    )

    show_collection_status(help_collection)

    help_ready = parser_ok and qdrant_ok and embeddings_ok
    if not help_ready:
        st.error("Нужны Parser + Qdrant + Embeddings.")

    if st.button(
        "✅ Индексировать справку платформы",
        disabled=not help_ready,
        type="primary",
        key="index_help",
        help="Вызывает Parser API /parse-hbk, получает чанки и индексирует в Qdrant.",
    ):
        help_progress = st.progress(0, text="Парсинг HBK-файла...")
        help_status = st.empty()

        help_status.text("Получение чанков из парсера (POST /parse-hbk)...")
        try:
            resp = httpx.post(f"{PARSER_SERVICE_URL}/parse-hbk", timeout=300.0)
            resp.raise_for_status()
            data = resp.json()
            chunks = data["chunks"]
        except Exception as e:
            st.error(f"Ошибка парсинга HBK: {e}")
            st.stop()

        st.info(f"Получено {len(chunks)} чанков. Индексация...")
        help_progress.progress(0.3, text=f"Чанков: {len(chunks)}. Создание коллекции...")

        cidx = ContentIndexer()
        try:
            cidx.create_collection(help_collection)
        except Exception as e:
            st.error(f"Ошибка создания коллекции: {e}")
            cidx.close()
            st.stop()

        def help_cb(indexed, total):
            pct = 0.3 + 0.7 * (indexed / total if total > 0 else 0)
            help_progress.progress(pct, text=f"Проиндексировано: {indexed}/{total}")

        try:
            stats = cidx.index_chunks(chunks, help_collection, text_field="content", progress_callback=help_cb)
        except Exception as e:
            st.error(f"Ошибка индексации: {e}")
            cidx.close()
            st.stop()

        cidx.close()
        help_progress.progress(1.0, text="Готово!")
        help_status.empty()
        st.success(
            f"Справка платформы проиндексирована.\n\n"
            f"- Чанков: {stats.total_objects}\n"
            f"- Проиндексировано: {stats.indexed}\n"
            f"- Ошибок: {stats.errors}"
        )


# ============================================================
# Вкладка: Справка БСП (#16)
# ============================================================
with tab_bsp:
    st.subheader("Индексация справки БСП")
    st.markdown(
        "Парсит HTML-файлы справки Библиотеки стандартных подсистем (БСП) из "
        "XML-выгрузки конфигурации и индексирует в Qdrant."
    )

    bsp_collection = st.text_input(
        "Коллекция для справки БСП",
        value=DEFAULT_BSP_COLLECTION,
        key="bsp_collection",
    )

    show_collection_status(bsp_collection)

    bsp_ready = parser_ok and qdrant_ok and embeddings_ok
    if not bsp_ready:
        st.error("Нужны Parser + Qdrant + Embeddings.")

    if st.button(
        "✅ Индексировать справку БСП",
        disabled=not bsp_ready,
        type="primary",
        key="index_bsp",
        help="Вызывает Parser API /parse-bsp-help, получает чанки и индексирует в Qdrant.",
    ):
        bsp_progress = st.progress(0, text="Парсинг справки БСП...")
        bsp_status = st.empty()

        bsp_status.text("Получение чанков из парсера (POST /parse-bsp-help)...")
        try:
            resp = httpx.post(f"{PARSER_SERVICE_URL}/parse-bsp-help", timeout=300.0)
            resp.raise_for_status()
            data = resp.json()
            chunks = data["chunks"]
        except Exception as e:
            st.error(f"Ошибка парсинга БСП: {e}")
            st.stop()

        st.info(f"Получено {len(chunks)} чанков. Индексация...")
        bsp_progress.progress(0.3, text=f"Чанков: {len(chunks)}. Создание коллекции...")

        cidx = ContentIndexer()
        try:
            cidx.create_collection(bsp_collection)
        except Exception as e:
            st.error(f"Ошибка создания коллекции: {e}")
            cidx.close()
            st.stop()

        def bsp_cb(indexed, total):
            pct = 0.3 + 0.7 * (indexed / total if total > 0 else 0)
            bsp_progress.progress(pct, text=f"Проиндексировано: {indexed}/{total}")

        try:
            stats = cidx.index_chunks(chunks, bsp_collection, text_field="content", progress_callback=bsp_cb)
        except Exception as e:
            st.error(f"Ошибка индексации: {e}")
            cidx.close()
            st.stop()

        cidx.close()
        bsp_progress.progress(1.0, text="Готово!")
        bsp_status.empty()
        st.success(
            f"Справка БСП проиндексирована.\n\n"
            f"- Чанков: {stats.total_objects}\n"
            f"- Проиндексировано: {stats.indexed}\n"
            f"- Ошибок: {stats.errors}"
        )


# ============================================================
# Вкладка: Шаблоны кода (#20)
# ============================================================
with tab_tpl:
    st.subheader("Индексация шаблонов кода 1С")
    st.markdown(
        "Загружает JSON-файл с шаблонами/сниппетами кода 1С и индексирует в Qdrant. "
        "Позволяет MCP-агенту находить готовые примеры кода по запросу."
    )

    tpl_collection = st.text_input(
        "Коллекция для шаблонов",
        value=DEFAULT_TEMPLATES_COLLECTION,
        key="tpl_collection",
    )

    show_collection_status(tpl_collection)

    tpl_ready = qdrant_ok and embeddings_ok
    if not tpl_ready:
        st.error("Нужны Qdrant + Embeddings.")

    uploaded_file = st.file_uploader(
        "JSON-файл с шаблонами",
        type=["json"],
        help='Массив объектов: [{"title": "...", "category": "...", "tags": [...], "description": "...", "code": "..."}]',
    )

    if st.button(
        "✅ Индексировать шаблоны",
        disabled=not (tpl_ready and uploaded_file is not None),
        type="primary",
        key="index_tpl",
    ):
        import json

        tpl_progress = st.progress(0, text="Чтение JSON...")
        tpl_status = st.empty()

        try:
            templates = json.loads(uploaded_file.read())
        except Exception as e:
            st.error(f"Ошибка чтения JSON: {e}")
            st.stop()

        if not isinstance(templates, list):
            st.error("JSON должен быть массивом объектов.")
            st.stop()

        # Формируем text_field: объединяем title + description + code для эмбеддинга
        for t in templates:
            t["content"] = f"{t.get('title', '')} {t.get('description', '')} {t.get('code', '')}"

        st.info(f"Загружено {len(templates)} шаблонов. Индексация...")
        tpl_progress.progress(0.2, text=f"Шаблонов: {len(templates)}. Создание коллекции...")

        cidx = ContentIndexer()
        try:
            cidx.create_collection(tpl_collection)
        except Exception as e:
            st.error(f"Ошибка создания коллекции: {e}")
            cidx.close()
            st.stop()

        def tpl_cb(indexed, total):
            pct = 0.2 + 0.8 * (indexed / total if total > 0 else 0)
            tpl_progress.progress(pct, text=f"Проиндексировано: {indexed}/{total}")

        try:
            stats = cidx.index_chunks(templates, tpl_collection, text_field="content", progress_callback=tpl_cb)
        except Exception as e:
            st.error(f"Ошибка индексации: {e}")
            cidx.close()
            st.stop()

        cidx.close()
        tpl_progress.progress(1.0, text="Готово!")
        tpl_status.empty()
        st.success(
            f"Шаблоны проиндексированы.\n\n"
            f"- Шаблонов: {stats.total_objects}\n"
            f"- Проиндексировано: {stats.indexed}\n"
            f"- Ошибок: {stats.errors}"
        )
