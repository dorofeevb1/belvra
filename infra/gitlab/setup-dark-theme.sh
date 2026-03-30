#!/bin/bash
set -e

SERVER="root@89.223.126.31"
GITLAB_URL="http://89.223.126.31:8929"

echo "=== Установка тёмной темы для GitLab ==="
echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║  СПОСОБ 1: Расширение Stylus (рекомендуется)        ║"
echo "╠══════════════════════════════════════════════════════╣"
echo "║                                                      ║"
echo "║  1. Установи расширение Stylus для браузера:         ║"
echo "║     Chrome: chrome web store → Stylus                ║"
echo "║     Firefox: addons.mozilla.org → Stylus             ║"
echo "║                                                      ║"
echo "║  2. Перейди на:                                      ║"
echo "║     https://github.com/vednoc/dark-gitlab            ║"
echo "║                                                      ║"
echo "║  3. Нажми Install с UserCSS badge                    ║"
echo "║                                                      ║"
echo "║  4. В настройках стиля укажи свой URL:               ║"
echo "║     ${GITLAB_URL}                                    ║"
echo "║                                                      ║"
echo "║  5. В GitLab: Settings → Preferences:                ║"
echo "║     - Syntax theme: White                            ║"
echo "║     - Navigation theme: Indigo                       ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║  СПОСОБ 2: Серверный CSS (для всех пользователей)    ║"
echo "╠══════════════════════════════════════════════════════╣"
echo "║                                                      ║"
echo "║  Внедрение кастомного CSS через GitLab Admin API     ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

read -p "Установить серверную тёмную тему для всех пользователей? (y/n): " INSTALL_SERVER

if [ "$INSTALL_SERVER" != "y" ]; then
    echo "Пропускаем серверную установку."
    exit 0
fi

echo ""
echo "Нужен Private Token от root-аккаунта GitLab."
echo "Создай его: ${GITLAB_URL}/-/user_settings/personal_access_tokens"
echo "Scope: api"
echo ""
read -p "Введи Private Token: " GITLAB_TOKEN

if [ -z "$GITLAB_TOKEN" ]; then
    echo "Ошибка: токен не указан."
    exit 1
fi

echo ""
echo "Скачиваю тёмную тему..."

DARK_CSS=$(curl -sL "https://raw.githubusercontent.com/vednoc/dark-gitlab/main/gitlab.user.css" | \
    sed -n '/@-moz-document/,/^}/p' | \
    sed '1d;$d' | \
    head -5000)

if [ ${#DARK_CSS} -lt 100 ]; then
    echo "Не удалось скачать полную тему, применяю встроенную тёмную тему..."
    DARK_CSS='
:root {
  --gl-background-color-default: #1e1e2e !important;
  --gl-background-color-subtle: #181825 !important;
  --gl-background-color-strong: #313244 !important;
  --gl-text-color-default: #cdd6f4 !important;
  --gl-text-color-subtle: #a6adc8 !important;
  --gl-border-color-default: #45475a !important;
}
body { background-color: #1e1e2e !important; color: #cdd6f4 !important; }
.navbar-gitlab, .top-bar-fixed { background-color: #181825 !important; }
.nav-sidebar { background-color: #11111b !important; }
.content-wrapper, .container-fluid { background-color: #1e1e2e !important; }
.card, .gl-card, .file-holder, .diff-file { background-color: #181825 !important; border-color: #45475a !important; }
a { color: #89b4fa !important; }
a:hover { color: #b4befe !important; }
.btn-confirm, .btn-primary { background-color: #89b4fa !important; border-color: #89b4fa !important; color: #1e1e2e !important; }
pre, code, .code { background-color: #11111b !important; color: #cdd6f4 !important; }
input, textarea, select, .form-control { background-color: #313244 !important; border-color: #45475a !important; color: #cdd6f4 !important; }
'
fi

echo "Применяю тему через API..."

RESPONSE=$(curl -s -w "\n%{http_code}" -X PUT \
    "${GITLAB_URL}/api/v4/application/appearance" \
    -H "PRIVATE-TOKEN: ${GITLAB_TOKEN}" \
    --form "title=GitLab" \
    --form "description=Belvra GitLab" \
    --form "new_project_guidelines=" \
    --form-string "header_message=<style>${DARK_CSS}</style>")

HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | sed '$d')

if [ "$HTTP_CODE" = "200" ]; then
    echo ""
    echo "Тёмная тема успешно применена!"
    echo "Открой ${GITLAB_URL} и проверь."
    echo ""
    echo "Чтобы убрать тему:"
    echo "  Admin Area → Appearance → Header message → очистить"
else
    echo ""
    echo "Ошибка (HTTP ${HTTP_CODE}):"
    echo "$BODY"
    echo ""
    echo "Альтернативный способ:"
    echo "  1. Зайди в ${GITLAB_URL}/admin/application_settings/appearances"
    echo "  2. В поле 'Header message' вставь:"
    echo "     <style>body{background:#1e1e2e!important;color:#cdd6f4!important}</style>"
    echo "  3. Или используй Stylus (Способ 1)"
fi
