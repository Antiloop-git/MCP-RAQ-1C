# Настройка MCP RAQ 1C для Claude Code

## 1. Запуск сервера

```bash
cd MCP_RAQ_1C
docker compose up -d
```

Дождитесь запуска всех сервисов. Проверка:
```bash
curl http://localhost:8000/health
```

## 2. Индексация метаданных

Откройте http://localhost:8501 (Loader UI) и нажмите "Индексировать".

## 3. Подключение к Claude Code

Добавьте MCP-сервер в конфигурацию Claude Code:

```bash
claude mcp add 1c-metadata --transport sse http://localhost:8000/sse
```

Или вручную — добавьте в `~/.claude.json` (секция `mcpServers`):

```json
{
  "mcpServers": {
    "1c-metadata": {
      "type": "sse",
      "url": "http://localhost:8000/sse"
    }
  }
}
```

Для подключения только в конкретном проекте используйте файл `.mcp.json` в корне проекта:

```json
{
  "mcpServers": {
    "1c-metadata": {
      "type": "sse",
      "url": "http://localhost:8000/sse"
    }
  }
}
```

## 4. Проверка

В Claude Code спросите:
> Найди структуру документа "Заказ клиента"

Claude должен вызвать `1c_metadata_search`, затем `1c_metadata_details`.

Для проверки доступных tools:
```bash
claude mcp list
```

## 5. agents.md

Скопируйте `docs/agents.md` из MCP_RAQ_1C в корень вашего 1С-проекта — Claude Code использует его как инструкцию для работы с MCP tools.

## 6. Скилл `1c-queries` — запросы к живой базе 1С

В репозитории есть готовый скилл для Claude Code (`.claude/skills/1c-queries/`), который позволяет выполнять запросы к живой базе 1С через HTTP-сервис.

**Связка MCP + скилл даёт полный цикл:**
1. Через MCP (`1c_metadata_search` / `1c_metadata_details`) — узнать структуру объектов
2. Через скилл `1c-queries` — выполнить запрос к реальной базе и получить данные

### Настройка

Для работы скилла нужен HTTP-сервис на стороне 1С (например, [1c-llm-requests](https://github.com/Antiloop-git/1c-llm-requests)). Настройте переменные в `.env`:

```env
QUERY_1C_URL=http://localhost/base/hs/llm-requests/query
QUERY_1C_AUTH=Base64EncodedLogin:Password
```

### Использование

Claude Code автоматически подхватывает скилл. Просто попросите:
> Покажи все заказы клиентов за сегодня с суммой больше 100 000

Claude:
1. Вызовет `1c_metadata_search("заказ клиента")` → найдёт документ
2. Вызовет `1c_metadata_details` → получит реквизиты и типы
3. Сформирует запрос на языке 1С
4. Выполнит его через скилл `1c-queries` → вернёт результат в TSV

## Multi-tenancy

Если у вас несколько конфигураций, задайте нужную коллекцию через переменную `DEFAULT_COLLECTION` в `.env`.
