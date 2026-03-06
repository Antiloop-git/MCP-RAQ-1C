# Настройка MCP RAQ 1C для Cursor

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

## 3. Подключение к Cursor

Создайте файл `.cursor/mcp.json` в корне вашего 1С-проекта:

```json
{
  "mcpServers": {
    "1c-metadata": {
      "url": "http://localhost:8000/mcp"
    }
  }
}
```

## 4. Проверка

В Cursor откройте чат и спросите:
> Найди структуру документа "Заказ клиента"

Cursor должен вызвать `1c_metadata_search`, затем `1c_metadata_details`.

## 5. agents.md

Скопируйте `docs/agents.md` из MCP_RAQ_1C в корень вашего 1С-проекта — Cursor использует его как инструкцию для работы с tools.

## Multi-tenancy

Если у вас несколько конфигураций, укажите заголовок `x-collection-name` в настройках MCP (пока Cursor не поддерживает кастомные заголовки — используйте значение `DEFAULT_COLLECTION` в `.env`).
