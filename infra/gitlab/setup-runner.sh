#!/bin/bash
set -e

SERVER="root@89.223.126.31"
GITLAB_URL="http://89.223.126.31:8929"

echo "=== GitLab Runner Setup ==="
echo ""
echo "Перед запуском этого скрипта:"
echo "  1. Зайди в GitLab: ${GITLAB_URL}/admin/runners"
echo "  2. Нажми 'New instance runner'"
echo "  3. Скопируй registration token"
echo ""
read -p "Введи registration token: " RUNNER_TOKEN

if [ -z "$RUNNER_TOKEN" ]; then
    echo "Ошибка: токен не указан."
    exit 1
fi

echo ""
echo "Устанавливаю GitLab Runner на сервер..."

ssh ${SERVER} 'bash -s' << RUNNER_EOF
# Устанавливаем GitLab Runner через Docker
docker run -d \
  --name gitlab-runner \
  --restart always \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v gitlab-runner-config:/etc/gitlab-runner \
  gitlab/gitlab-runner:latest

# Регистрируем docker runner
docker exec gitlab-runner gitlab-runner register \
  --non-interactive \
  --url "${GITLAB_URL}" \
  --token "${RUNNER_TOKEN}" \
  --executor "docker" \
  --docker-image "alpine:3.20" \
  --docker-privileged \
  --docker-pull-policy "if-not-present" \
  --docker-volumes "/var/run/docker.sock:/var/run/docker.sock" \
  --description "belvra-docker-runner"

# Регистрируем shell runner (для деплоя через SSH)
docker exec gitlab-runner gitlab-runner register \
  --non-interactive \
  --url "${GITLAB_URL}" \
  --token "${RUNNER_TOKEN}" \
  --executor "shell" \
  --description "belvra-shell-runner"

echo ""
echo "Runners зарегистрированы!"
docker exec gitlab-runner gitlab-runner list
RUNNER_EOF

echo ""
echo "=== GitLab Runner установлен ==="
echo ""
echo "Не забудь добавить SSH ключ в GitLab CI/CD Variables:"
echo "  1. Зайди в проект → Settings → CI/CD → Variables"
echo "  2. Добавь переменную SSH_PRIVATE_KEY"
echo "     Тип: Variable, Protected: Yes, Masked: Yes"
echo "     Значение: содержимое ~/.ssh/id_rsa (приватный ключ)"
