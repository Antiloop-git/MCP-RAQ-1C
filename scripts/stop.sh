#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

echo "Остановка сервисов..."
docker compose down

echo "Сервисы остановлены."
