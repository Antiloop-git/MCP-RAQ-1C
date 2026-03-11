#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

COMPOSE_CMD="docker compose -f docker-compose.comol.yml --env-file .env.comol"

# Маппинг алиасов → имена сервисов в compose
resolve_service() {
    case "$1" in
        help)      echo "1c-help-mcp" ;;
        ssl)       echo "mcp-ssl-server" ;;
        templates) echo "template-search-mcp" ;;
        syntax)    echo "1c-syntaxcheck-mcp" ;;
        *)         echo "Неизвестный сервис: $1" >&2
                   echo "Доступные: help, ssl, templates, syntax" >&2
                   exit 1 ;;
    esac
}

usage() {
    cat <<'EOF'
Управление COMOL MCP-серверами

Использование:
  ./scripts/comol.sh start [help|ssl|templates|syntax]   — запуск (без аргумента = все)
  ./scripts/comol.sh stop  [help|ssl|templates|syntax]   — остановка
  ./scripts/comol.sh status                              — статус контейнеров
  ./scripts/comol.sh logs  [help|ssl|templates|syntax]   — логи (Ctrl+C для выхода)

Серверы:
  help       Справка по платформе 1С         (порт 8003, ~10 ГБ)
  ssl        Справка по БСП                  (порт 8008, ~10 ГБ)
  templates  Шаблоны кода 1С                 (порт 8004, ~10 ГБ)
  syntax     Проверка синтаксиса BSL         (порт 8002, ~5 ГБ)
EOF
}

cmd_start() {
    if [ ! -f .env.comol ]; then
        if [ -f .env.example.comol ]; then
            echo "Создаю .env.comol из .env.example.comol..."
            cp .env.example.comol .env.comol
            echo "Заполните лицензионные ключи в .env.comol и запустите снова."
            exit 1
        else
            echo "Файл .env.comol не найден. Создайте его с лицензионными ключами." >&2
            exit 1
        fi
    fi

    local services=""
    if [ $# -gt 0 ]; then
        for alias in "$@"; do
            services="$services $(resolve_service "$alias")"
        done
    fi

    echo "Первый запуск может занять несколько часов (индексация + скачивание моделей)."
    echo "Используйте './scripts/comol.sh logs' для отслеживания прогресса."
    echo ""

    # shellcheck disable=SC2086
    $COMPOSE_CMD up -d $services

    echo ""
    cmd_status
}

cmd_stop() {
    local services=""
    if [ $# -gt 0 ]; then
        for alias in "$@"; do
            services="$services $(resolve_service "$alias")"
        done
        # shellcheck disable=SC2086
        $COMPOSE_CMD stop $services
    else
        $COMPOSE_CMD down
    fi
    echo "Остановлено."
}

cmd_status() {
    echo "COMOL MCP-серверы:"
    echo ""
    printf "  %-12s %-8s %s\n" "Сервис" "Порт" "Статус"
    printf "  %-12s %-8s %s\n" "------" "----" "------"

    check_container() {
        local name=$1 port=$2 container=$3
        local status
        status=$(docker inspect --format='{{.State.Status}}' "$container" 2>/dev/null || echo "не запущен")
        printf "  %-12s %-8s %s\n" "$name" "$port" "$status"
    }

    check_container "help"      "8003" "1c_help_mcp"
    check_container "templates" "8004" "template_search_mcp"
    check_container "syntax"    "8002" "1c_syntaxcheck_mcp"
    check_container "ssl"       "8008" "mcp_ssl_server"
}

cmd_logs() {
    local services=""
    if [ $# -gt 0 ]; then
        for alias in "$@"; do
            services="$services $(resolve_service "$alias")"
        done
    fi
    # shellcheck disable=SC2086
    $COMPOSE_CMD logs -f $services
}

# --- main ---
if [ $# -eq 0 ]; then
    usage
    exit 0
fi

command="$1"
shift

case "$command" in
    start)  cmd_start "$@" ;;
    stop)   cmd_stop "$@" ;;
    status) cmd_status ;;
    logs)   cmd_logs "$@" ;;
    *)      usage; exit 1 ;;
esac
