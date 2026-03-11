# Подключение comol/DISTAR MCP-серверов

4 дополнительных MCP-сервера от comol/DISTAR расширяют возможности для разработки на 1С.

## Серверы

| Сервер | Порт | Описание |
|---|---|---|
| `1c_help_mcp` | 8003 | Справка по платформе 1С:Предприятие 8.3 |
| `template-search-mcp` | 8004 | Шаблоны кода 1С + веб-редактор |
| `1c_syntaxcheck_mcp` | 8002 | Проверка синтаксиса BSL (BSL Language Server) |
| `mcp_ssl_server` | 8008 | Справка по БСП (Библиотека стандартных подсистем) |

## Быстрый старт

```bash
# 1. Скопировать шаблон переменных окружения
cp .env.example.comol .env.comol

# 2. Заполнить лицензионные ключи в .env.comol
#    LICENSE_KEY_HELP, LICENSE_KEY_TEMPLATES, LICENSE_KEY_SYNTAX, LICENSE_KEY_SSL

# 3. Запустить
docker compose -f docker-compose.comol.yml --env-file .env.comol up -d

# 4. Проверить
docker compose -f docker-compose.comol.yml ps
```

## Лицензионные ключи

Каждый сервер требует свой лицензионный ключ. Ключи находятся в `_private/MCP_Distr/` (не в git).

## Настройка в IDE

### Cursor / VS Code

В `mcp.json` добавьте серверы:

```json
{
  "mcpServers": {
    "1c-help": {
      "url": "http://localhost:8003/mcp"
    },
    "1c-templates": {
      "url": "http://localhost:8004/mcp"
    },
    "1c-syntax": {
      "url": "http://localhost:8002/mcp"
    },
    "1c-ssl": {
      "url": "http://localhost:8008/mcp"
    }
  }
}
```

### RooCode

В `mcp_settings.json` добавьте аналогичные записи с `"transportType": "streamableHttp"`.

## Настройки

| Переменная | Описание | По умолчанию |
|---|---|---|
| `SSL_VERSION` | Версия БСП для SSL-сервера | `3.1.11` |
| `COMOL_USESSE` | SSE-транспорт для Legacy-клиентов | `false` |
| `COMOL_*_RESET_CACHE` | Сброс кэша при старте | `false` |
| `COMOL_*_RESET_DATABASE` | Пересоздание БД при старте | `false` |

## Выборочный запуск

Скрипт `scripts/comol.sh` позволяет запускать серверы по отдельности:

```bash
# Справка
./scripts/comol.sh

# Запустить только Help (справка по платформе)
./scripts/comol.sh start help

# Запустить Help + SSL
./scripts/comol.sh start help ssl

# Статус всех COMOL-контейнеров
./scripts/comol.sh status

# Логи индексации (Ctrl+C для выхода)
./scripts/comol.sh logs help

# Остановить конкретный сервер
./scripts/comol.sh stop help

# Остановить все
./scripts/comol.sh stop
```

Доступные алиасы: `help` (8003), `ssl` (8008), `templates` (8004), `syntax` (8002).

## Порты

Порты comol-серверов (8002-8008) не конфликтуют с основным стеком (5050, 6333, 8000, 8001, 8501). При необходимости порты настраиваются через переменные `COMOL_*_PORT` в `.env.comol`.
