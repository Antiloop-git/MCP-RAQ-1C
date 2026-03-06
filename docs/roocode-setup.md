# Настройка MCP RAQ 1C для RooCode (Cline)

## 1. Запуск сервера

```bash
cd MCP_RAQ_1C
docker compose up -d
```

## 2. Индексация

Откройте http://localhost:8501 и нажмите "Индексировать".

## 3. Подключение

В настройках RooCode (Cline) добавьте MCP-сервер:

- **Transport:** SSE
- **URL:** `http://localhost:8000/sse`

Либо добавьте в файл конфигурации MCP (`~/.config/roocode/mcp_settings.json` или через UI):

```json
{
  "mcpServers": {
    "1c-metadata": {
      "transport": "sse",
      "url": "http://localhost:8000/sse"
    }
  }
}
```

## 4. agents.md

RooCode/Cline автоматически читает `agents.md` из корня проекта. Скопируйте этот файл в корень вашего 1С-проекта.

## 5. Проверка

Спросите RooCode:
> Покажи структуру справочника Номенклатура

Агент должен вызвать `1c_metadata_search`, а затем `1c_metadata_details`.
