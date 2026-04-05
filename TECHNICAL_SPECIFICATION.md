# Belvra - Полное Техническое Задание

## Содержание
1. [Общее описание проекта](#1-общее-описание-проекта)
2. [Технический стек](#2-технический-стек)
3. [Архитектура системы](#3-архитектура-системы)
4. [База данных](#4-база-данных)
5. [Backend API](#5-backend-api)
6. [Frontend](#6-frontend)
7. [Платежная система](#7-платежная-система)
8. [Безопасность](#8-безопасность)
9. [Текущий статус реализации](#9-текущий-статус-реализации)
10. [Что нужно доделать](#10-что-нужно-доделать)
11. [Новые фичи для добавления](#11-новые-фичи-для-добавления)

---

## 1. Общее описание проекта

### 1.1 Назначение
**Belvra** — платформа для записи на услуги красоты, объединяющая клиентов и мастеров (парикмахеры, маникюр, косметологи и т.д.).

### 1.2 Целевая аудитория
- **Клиенты**: люди, ищущие услуги красоты
- **Мастера**: специалисты индустрии красоты (фрилансеры и салоны)
- **Администраторы**: управление платформой

### 1.3 Основные функции
- Поиск и бронирование услуг
- Управление расписанием мастеров
- Онлайн-оплата (YooKassa)
- Система отзывов и рейтингов
- Кошелек и вывод средств для мастеров
- Портфолио работ
- Чат между клиентом и мастером

---

## 2. Технический стек

### 2.1 Backend
| Технология | Версия | Назначение |
|------------|--------|------------|
| Python | 3.11+ | Язык программирования |
| Django | 5.0.1 | Web-фреймворк |
| Django REST Framework | 3.14.0 | REST API |
| PostgreSQL | 13+ | База данных |
| Redis | 7+ | Кэширование, очереди |
| Celery | 5.3.6 | Фоновые задачи |
| SimpleJWT | 5.3.1 | JWT аутентификация |
| YooKassa SDK | 3.3.0 | Платежная система |
| Gunicorn | 21.2.0 | WSGI сервер |
| WhiteNoise | 6.6.0 | Статические файлы |

### 2.2 Frontend
| Технология | Версия | Назначение |
|------------|--------|------------|
| Angular | 21.0.0 | Frontend фреймворк |
| TypeScript | 5.9.2 | Язык программирования |
| Tailwind CSS | 4.1.18 | CSS фреймворк |
| dayjs | 1.11.19 | Работа с датами |
| Google Gemini | 2.0 Flash | AI функции |
| Yandex Maps | - | Карты |

### 2.3 Инфраструктура
| Компонент | Технология |
|-----------|------------|
| Контейнеризация | Docker |
| Web-сервер | Nginx (production) |
| CI/CD | GitHub Actions (planned) |
| Мониторинг | Flower (Celery), Sentry (planned) |

---

## 3. Архитектура системы

### 3.1 Общая архитектура
```
┌─────────────────┐     ┌─────────────────┐
│   Angular SPA   │────▶│   Nginx/CDN     │
└─────────────────┘     └────────┬────────┘
                                 │
                                 ▼
┌─────────────────┐     ┌─────────────────┐
│   YooKassa      │◀───▶│   Django API    │
│   (Webhooks)    │     │   (Gunicorn)    │
└─────────────────┘     └────────┬────────┘
                                 │
        ┌────────────────────────┼────────────────────────┐
        ▼                        ▼                        ▼
┌───────────────┐       ┌───────────────┐       ┌───────────────┐
│  PostgreSQL   │       │    Redis      │       │    Celery     │
│  (Database)   │       │   (Cache)     │       │   (Workers)   │
└───────────────┘       └───────────────┘       └───────────────┘
```

### 3.2 Структура Backend
```
backend/
├── config/                 # Конфигурация Django
│   ├── settings/          # Настройки по окружениям
│   │   ├── base.py
│   │   ├── development.py
│   │   ├── production.py
│   │   └── test.py
│   ├── urls.py            # Главный роутинг
│   ├── celery.py          # Конфиг Celery
│   └── wsgi.py
├── apps/
│   ├── core/              # Базовые модели, permissions
│   ├── users/             # Пользователи, мастера, auth
│   ├── services/          # Услуги, категории
│   ├── appointments/      # Записи, расписания, отзывы
│   └── payments/          # Платежи, кошельки, выводы
└── requirements.txt
```

### 3.3 Структура Frontend
```
frontend/src/app/
├── core/
│   ├── guards/            # authGuard, masterGuard, clientGuard
│   ├── interceptors/      # JWT interceptor
│   ├── models/            # TypeScript интерфейсы
│   └── services/          # Auth, API, Data, Wallet и др.
├── features/
│   ├── auth/              # Логин
│   ├── master/            # Кабинет мастера (10 компонентов)
│   └── client/            # Кабинет клиента (6 компонентов)
├── shared/
│   ├── components/        # Header, Sidebar, Modal, Toast
│   ├── directives/        # DragDrop
│   └── pipes/             # CurrencyRub, DateFormat
└── app.routes.ts          # Роутинг
```

---

## 4. База данных

### 4.1 ER-диаграмма (основные связи)
```
User (1) ─────────────────── (1) MasterProfile
  │                                    │
  │ (many)                            │ (many)
  ▼                                    ▼
Appointment ◀─────────────────────── WorkSchedule
  │                                    │
  │ (1)                               │ (many)
  ▼                                    ▼
Review                            MasterService
                                       │
                                       ▼
                                    Service ◀── Category

MasterProfile (1) ─── (1) Wallet
                           │
                          ▼
                      Withdrawal
                      Payment
                      PayoutDestination
```

### 4.2 Модели данных

#### User (Пользователь)
| Поле | Тип | Описание |
|------|-----|----------|
| id | UUID | Primary Key |
| email | EmailField | Уникальный, для входа |
| password | CharField | Хешированный пароль |
| phone | CharField | Телефон |
| first_name | CharField | Имя |
| last_name | CharField | Фамилия |
| avatar | ImageField | Аватар |
| role | Enum | CLIENT / MASTER / ADMIN |
| is_active | Boolean | Активен ли аккаунт |
| is_verified | Boolean | Email подтвержден |
| created_at | DateTime | Дата создания |

#### MasterProfile (Профиль мастера)
| Поле | Тип | Описание |
|------|-----|----------|
| id | UUID | Primary Key |
| user | OneToOne | Связь с User |
| bio | TextField | Описание |
| experience_years | Integer | Опыт в годах |
| specialization | CharField | Специализация |
| rating | Decimal | Средний рейтинг (1-5) |
| reviews_count | Integer | Количество отзывов |
| is_available | Boolean | Принимает записи |

#### Service (Услуга)
| Поле | Тип | Описание |
|------|-----|----------|
| id | UUID | Primary Key |
| category | ForeignKey | Категория услуги |
| name | CharField | Название |
| slug | SlugField | URL-slug |
| description | TextField | Описание |
| price | Decimal | Базовая цена |
| duration | Integer | Длительность (минуты) |
| is_active | Boolean | Активна |
| is_popular | Boolean | Популярная |

#### Appointment (Запись)
| Поле | Тип | Описание |
|------|-----|----------|
| id | UUID | Primary Key |
| client | ForeignKey | Клиент |
| master | ForeignKey | Мастер |
| service | ForeignKey | Услуга |
| date | DateField | Дата записи |
| start_time | TimeField | Начало |
| end_time | TimeField | Окончание |
| status | Enum | pending/confirmed/completed/cancelled |
| price | Decimal | Стоимость |
| notes | TextField | Примечания |

#### Payment (Платеж)
| Поле | Тип | Описание |
|------|-----|----------|
| id | UUID | Primary Key |
| appointment | ForeignKey | Запись |
| client | ForeignKey | Клиент |
| master | ForeignKey | Мастер |
| payment_type | Enum | prepayment/full_payment/remaining/tip |
| status | Enum | pending/succeeded/failed/refunded |
| payment_method | Enum | card/sbp/yoomoney/cash |
| amount | Decimal | Сумма |
| commission | Decimal | Комиссия платформы (5%) |
| provider_fee | Decimal | Комиссия провайдера (~2%) |
| net_amount | Decimal | Сумма мастеру |
| external_payment_id | CharField | ID в YooKassa |
| confirmation_url | URLField | Ссылка на оплату |

#### Wallet (Кошелек мастера)
| Поле | Тип | Описание |
|------|-----|----------|
| id | UUID | Primary Key |
| master | OneToOne | Мастер |
| available_balance | Decimal | Доступно к выводу |
| pending_balance | Decimal | В ожидании (холд 3 дня) |
| hold_balance | Decimal | Заморожено |
| total_earned | Decimal | Всего заработано |
| total_withdrawn | Decimal | Всего выведено |
| auto_withdraw | Boolean | Автовывод |

---

## 5. Backend API

### 5.1 Аутентификация
| Метод | Endpoint | Описание |
|-------|----------|----------|
| POST | /api/v1/auth/register/ | Регистрация |
| POST | /api/v1/auth/login/ | Вход |
| POST | /api/v1/auth/logout/ | Выход |
| POST | /api/v1/auth/token/refresh/ | Обновление токена |
| GET | /api/v1/auth/profile/ | Получить профиль |
| PATCH | /api/v1/auth/profile/ | Обновить профиль |
| POST | /api/v1/auth/password/change/ | Сменить пароль |

### 5.2 Мастера
| Метод | Endpoint | Описание |
|-------|----------|----------|
| GET | /api/v1/auth/masters/ | Список мастеров |
| GET | /api/v1/auth/masters/{id}/ | Профиль мастера |

### 5.3 Услуги
| Метод | Endpoint | Описание |
|-------|----------|----------|
| GET | /api/v1/services/categories/ | Категории |
| GET | /api/v1/services/items/ | Все услуги |
| GET | /api/v1/services/items/popular/ | Популярные |
| GET | /api/v1/services/master-services/ | Услуги мастеров |

### 5.4 Записи
| Метод | Endpoint | Описание |
|-------|----------|----------|
| GET | /api/v1/appointments/bookings/ | Мои записи |
| POST | /api/v1/appointments/bookings/ | Создать запись |
| POST | /api/v1/appointments/bookings/{id}/cancel/ | Отменить |
| POST | /api/v1/appointments/bookings/{id}/confirm/ | Подтвердить |
| POST | /api/v1/appointments/bookings/{id}/complete/ | Завершить |
| POST | /api/v1/appointments/available-slots/ | Свободные слоты |
| GET | /api/v1/appointments/schedules/ | Расписание |
| POST | /api/v1/appointments/reviews/ | Оставить отзыв |

### 5.5 Платежи
| Метод | Endpoint | Описание |
|-------|----------|----------|
| GET | /api/v1/payments/wallet/ | Кошелек |
| GET | /api/v1/payments/wallet/stats/ | Статистика |
| POST | /api/v1/payments/payments/ | Создать платеж |
| GET | /api/v1/payments/payments/{id}/status/ | Статус платежа |
| POST | /api/v1/payments/payments/{id}/refund/ | Возврат |
| GET | /api/v1/payments/payout-destinations/ | Способы вывода |
| POST | /api/v1/payments/payout-destinations/ | Добавить способ |
| GET | /api/v1/payments/withdrawals/ | История выводов |
| POST | /api/v1/payments/withdrawals/ | Запрос вывода |
| POST | /api/v1/payments/webhook/yookassa/ | Webhook |

### 5.6 Celery задачи
| Задача | Расписание | Описание |
|--------|-----------|----------|
| cleanup_expired_tokens | Ежедневно 00:00 | Очистка токенов |
| send_appointment_reminders | Ежедневно 08:00 | Напоминания |
| release_held_funds | Каждый час | Разморозка средств |
| process_auto_withdrawals | Ежедневно 06:00 | Автовыводы |
| sync_payment_statuses | Каждые 10 мин | Синхронизация платежей |
| cleanup_expired_payments | Каждые 2 часа | Отмена старых платежей |

---

## 6. Frontend

### 6.1 Компоненты

#### Авторизация
| Компонент | Описание |
|-----------|----------|
| LoginComponent | Форма входа с поддержкой API и demo режима |

#### Кабинет мастера (/master)
| Компонент | Описание |
|-----------|----------|
| DashboardComponent | Главная: статистика, графики, активность |
| CalendarComponent | Календарь записей по неделям |
| KanbanBoardComponent | Kanban доска для задач |
| AppointmentsComponent | Список записей с фильтрами |
| PortfolioComponent | Портфолио работ с AI генерацией |
| ChatComponent | Чаты с клиентами + AI подсказки |
| FinancesComponent | Финансовая статистика |
| WalletComponent | Кошелек, выводы средств |
| SettingsComponent | Настройки профиля |

#### Кабинет клиента (/client)
| Компонент | Описание |
|-----------|----------|
| MasterSearchComponent | Поиск мастеров + AI поиск |
| MasterProfileComponent | Профиль мастера, услуги, отзывы |
| BookingCalendarComponent | Выбор даты и времени записи |
| MyAppointmentsComponent | Мои записи с оплатой |
| ClientProfileComponent | Профиль клиента |

#### Общие компоненты
| Компонент | Описание |
|-----------|----------|
| HeaderComponent | Шапка с темой, уведомлениями, меню |
| SidebarComponent | Боковая навигация |
| ModalComponent | Модальные окна |
| NotificationToastComponent | Уведомления |

### 6.2 Сервисы

| Сервис | Методы | Описание |
|--------|--------|----------|
| AuthService | login, logout, register | Авторизация |
| ApiService | HTTP методы для всех endpoints | API клиент |
| DataService | Услуги, записи, отзывы, портфолио | Данные |
| WalletService | Кошелек, транзакции, выводы | Финансы |
| DateService | Форматирование, локализация дат | Даты |
| ThemeService | toggleTheme, setTheme | Тема |
| NotificationService | success, error, warning, info | Уведомления |
| GeminiService | AI генерация, поиск, подсказки | AI |

### 6.3 Guards
| Guard | Защита |
|-------|--------|
| authGuard | Требует авторизации |
| masterGuard | Только для мастеров |
| clientGuard | Только для клиентов |
| guestGuard | Только для гостей |

### 6.4 Роуты
```
/login                    → LoginComponent (guestGuard)

/master                   → MasterView (masterGuard)
├── /dashboard           → Dashboard
├── /calendar            → Calendar
├── /kanban              → KanbanBoard
├── /appointments        → Appointments
├── /portfolio           → Portfolio
├── /chat                → Chat
├── /finances            → Finances
├── /wallet              → Wallet
└── /settings            → Settings

/client                   → ClientView (clientGuard)
├── /                    → MasterSearch
├── /master/:id          → MasterProfile
├── /booking/:masterId   → BookingCalendar
├── /my-appointments     → MyAppointments
└── /profile             → ClientProfile
```

---

## 7. Платежная система

### 7.1 Интеграция YooKassa

#### Процесс оплаты
```
1. Клиент нажимает "Оплатить"
2. Frontend → POST /api/v1/payments/payments/
3. Backend создает Payment + YooKassa payment
4. Backend возвращает confirmation_url
5. Клиент переходит по ссылке
6. После оплаты YooKassa шлет webhook
7. Backend обновляет статус Payment
8. Средства уходят в pending_balance (холд 3 дня)
9. Через 3 дня переходят в available_balance
```

#### Типы платежей
| Тип | Описание |
|-----|----------|
| prepayment | Предоплата (20%) |
| full_payment | Полная оплата |
| remaining | Доплата |
| tip | Чаевые |

#### Методы оплаты
| Метод | Описание |
|-------|----------|
| bank_card | Банковская карта |
| sbp | СБП (Система Быстрых Платежей) |
| yoomoney | ЮMoney |
| cash | Наличные (оффлайн) |

### 7.2 Комиссии
| Комиссия | Размер |
|----------|--------|
| Платформа | 5% (мин 10₽) |
| Провайдер | ~2% |
| Вывод на карту | 50₽ |
| Вывод на ЮMoney | 3% |
| Вывод на р/с | 1% |

### 7.3 Вывод средств
- Минимальная сумма: 100₽
- Автовывод: при балансе ≥ 1000₽
- Методы: карта, ЮMoney, банковский счет

---

## 8. Безопасность

### 8.1 Аутентификация
- JWT токены (Access: 60 мин, Refresh: 7 дней)
- Ротация refresh токенов
- Blacklist при ротации
- Хеширование паролей (PBKDF2)

### 8.2 Авторизация
- Роли: CLIENT, MASTER, ADMIN
- Permission классы для endpoints
- Object-level permissions

### 8.3 Защита API
- CORS whitelist
- CSRF protection
- Rate limiting (100/час анон, 1000/час auth)
- Валидация данных на уровне сериализаторов

### 8.4 Платежи
- Webhook signature verification
- Токенизация карт через YooKassa
- Холдирование средств 3 дня

---

## 9. Текущий статус реализации

### 9.1 Backend (100% MVP)
| Модуль | Статус | Примечание |
|--------|--------|------------|
| Аутентификация | ✅ | JWT, роли, профили |
| Пользователи | ✅ | User, MasterProfile |
| Регистрация | ✅ | Многошаговая форма + роль |
| Верификация email | ✅ | 6-значный код, Celery |
| Восстановление пароля | ✅ | Токен, сброс, email |
| Услуги | ✅ | CRUD, категории, кастомные |
| Записи | ✅ | Полный цикл + материалы |
| Расписание | ✅ | По дням недели, bulk |
| Отзывы | ✅ | С пересчетом рейтинга |
| Платежи | ✅ | YooKassa, SBP, test mode |
| Кошелек | ✅ | Балансы, холд, выводы |
| Подписки | ✅ | Free/Pro, авто-продление |
| Webhooks | ✅ | Все события + логирование |
| Celery | ✅ | 17 задач (расписание в base.py) |
| AI | ✅ | Perplexity + Ollama LLaVA |
| Уведомления | ✅ | In-app + email, 11 типов |
| Избранное | ✅ | FavoriteMaster, toggle |
| Чат | ✅ | Текст, файлы, аудио, reply |
| Портфолио | ✅ | Лайки с дедупликацией |

### 9.2 Frontend (~95% MVP)
| Модуль | Статус | Примечание |
|--------|--------|------------|
| Авторизация | ✅ | Вход, выход, JWT |
| Регистрация | ✅ | Многошаговая, роли |
| Верификация email | ✅ | 6 цифр, повторная отправка |
| Восстановление пароля | ✅ | Запрос, валидация, сброс |
| Dashboard | ✅ | Статистика, графики, карта |
| Календарь | ✅ | Неделя, kanban, todo |
| Записи мастера | ✅ | Статусы, материалы |
| Портфолио | ✅ | AI генерация, лайки |
| Чат | ✅ | AI подсказки, файлы, аудио |
| Кошелек | ✅ | YooKassa, выводы |
| Финансы | ✅ | Статистика, транзакции |
| Поиск мастеров | ✅ | AI + Yandex Maps |
| Бронирование | ✅ | Слоты + реальная оплата |
| Мои записи (клиент) | ✅ | Оплата, история |
| Профиль клиента | ✅ | Редактирование |
| Избранное | ✅ | Добавление/удаление |
| Подписки | ✅ | Free/Pro, оплата |
| Настройки мастера | ✅ | Профиль, расписание, услуги, уведомления, платежи |
| Мобильная адаптация | ✅ | 480px breakpoint, все компоненты |

---

## 10. Что нужно доделать

### 10.1 Ранее запланированные задачи (ВЫПОЛНЕНЫ)

Следующие задачи из оригинального ТЗ были реализованы:
- ~~Страница регистрации~~ ✅ Многошаговая форма с выбором роли
- ~~UI расписания мастера~~ ✅ В настройках: 7 дней, шаблоны, bulk API
- ~~UI управления услугами~~ ✅ В настройках: CRUD, категории, лимиты подписки
- ~~Настройки профиля мастера~~ ✅ 6 вкладок: профиль, расписание, услуги, уведомления, платежи, подписка
- ~~Верификация email~~ ✅ 6-значный код, повторная отправка
- ~~Восстановление пароля~~ ✅ Токен-based сброс, email
- ~~Email уведомления~~ ✅ Celery задачи, HTML шаблоны

### 10.2 Оставшиеся задачи

#### Безопасность
| Задача | Приоритет |
|--------|-----------|
| Убрать .env.prod из git, ротация секретов | CRITICAL |
| SSL/TLS для продакшена | CRITICAL |
| 2FA для мастеров | MEDIUM |
| Audit logging | LOW |

#### Инфраструктура
| Задача | Приоритет |
|--------|-----------|
| Бэкапы БД (автоматические) | HIGH |
| Мониторинг (Sentry) | MEDIUM |
| Push-уведомления (Firebase для web) | MEDIUM |
| WebSocket для чата (вместо polling) | MEDIUM |

---

## 11. Новые фичи для добавления

### 11.1 Высокий приоритет

#### Система уведомлений
```
- Email уведомления (регистрация, запись, напоминание)
- SMS уведомления (опционально)
- Push уведомления (PWA)
- In-app уведомления (bell icon)
```

#### Расширенный поиск
```
- Фильтр по цене
- Фильтр по рейтингу
- Фильтр по местоположению (радиус)
- Сортировка по популярности
- История поиска
```

#### Избранное
```
- Избранные мастера
- Избранные услуги
- История просмотров
```

### 11.2 Средний приоритет

#### Промокоды и скидки
```
- Система промокодов
- Скидки на первый визит
- Скидки постоянным клиентам
- Реферальная программа
```

#### Расширенное расписание
```
- Выходные и праздники
- Особые часы работы
- Интеграция с Google Calendar
- Автоматические напоминания
```

#### Аналитика для мастеров
```
- Детальная статистика по услугам
- График загруженности
- Анализ отмен
- Рекомендации по ценам
- Экспорт отчетов (PDF, Excel)
```

### 11.3 Низкий приоритет (v2.0)

#### Видеоконсультации
```
- Онлайн-консультации
- Запись видео
- Интеграция WebRTC
```

#### Групповые записи
```
- Мастер-классы
- Групповые услуги
- Бронирование на группу
```

#### Marketplace материалов
```
- Продажа косметики
- Рекомендации продуктов
- Интеграция с магазинами
```

#### Подписки
```
- Пакеты услуг
- Абонементы
- Программы лояльности
```

#### Мобильное приложение
```
- React Native или Flutter
- Пуш-уведомления
- Offline режим
```

---

## Приложения

### A. Переменные окружения (.env)
```env
# Django
DEBUG=False
SECRET_KEY=your-super-secret-key
ALLOWED_HOSTS=localhost,yourdomain.com

# Database
POSTGRES_DB=belvra
POSTGRES_USER=belvra
POSTGRES_PASSWORD=secure-password
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

# Redis
REDIS_URL=redis://localhost:6379/0

# JWT
JWT_SECRET_KEY=jwt-secret-key

# YooKassa
YOOKASSA_SHOP_ID=your-shop-id
YOOKASSA_SECRET_KEY=your-secret-key
YOOKASSA_WEBHOOK_SECRET=webhook-secret

# Email
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=app-password

# Gemini (перенести на backend!)
GEMINI_API_KEY=your-gemini-key

# Yandex Maps
YANDEX_MAPS_API_KEY=your-yandex-key
```

### B. Команды для разработки

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver

# Celery
celery -A config worker -l INFO
celery -A config beat -l INFO

# Frontend
cd frontend
npm install
ng serve

# Docker
docker-compose up -d
docker-compose logs -f
```

### C. API Документация
- Swagger UI: http://localhost:8000/api/docs/
- ReDoc: http://localhost:8000/api/redoc/
- OpenAPI Schema: http://localhost:8000/api/schema/

---

*Документ создан: 2026-01-12*
*Версия: 1.0*

---

## Статус реализации (обновлено 2026-04-05)

### Изменения относительно исходного ТЗ

- Платёжная система: YooKassa → T-Bank (только для подписок, не для оплаты услуг)
- Удалено: кошелёк, вывод средств, комиссия платформы, скидки, кешбэк
- Удалено: payments app целиком
- CI/CD: Ionic Appflow → GitLab CI/CD
- Чат: добавлен WebSocket (Django Channels) параллельно с REST
- Сервер: gunicorn → daphne (ASGI)

### Новые фичи (не в исходном ТЗ)

- WebSocket чат (Django Channels + Daphne)
- AI-поиск мастеров (Perplexity API)
- Текстовый + геопоиск в одном эндпоинте
- Заметки о клиентах (мини-CRM, PRO)
- PRO-бейдж в профиле мастера
- Закрепление работ в портфолио (PRO)
- Авто-напоминания клиентам о повторной записи (PRO)
- Быстрая перезапись (rebook action)
- Расширенные фильтры поиска (PRO)
- Статистика расходов клиента (PRO)
- Продающий лендинг для неавторизованных
- Push-уведомления (Firebase FCM, интегрированы)
- Единая система адаптивных брейкпоинтов (SCSS mixins)

### Актуальная документация

- docs/BUSINESS_LOGIC.md — полная бизнес-логика (700+ строк)
- docs/AUDIT_REPORT.md — аудит кодовой базы (52 находки)
- docs/PENTEST_REPORT.md — пентест раунд 1 (10 находок)
- docs/PENTEST_REPORT_R2.md — пентест раунд 2 (14 находок)
- docs/ROADMAP.md — дорожная карта развития
