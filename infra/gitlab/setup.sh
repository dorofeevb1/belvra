#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SERVER="root@89.223.126.31"
GITLAB_COMPOSE="${SCRIPT_DIR}/docker-compose.yml"
REMOTE_DIR="/opt/gitlab"

echo "=== GitLab CE Installation ==="
echo "Server: ${SERVER}"
echo "URL:    http://89.223.126.31:8929"
echo "SSH:    ssh://git@89.223.126.31:2224"
echo ""

# 1. Создаём директорию на сервере
echo "[1/5] Подготовка сервера..."
ssh ${SERVER} "mkdir -p ${REMOTE_DIR}"

# 2. Копируем docker-compose на сервер
echo "[2/5] Копирование конфигурации..."
scp ${GITLAB_COMPOSE} ${SERVER}:${REMOTE_DIR}/docker-compose.yml

# 3. Настраиваем swap (запас для GitLab + Runner)
echo "[3/5] Настройка swap (если нет)..."
ssh ${SERVER} 'bash -s' << 'SWAP_EOF'
if [ ! -f /swapfile ]; then
    echo "Создаём swap 2 ГБ..."
    fallocate -l 2G /swapfile
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    echo '/swapfile none swap sw 0 0' >> /etc/fstab
    sysctl vm.swappiness=10
    echo 'vm.swappiness=10' >> /etc/sysctl.conf
    echo "Swap создан."
else
    echo "Swap уже существует."
fi
free -h
SWAP_EOF

# 4. Запускаем GitLab
echo ""
echo "[4/5] Запуск GitLab (первый запуск займёт 3-5 минут)..."
ssh ${SERVER} "cd ${REMOTE_DIR} && docker compose up -d"

# 5. Ждём готовности и получаем пароль root
echo ""
echo "[5/5] Ожидание запуска GitLab..."
echo "  (это может занять до 5 минут на первый раз)"

ssh ${SERVER} 'bash -s' << 'WAIT_EOF'
echo "Ожидание health check..."
for i in $(seq 1 60); do
    STATUS=$(docker inspect --format='{{.State.Health.Status}}' gitlab 2>/dev/null || echo "starting")
    if [ "$STATUS" = "healthy" ]; then
        echo "GitLab готов!"
        break
    fi
    echo "  [$i/60] Статус: $STATUS"
    sleep 10
done

echo ""
echo "============================================"
echo "  GitLab CE установлен!"
echo "============================================"
echo ""
echo "URL:      http://89.223.126.31:8929"
echo "Логин:    root"

if docker exec gitlab cat /etc/gitlab/initial_root_password 2>/dev/null | grep -oP 'Password: \K.*'; then
    PASS=$(docker exec gitlab cat /etc/gitlab/initial_root_password 2>/dev/null | grep -oP 'Password: \K.*')
    echo "Пароль:   ${PASS}"
else
    echo "Пароль:   (файл ещё не создан, подожди и проверь командой ниже)"
fi

echo ""
echo "Получить пароль позже:"
echo "  ssh root@89.223.126.31 'docker exec gitlab cat /etc/gitlab/initial_root_password'"
echo ""
echo "ВАЖНО: Смени пароль root в течение 24 часов!"
echo "Git SSH clone:  ssh://git@89.223.126.31:2224/username/repo.git"
echo "Git HTTP clone: http://89.223.126.31:8929/username/repo.git"
echo "============================================"
WAIT_EOF

echo ""
echo "=== Установка завершена ==="
