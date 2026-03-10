# Гид изменений: MCP-сервер v0.2 → v0.3

## Что меняется

### Новые файлы

| Файл | Назначение |
|------|------------|
| `mcp-server/src/services/graphService.ts` | Сервис графа зависимостей (scroll Qdrant → in-memory Map) |
| `mcp-server/src/services/subsystemService.ts` | Сервис подсистем (scroll Qdrant → in-memory tree) |
| `mcp-server/src/tools/dependencies.ts` | MCP-инструмент `1c_dependencies` |
| `mcp-server/src/tools/subsystems.ts` | MCP-инструмент `1c_subsystems` |
| `docker-compose.comol.yml` | Docker Compose для 4 comol-серверов |
| `docs/comol-setup.md` | Инструкция настройки comol-серверов |

### Изменяемые файлы

| Файл | Что меняется |
|------|-------------|
| `mcp-server/src/server.ts` | +2 импорта, +2 вызова register*, версия → 0.3.0 |
| `docs/agents.md` | Полная переработка: все 9 инструментов + workflow |
| `docs/tools-map.md` | Статус dependencies и subsystems → «Реализовано», раздел comol |
| `.env.example` | +переменные для comol LICENSE_KEY_* |

### Файлы БЕЗ изменений

- `mcp-server/src/services/qdrantService.ts` — используем существующий scroll API
- `mcp-server/src/services/embeddingService.ts` — не нужен для dependencies/subsystems
- `mcp-server/src/config.ts` — новые инструменты не требуют конфигурации
- `mcp-server/src/tools/odataQuery.ts` и другие OData-инструменты — без изменений
- `docker-compose.yml` — основной compose без изменений (comol в отдельном файле)
- `parser/` — парсер не трогаем
- `loader/` — загрузчик не трогаем

## Архитектура изменений

```
mcp-server/src/
├── server.ts              ← ИЗМЕНЯЕТСЯ (+2 инструмента, версия 0.3.0)
├── config.ts              ← без изменений
├── services/
│   ├── qdrantService.ts   ← без изменений (scroll API уже есть)
│   ├── graphService.ts    ← НОВЫЙ (граф зависимостей)
│   └── subsystemService.ts← НОВЫЙ (дерево подсистем)
└── tools/
    ├── searchMetadata.ts  ← без изменений
    ├── getObjectDetails.ts← без изменений
    ├── listObjectTypes.ts ← без изменений
    ├── searchCode.ts      ← без изменений
    ├── odataQuery.ts      ← без изменений
    ├── registerBalances.ts← без изменений
    ├── registerMovements.ts← без изменений
    ├── dependencies.ts    ← НОВЫЙ
    └── subsystems.ts      ← НОВЫЙ
```

## Паттерны для новых файлов

### graphService.ts — паттерн

Использует тот же подход, что `getObjectTypeStats` в `qdrantService.ts`:
- `client.scroll()` с `limit: 250` и `with_payload: ["object_name", "register_records"]`
- Фильтр: `{ must: [{ key: "object_type", match: { value: "Document" } }] }`
- Пагинация через `next_page_offset`
- Lazy loading: загрузка при первом вызове, потом кэш

### subsystemService.ts — паттерн

Аналогично:
- `client.scroll()` с `with_payload: ["object_name", "synonym", "content", "child_subsystems"]`
- Фильтр: `{ must: [{ key: "object_type", match: { value: "Subsystem" } }] }`
- Построение обратного индекса `objectToSubsystems`

### dependencies.ts / subsystems.ts — паттерн

Копируем структуру из `searchMetadata.ts`:
- `export function registerXxx(server: McpServer, getCollection: () => string)`
- `server.tool(name, description, zodSchema, handler)`
- Описания на русском
- `try/catch` → `isError: true`
- Текстовый вывод (TSV или нумерованный список)

## Порядок разработки

```
Задачи 1+3 (параллельно)     Задачи 2+4        Задача 5       Задачи 6-9      Задача 10
┌──────────────────────┐   ┌─────────────┐   ┌───────────┐   ┌──────────┐   ┌──────────┐
│ graphService.ts      │──▶│ dependencies│──▶│ server.ts │──▶│ docs +   │──▶│ build +  │
│ subsystemService.ts  │──▶│ subsystems  │──▶│ v0.3.0    │──▶│ comol    │──▶│ test     │
└──────────────────────┘   └─────────────┘   └───────────┘   └──────────┘   └──────────┘
```

## Чеклист верификации

- [ ] `cd mcp-server && npm run build` — 0 ошибок
- [ ] `docker compose up mcp-server --build -d` — контейнер стартует
- [ ] `curl http://localhost:8000/health` → `{"status":"ok"}`
- [ ] `1c_dependencies` name="УчетПартий" direction="reverse" → список документов
- [ ] `1c_subsystems` action="tree" → 49 подсистем
- [ ] `1c_subsystems` action="find" name="Номенклатура" → подсистемы
- [ ] `docs/agents.md` описывает все 9 инструментов
- [ ] `docker compose -f docker-compose.comol.yml up -d` → comol-серверы стартуют (если настроены)
