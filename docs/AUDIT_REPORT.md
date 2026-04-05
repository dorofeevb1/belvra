# BeautyStyleService — Полный аудит кодовой базы

> Дата: 2026-04-05
> Аудитор: Claude Opus 4.6 (автоматизированный аудит)

---

## Сводка

| Severity | Кол-во | Описание |
|----------|--------|----------|
| **CRITICAL** | 8 | Приложение падает, данные теряются, безопасность скомпрометирована |
| **HIGH** | 16 | Функционал сломан, race condition, IDOR |
| **MEDIUM** | 18 | Edge case, потенциальная проблема при нагрузке |
| **LOW** | 10 | Code smell, оптимизация |
| **Итого** | **52** | |

---

## TOP-10 для немедленного исправления

| # | ID | Severity | Проблема |
|---|-----|----------|----------|
| 1 | BUG-01 | CRITICAL | `ClientStatsView` — F("master__user__full_name") падает с FieldError (full_name это property, не поле) |
| 2 | BUG-02 | CRITICAL | `NotificationService.create_notification()` вызывается с `data=` kwarg который не существует — TypeError в 3 Celery тасках |
| 3 | BUG-04 | CRITICAL | Лимит услуг мастера НИКОГДА не работает — `getattr(master, 'subscription')` всегда None (Subscription на User, не MasterProfile) |
| 4 | SEC-01 | CRITICAL | Захардкоженные T-Bank DEMO-креды как дефолты в settings |
| 5 | SEC-02 | CRITICAL | SECRET_KEY дефолт "change-me-in-production" |
| 6 | SEC-03 | CRITICAL | Email verification code brute-force — нет throttle на verify endpoint |
| 7 | S-06 | HIGH | T-Bank REVERSED webhook не деактивирует подписку (чарджбэк проходит, подписка остаётся) |
| 8 | S-11 | HIGH | Самореферал не запрещён — пользователь может пригласить себя и получить бесплатный PRO |
| 9 | BUG-06 | HIGH | Все проверки PRO-фич НЕ проверяют sub.is_active — истёкшие подписки сохраняют доступ |
| 10 | BUG-03 | CRITICAL | ChatSerializer.master_avatar ссылается на master.avatar — но avatar на User, не MasterProfile |

---

## 1. БАГИ (CRITICAL + HIGH)

### [CRITICAL] BUG-01: ClientStatsView падает с FieldError
**Файл:** `appointments/views.py:742`
**Проблема:** `F("master__user__full_name")` — `full_name` это @property, не поле БД. Endpoint всегда возвращает 500.
**Решение:** Использовать `Concat(F("master__user__first_name"), Value(" "), F("master__user__last_name"))`.

### [CRITICAL] BUG-02: TypeError в 3 Celery тасках — `data=` kwarg
**Файлы:** `subscriptions/tasks.py:44,211`, `appointments/tasks.py:163`
**Проблема:** `NotificationService.create_notification()` не принимает `data=` параметр. Таски `check_expiring_subscriptions`, `notify_past_due_subscriptions`, `send_completion_reminder` падают.
**Решение:** Убрать `data=` из вызовов или добавить параметр в метод.

### [CRITICAL] BUG-03: Chat master_avatar всегда null
**Файл:** `chat/serializers.py:67`
**Проблема:** `source="master.avatar"` — avatar на User, не MasterProfile. Всегда None.
**Решение:** Изменить на `source="master.user.avatar"`.

### [CRITICAL] BUG-04: Лимит услуг мастера никогда не работает
**Файл:** `services/views.py:154`
**Проблема:** `getattr(master, 'subscription', None)` — master это MasterProfile, а Subscription привязан к User. Всегда None → лимит не проверяется.
**Решение:** Изменить на `getattr(master.user, 'subscription', None)`.

### [HIGH] BUG-05: cancel_subscription падает если period_end=None
**Файл:** `subscriptions/services.py:316`
**Проблема:** `subscription.current_period_end.strftime(...)` — NoneType has no attribute 'strftime'. Любая подписка без period_end (free, lifetime) крашит.
**Решение:** Добавить проверку на None.

### [HIGH] BUG-06: PRO-фичи работают после истечения подписки
**Файлы:** `ai/permissions.py:17`, `appointments/views.py:173,711,848`, `services/views.py:311`, `subscriptions/views.py:542,624`, `users/views.py:1301`
**Проблема:** Проверяется `sub.plan.feature_flag` без `sub.is_active`. Истёкшая подписка = все PRO-фичи доступны.
**Решение:** Везде добавить `sub.is_active and sub.plan.<feature>`.

### [HIGH] BUG-07: Любой пользователь может обновить/удалить чужой отзыв
**Файл:** `appointments/views.py:762-778`
**Проблема:** `ReviewViewSet` не проверяет ownership при update/delete. Queryset возвращает все отзывы.
**Решение:** Добавить проверку `review.appointment.client == request.user`.

### [HIGH] BUG-08: PortfolioItem update/destroy крашит для клиентов
**Файл:** `services/views.py:224-233`
**Проблема:** `self.request.user.master_profile` без hasattr → RelatedObjectDoesNotExist для клиентов.
**Решение:** Добавить проверку `hasattr(self.request.user, "master_profile")`.

### [HIGH] BUG-09: Service CASCADE удаляет все записи
**Файл:** `appointments/models.py:78`, `services/models.py:82`
**Проблема:** `Appointment.service` и `MasterService.service` — `on_delete=CASCADE`. Удаление услуги из каталога удаляет все записи клиентов.
**Решение:** Изменить на `SET_NULL` (оба поля уже nullable).

### [HIGH] BUG-10: Аккаунт удаляется через 5 мин, код валиден 10 мин
**Файл:** `core/tasks.py:21`
**Проблема:** `cleanup_unverified_accounts` удаляет через 5 мин, но код верификации живёт 10 мин. Пользователь может ввести код для уже удалённого аккаунта.
**Решение:** Увеличить threshold до 10+ минут.

---

## 2. БЕЗОПАСНОСТЬ (CRITICAL + HIGH)

### [CRITICAL] SEC-01: T-Bank DEMO-креды в коде
**Файл:** `config/settings/base.py:303-304`
**Проблема:** `TBANK_TERMINAL_KEY` default="1774615155386DEMO", `TBANK_PASSWORD` default="cAk9hZfCjw6b3gqu"`. Если .env не настроен — приложение работает с демо-кредами.
**Решение:** Убрать дефолты, крашить при запуске без ключей.

### [CRITICAL] SEC-02: SECRET_KEY по умолчанию
**Файл:** `config/settings/base.py:18`
**Проблема:** `default="change-me-in-production"` — если env не задан, все JWT/CSRF/sessions скомпрометированы.
**Решение:** Убрать дефолт.

### [CRITICAL] SEC-03: Brute-force кода верификации
**Файл:** `users/views.py:678-717`
**Проблема:** `VerifyEmailView` — AllowAny, без throttle. 6-значный код, 10-мин окно.
**Решение:** Добавить throttle 5 попыток/10 мин на email.

### [CRITICAL] SEC-04: Password reset без rate limit
**Файл:** `users/views.py:558-595`
**Проблема:** 500 запросов/час → email bombing.
**Решение:** Throttle 3/15 мин на IP.

### [HIGH] SEC-05: Медиафайлы чата доступны без авторизации
**Файл:** `nginx/conf.d/prod.conf:95-99`
**Проблема:** `/media/` отдаётся nginx напрямую. Файлы из приватного чата доступны по URL.
**Решение:** Проксировать `/media/chat/` через Django с проверкой доступа.

### [HIGH] SEC-06: Chat file upload — нет фильтрации типов
**Файл:** `chat/views.py:94-136`
**Проблема:** Можно загрузить .py, .sh, .html, .svg с XSS.
**Решение:** Allowlist MIME типов.

### [HIGH] SEC-07: Avatar валидирует Content-Type, а не содержимое
**Файл:** `users/views.py:291-299`
**Проблема:** Клиент может подделать Content-Type и загрузить SVG с JavaScript.
**Решение:** Проверять magic bytes через python-magic или Pillow.

### [HIGH] SEC-08: Permissions-Policy блокирует геолокацию
**Файл:** `nginx/nginx.conf:51`
**Проблема:** `geolocation=(), microphone=()` — но приложение использует оба (карты, голосовые сообщения).
**Решение:** `geolocation=(self), microphone=(self)`.

---

## 3. RACE CONDITIONS + ЦЕЛОСТНОСТЬ

### [HIGH] S-01: appointments_this_month — read-modify-write без лока
**Файл:** `appointments/views.py:207-208`
**Проблема:** Два параллельных запроса могут оба прочитать count=9, оба пройти проверку, оба инкрементить до 10.
**Решение:** `select_for_update()` или `F("appointments_this_month") + 1`.

### [HIGH] S-06: REVERSED webhook не деактивирует подписку
**Файл:** `subscriptions/views.py:414-417`
**Проблема:** Чарджбэк T-Bank ставит payment=CANCELLED, но подписка остаётся ACTIVE.
**Решение:** При REVERSED после CONFIRMED → деактивировать/даунгрейдить подписку.

### [HIGH] S-11: Самореферал возможен
**Файл:** `subscriptions/services.py:611`
**Проблема:** Нет проверки referrer != referred_user. Пользователь может ввести свой код.
**Решение:** CHECK constraint или валидация в регистрации.

### [HIGH] Review.save() — пересчёт рейтинга без лока
**Файл:** `appointments/models.py:189-196`
**Проблема:** Два отзыва одновременно → стейл aggregate → неверный рейтинг.
**Решение:** `@transaction.atomic` + `select_for_update()` на мастере.

---

## 4. ПРОИЗВОДИТЕЛЬНОСТЬ

### [HIGH] P-02: Chat list загружает ВСЕ сообщения
**Файл:** `chat/views.py:44-59`
**Проблема:** `prefetch_related("messages")` грузит все сообщения каждого чата в список.
**Решение:** Убрать prefetch, использовать аннотации для last_message/unread_count.

### [HIGH] P-17: 9 эндпоинтов без пагинации
**Файлы:** upcoming, by_master (reviews), my_services, my_portfolio, by_master (portfolio), category services, todo by_date/today, bulk
**Проблема:** Возвращают все результаты без лимита.
**Решение:** Использовать `self.paginate_queryset()`.

### [MEDIUM] P-09/P-10: Analytics — 10-12 запросов без кэша
**Решение:** Кэшировать на 5-15 минут.

### [MEDIUM] P-11: Haversine без bounding box
**Решение:** Предфильтр по lat/lng ± delta перед тригонометрией.

### [MEDIUM] P-14: Subscription запрашивается на каждом запросе
**Решение:** select_related в аутентификации или кэш в JWT claims.

---

## 5. ИНФРАСТРУКТУРА

### [HIGH] Nginx Permissions-Policy блокирует геолокацию/микрофон
### [MEDIUM] Нет healthcheck для backend/celery/celery-beat контейнеров
### [MEDIUM] Нет memory/CPU лимитов в Docker (8 GB сервер)
### [MEDIUM] client_max_body_size=10M vs chat upload limit=50M (Nginx вернёт 413)
### [MEDIUM] 5 env vars отсутствуют в .env.example
### [MEDIUM] README устарел (упоминает YooKassa, Ionic Appflow, payments app)
### [HIGH] Nginx: orphaned /api/v1/payments/webhook/ location (app удалён)

---

## 6. ФРОНТЕНД

### [HIGH] Memory leaks — subscribe() без unsubscribe в 6+ компонентах
**Файлы:** client-chat, subscription, my-appointments, legal-page, payment-result, master-view
**Решение:** takeUntil(destroy$) или Subscription collector.

### [MEDIUM] Master interface не совпадает с MasterProfileSerializer
**Проблема:** Frontend ожидает description, workSchedule, services — backend не отдаёт.

### [MEDIUM] Нет глобального обработчика 500 ошибок

---

## 7. ТЕСТЫ

| App | Тесты | Покрытие |
|-----|-------|----------|
| appointments | 4 файла | Статусы, бронирование, лимиты — хорошо |
| subscriptions | 4 файла | Лимиты, lifecycle — хорошо |
| users | 3 файла | Геопоиск — хорошо |
| services | 2 файла | Базовое |
| chat | 2 файла | Базовое |
| todo | 2 файла | Базовое |
| **core** | **0 файлов** | **Нет тестов** |
| **ai** | **0 файлов** | **Нет тестов** |
