# Настройка MCP RAQ 1C для VS Code (GitHub Copilot)

## 1. Запуск сервера

```bash
cd MCP_RAQ_1C
docker compose up -d
```

## 2. Индексация

Откройте http://localhost:8501 и нажмите "Индексировать".

## 3. Подключение

Создайте файл `.vscode/mcp.json` в корне вашего проекта:

```json
{
  "servers": {
    "1c-metadata": {
      "type": "sse",
      "url": "http://localhost:8000/sse"
    }
  }
}
```

Или через `settings.json`:

```json
{
  "github.copilot.chat.mcp.servers": {
    "1c-metadata": {
      "type": "sse",
      "url": "http://localhost:8000/sse"
    }
  }
}
```

## 4. Проверка

В Copilot Chat (Agent mode) спросите:
> @1c-metadata Найди регистр накопления для остатков товаров

## 5. agents.md

Скопируйте `agents.md` в корень 1С-проекта для контекста.
