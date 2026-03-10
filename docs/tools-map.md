# Карта MCP-инструментов v0.3.0

## Инфраструктура

| Компонент | Технология | Роль | Порт |
|---|---|---|---|
| **Parser** | Python / FastAPI | Читает XML-выгрузку конфигурации 1С, отдаёт объекты по REST | 8001 |
| **Embeddings** | `sergeyzh/BERTA` (768d) | Векторизует описания и BSL-код; dense + sparse (BM25) | 5050 |
| **Qdrant** | v1.13.2 | Векторная БД: коллекции `metadata_1c` и `code_1c` | 6333 |
| **Loader** | Python / Streamlit | UI индексации: «Метаданные» и «BSL-код» | 8501 |
| **MCP Server** | TypeScript / Node.js | HTTP MCP-сервер (Streamable HTTP + SSE), 9 инструментов | 8000 |

```bash
docker compose up -d                    # основной стек
docker compose -f docker-compose.comol.yml up -d  # comol-серверы (опционально)
```

---

## Наши инструменты (MCP Server :8000) — 9 шт.

### Метаданные (4)

| Инструмент | Описание | Статус |
|---|---|---|
| `1c_metadata_search` | Гибридный поиск объектов (BERTA + BM25 + RRF) | ✅ Работает |
| `1c_metadata_details` | Структура объекта: реквизиты, ТЧ, движения | ✅ Работает |
| `1c_metadata_types` | Статистика по типам объектов | ✅ Работает |
| `1c_code_search` | Поиск по BSL-коду: процедуры, функции | ✅ Работает |

### Граф и навигация (2) — NEW в v0.3.0

| Инструмент | Описание | Статус |
|---|---|---|
| `1c_dependencies` | Граф зависимостей: документ↔регистры | ✅ Реализовано |
| `1c_subsystems` | Навигация по подсистемам (дерево, содержимое, поиск) | ✅ Реализовано |

### OData — живые данные (3)

| Инструмент | Описание | Статус |
|---|---|---|
| `1c_odata_query` | Универсальный OData-запрос к 1С | ✅ Работает (при ODATA_URL) |
| `1c_register_balances` | Остатки/обороты регистров | ✅ Работает (при ODATA_URL) |
| `1c_register_movements` | Движения регистров за период | ✅ Работает (при ODATA_URL) |

---

## Внешние серверы (comol/DISTAR)

Запускаются через `docker-compose.comol.yml`. Лицензионные ключи в `.env`.

| Сервер | Образ | Порт | Описание | Статус |
|---|---|---|---|---|
| HelpSearchServer | `comol/1c_help_mcp` | 8003 | Справка по платформе 1С | ⬜ Настроить |
| TemplatesSearchServer | `comol/template-search-mcp` | 8004 | Шаблоны кода + веб-редактор | ⬜ Настроить |
| SyntaxCheckServer | `comol/1c_syntaxcheck_mcp` | 8002 | Проверка синтаксиса BSL LS | ⬜ Настроить |
| SSLSearchServer | `comol/mcp_ssl_server` | 8008 | Справка по БСП | ⬜ Настроить |

Не подключаем (причины):
- `1c_code_metadata_mcp` — дублирует наши `1c_metadata_search` + `1c_code_search`
- `1c_graph_metadata` — тяжёлый (Neo4j + 2GB RAM), дублирует `1c_dependencies`
- `1c-code-checker` — требует партнёрский токен
- `1c_forms` — отложен на будущее

---

## Матрица покрытия

| Задача | Аналитик | Разработчик | Инструмент |
|---|:---:|:---:|---|
| Найти объект по описанию | ✅ | ✅ | `1c_metadata_search` |
| Понять структуру объекта | ✅ | ✅ | `1c_metadata_details` |
| Узнать зависимости объекта | — | ✅ | `1c_dependencies` |
| Найти объект в подсистемах | ✅ | ✅ | `1c_subsystems` |
| Найти код бизнес-логики | — | ✅ | `1c_code_search` |
| Получить данные из 1С | ✅ | — | `1c_odata_query` |
| Остатки/обороты регистров | ✅ | — | `1c_register_balances` |
| Справка по платформе | — | ✅ | comol HelpSearch |
| Проверить синтаксис BSL | — | ✅ | comol SyntaxCheck |
| Шаблоны кода | — | ✅ | comol Templates |
