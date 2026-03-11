# Подключение MCP-сервера 1С к IDE

MCP-сервер доступен по адресу: `http://10.1.231.253/mcp`

## Cursor

Файл `.cursor/mcp.json` в корне проекта (или `~/.cursor/mcp.json` глобально):

```json
{
  "mcpServers": {
    "1c-metadata": {
      "url": "http://10.1.231.253/mcp"
    }
  }
}
```

После сохранения: **Cursor Settings → MCP** — убедиться, что сервер отображается со статусом «Connected».

## VS Code + GitHub Copilot

Файл `.vscode/mcp.json` в корне проекта:

```json
{
  "servers": {
    "1c-metadata": {
      "type": "http",
      "url": "http://10.1.231.253/mcp"
    }
  }
}
```

Или глобально в `settings.json`:

```json
{
  "mcp": {
    "servers": {
      "1c-metadata": {
        "type": "http",
        "url": "http://10.1.231.253/mcp"
      }
    }
  }
}
```

Требуется: VS Code ≥ 1.99, расширение GitHub Copilot с поддержкой MCP (Agent mode).

## RooCode

В настройках RooCode → **MCP Servers → Add Server**:

```json
{
  "mcpServers": {
    "1c-metadata": {
      "url": "http://10.1.231.253/mcp"
    }
  }
}
```

## Claude Code (CLI)

Файл `.claude/settings.json` в корне проекта:

```json
{
  "mcpServers": {
    "1c-metadata": {
      "type": "url",
      "url": "http://10.1.231.253/mcp"
    }
  }
}
```

## Проверка работоспособности

1. Health-check: `curl http://10.1.231.253/health` → `{"status":"ok"}`
2. В IDE: попробуйте запрос к агенту: *«найди справочник Номенклатура в 1С»*
3. Агент должен вызвать `1c_metadata_search` и вернуть результат

## 13 доступных инструментов

| Инструмент | Описание |
|------------|----------|
| `1c_metadata_search` | Поиск объектов метаданных по текстовому запросу |
| `1c_metadata_details` | Полная структура объекта (реквизиты, ТЧ, движения) |
| `1c_metadata_types` | Статистика по типам объектов |
| `1c_code_search` | Поиск по BSL-коду модулей |
| `1c_dependencies` | Граф зависимостей документ↔регистры |
| `1c_subsystems` | Навигация по подсистемам |
| `1c_odata_query` | Запрос к живой базе 1С через OData |
| `1c_register_balances` | Остатки/обороты регистров накопления |
| `1c_register_movements` | Движения регистров за период |
| `1c_syntax_check` | Проверка синтаксиса BSL-кода |
| `1c_help_search` | Справка по платформе 1С |
| `1c_bsp_search` | Поиск по документации БСП |
| `1c_templates` | Шаблоны кода 1С |

## Устранение проблем

| Проблема | Решение |
|----------|---------|
| Сервер не подключается | Проверить VPN/сеть до 10.1.231.253 |
| «Not Acceptable» | IDE должна отправлять `Accept: application/json, text/event-stream` |
| Инструменты не отображаются | Перезапустить IDE, проверить формат конфига |
| OData-инструменты отсутствуют | На сервере не настроен ODATA_URL — обратиться к администратору |
