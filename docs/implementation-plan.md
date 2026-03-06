# Тактический план реализации MCP_RAQ_1C

## 1. Архитектура

### 1.1. Схема компонентов

```
┌─────────────────────────────────────────────────────────────────┐
│                      Docker Compose                             │
│                                                                 │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────┐  │
│  │  XML Parser   │    │  Embedding   │    │     Qdrant       │  │
│  │  (Python)     │───>│  Service     │───>│   (векторная БД) │  │
│  │  FastAPI      │    │  (Python)    │    │   порт 6333      │  │
│  │  порт 8502    │    │  FastAPI     │    │                  │  │
│  └──────────────┘    │  порт 5000   │    └────────┬─────────┘  │
│         │            └──────────────┘             │             │
│         v                    ^                    │             │
│  ┌──────────────┐            │            ┌───────┴──────────┐  │
│  │   Loader      │───────────┘            │   MCP Server     │  │
│  │  (Streamlit)  │                        │  (TypeScript)    │  │
│  │  порт 8501    │──────────────────────> │  порт 8000       │  │
│  └──────────────┘   индексация в Qdrant   │  SSE + HTTP      │  │
│                                           └──────────────────┘  │
│                                                    ^            │
└────────────────────────────────────────────────────│────────────┘
                                                     │
                                          ┌──────────┴──────────┐
                                          │  AI-агенты:         │
                                          │  Cursor, VS Code    │
                                          │  Copilot, RooCode   │
                                          └─────────────────────┘
```

### 1.2. Поток данных

1. **XML -> Parsed JSON:** XML Parser читает файлы из `Конфигуратор/Prod/`, извлекает структурированные метаданные (Name, Synonym, тип объекта, реквизиты, табличные части, измерения, ресурсы, движения регистров).
2. **Parsed JSON -> Embeddings:** Loader отправляет текстовые описания в Embedding Service, получает dense-векторы (768d) + sparse-векторы (BM25).
3. **Embeddings -> Qdrant:** Loader загружает points с named vectors и payload в коллекцию Qdrant.
4. **Query -> RAG -> Response (двухэтапный):** MCP Server получает запрос от агента, выполняет hybrid search (prefetch dense по object_name + friendly_name + sparse BM25, fusion=RRF). Первый этап — возвращает **компактный список** (только имя + синоним + тип + score). Второй этап — LLM сама выбирает нужный объект и дозапрашивает полное описание через `get_object_details`. Такой подход не засоряет контекстное окно (идея из Infostart MCP v1.6).

### 1.3. Схема данных в Qdrant

**Конфигурация коллекции:**
```python
vectors_config = {
    "object_name": VectorParams(size=768, distance=Distance.COSINE, on_disk=True),
    "friendly_name": VectorParams(size=768, distance=Distance.COSINE, on_disk=True),
}
sparse_vectors_config = {
    "bm25": SparseVectorParams()
}
```

**Структура point:**
```json
{
    "id": "uuid-v4",
    "vector": {
        "object_name": [0.012, ...],
        "friendly_name": [0.034, ...],
        "bm25": {"indices": [...], "values": [...]}
    },
    "payload": {
        "object_name": "SS_ЗаказКлиента",
        "object_type": "Document",
        "object_type_ru": "Документ",
        "synonym": "Заказ клиента",
        "friendly_name": "Документ: Заказ клиента",
        "description": "Документ SS_ЗаказКлиента (Заказ клиента)\n\nРеквизиты:\n- Фирма (CatalogRef.Организации)...",
        "attributes": ["Фирма", "СтруктурнаяЕдиница", "..."],
        "tabular_sections": ["Товары", "..."],
        "register_records": ["AccumulationRegister.SS_УчетЗаказовКлиентов"],
        "hierarchical": false,
        "config_name": "MY_CONFIG"
    }
}
```

**Запрос hybrid search (RRF):**
```python
client.query_points(
    collection_name=collection_name,
    prefetch=[
        Prefetch(query=query_dense, using="object_name", limit=20),
        Prefetch(query=query_dense, using="friendly_name", limit=20),
        Prefetch(query=query_sparse, using="bm25", limit=20),
    ],
    query=FusionQuery(fusion=Fusion.RRF),
    query_filter=Filter(must=[
        FieldCondition(key="object_type", match=MatchAny(any=["Catalog", "Document"]))
    ]) if object_type_filter else None,
    limit=10,
    with_payload=True,
)
```

---

## 2. Стек технологий

| Компонент | Технология | Версия | Обоснование |
|-----------|-----------|--------|-------------|
| **Vector DB** | Qdrant | 1.13+ | Нативная поддержка named vectors, sparse vectors, prefetch+RRF fusion. Легкий Docker-образ, работает на CPU. |
| **XML Parser** | Python + lxml | lxml 5.x | lxml быстрее xml.etree в 5-10 раз, поддерживает namespaces, XPath. Критично для ~1950 XML файлов. |
| **Embedding model (dense)** | sergeyzh/BERTA | - | 768d, оптимизирован для русского языка, отличные retrieval-метрики (NDCG@10=0.816 на RiaNews). Поддерживает search_query/search_document prefixes. |
| **Embedding model (sparse)** | Qdrant/bm25 (fastembed) | fastembed 0.7+ | BM25 через fastembed — нулевая стоимость обучения, отлично для точного совпадения терминов 1С. |
| **Embedding Service** | Python + FastAPI + sentence-transformers | FastAPI 0.115+, ST 3.x | FastAPI — минимальный overhead, sentence-transformers — стандарт для inference. |
| **Loader** | Python + Streamlit | Streamlit 1.40+ | Быстрый UI без фронтенда. Один файл — весь интерфейс загрузки. |
| **MCP Server** | TypeScript + @modelcontextprotocol/sdk | SDK 1.x | Официальный SDK, нативная поддержка Streamable HTTP и SSE. |
| **MCP Server HTTP** | Express.js | 5.x | Рекомендуемый адаптер для MCP SDK. |
| **Docker** | Docker Compose | 3.8+ | Единая оркестрация всех сервисов. |

---

## 3. Структура проекта

```
MCP_RAQ_1C/
├── docker-compose.yml
├── .env.example
├── .env
├── .gitignore
├── README.md
├── CLAUDE.md
├── agents.md                       # инструкция для LLM-агентов (описание tools, примеры)
├── docs/
│   └── implementation-plan.md
│
├── parser/                          # XML Parser + API
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── config.py
│   ├── main.py                      # FastAPI app
│   ├── xml_parser.py                # ядро парсинга XML
│   ├── models.py                    # Pydantic-модели
│   ├── type_resolver.py             # маппинг типов 1С
│   └── tests/
│       ├── test_parser.py
│       └── fixtures/
│
├── embeddings/                      # Embedding Service
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── config.py
│   ├── embedding_service.py         # FastAPI: /embed, /embed-sparse, /health
│   └── tests/
│       └── test_embeddings.py
│
├── loader/                          # Loader + Indexer (Streamlit)
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── config.py
│   ├── loader.py                    # Streamlit UI
│   ├── indexer.py                   # батчевая индексация в Qdrant
│   └── tests/
│       └── test_indexer.py
│
├── mcp-server/                      # MCP Server (TypeScript)
│   ├── Dockerfile
│   ├── package.json
│   ├── tsconfig.json
│   ├── src/
│   │   ├── index.ts                 # Express + MCP transport
│   │   ├── server.ts                # MCP Server: регистрация tools
│   │   ├── tools/
│   │   │   ├── searchMetadata.ts    # tool: 1c_metadata_search (компактный вывод)
│   │   │   ├── getObjectDetails.ts  # tool: 1c_metadata_details (полное описание + TSV)
│   │   │   └── listObjectTypes.ts   # tool: 1c_metadata_types
│   │   ├── services/
│   │   │   ├── qdrantService.ts
│   │   │   └── embeddingService.ts
│   │   ├── types/
│   │   │   └── metadata.ts
│   │   └── config.ts
│   └── tests/
│       └── searchMetadata.test.ts
│
├── Конфигуратор/                    # исходные XML (в .gitignore)
│   └── Prod/
│
└── scripts/
    ├── start.sh
    └── stop.sh
```

---

## 4. Docker-инфраструктура

### 4.1. docker-compose.yml

```yaml
version: "3.8"

services:
  qdrant:
    image: qdrant/qdrant:v1.13.2
    ports:
      - "6333:6333"
      - "6334:6334"
    volumes:
      - qdrant_data:/qdrant/storage
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:6333/healthz"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped
    networks:
      - mcp-network
    deploy:
      resources:
        limits:
          memory: 2G

  embeddings:
    build:
      context: ./embeddings
      dockerfile: Dockerfile
    ports:
      - "5000:5000"
    volumes:
      - model_cache:/root/.cache/huggingface
    environment:
      - MODEL_NAME=sergeyzh/BERTA
      - MODEL_DIMENSIONS=768
      - HOST=0.0.0.0
      - PORT=5000
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 120s
    restart: unless-stopped
    networks:
      - mcp-network
    deploy:
      resources:
        limits:
          memory: 3G

  parser:
    build:
      context: ./parser
      dockerfile: Dockerfile
    ports:
      - "8502:8502"
    volumes:
      - ./Конфигуратор:/app/config_data:ro
    environment:
      - HOST=0.0.0.0
      - PORT=8502
      - CONFIG_PATH=/app/config_data/Prod
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8502/health"]
      interval: 15s
      timeout: 5s
      retries: 3
    restart: unless-stopped
    networks:
      - mcp-network
    deploy:
      resources:
        limits:
          memory: 512M

  loader:
    build:
      context: ./loader
      dockerfile: Dockerfile
    ports:
      - "8501:8501"
    environment:
      - QDRANT_HOST=qdrant
      - QDRANT_PORT=6333
      - EMBEDDING_SERVICE_URL=http://embeddings:5000
      - PARSER_SERVICE_URL=http://parser:8502
      - ROW_BATCH_SIZE=200
      - EMBEDDING_BATCH_SIZE=32
      - VECTOR_DIMENSIONS=768
    depends_on:
      qdrant:
        condition: service_healthy
      embeddings:
        condition: service_healthy
      parser:
        condition: service_healthy
    restart: unless-stopped
    networks:
      - mcp-network
    deploy:
      resources:
        limits:
          memory: 1G

  mcp-server:
    build:
      context: ./mcp-server
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - QDRANT_HOST=qdrant
      - QDRANT_PORT=6333
      - EMBEDDING_SERVICE_URL=http://embeddings:5000
      - DEFAULT_COLLECTION=metadata_1c
      - PORT=8000
      - HOST=0.0.0.0
      - SEARCH_LIMIT=10
    depends_on:
      qdrant:
        condition: service_healthy
      embeddings:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 15s
      timeout: 5s
      retries: 3
    restart: unless-stopped
    networks:
      - mcp-network
    deploy:
      resources:
        limits:
          memory: 512M

volumes:
  qdrant_data:
  model_cache:

networks:
  mcp-network:
    driver: bridge
```

### 4.2. .env.example

```env
# Qdrant
QDRANT_HOST=localhost
QDRANT_PORT=6333

# Embedding Service
MODEL_NAME=sergeyzh/BERTA
MODEL_DIMENSIONS=768

# Loader
ROW_BATCH_SIZE=200
EMBEDDING_BATCH_SIZE=32

# MCP Server
DEFAULT_COLLECTION=metadata_1c
SEARCH_LIMIT=10
MCP_SERVER_PORT=8000

# Parser
CONFIG_PATH=./Конфигуратор/Prod
```

---

## 5. Этапы реализации

### Этап 1: Инфраструктура и XML Parser (3-4 дня)

**Цель:** Docker-инфраструктура поднимается одной командой. XML-парсер извлекает структурированные метаданные из всех типов объектов 1С.

**Файлы:**
- `docker-compose.yml` (только qdrant + parser)
- `parser/Dockerfile`, `parser/requirements.txt`
- `parser/config.py`, `parser/models.py`
- `parser/xml_parser.py`, `parser/type_resolver.py`
- `parser/main.py`
- `parser/tests/test_parser.py`
- `.env.example`, `.gitignore`, `README.md`

**Зависимости:** Нет (первый этап).

**Критерий готовности:**
- `docker compose up qdrant parser` запускается без ошибок
- `GET /parse/all` возвращает JSON со всеми ~1950 объектами
- `GET /parse/Catalogs/EDIПровайдеры` возвращает корректные Name, Synonym, Attributes с типами, TabularSections
- Парсер обрабатывает все 6 типов: Catalog, Document, AccumulationRegister, InformationRegister, Enum, AccountingRegister
- Для Document извлекаются RegisterRecords; для Register — Dimensions, Resources, Attributes; для Enum — EnumValues

**Объём:** ~800 строк Python.

---

### Этап 2: Embedding Service (2-3 дня)

**Цель:** Сервис генерирует dense-эмбеддинги (BERTA, 768d) и sparse-эмбеддинги (BM25 через fastembed).

**Файлы:**
- `embeddings/Dockerfile`, `embeddings/requirements.txt`
- `embeddings/config.py`, `embeddings/embedding_service.py`
- `embeddings/tests/test_embeddings.py`

**Зависимости:** Этап 1 (Docker-инфраструктура).

**Критерий готовности:**
- `POST /embed` принимает `{"texts": ["Справочник: Номенклатура"], "prefix": "search_document"}` и возвращает массив 768d-векторов
- `POST /embed-sparse` возвращает sparse vectors `{indices, values}`
- Batch из 32 текстов на CPU < 5 сек
- Потребление RAM < 2.5 ГБ

**Объём:** ~300 строк Python.

---

### Этап 3: Loader + Индексация (3-4 дня)

**Цель:** Streamlit UI запускает полный pipeline: парсинг XML → эмбеддинги → коллекция в Qdrant → батчевая загрузка.

**Файлы:**
- `loader/Dockerfile`, `loader/requirements.txt`
- `loader/config.py`, `loader/indexer.py`, `loader/loader.py`
- `loader/tests/test_indexer.py`

**Зависимости:** Этапы 1, 2.

**Критерий готовности:**
- В Streamlit UI (порт 8501): кнопка "Индексировать" запускает полный pipeline
- В Qdrant Dashboard видна коллекция `metadata_1c` с ~1950 points
- Каждый point содержит 3 вектора (object_name, friendly_name, bm25) и полный payload
- Полная индексация < 30 минут на CPU

**Объём:** ~600 строк Python.

---

### Этап 4: MCP Server (3-4 дня)

**Цель:** TypeScript MCP-сервер предоставляет tools для поиска метаданных. Поддерживает Streamable HTTP и SSE.

**Файлы:**
- `mcp-server/Dockerfile`, `mcp-server/package.json`, `mcp-server/tsconfig.json`
- `mcp-server/src/config.ts`, `mcp-server/src/types/metadata.ts`
- `mcp-server/src/services/embeddingService.ts`, `mcp-server/src/services/qdrantService.ts`
- `mcp-server/src/tools/searchMetadata.ts`, `mcp-server/src/tools/getObjectDetails.ts`, `mcp-server/src/tools/listObjectTypes.ts`
- `mcp-server/src/server.ts`, `mcp-server/src/index.ts`

**Зависимости:** Этапы 1-3 (данные проиндексированы в Qdrant).

**Критерий готовности:**
- MCP Inspector подключается к `http://localhost:8000/mcp` и видит 3 tools с префиксом `1c_`
- `1c_metadata_search({query: "заказ клиента"})` возвращает **компактный список** (имя + синоним + тип) с SS_ЗаказКлиента в топе
- `1c_metadata_search({query: "остатки товаров", object_type: "AccumulationRegister"})` находит корректный регистр
- `1c_metadata_details({name: "SS_ЗаказКлиента"})` возвращает полное описание с реквизитами
- `1c_metadata_details({name: "НесуществующийОбъект"})` возвращает feedback с ближайшими совпадениями
- `1c_metadata_types()` возвращает статистику по типам
- Ответы доступны в двух форматах: structured JSON и плоский текст

**Объём:** ~700 строк TypeScript.

---

### Этап 5: Интеграция с IDE и тестирование (2-3 дня)

**Цель:** Рабочая интеграция с Cursor, VS Code Copilot, RooCode. Проверка на реальных use-cases.

**Файлы:**
- `docs/cursor-setup.md`, `docs/vscode-setup.md`, `docs/roocode-setup.md`
- `mcp-server/tests/searchMetadata.test.ts`
- Обновление `README.md`

**Зависимости:** Этап 4.

**Критерий готовности:**
- В Cursor: tools с префиксом `1c_` вызываются при вопросах о структуре 1С
- `agents.md` корректно подхватывается агентами — workflow "поиск → выбор → детали" работает
- Тест: "Напиши запрос чтобы получить остатки товаров" — агент сначала ищет через `1c_metadata_search`, затем дозапрашивает детали через `1c_metadata_details`, генерирует корректный запрос
- Тест: поиск по синониму "Контрагенты" находит справочник
- Multi-tenancy: заголовок `x-collection-name` переключает между коллекциями

**Объём:** ~300 строк.

---

### Этап 6: Оптимизация и полировка (2 дня)

**Цель:** Оптимизация производительности, edge cases, финальная документация.

**Задачи:**
- Настройка HNSW-параметров для CPU (m=16, ef_construct=100)
- Кеширование embeddings запросов в MCP Server (LRU cache)
- Graceful shutdown для всех сервисов
- Обработка составных типов данных
- `scripts/start.sh`, `scripts/stop.sh`
- Финальный `README.md`

---

## 6. Детальные задачи

### Этап 1: Инфраструктура и XML Parser

**Задача 1.1.** Создать базовую структуру проекта: `docker-compose.yml` (только qdrant), `.env.example`, `.gitignore`, `README.md`, пустые каталоги сервисов.

**Задача 1.2.** Создать `parser/models.py` — Pydantic-модели: `MetadataAttribute`, `TabularSection`, `MetadataObject`. Покрыть все 6 типов объектов.

**Задача 1.3.** Создать `parser/type_resolver.py` — маппинг типов 1С: `cfg:CatalogRef.X` → `СправочникСсылка.X`, `xs:string` → `Строка` и т.д. Включить StringQualifiers и NumberQualifiers.

**Задача 1.4.** Создать `parser/xml_parser.py` — класс `MetadataXMLParser`. Парсинг всех полей через lxml с namespaces. Тестировать на реальных файлах из `Конфигуратор/Prod/`.

**Задача 1.5.** Создать `parser/main.py` — FastAPI endpoints: `/health`, `/parse/{object_type}/{object_name}`, `/parse/all`, `/stats`. Добавить `Dockerfile`, `requirements.txt`, обновить `docker-compose.yml`.

**Задача 1.6.** Написать `parser/tests/test_parser.py` — fixtures из 3 XML, проверка Name, Synonym, атрибуты, типы, табличные части.

### Этап 2: Embedding Service

**Задача 2.1.** Создать `embeddings/embedding_service.py` — FastAPI с `sergeyzh/BERTA`. Endpoints: `POST /embed` (dense, с prefix), `GET /health`, `GET /model-info`. Batch до 32 текстов.

**Задача 2.2.** Добавить `POST /embed-sparse` — BM25 через fastembed. Fallback на TF-IDF если BM25 плохо работает с русским.

**Задача 2.3.** Написать тесты: размерность 768d, sparse indices/values, batch, русский текст.

### Этап 3: Loader + Индексация

**Задача 3.1.** Создать `loader/indexer.py` — класс `QdrantIndexer`: создание коллекции с named vectors + sparse, батчевый upsert points.

**Задача 3.2.** Создать `loader/loader.py` — Streamlit UI: имя коллекции, кнопка индексации, прогресс-бар, pipeline парсинг → эмбеддинги → Qdrant.

**Задача 3.3.** Протестировать полный pipeline: индексация всех ~1950 объектов, проверка в Qdrant Dashboard.

### Этап 4: MCP Server

**Задача 4.1.** Создать `package.json`, `tsconfig.json`, `config.ts`, `types/metadata.ts`.

**Задача 4.2.** Создать `services/embeddingService.ts` — HTTP-клиент к embedding service.

**Задача 4.3.** Создать `services/qdrantService.ts` — hybrid search с prefetch + RRF fusion, scroll по имени.

**Задача 4.4.** Создать `tools/searchMetadata.ts` — tool `1c_metadata_search` с фильтрацией по типу. **Компактный вывод:** возвращать только имя + синоним + тип + score (не полное описание). Два формата ответа: structured JSON + плоский текст для совместимости. Уникальный префикс `1c_` в имени tool для избежания конфликтов с другими MCP (ref: Microsoft Research про интерференцию агентских инструментов).

**Задача 4.5.** Создать `tools/getObjectDetails.ts` (`1c_metadata_details`) и `tools/listObjectTypes.ts` (`1c_metadata_types`). `1c_metadata_details` — возвращает полное описание объекта; поддержка TSV-формата для экономии токенов (ref: Antiloop/1c-llm-requests). Добавить feedback: если объект не найден, подсказать ближайшие совпадения.

**Задача 4.6.** Создать `server.ts` + `index.ts` — Express + MCP transport (Streamable HTTP на `/mcp`), multi-tenancy через `x-collection-name`.

**Задача 4.7.** Протестировать через MCP Inspector: все 3 tools, поиск по синониму, фильтрация по типу.

### Этап 5: Интеграция с IDE

**Задача 5.1.** Создать `agents.md` — универсальная инструкция для LLM-агентов: описание tools (имена с префиксом `1c_`, параметры, примеры вызовов), рекомендуемый workflow (сначала `1c_metadata_search` → выбрать → `1c_metadata_details`), подсказки по формированию запросов на языке 1С. Файл `agents.md` в корне проекта читают Cursor, RooCode, Cline и другие агенты (ref: Infostart MCP v1.6).

**Задача 5.2.** Создать `docs/cursor-setup.md` — инструкция + `.cursor/mcp.json`. Создать `docs/vscode-setup.md` и `docs/roocode-setup.md`.

**Задача 5.3.** Обновить `README.md` и `CLAUDE.md`.

### Этап 6: Оптимизация

**Задача 6.1.** LRU-кеш в MCP Server, HNSW-настройки в Loader, memmap для Qdrant.

**Задача 6.2.** Edge cases в парсере: составные типы, пустые Synonym, DefinedType, ChartsOfCharacteristicTypes.

**Задача 6.3.** Скрипты `start.sh`/`stop.sh`, graceful shutdown.

---

## 7. Идеи из референсных проектов

### Infostart MCP v1.6 («Вайб-кодинг в 1С»)
Коммерческий продукт, наиболее зрелая реализация. Ключевые идеи, заимствованные в наш план:
- **Компактный вывод** — поиск возвращает только имя + синоним, LLM сама дозапрашивает детали. Не засоряет контекстное окно.
- **Два формата ответа** — structured JSON (для Cursor) + плоский текст (обратная совместимость).
- **`agents.md` в корне** — универсальный файл инструкций, который читают все современные агенты.
- **Уникальные имена tools** с префиксами — избежание конфликтов при подключении нескольких MCP (ref: Microsoft Research про интерференцию).
- **SSE + Streamable HTTP** — оба транспорта обязательны (Gemini CLI работает только по SSE).
- **Гибридный поиск** — dense + sparse/BM25 по ключевым словам всего тела описания.

### Antiloop/1c-llm-requests
Расширение 1С для выполнения запросов через HTTP-сервис. Ключевые идеи:
- **TSV вместо JSON** — экономия токенов при передаче табличных результатов. Применяем в `1c_metadata_details` для вывода списков реквизитов.
- **Skill/инструкция для LLM** — детальный prompt, минимизирующий галлюцинации. Реализуем через `agents.md`.
- **Feedback-loop** — если запрос невалиден или объект не найден, сервер подсказывает ближайшие совпадения. Реализуем в `1c_metadata_details`.
- **Подход "сначала метаданные, потом запрос"** — агент читает структуру через MCP и только потом генерирует код, что даёт корректный результат с первой попытки.

### FSerg/mcp-1c-v1
- Использует EPF-выгрузку в CSV+Markdown. Мы упрощаем: парсим XML напрямую.
- Мультивекторный подход (object_name + friendly_name) — заимствован в наш план.

### alkoleft/mcp-bsl-context
- BSL Language Server для проверки синтаксиса — можно добавить как опциональный сервис в будущем (этап 6+).

---

## 8. Ключевые архитектурные решения

### Почему XML Parser как отдельный сервис?
Данные уже доступны как XML (стандартная выгрузка конфигуратора). Отдельный сервис: (a) можно вызывать парсинг повторно без переиндексации; (b) API для отладки конкретного объекта; (c) независимое масштабирование.

### Почему BERTA вместо all-MiniLM-L6-v2?
Use-case — русскоязычные метаданные 1С. BERTA: 768d, специализация на русском, NDCG@10=0.816. Критично для различения "Запасы" vs "ЗапасыИЗатраты".

### Почему sparse vectors (BM25) вместо только dense?
Технические имена 1С (SS_ЗаказКлиента, EDIПровайдеры) терминологически уникальны. Dense-поиск может промахнуться по точному имени, BM25 его гарантированно найдёт. RRF объединяет лучшее.

### Почему TypeScript MCP вместо Python fastmcp?
Официальный SDK от Anthropic, нативная типобезопасность для MCP-протокола, лучшая поддержка Streamable HTTP transport.

---

## 9. Риски и митигация

| Риск | Вероятность | Митигация |
|------|-------------|-----------|
| BERTA не вмещается в 3 ГБ RAM | Низкая | Fallback на `intfloat/multilingual-e5-small` (384d, ~400 МБ) |
| fastembed BM25 плохо с русским | Средняя | Fallback на TF-IDF sparse encoder (задача 2.2) |
| Индексация > 30 мин на CPU | Средняя | Увеличить EMBEDDING_BATCH_SIZE, сократить description |
| XML-структура нестандартна для некоторых типов | Средняя | Тесты на всех типах (задача 1.6), graceful fallback |
| Конфликт имён tools с другими MCP | Низкая | Префикс `1c_` в именах tools (ref: Microsoft Research) |

---

## 10. Следующий шаг

**Начать с Задачи 1.1:** Создать базовую структуру проекта.

Конкретный промпт для Claude Code:

> Создай базовую структуру проекта MCP_RAQ_1C:
> 1. `docker-compose.yml` с сервисом `qdrant` (образ `qdrant/qdrant:v1.13.2`, порты 6333:6333, volume `qdrant_data`, healthcheck, network `mcp-network`)
> 2. `.env.example` с переменными: QDRANT_HOST, QDRANT_PORT, MODEL_NAME, MODEL_DIMENSIONS, ROW_BATCH_SIZE, EMBEDDING_BATCH_SIZE, DEFAULT_COLLECTION, SEARCH_LIMIT, MCP_SERVER_PORT, CONFIG_PATH
> 3. `.gitignore` — исключить: `Конфигуратор/`, `node_modules/`, `__pycache__/`, `.env`, `qdrant_data/`, `dist/`, `*.pyc`, `model_cache/`
> 4. Обновить `README.md` — описание проекта, архитектура, быстрый старт
> 5. Создать пустые каталоги: `parser/`, `embeddings/`, `loader/`, `mcp-server/src/`, `docs/`, `scripts/`
> Проверь что `docker compose up qdrant` запускается.
