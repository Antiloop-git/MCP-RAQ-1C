#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if [ ! -f .env ]; then
    echo "Создаю .env из .env.example..."
    cp .env.example .env
fi

echo "Запуск сервисов..."
docker compose up -d

echo ""
echo "Сервисы запущены:"
echo "  MCP Server:  http://localhost:${MCP_SERVER_PORT:-8000}/health"
echo "  Loader UI:   http://localhost:${LOADER_PORT:-8501}"
echo "  Parser:      http://localhost:${PARSER_PORT:-8001}/health"
echo "  Embeddings:  http://localhost:${EMBEDDINGS_PORT:-5000}/health"
echo "  Qdrant:      http://localhost:${QDRANT_PORT:-6333}/dashboard"
echo ""
echo "Для индексации откройте Loader UI и нажмите 'Индексировать'."
