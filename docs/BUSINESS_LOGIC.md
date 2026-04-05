# BeautyStyleService (Belvra) — Полная бизнес-логика

> Актуально на: 2026-04-05
> Стек: Django 6 + Angular 17 + PostgreSQL + Redis + Celery + T-Bank

---

## 1. Пользователи и роли

### 1.1 Модель User

| Поле | Тип | Default | Описание |
|------|-----|---------|----------|
| id | UUID | auto | Первичный ключ |
| email | EmailField | required, unique | Основной идентификатор |
| phone | CharField(20) | blank | Телефон |
| first_name / last_name | CharField(150) | blank | ФИО |
| avatar | ImageField | null | Аватар (JPEG/PNG/GIF/WebP, max 5MB) |
| role | CharField | CLIENT | CLIENT / MASTER / ADMIN |
| is_verified | BooleanField | False | Email подтверждён |
| is_active | BooleanField | True | Аккаунт активен |
| is_early_adopter | BooleanField | False | Ранний пользователь |
| referral_code | CharField(8) | auto | Уникальный реферальный код (A-Z, 0-9) |
| referred_by | FK(self) | null | Кто пригласил |
| privacy_accepted_at | DateTimeField | null | Дата принятия политики |
| terms_accepted_at | DateTimeField | null | Дата принятия условий |
| privacy_version_accepted | CharField | blank | Версия политики |
| terms_version_accepted | CharField | blank | Версия условий |

### 1.2 Модель MasterProfile

Связана с User через OneToOneField (CASCADE).

| Поле | Тип | Default | Описание |
|------|-----|---------|----------|
| id | UUID | auto | PK (отличается от user.id) |
| bio | TextField | blank | Описание мастера |
| experience_years | PositiveInt | 0 | Стаж в годах |
| specialization | CharField(255) | blank | Специализация |
| rating | Decimal(3,2) | 0.00 | Средний рейтинг (авто-пересчёт) |
| reviews_count | PositiveInt | 0 | Кол-во отзывов (авто-пересчёт) |
| is_available | BooleanField | True | Доступен для записи |
| address | CharField(255) | blank | Адрес |
| latitude / longitude | Decimal(9,6) | null | Координаты для геопоиска |
| telegram, instagram, vk, whatsapp | CharField | blank | Соцсети |
| email_notifications | BooleanField | True | Уведомления на email |
| sms_notifications | BooleanField | False | SMS (не реализовано) |
| push_notifications | BooleanField | True | Push-уведомления |
| reminder_hours | PositiveInt | 24 | За сколько часов напоминать |
| rebooking_reminder_days | PositiveInt | 0 | Авто-напоминание о перезаписи (0=выкл) |

### 1.3 Избранные мастера (FavoriteMaster)

- Уникальная пара: (user, master)
- Лимит определяется подпиской: FREE = 5, PRO = безлимит
- Добавление/удаление через toggle endpoint (атомарная операция с `select_for_update`)

---

## 2. Регистрация и авторизация

### 2.1 Регистрация

1. Пользователь отправляет email + password + role
2. Создаётся User (is_verified=False)
3. Генерируется 6-значный код верификации → кэш на 10 минут (`email_verify_code_{user_id}`)
4. Отправляется email с кодом
5. **Early Adopter** (is_early_adopter=True): пожизненный PRO (period_end=NULL)
6. **Все остальные**: бесплатный PRO-trial на 30 дней (period_end=now+30d, auto_renew=False)
7. Если указан реферальный код: создаётся запись Referral (status=PENDING)
8. Возвращаются JWT-токены + профиль

### 2.2 Верификация email

- POST с 6-значным кодом
- Код проверяется против кэша
- При совпадении: is_verified=True, кэш удаляется, отправляется welcome email

### 2.3 Авторизация

- JWT-токены: access (60 мин), refresh (7 дней)
- Ротация refresh-токенов с blacklist
- Rate limit: login 10/мин, register 5/мин

### 2.4 Сброс пароля

1. Запрос: генерируется `secrets.token_urlsafe(32)` → кэш на 1 час
2. Email с ссылкой: `{FRONTEND_URL}/reset-password?token={token}`
3. Подтверждение: токен валидируется, пароль обновляется, кэш удаляется

### 2.5 Становление мастером

- Если у пользователя уже есть master_profile: просто меняется role на MASTER
- Если нет: атомарная транзакция создаёт MasterProfile + меняет role

### 2.6 Удаление аккаунта

- Требует подтверждение паролем
- Все refresh-токены в blacklist
- Каскадное удаление всех связанных данных

---

## 3. Записи (Appointments)

### 3.1 Модель Appointment

| Поле | Тип | Default | Описание |
|------|-----|---------|----------|
| client | FK(User) | required | Клиент |
| master | FK(MasterProfile) | required | Мастер |
| service | FK(Service) | null | Каталожная услуга |
| master_service | FK(MasterService) | null | Услуга мастера |
| date | DateField | required | Дата записи |
| start_time / end_time | TimeField | required | Время |
| status | CharField | PENDING | Статус |
| price | Decimal(10,2) | required | Цена услуги |
| notes | TextField | blank | Заметки |
| used_materials | JSONField | [] | Список материалов |
| materials_cost | Decimal(10,2) | 0 | Стоимость материалов |
| cancelled_at | DateTimeField | null | Когда отменено |
| cancellation_reason | TextField | blank | Причина отмены |
| is_archived | BooleanField | False | Архивировано |

### 3.2 Статусы и переходы

```
PENDING → CONFIRMED → COMPLETED
       ↘ CANCELLED     ↘ CANCELLED
                        ↘ NO_SHOW
```

Допустимые переходы:
- pending → [confirmed, cancelled]
- confirmed → [completed, cancelled, no_show]
- completed, cancelled, no_show → [] (терминальные)

### 3.3 Создание записи — правила валидации

1. **Дата**: не в прошлом, не далее 30 дней вперёд
2. **Время**: не в прошлом (если сегодня)
3. **Самозапись**: нельзя записаться к себе
4. **Расписание**: мастер должен работать в этот день недели
5. **Рабочие часы**: start_time >= schedule.start_time И < schedule.end_time
6. **Длительность**: master_service.actual_duration → вычисляется end_time
7. **Конфликты**: нет пересечения с существующими PENDING/CONFIRMED записями
8. **Лимит подписки**: subscription.can_create_appointment() — FREE мастер max 10/мес
9. **Цена**: master_service.actual_price

### 3.4 Доступные слоты (Available Slots)

Алгоритм генерации:
1. Получить расписание мастера на день недели
2. Генерировать 30-минутные слоты от start_time до end_time
3. Для каждого слота проверить:
   - Не пересекается с PENDING/CONFIRMED записями
   - Не раньше min_booking_time (сейчас + min_advance_hours)
4. **min_advance_hours**: 2 часа (FREE) или 1 час (PRO с priority_booking)
5. Вернуть массив {start_time, end_time}

### 3.5 Отмена записи

- **Правило**: можно отменить не позднее чем за 2 часа до записи
- Определяется кто отменил (мастер/клиент)
- Email обеим сторонам + in-app уведомление другой стороне
- Статус: CANCELLED, cancelled_at=now

### 3.6 Перенос записи

- Можно перенести только PENDING или CONFIRMED
- Минимальное время: 2 часа (или 1 час для PRO с priority_booking)
- Валидация новой даты/времени аналогична созданию
- Статус сбрасывается на PENDING
- Уведомление другой стороне

### 3.7 Завершение записи

- Только мастер
- Переход: confirmed → completed

### 3.8 Перезапись (rebook)

- Только клиент, по своей записи
- Возвращает предзаполненные данные: master_id, service_id, name, price, duration
- Клиент затем создаёт новую запись через стандартный flow

### 3.9 Обновление материалов

- Только мастер, по своей записи
- Обновляет used_materials (JSON) и materials_cost

---

## 4. Расписание (WorkSchedule)

| Поле | Тип | Описание |
|------|-----|----------|
| master | FK(MasterProfile) | Мастер |
| weekday | IntegerField | 0=Пн ... 6=Вс |
| start_time / end_time | TimeField | Рабочие часы |
| is_working | BooleanField | Рабочий/нерабочий день |

- Уникальная пара: (master, weekday)
- Валидация: start_time < end_time
- Массовое обновление через bulk endpoint

---

## 5. Отзывы (Reviews)

| Поле | Тип | Описание |
|------|-----|----------|
| appointment | OneToOne(Appointment) | Связь с записью |
| rating | PositiveSmallInt | 1-5 звёзд |
| comment | TextField | Текст отзыва |

Правила:
- Один отзыв на одну запись
- Только для COMPLETED записей
- Только клиент записи может оставить
- **Авто-пересчёт рейтинга мастера**: AVG(rating) и COUNT по всем отзывам

---

## 6. Услуги

### 6.1 Каталог (Category + Service)

- **Category**: name, slug, description, image, is_active, order
- **Service**: category FK, name, slug, price, duration (мин), is_popular

### 6.2 Услуги мастера (MasterService) — двойной режим

**Каталожная услуга**: service FK установлен, можно переопределить цену/длительность
**Кастомная услуга**: service=NULL, custom_name обязательно

| Свойство | Логика |
|----------|--------|
| name | custom_name если есть, иначе service.name |
| actual_price | self.price если есть, иначе service.price |
| actual_duration | self.duration если есть, иначе service.duration |
| is_custom | service is None |

Ограничения:
- Unique: (master, service) для каталожных
- Unique: (master, custom_name) для кастомных
- Лимит подписки: FREE max 5 услуг, PRO безлимит

---

## 7. Портфолио

### 7.1 PortfolioItem

| Поле | Тип | Default | Описание |
|------|-----|---------|----------|
| master | FK(MasterProfile) | required | Мастер |
| title | CharField(200) | required | Название работы |
| description | TextField | blank | Описание |
| image | ImageField | required | Фото работы |
| service | FK(Service) | null | Категоризация |
| hashtags | JSONField | [] | Хештеги |
| likes_count | PositiveInt | 0 | Кол-во лайков |
| is_published | BooleanField | True | Опубликовано |
| is_pinned | BooleanField | False | Закреплено наверху (PRO) |

Сортировка: [-is_pinned, -created_at] (закреплённые первыми)

### 7.2 Лайки (PortfolioLike)

- Уникальная пара: (user, portfolio_item)
- Атомарное обновление: `F("likes_count") + 1` / `F("likes_count") - 1`
- Идемпотентность: get_or_create для лайка, delete для анлайка

### 7.3 Закрепление (pin)

- PRO: max_pinned_portfolio=3 (default)
- FREE: max_pinned_portfolio=0 (нельзя)
- Toggle: is_pinned = !is_pinned
- Проверка: current_pinned_count < max_pinned перед закреплением

---

## 8. Подписки

### 8.1 Планы (SubscriptionPlan)

**FREE мастер** (создаётся автоматически):
| Параметр | Значение |
|----------|----------|
| Цена | 0 ₽ |
| Записей в месяц | 10 |
| Услуг | 5 |
| Портфолио | 5 |
| Буст в поиске | Нет |
| AI-ассистент | Нет |
| Аналитика | NONE |
| Экспорт | Нет |
| PRO-бейдж | Нет |
| Заметки о клиентах | Нет |
| Закрепление портфолио | 0 |
| Напоминания о перезаписи | Нет |
| Расширенные уведомления | Нет |

**PRO мастер** (цена задаётся в Django Admin, в тестах 999 ₽/мес):
| Параметр | Значение |
|----------|----------|
| Записей в месяц | Безлимит (0) |
| Услуг | Безлимит (0) |
| Портфолио | Безлимит (0) |
| Буст в поиске | Да |
| AI-ассистент | Да |
| Аналитика | ADVANCED |
| Экспорт | Да |
| PRO-бейдж | Да |
| Заметки о клиентах | Да |
| Закрепление портфолио | 3 |
| Напоминания о перезаписи | Да |
| Расширенные уведомления | Да |

**FREE клиент**:
| Параметр | Значение |
|----------|----------|
| Приоритетная запись | Нет (2ч вперёд) |
| Расширенный поиск | Нет |
| История записей | 3 месяца |
| Статистика | Нет |
| Избранных мастеров | 5 |

**PRO клиент** (цена задаётся в Django Admin, в тестах 299 ₽/мес):
| Параметр | Значение |
|----------|----------|
| Приоритетная запись | Да (1ч вперёд) |
| Расширенный поиск | Да |
| История записей | Вся (0) |
| Статистика | Да |
| Избранных мастеров | Безлимит (0) |

**Early Adopter PRO** (пожизненно, 0 ₽):
- Все PRO-фичи включены
- period_end = NULL (не истекает)
- auto_renew = False
- Нельзя отменить/изменить (API возвращает 403)

### 8.2 Подписка (Subscription)

**Статусы:**
```
PENDING → ACTIVE → (продление) → ACTIVE → ...
                 → EXPIRED → downgrade → FREE (ACTIVE)
                 → CANCELLED
                 → PAST_DUE → retry/expire
```

| Свойство | Логика |
|----------|--------|
| is_active | status==ACTIVE AND (period_end > now OR period_end==NULL) |
| days_until_expiry | max(0, period_end - now) в днях |

**Использование (usage tracking):**
- appointments_this_month: инкрементируется при создании записи (в perform_create)
- last_usage_reset: дата последнего сброса
- Сброс: 1-го числа каждого месяца (Celery task)

**Проверка лимитов:**
- can_create_appointment(): limit==0 OR used < limit
- can_add_service(count): limit==0 OR count < limit
- can_add_portfolio_item(count): limit==0 OR count < limit
- Конвенция: 0 = безлимит

### 8.3 Денежный поток оплаты

```
1. Клиент → POST /subscriptions/subscribe/ {plan_id}
2. Backend → SubscriptionPayment (PENDING)
3. Backend → T-Bank Init API (сумма в копейках, Recurrent=Y)
4. T-Bank → confirmation_url → Frontend redirect
5. Пользователь → оплата на странице T-Bank
6. T-Bank → webhook POST /subscriptions/webhook/ {Status: CONFIRMED}
7. Backend → process_successful_payment():
   - payment.status = SUCCEEDED, paid_at = now
   - subscription.status = ACTIVE
   - subscription.period_start = now
   - subscription.period_end = now + 30d (monthly) / 365d (yearly)
   - subscription.tbank_rebill_id = RebillId (для автоплатежей)
   - Применяется реферальная награда если есть
```

### 8.4 Автопродление

Celery задача `renew_subscriptions` (ежедневно 06:00):

1. Найти подписки: status=ACTIVE/PAST_DUE, period_end <= now, auto_renew=True, есть tbank_rebill_id
2. Для каждой:
   - Создать SubscriptionPayment (is_recurring=True)
   - T-Bank Init → Charge (списание по сохранённой карте)
   - Webhook подтвердит → process_successful_payment()
3. При ошибке: status = PAST_DUE, payment.status = FAILED

### 8.5 Истечение и даунгрейд

- **expire_subscriptions** (01:00): ACTIVE + period_end < now + (auto_renew=False ИЛИ cancel_at_period_end=True) → EXPIRED
- **downgrade_to_free** (02:00): EXPIRED + tier != FREE → перевод на FREE план (ACTIVE, period_end=NULL)
- **check_expiring_subscriptions** (10:00): уведомление за 3 дня до истечения

### 8.6 Отмена подписки

**Немедленная** (immediately=True):
- status = CANCELLED, cancelled_at = now, auto_renew = False

**В конце периода** (immediately=False):
- cancel_at_period_end = True, auto_renew = False
- Работает до period_end, потом expire → downgrade

### 8.7 Реферальная программа

| Поле | Описание |
|------|----------|
| referrer | Кто пригласил |
| referred_user | Кого пригласили |
| reward_type | FREE_MONTH_PRO |
| status | PENDING → APPLIED / EXPIRED |

Механика:
- Когда referred_user оплачивает PRO:
  - Если referrer на FREE → апгрейд до PRO на 30 дней
  - Если referrer на PRO → +30 дней к period_end
  - referral.status = APPLIED

---

## 9. Чат

### 9.1 Chat Model

- Уникальная пара: (master, client)
- is_active: bool
- Свойства: last_message, unread_count_for_master, unread_count_for_client

### 9.2 ChatMessage

| Поле | Тип | Описание |
|------|-----|----------|
| chat | FK(Chat) | Чат |
| sender | FK(User) | Отправитель |
| sender_role | MASTER / CLIENT | Роль |
| content | TextField | Текст (может быть пустым для файлов) |
| message_type | TEXT / IMAGE / FILE / AUDIO | Тип сообщения |
| file | FileField | Файл (max 50MB) |
| is_read | BooleanField | Прочитано |
| read_at | DateTimeField | Когда прочитано |
| reply_to | FK(self) | Ответ на сообщение (треды) |

### 9.3 Функции чата

- **Отправка**: POST с text или multipart file upload
- **Типы файлов**: автоопределение (image/* → IMAGE, audio/* → AUDIO, остальное → FILE)
- **Печатает**: Redis cache с TTL 6 сек (`chat_typing:{chat_id}:{user_id}`)
- **Прочитано**: batch mark_read для всех непрочитанных
- **Поиск**: по содержимому сообщений
- **Пагинация**: 40 сообщений на страницу
- **Уведомления**: in-app нотификация при новом сообщении (превью до 100 символов)
- **Архитектура**: REST-polling (НЕ WebSocket)

---

## 10. AI-функции

### 10.1 Доступ

- PRO only: проверяется через HasAIAccess permission (ai_assistant_enabled в плане)
- FREE → 403 "AI-ассистент доступен только на тарифе PRO"

### 10.2 Анализ фото (analyze_photo)

Модель: Ollama moondream:1.8b-v2-q4_K_M (локальная vision-модель)

Типы анализа:
- **general**: тип, описание, детали, цвета, качество фото
- **style**: стиль, тренды, целевая аудитория, сезон
- **quality**: оценки 1-10 (overall, technical, creativity, cleanliness), рекомендации
- **recommendation**: форма лица, тон кожи, рекомендуемые услуги, палитра

### 10.3 Генерация контента портфолио

- Вход: фото (base64)
- Выход: описание (2-3 предложения на русском) + массив хештегов

### 10.4 Подсказки в чате

- Модель: Perplexity API (sonar)
- Вход: последние 10 сообщений + последнее сообщение клиента
- Выход: 3 варианта ответа (max 50 символов каждый)

### 10.5 AI-поиск мастеров

- Модель: Perplexity API
- Вход: текстовый запрос + массив мастеров
- Выход: массив master_id отсортированный по релевантности
- Fallback: возврат исходного порядка при ошибке

---

## 11. Поиск мастеров

### 11.1 Текстовый поиск (?q=)

Поиск по полям:
- user.first_name, user.last_name (icontains)
- specialization, bio, address (icontains)
- MasterService.custom_name, Service.name (icontains через subquery)

### 11.2 Геопоиск (?lat=&lng=&radius_km=)

- Формула Хаверсина: `R * acos(sin(lat1)*sin(lat2) + cos(lat1)*cos(lat2)*cos(lng2-lng1))`
- R = 6371 км
- Фильтр: distance_km <= radius_km (default 10 км)
- Сортировка: по расстоянию (ближайшие первыми)

### 11.3 Буст PRO (search_boost_enabled)

- PRO мастера с search_boost_enabled=True получают boost=0
- Остальные: boost=1
- Сортировка: boost ASC → по distance/rating
- Реализация: Case/When аннотация в queryset

### 11.4 Расширенные фильтры (extended_search, PRO клиенты)

- min_rating: мин. рейтинг (float)
- min_experience: мин. опыт в годах (int)
- sort_by: rating / experience / reviews / distance

---

## 12. Уведомления

### 12.1 In-app уведомления (Notification)

Типы:
- APPOINTMENT_NEW, APPOINTMENT_CONFIRMED, APPOINTMENT_CANCELLED
- APPOINTMENT_RESCHEDULED, APPOINTMENT_REMINDER, APPOINTMENT_COMPLETED
- REVIEW_NEW
- PAYMENT_RECEIVED, PAYMENT_REFUNDED
- CHAT_MESSAGE
- SYSTEM

**Расширенные типы** (только PRO с advanced_notifications):
- APPOINTMENT_REMINDER
- REVIEW_NEW

### 12.2 Email-уведомления

8 шаблонов:
- welcome.html — приветствие
- email_verification_code.html — код верификации
- password_reset.html — сброс пароля
- appointment_confirmation.html — подтверждение записи (клиенту)
- appointment_reminder.html — напоминание за 24ч (клиенту)
- appointment_cancelled.html — отмена (обеим сторонам)
- new_appointment_master.html — новая запись (мастеру)
- new_review.html — новый отзыв (мастеру)

SMTP: Yandex (smtp.yandex.ru:465, SSL)
From: Belvra <noreply@belvra.ru>

### 12.3 Push-уведомления

- DeviceToken модель: user, token, platform (IOS/ANDROID/WEB)
- Фреймворк существует, FCM/APNs НЕ подключены
- Токены регистрируются/деактивируются через API

---

## 13. Заметки о клиентах (ClientNote)

PRO-фича для мастеров (client_notes_enabled).

| Поле | Тип | Описание |
|------|-----|----------|
| master | FK(MasterProfile) | Мастер |
| client | FK(User) | Клиент |
| text | TextField | Текст заметки |

- Уникальная пара: (master, client)
- CRUD через ViewSet
- FREE → "Заметки о клиентах доступны только на тарифе PRO"

---

## 14. Список дел (TodoItem)

| Поле | Тип | Default | Описание |
|------|-----|---------|----------|
| master | FK(MasterProfile) | required | Мастер |
| title | CharField | required | Название |
| description | TextField | blank | Описание |
| date | DateField | required | Дата |
| time | TimeField | null | Время (опционально) |
| status | CharField | TODO | TODO / IN_PROGRESS / DONE |
| priority | CharField | MEDIUM | LOW / MEDIUM / HIGH |

Эндпоинты: CRUD + by-date/{date}/ + today/ + stats/ + update_status/

---

## 15. Финансы мастера

Платформа НЕ проводит платежи между пользователями. Клиенты платят мастерам напрямую.

Финансы = учёт на основе завершённых записей:
- **Общий доход**: SUM(price) завершённых записей
- **Расходы на материалы**: SUM(materials_cost)
- **Чистый доход**: доход - материалы
- **Средний чек**: AVG(price)

Экспорт в CSV (PRO, export_data_enabled):
- Тип "appointments": Дата, Время, Клиент, Услуга, Цена, Статус
- Тип "finances": Дата, Клиент, Услуга, Доход, Материалы, Чистый доход

---

## 16. Аналитика (AnalyticsView)

Уровни зависят от analytics_level в подписке:

**NONE** (FREE): total_appointments, rating

**BASIC**: + weekly_appointments (7 дней), weekly_revenue, service_popularity

**ADVANCED** (PRO): + monthly/quarterly revenue, conversion_rate (confirmed+completed / total %),
rating_trend (помесячный avg рейтинга), top_services_by_revenue (top 10)

---

## 17. Celery-задачи (расписание)

| Задача | Расписание | Описание |
|--------|-----------|----------|
| send_appointment_reminders | 09:00 ежедневно | Email+push напоминание за 24ч |
| mark_no_show_appointments | 00:30 ежедневно | Авто-complete прошедших, no_show pending |
| cleanup_old_appointments | Вс 03:00 | Архивация записей старше 1 года |
| send_completion_reminder | каждые 15 мин | Напоминание мастеру завершить запись |
| check_expiring_subscriptions | 10:00 ежедневно | Уведомление за 3 дня до истечения |
| renew_subscriptions | 06:00 ежедневно | Автопродление через T-Bank Charge |
| expire_subscriptions | 01:00 ежедневно | Перевод в EXPIRED |
| downgrade_to_free | 02:00 ежедневно | Даунгрейд EXPIRED → FREE |
| reset_monthly_usage | 1-го числа 00:05 | Сброс appointments_this_month |
| notify_past_due_subscriptions | 11:00 ежедневно | Уведомление о просрочке |
| cleanup_expired_tokens | 00:00 ежедневно | Очистка JWT blacklist |
| cleanup_unverified_accounts | каждые 6ч | Удаление неверифицированных > 5 мин |
| close_overdue_todos | 00:15 ежедневно | Закрытие просроченных todo |
| cleanup_old_notifications | Вс 04:00 | Очистка старых уведомлений |
| send_rebooking_reminders | 10:30 ежедневно | Авто-напоминание клиентам (PRO) |

---

## 18. T-Bank интеграция

| Параметр | Значение |
|----------|----------|
| TBANK_TERMINAL_KEY | env (DEMO по умолчанию) |
| TBANK_PASSWORD | env (DEMO) |
| TBANK_API_URL | https://securepay.tinkoff.ru/v2/ |
| TBANK_SEND_RECEIPT | False (FZ-54) |
| TBANK_TAXATION | usn_income |

Методы:
- **Init**: создание платежа (amount в копейках, OrderId, Recurrent=Y)
- **Charge**: списание по RebillId (автоплатёж)
- **verify_notification_token**: SHA-256 проверка webhook-подписи
- **Test mode**: если terminal_key пуст → mock URL с test_ prefix

---

## 19. ФЗ-152 и GDPR

- **Политика конфиденциальности**: v1.2 от 30.03.2026
- **Условия использования**: v1.2 от 30.03.2026
- **Согласие**: трекинг версий, даты принятия
- **Отзыв согласия**: деактивация аккаунта (is_active=False)
- **Удаление данных**: полное каскадное удаление всех данных пользователя
- **Проверка актуальности**: API сравнивает version_accepted vs current_version

---

## 20. Конфигурация

**JWT**: access 60 мин, refresh 7 дней, ротация + blacklist

**Rate Limiting**: anon 500/ч, user 5000/ч, login 10/мин, register 5/мин

**Cache**: Redis (localhost:6379/0)

**Celery**: broker Redis /1, result Redis /2

**Файлы**: загрузка через UUID-имена (предотвращение перезаписи)

**Аватар**: JPEG/PNG/GIF/WebP, max 5MB

**Файлы чата**: max 50MB
