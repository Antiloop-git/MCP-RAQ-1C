#!/bin/bash
# Auto-deploy script for MCP RAQ 1C on VPS
# Checks for new commits on GitHub and redeploys if needed
#
# Usage:
#   ./deploy.sh              # Check and deploy if changed
#   ./deploy.sh --force      # Force redeploy (rebuild all)
#   ./deploy.sh --status     # Show current status
#
# Cron (every 2 minutes):
#   */2 * * * * /home/mcp/MCP-RAQ-1C/scripts/deploy.sh >> /home/mcp/deploy.log 2>&1

set -euo pipefail

PROJECT_DIR="${PROJECT_DIR:-$HOME/MCP-RAQ-1C}"
COMPOSE_FILE="$PROJECT_DIR/docker-compose.yml"
LOG_PREFIX="[deploy $(date '+%Y-%m-%d %H:%M:%S')]"

cd "$PROJECT_DIR"

log() { echo "$LOG_PREFIX $1"; }

case "${1:-}" in
  --status)
    log "Branch: $(git branch --show-current)"
    log "Last commit: $(git log --oneline -1)"
    log "Remote: $(git ls-remote origin HEAD | cut -f1 | head -c 7)"
    echo "---"
    docker compose ps --format "table {{.Name}}\t{{.Status}}"
    exit 0
    ;;
  --force)
    log "Force redeploy requested"
    docker compose -f "$COMPOSE_FILE" up -d --build
    log "Force redeploy complete"
    exit 0
    ;;
esac

# Fetch latest from remote
git fetch origin main --quiet

LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/main)

if [ "$LOCAL" = "$REMOTE" ]; then
    exit 0  # Nothing to do — silent exit for cron
fi

log "New commits detected: $LOCAL -> $REMOTE"

# Pull changes
git pull origin main --quiet
log "Pulled: $(git log --oneline -1)"

# Find which services need rebuild
CHANGED_FILES=$(git diff --name-only "$LOCAL" "$REMOTE")
SERVICES_TO_REBUILD=""

if echo "$CHANGED_FILES" | grep -q "^parser/"; then
    SERVICES_TO_REBUILD="$SERVICES_TO_REBUILD parser"
fi
if echo "$CHANGED_FILES" | grep -q "^mcp-server/"; then
    SERVICES_TO_REBUILD="$SERVICES_TO_REBUILD mcp-server"
fi
if echo "$CHANGED_FILES" | grep -q "^loader/"; then
    SERVICES_TO_REBUILD="$SERVICES_TO_REBUILD loader"
fi
if echo "$CHANGED_FILES" | grep -q "^embeddings/"; then
    SERVICES_TO_REBUILD="$SERVICES_TO_REBUILD embeddings"
fi
if echo "$CHANGED_FILES" | grep -q "^docker-compose.yml"; then
    SERVICES_TO_REBUILD="ALL"
fi

if [ "$SERVICES_TO_REBUILD" = "ALL" ] || [ -z "$SERVICES_TO_REBUILD" ]; then
    log "Rebuilding all services..."
    docker compose -f "$COMPOSE_FILE" up -d --build
else
    log "Rebuilding:$SERVICES_TO_REBUILD"
    docker compose -f "$COMPOSE_FILE" up -d --build $SERVICES_TO_REBUILD
fi

log "Deploy complete. Services:"
docker compose ps --format "table {{.Name}}\t{{.Status}}" 2>/dev/null || true
