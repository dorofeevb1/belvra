#!/bin/bash
set -e

NEW_SERVER="89.223.126.31"
GITLAB_PORT="8929"
SSH_PORT="2224"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=========================================="
echo "  Belvra — Full GitLab Setup"
echo "=========================================="
echo ""
echo "Сервер:    ${NEW_SERVER}"
echo "GitLab:    http://${NEW_SERVER}:${GITLAB_PORT}"
echo "Git SSH:   ssh://git@${NEW_SERVER}:${SSH_PORT}"
echo ""
echo "Этот скрипт выполнит:"
echo "  1. Установку Docker (если нет)"
echo "  2. Установку GitLab CE"
echo "  3. Настройку GitLab Runner"
echo "  4. Настройку CI/CD переменных"
echo "  5. Миграцию репозитория"
echo ""
read -p "Продолжить? (y/n) " -n 1 -r
echo ""
[[ ! $REPLY =~ ^[Yy]$ ]] && exit 0

# ==============================
# Step 1: Install Docker
# ==============================
echo ""
echo "=== [1/5] Установка Docker ==="
ssh root@${NEW_SERVER} 'bash -s' << 'DOCKER_EOF'
if command -v docker &> /dev/null; then
    echo "Docker уже установлен: $(docker --version)"
else
    echo "Устанавливаю Docker..."
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker
    systemctl start docker
    echo "Docker установлен: $(docker --version)"
fi

if docker compose version &> /dev/null; then
    echo "Docker Compose: $(docker compose version)"
else
    echo "Устанавливаю Docker Compose plugin..."
    apt-get update && apt-get install -y docker-compose-plugin
fi
DOCKER_EOF

# ==============================
# Step 2: Install GitLab
# ==============================
echo ""
echo "=== [2/5] Установка GitLab CE ==="
bash "${SCRIPT_DIR}/setup.sh"

# ==============================
# Step 3: Setup Runner
# ==============================
echo ""
echo "=== [3/5] Настройка GitLab Runner ==="
echo ""
echo "Нужно зарегистрировать Runner."
echo "  1. Открой http://${NEW_SERVER}:${GITLAB_PORT}/admin/runners"
echo "  2. Нажми 'New instance runner'"
echo "  3. Скопируй token"
echo ""
read -p "Готов настроить runner сейчас? (y/n) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    bash "${SCRIPT_DIR}/setup-runner.sh"
fi

# ==============================
# Step 4: CI/CD Variables
# ==============================
echo ""
echo "=== [4/5] Настройка CI/CD переменных ==="
read -p "Настроить CI/CD переменные сейчас? (y/n) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    bash "${SCRIPT_DIR}/setup-ci-variables.sh"
fi

# ==============================
# Step 5: Migrate repository
# ==============================
echo ""
echo "=== [5/5] Миграция репозитория ==="
echo ""
GITLAB_URL="http://${NEW_SERVER}:${GITLAB_PORT}"
echo "ВАЖНО: Сначала создай проект в GitLab:"
echo "  ${GITLAB_URL}/projects/new"
echo ""
read -p "Введи путь проекта (например root/belvra): " PROJECT_PATH
if [ -n "$PROJECT_PATH" ]; then
    REPO_ROOT="$(git -C "${SCRIPT_DIR}" rev-parse --show-toplevel 2>/dev/null || echo "")"
    if [ -n "$REPO_ROOT" ]; then
        cd "$REPO_ROOT"

        if git remote get-url gitlab-new &> /dev/null; then
            echo "Remote 'gitlab-new' уже существует, обновляю URL..."
            git remote set-url gitlab-new "ssh://git@${NEW_SERVER}:${SSH_PORT}/${PROJECT_PATH}.git"
        else
            git remote add gitlab-new "ssh://git@${NEW_SERVER}:${SSH_PORT}/${PROJECT_PATH}.git"
        fi

        echo ""
        echo "Remote добавлен: gitlab-new"
        read -p "Запушить master сейчас? (y/n) " -n 1 -r
        echo ""
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            git push -u gitlab-new master
            echo "Код запушен!"
        fi
    fi
fi

echo ""
echo "=========================================="
echo "  Установка завершена!"
echo "=========================================="
echo ""
echo "GitLab:     http://${NEW_SERVER}:${GITLAB_PORT}"
echo "Git SSH:    ssh://git@${NEW_SERVER}:${SSH_PORT}/${PROJECT_PATH:-username/repo}.git"
echo ""
echo "Следующие шаги:"
echo "  1. Смени пароль root в GitLab"
echo "  2. Добавь SSH ключ: http://${NEW_SERVER}:${GITLAB_PORT}/-/user_settings/ssh_keys"
echo "  3. Обнови IP в .gitlab-ci.yml для деплоя"
echo "  4. Сделай пуш и проверь пайплайн"
echo "=========================================="
