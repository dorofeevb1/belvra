# BeautyBook

**Платформа для онлайн-записи к мастерам красоты**

Полнофункциональное веб- и мобильное приложение для бронирования услуг индустрии красоты с интегрированной системой платежей, чатом, подписками и AI-ассистентом.

---

## Содержание

- [Обзор](#обзор)
- [Технологии](#технологии)
- [Архитектура](#архитектура)
- [Быстрый старт](#быстрый-старт)
- [Структура проекта](#структура-проекта)
- [Разработка](#разработка)
- [API](#api)
- [Мобильное приложение](#мобильное-приложение)
- [Деплой](#деплой)
- [Переменные окружения](#переменные-окружения)

---

## Обзор

BeautyBook объединяет мастеров красоты и клиентов на единой платформе. Мастера управляют расписанием, услугами, портфолио и финансами. Клиенты находят мастеров на карте, бронируют время и оплачивают услуги онлайн.

### Возможности для клиентов

- Поиск мастеров по геолокации (Яндекс Карты)
- Онлайн-бронирование с выбором свободных слотов
- Чат с мастером
- Отзывы и рейтинги
- Избранные мастера
- Подписка PRO (приоритетная запись, кэшбек)

### Возможности для мастеров

- Дашборд с аналитикой и статистикой
- Управление расписанием и услугами
- Календарь и канбан-доска записей
- Портфолио работ
- Кошелек и вывод средств
- AI-ассистент для анализа фото и генерации контента
- Подписка PRO (безлимитные записи, расширенная аналитика, сниженная комиссия)

---

## Технологии

### Backend

| Компонент | Технология |
|-----------|-----------|
| Фреймворк | Django 5.0 + Django REST Framework |
| База данных | PostgreSQL 16 |
| Кэш и брокер | Redis 7 |
| Очередь задач | Celery 5.3 |
| Аутентификация | JWT (SimpleJWT) |
| Платежи | YooKassa |
| AI | Ollama (анализ изображений) |
| Документация API | drf-spectacular (Swagger / ReDoc) |
| Сервер | Gunicorn + Nginx |

### Frontend

| Компонент | Технология |
|-----------|-----------|
| Фреймворк | Angular 21 (Standalone Components) |
| UI | Ionic 8 + TailwindCSS 4 |
| Язык | TypeScript 5.9 (strict mode) |
| Состояние | Angular Signals |
| Карты | Yandex Maps API |
| AI | Google GenAI SDK |

### Mobile

| Компонент | Технология |
|-----------|-----------|
| Фреймворк | Ionic + Capacitor 7 |
| Платформы | iOS, Android |
| Нативные плагины | Camera, Push Notifications, Network, Preferences, Keyboard, StatusBar, Haptics |

### Инфраструктура

| Компонент | Технология |
|-----------|-----------|
| Контейнеризация | Docker (multi-stage builds) |
| Оркестрация | Docker Compose |
| Reverse proxy | Nginx |
| Мониторинг | Flower (Celery) |
| CI/CD | Ionic Appflow |

---

## Архитектура

```
                         +-----------+
                         |   Nginx   |
                         |  :80/:443 |
                         +-----+-----+
                               |
                 +-------------+-------------+
                 |                           |
          +------+------+            +------+------+
          |   Angular   |            |   Django    |
          |  Web / SPA  |            |  REST API   |
          |    :4200    |            |    :8000    |
          +-------------+            +------+------+
                                            |
                         +------------------+------------------+
                         |                  |                  |
                  +------+------+    +------+------+    +------+------+
                  | PostgreSQL  |    |    Redis    |    |   Celery    |
                  |    :5432    |    |    :6379    |    |   Worker    |
                  +-------------+    +-------------+    +------+------+
                                                               |
                                                        +------+------+
                                                        | Celery Beat |
                                                        +-------------+
```

**Монорепозиторий** с npm workspaces:

- `backend/` -- Django REST API
- `apps/web/` -- Angular SPA
- `apps/mobile/` -- Ionic + Capacitor (iOS/Android)
- `libs/shared/` -- общие TypeScript-модели

---

## Быстрый старт

### Требования

- Docker 24+ и Docker Compose v2
- Node.js 20+ (для локальной разработки фронтенда)
- Python 3.12+ (для локальной разработки бэкенда)

### Запуск через Docker (рекомендуется)

```bash
# 1. Клонировать репозиторий
git clone <repo-url>
cd BeautyStyleService

# 2. Скопировать переменные окружения
cp .env.example .env

# 3. Собрать и запустить все сервисы
make build
make up

# 4. Применить миграции и создать администратора
make migrate
make createsuperuser

# 5. Открыть приложение
# Web:        http://localhost
# API:        http://localhost:8000/api/v1/
# Swagger:    http://localhost:8000/api/docs/
# Admin:      http://localhost:8000/admin/
# Flower:     http://localhost:5555
```

### Запуск фронтенда локально

```bash
# Установить зависимости (из корня монорепо)
npm install

# Запустить web-приложение
npm run web:dev

# Запустить мобильное приложение (dev server)
npm run mobile:dev
```

---

## Структура проекта

```
BeautyStyleService/
├── apps/
│   ├── web/                    # Angular Web SPA
│   │   └── src/app/
│   │       ├── core/           # Сервисы, guards, interceptors
│   │       ├── features/       # Модули по фичам
│   │       │   ├── auth/       #   Авторизация
│   │       │   ├── client/     #   Клиентская часть
│   │       │   └── master/     #   Мастерская часть
│   │       └── shared/         # Общие компоненты
│   └── mobile/                 # Ionic Mobile App
│       ├── ios/                # Xcode-проект
│       └── android/            # Android Studio-проект
│
├── backend/
│   ├── apps/
│   │   ├── users/              # Пользователи, профили, авторизация
│   │   ├── services/           # Услуги, портфолио, отзывы
│   │   ├── appointments/       # Записи, расписание
│   │   ├── payments/           # Платежи, кошелек, выводы
│   │   ├── subscriptions/      # Подписки и тарифы
│   │   ├── chat/               # Чат
│   │   ├── todo/               # Задачи мастера
│   │   ├── ai/                 # AI-интеграция
│   │   └── core/               # Уведомления, права, базовые модели
│   └── config/
│       ├── settings/           # Настройки по окружениям
│       ├── urls.py             # Маршрутизация API
│       └── celery.py           # Конфигурация Celery
│
├── libs/shared/                # Общие TypeScript-модели
├── nginx/                      # Конфигурация Nginx
├── docker-compose.yml          # Dev-окружение
├── docker-compose.prod.yml     # Prod-окружение
├── Makefile                    # Команды разработки
└── capacitor.config.json       # Capacitor (mobile)
```

---

## Разработка

### Make-команды

| Команда | Описание |
|---------|----------|
| `make build` | Сборка Docker-образов |
| `make up` | Запуск всех сервисов |
| `make down` | Остановка всех сервисов |
| `make logs` | Просмотр логов |
| `make logs-backend` | Логи бэкенда |
| `make migrate` | Миграции БД |
| `make makemigrations` | Создание миграций |
| `make createsuperuser` | Создание администратора |
| `make test` | Запуск тестов (pytest) |
| `make lint` | Проверка кода (flake8 + black) |
| `make format` | Форматирование кода (isort + black) |
| `make shell` | Django shell_plus |
| `make restart` | Перезапуск сервисов |
| `make clean` | Полная очистка (volumes + prune) |

### npm-скрипты

| Команда | Описание |
|---------|----------|
| `npm run web:dev` | Dev-сервер Angular (:4200) |
| `npm run web:build` | Production-сборка веба |
| `npm run mobile:dev` | Dev-сервер мобильного приложения |
| `npm run mobile:build` | Production-сборка мобильного |
| `npm run mobile:sync` | Синхронизация Capacitor с нативными проектами |
| `npm run shared:build` | Сборка общей TypeScript-библиотеки |

### Тестирование

```bash
# Backend (pytest)
make test

# Линтинг
make lint

# Форматирование
make format
```

---

## API

### Базовый URL

```
http://localhost:8000/api/v1/
```

### Документация

| Формат | URL |
|--------|-----|
| Swagger UI | `http://localhost:8000/api/docs/` |
| ReDoc | `http://localhost:8000/api/redoc/` |
| OpenAPI Schema | `http://localhost:8000/api/schema/` |

### Основные endpoints

| Группа | Путь | Описание |
|--------|------|----------|
| Auth | `/api/v1/auth/` | Регистрация, логин, JWT, сброс пароля |
| Users | `/api/v1/auth/profile/` | Профиль, аватар, избранное |
| Masters | `/api/v1/auth/masters/` | Список мастеров, гео-поиск |
| Services | `/api/v1/services/` | Категории, услуги, портфолио |
| Appointments | `/api/v1/appointments/` | Записи, расписание, отзывы |
| Payments | `/api/v1/payments/` | Платежи, кошелек, выводы |
| Subscriptions | `/api/v1/subscriptions/` | Тарифы, подписки, лимиты |
| Chat | `/api/v1/chats/` | Чаты, сообщения |
| Todos | `/api/v1/todos/` | Задачи мастера |
| Notifications | `/api/v1/notifications/` | Уведомления |
| AI | `/api/v1/ai/` | AI-анализ фото, генерация контента |

### Аутентификация

API использует JWT-токены (Bearer):

```bash
# Получить токены
curl -X POST http://localhost:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password123"}'

# Использовать access-токен
curl http://localhost:8000/api/v1/auth/profile/ \
  -H "Authorization: Bearer <access_token>"

# Обновить токен
curl -X POST http://localhost:8000/api/v1/auth/token/refresh/ \
  -H "Content-Type: application/json" \
  -d '{"refresh": "<refresh_token>"}'
```

---

## Мобильное приложение

**App ID:** `com.beautybook.app`

### Сборка

```bash
# Синхронизация с нативными проектами
npm run mobile:sync

# iOS
npx cap open ios

# Android
npx cap open android
```

### Нативные возможности

- Камера (фото для портфолио)
- Push-уведомления
- Определение сети (online/offline)
- Локальное хранилище (Preferences)
- Haptics (тактильная отдача)
- Управление StatusBar и Keyboard

---

## Деплой

### Production

```bash
# Сборка production-образов
make prod-build

# Запуск
make prod-up

# Остановка
make prod-down

# Логи
make prod-logs
```

### Production-стек

- **Nginx** -- reverse proxy с SSL (порты 80/443)
- **Django + Gunicorn** -- 4 воркера, 2 потока
- **Celery** -- 4 конкурентных воркера
- **Celery Beat** -- планировщик периодических задач
- **PostgreSQL 16** -- с парольной защитой
- **Redis 7** -- с парольной защитой

### Периодические задачи (Celery Beat)

| Задача | Расписание |
|--------|-----------|
| Напоминания о записях | 09:00 ежедневно |
| Автоматическая пометка неявок | 00:30 ежедневно |
| Проверка истекающих подписок | 10:00 ежедневно |
| Продление подписок | 06:00 ежедневно |
| Сброс месячных лимитов | 00:05 1-го числа |
| Синхронизация статусов платежей | Каждые 10 минут |
| Архивация старых записей | 03:00 по воскресеньям |

---

## Переменные окружения

Скопируйте `.env.example` в `.env` и заполните значения:

```bash
cp .env.example .env
```

### Django

| Переменная | Описание | По умолчанию |
|-----------|----------|-------------|
| `DJANGO_ENV` | Окружение (development/production) | `development` |
| `DJANGO_DEBUG` | Режим отладки | `True` |
| `DJANGO_SECRET_KEY` | Секретный ключ Django | -- |
| `DJANGO_ALLOWED_HOSTS` | Разрешенные хосты | `localhost,127.0.0.1` |

### База данных

| Переменная | Описание | По умолчанию |
|-----------|----------|-------------|
| `POSTGRES_DB` | Имя базы данных | `beautystyle` |
| `POSTGRES_USER` | Пользователь БД | `postgres` |
| `POSTGRES_PASSWORD` | Пароль БД | `postgres` |

### Redis

| Переменная | Описание | По умолчанию |
|-----------|----------|-------------|
| `REDIS_PASSWORD` | Пароль Redis (prod) | -- |

### Платежи (YooKassa)

| Переменная | Описание |
|-----------|----------|
| `YOOKASSA_SHOP_ID` | ID магазина YooKassa |
| `YOOKASSA_SECRET_KEY` | Секретный ключ YooKassa |
| `YOOKASSA_WEBHOOK_SECRET` | Секрет для проверки webhook |

### Email (SMTP)

| Переменная | Описание | По умолчанию |
|-----------|----------|-------------|
| `EMAIL_HOST` | SMTP-сервер | `smtp.gmail.com` |
| `EMAIL_PORT` | Порт | `587` |
| `EMAIL_HOST_USER` | Email отправителя | -- |
| `EMAIL_HOST_PASSWORD` | Пароль | -- |

### AI

| Переменная | Описание |
|-----------|----------|
| `OLLAMA_URL` | URL сервиса Ollama |
| `PERPLEXITY_API_KEY` | API-ключ Perplexity |

---

## Порты (dev-окружение)

| Сервис | Порт | URL |
|--------|------|-----|
| Nginx | 80 | http://localhost |
| Angular | 4200 | http://localhost:4200 |
| Django API | 8000 | http://localhost:8000 |
| PostgreSQL | 5432 | -- |
| Redis | 6379 | -- |
| Flower | 5555 | http://localhost:5555 |
| Ollama | 11434 | http://localhost:11434 |

---

## Лицензия

Проприетарное ПО. Все права защищены.
