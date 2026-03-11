#!/bin/bash
set -e

GITLAB_URL="http://89.223.126.31:8929"

echo "=== Настройка CI/CD переменных GitLab ==="
echo ""
echo "Для работы нужен Personal Access Token с правами 'api'."
echo "  Создай его: ${GITLAB_URL}/-/user_settings/personal_access_tokens"
echo ""
read -p "Введи GitLab Access Token: " GITLAB_TOKEN

if [ -z "$GITLAB_TOKEN" ]; then
    echo "Ошибка: токен не указан."
    exit 1
fi

read -p "Введи путь проекта (например root/beautystyle): " PROJECT_PATH

if [ -z "$PROJECT_PATH" ]; then
    echo "Ошибка: путь проекта не указан."
    exit 1
fi

# URL-encode project path
ENCODED_PATH=$(echo "$PROJECT_PATH" | sed 's/\//%2F/g')
API_URL="${GITLAB_URL}/api/v4/projects/${ENCODED_PATH}/variables"

add_variable() {
    local key="$1"
    local value="$2"
    local protected="${3:-true}"
    local masked="${4:-false}"

    echo -n "  ${key}... "

    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
        --request POST "${API_URL}" \
        --header "PRIVATE-TOKEN: ${GITLAB_TOKEN}" \
        --form "key=${key}" \
        --form "value=${value}" \
        --form "protected=${protected}" \
        --form "masked=${masked}" \
        --form "variable_type=env_var")

    if [ "$HTTP_CODE" = "201" ]; then
        echo "OK"
    elif [ "$HTTP_CODE" = "400" ]; then
        echo "уже существует, обновляю..."
        curl -s -o /dev/null \
            --request PUT "${API_URL}/${key}" \
            --header "PRIVATE-TOKEN: ${GITLAB_TOKEN}" \
            --form "value=${value}" \
            --form "protected=${protected}" \
            --form "masked=${masked}"
        echo "  обновлено"
    else
        echo "ОШИБКА (HTTP ${HTTP_CODE})"
    fi
}

echo ""
echo "Добавляю переменные в проект ${PROJECT_PATH}..."
echo ""

# 1. SSH_PRIVATE_KEY
echo "--- SSH ключ для деплоя ---"
DEFAULT_KEY="$HOME/.ssh/id_rsa"
read -p "Путь к приватному SSH ключу [${DEFAULT_KEY}]: " KEY_PATH
KEY_PATH="${KEY_PATH:-$DEFAULT_KEY}"

if [ -f "$KEY_PATH" ]; then
    SSH_KEY=$(cat "$KEY_PATH")
    add_variable "SSH_PRIVATE_KEY" "$SSH_KEY" "true" "true"
else
    echo "  Файл ${KEY_PATH} не найден, пропускаю SSH_PRIVATE_KEY."
fi

# 2. DEPLOY_SERVER
add_variable "DEPLOY_SERVER" "89.223.126.31" "true" "false"

# 3. DEPLOY_USER
add_variable "DEPLOY_USER" "root" "true" "false"

# 4. DEPLOY_PORT
add_variable "DEPLOY_PORT" "22" "true" "false"

echo ""
echo "=== Переменные настроены ==="
echo ""
echo "Проверить: ${GITLAB_URL}/${PROJECT_PATH}/-/settings/ci_cd (раздел Variables)"
