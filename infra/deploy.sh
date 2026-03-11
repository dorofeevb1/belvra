#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

SERVER="root@89.223.126.31"

# Parse environment argument
ENV="${1:-dev}"

if [ "$ENV" = "prod" ]; then
    REMOTE_DIR="/opt/beautystyle/prod"
    COMPOSE_FILE="docker-compose.prod.yml"
    ENV_FILE=".env.prod"
    CHECK_PORT=""
    LABEL="PRODUCTION"
elif [ "$ENV" = "dev" ]; then
    REMOTE_DIR="/opt/beautystyle/dev"
    COMPOSE_FILE="docker-compose.dev.yml"
    ENV_FILE=".env.dev"
    CHECK_PORT=":8080"
    LABEL="DEVELOPMENT"
else
    echo "Usage: $0 [dev|prod]"
    echo "  dev  - Deploy to development (port 8080)"
    echo "  prod - Deploy to production (port 80)"
    exit 1
fi

echo "=== BeautyStyleService Deploy [${LABEL}] ==="
echo "Project: ${PROJECT_ROOT}"
echo "Remote:  ${SERVER}:${REMOTE_DIR}"

# 1. Create remote dir if needed
echo ""
echo "[1/6] Подготовка сервера..."
ssh ${SERVER} "mkdir -p ${REMOTE_DIR}"

# 2. Sync code to server
echo ""
echo "[2/6] Синхронизация кода на сервер..."
rsync -avz --delete \
  --exclude=node_modules \
  --exclude=.git \
  --exclude=__pycache__ \
  --exclude='*.pyc' \
  --exclude=dist \
  --exclude=.angular \
  --exclude=.env \
  --exclude=.env.prod \
  --exclude=.env.dev \
  --exclude=celerybeat-schedule \
  -e ssh ${PROJECT_ROOT}/ ${SERVER}:${REMOTE_DIR}/

# 3. Restore .env from env file on server
echo ""
echo "[3/6] Восстановление .env из ${ENV_FILE}..."
ssh ${SERVER} "cd ${REMOTE_DIR} && cp ${ENV_FILE} .env"

# 4. Build all containers
echo ""
echo "[4/6] Сборка контейнеров..."
ssh ${SERVER} "cd ${REMOTE_DIR} && docker compose -f ${COMPOSE_FILE} build"

# 5. Restart everything
echo ""
echo "[5/6] Перезапуск сервисов..."
ssh ${SERVER} "cd ${REMOTE_DIR} && docker compose -f ${COMPOSE_FILE} down && docker compose -f ${COMPOSE_FILE} up -d"

# 6. Wait for health checks + run migrations + collectstatic
echo ""
echo "[6/6] Миграции и статика..."
ssh ${SERVER} "cd ${REMOTE_DIR} && sleep 5 && \
  docker compose -f ${COMPOSE_FILE} exec -T backend python manage.py migrate --noinput && \
  docker compose -f ${COMPOSE_FILE} exec -T backend python manage.py collectstatic --noinput"

# Verify
echo ""
echo "=== Проверка [${LABEL}] ==="
STATUS=$(ssh ${SERVER} "curl -s -o /dev/null -w '%{http_code}' http://localhost${CHECK_PORT}/")
echo "Frontend: HTTP ${STATUS}"
STATUS=$(ssh ${SERVER} "curl -s -o /dev/null -w '%{http_code}' http://localhost${CHECK_PORT}/api/v1/services/categories/")
echo "API:      HTTP ${STATUS}"

echo ""
ssh ${SERVER} "cd ${REMOTE_DIR} && docker compose -f ${COMPOSE_FILE} ps --format 'table {{.Name}}\t{{.Status}}'"

echo ""
echo "=== Деплой [${LABEL}] завершён ==="
