#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

SERVER="root@37.77.104.201"
REMOTE_DIR="/opt/beautystyle"
COMPOSE_FILE="docker-compose.prod.yml"

echo "=== BeautyStyleService Deploy ==="
echo "Project: ${PROJECT_ROOT}"

# 1. Sync code to server (exclude junk and .env)
echo ""
echo "[1/5] Синхронизация кода на сервер..."
rsync -avz --delete \
  --exclude=node_modules \
  --exclude=.git \
  --exclude=__pycache__ \
  --exclude='*.pyc' \
  --exclude=dist \
  --exclude=.angular \
  --exclude=.env \
  --exclude=.env.prod \
  --exclude=celerybeat-schedule \
  -e ssh ${PROJECT_ROOT}/ ${SERVER}:${REMOTE_DIR}/

# 2. Restore .env.prod as .env on server
echo ""
echo "[2/5] Восстановление .env из .env.prod..."
ssh ${SERVER} "cd ${REMOTE_DIR} && cp .env.prod .env"

# 3. Build all containers
echo ""
echo "[3/5] Сборка контейнеров..."
ssh ${SERVER} "cd ${REMOTE_DIR} && docker compose -f ${COMPOSE_FILE} build"

# 4. Restart everything
echo ""
echo "[4/5] Перезапуск сервисов..."
ssh ${SERVER} "cd ${REMOTE_DIR} && docker compose -f ${COMPOSE_FILE} down && docker compose -f ${COMPOSE_FILE} up -d"

# 5. Wait for health checks + run migrations + collectstatic
echo ""
echo "[5/5] Миграции и статика..."
ssh ${SERVER} "cd ${REMOTE_DIR} && sleep 5 && \
  docker compose -f ${COMPOSE_FILE} exec -T backend python manage.py migrate --noinput && \
  docker compose -f ${COMPOSE_FILE} exec -T backend python manage.py collectstatic --noinput"

# Verify
echo ""
echo "=== Проверка ==="
STATUS=$(ssh ${SERVER} "curl -s -o /dev/null -w '%{http_code}' http://localhost/")
echo "Frontend: HTTP ${STATUS}"
STATUS=$(ssh ${SERVER} "curl -s -o /dev/null -w '%{http_code}' http://localhost/api/v1/services/categories/")
echo "API:      HTTP ${STATUS}"

echo ""
ssh ${SERVER} "cd ${REMOTE_DIR} && docker compose -f ${COMPOSE_FILE} ps --format 'table {{.Name}}\t{{.Status}}'"

echo ""
echo "=== Деплой завершён ==="
