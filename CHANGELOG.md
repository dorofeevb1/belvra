# Changelog

## [Unreleased] — 2026-03-12

### Аудит кодовой базы и исправления

Проведён полный аудит проекта: backend (Django), frontend (Angular), инфраструктура (Docker, Nginx, CI/CD).

---

### Итерация 2: Доработка незавершённых фич (2026-03-12)

#### 5. Реальная оплата при бронировании
- **Проблема:** `processPayment()` в `booking-calendar.component.ts` использовал `setTimeout(2000)` — полная имитация оплаты
- **Решение:** Теперь после создания записи вызывается `walletService.createPayment()`, который создаёт реальный платёж через YooKassa и перенаправляет на страницу оплаты
- **Файл:** `apps/web/src/app/features/client/booking/booking-calendar.component.ts`

#### 6. API для материалов записей
- **Проблема:** `updateAppointmentMaterials()` в `data.service.ts` был заглушкой — возвращал локальный объект без вызова API
- **Решение:**
  - Добавлены поля `used_materials` (JSONField) и `materials_cost` (DecimalField) в модель `Appointment`
  - Создан endpoint `POST /appointments/{id}/update-materials/` (только для мастера)
  - Обновлен `AppointmentSerializer` — включены новые поля
  - Frontend `DataService.updateAppointmentMaterials()` теперь вызывает реальный API
  - Миграция: `0004_appointment_materials.py`

#### 7. Настройки мастера: опыт работы и доступность
- **Проблема:** Поля `experience_years` и `is_available` существовали в backend модели, но не были доступны в UI и API обновления профиля
- **Решение:**
  - Backend: добавлены `experience_years` и `is_available` как write-fields в `UserSerializer`
  - Frontend: добавлены поля в форму настроек (число + тоггл)
  - Модель `Master`: добавлены `experienceYears?` и `isAvailable?`

#### 8. Обновлён TECHNICAL_SPECIFICATION.md
- ТЗ содержало устаревшую информацию (7 фич помечены как "не реализованы", хотя они полностью работают)
- Обновлены секции 9 (статус реализации) и 10 (что нужно доделать)
- Backend: 19 модулей ✅ | Frontend: ~95% MVP → обновлено

---

### Итерация 3: Финальная доработка (2026-03-12)

#### 9. Исправлены маппинги данных Frontend ↔ Backend
- `mapBackendMaster()` — добавлено маппинг `experienceYears` и `isAvailable` из backend
- `mapBackendAppointment()` — добавлено маппинг `usedMaterials` и `materialsCost` из backend
- **Файл:** `apps/web/src/app/core/services/data.service.ts`

#### 10. Исправлен баг идемпотентности возвратов
- **Проблема:** `idempotency_key` для refund содержал `uuid.uuid4()` — при повторном webhook создавался дубликат возврата
- **Решение:** Ключ теперь `f"refund-{payment.id}"` — детерминированный
- **Файл:** `backend/apps/payments/services.py`

#### 11. Устранены N+1 запросы
- `MasterListView` — `select_related("user", "user__subscription", "user__subscription__plan")`
- `MasterDetailView` — `select_related("user", "user__subscription", "user__subscription__plan")`
- `PaymentViewSet` — `select_related("client", "master__user", "appointment__service", "appointment__master_service")`
- **Файлы:** `backend/apps/users/views.py`, `backend/apps/payments/views.py`

#### 12. Удалены мёртвые mock-методы
- Удалены `getMockServices`, `getMockAppointments`, `getMockReviews`, `getMockMasters` (~100 строк)
- **Файл:** `apps/web/src/app/core/services/data.service.ts`

#### 13. Исправлена утечка памяти в MyAppointmentsComponent
- Добавлен `OnDestroy` + `Subject<void>` + `takeUntil(this.destroy$)` для `route.queryParams`
- **Файл:** `apps/web/src/app/features/client/my-appointments/my-appointments.component.ts`

#### 14. Удалены последние mock-data fallbacks (getAvailableSlots)
- `getAvailableSlots()` и `getAvailableSlotsForService()` возвращали фейковые слоты при ошибке API
- Удалён метод `generateMockSlots()` целиком
- Добавлена обработка ошибок в вызывающих компонентах (`booking-calendar`, `reschedule-modal`)
- **Файлы:** `data.service.ts`, `booking-calendar.component.ts`, `reschedule-modal.component.ts`

---

### Исправлено (Backend)

#### 1. Логирование вместо молчаливого проглатывания ошибок
Во всех файлах заменены `except: pass` на правильное логирование:

| Файл | Что исправлено |
|------|----------------|
| `apps/subscriptions/views.py` | Webhook-обработчики `payment.succeeded` и `payment.canceled` теперь логируют, если `SubscriptionPayment` не найден |
| `apps/chat/views.py` | Логирование при ненайденном reply-to сообщении и при ошибке обновления уведомлений |
| `apps/users/views.py` | Логирование при ошибке blacklist refresh-токена (logout) и при запросе сброса пароля для несуществующего email |
| `apps/payments/models.py` | Логирование при ошибке получения комиссии из подписки мастера |
| `apps/appointments/views.py` | Логирование при ненайденном MasterProfile при создании записи |
| `apps/ai/services.py` | Логирование при ошибке парсинга JSON из ответа AI |

#### 2. Устранено дублирование Celery Beat расписания
- **Проблема:** `config/celery.py` перезаписывал `CELERY_BEAT_SCHEDULE` из `config/settings/base.py`, из-за чего **9 задач никогда не выполнялись**:
  - `send-completion-reminder`
  - `check-expiring-subscriptions`, `renew-subscriptions`, `expire-subscriptions`
  - `downgrade-to-free`, `reset-monthly-usage`, `notify-past-due-subscriptions`
  - `close-overdue-todos`, `cleanup-old-notifications`
- **Также:** `cleanup-unverified-accounts` запускалась каждую минуту вместо каждых 6 часов
- **Решение:** Удалено дублирующее расписание из `celery.py`, единственный источник — `settings/base.py`

#### 3. Дедупликация лайков портфолио
- **Проблема:** Один пользователь мог лайкнуть работу неограниченное количество раз (race condition)
- **Решение:**
  - Создана модель `PortfolioLike` с `unique_together = (user, portfolio_item)`
  - Метод `like()` теперь использует `get_or_create` — повторный лайк не увеличивает счётчик
  - Добавлен метод `unlike()` для снятия лайка
  - Миграция: `0005_add_portfolio_like.py`

---

### Исправлено (Frontend)

#### 4. Удалены mock-data fallbacks из DataService
- **Проблема:** При ошибке API пользователь получал фейковые данные (поддельные услуги, мастера, отзывы, сообщения) вместо уведомления об ошибке. Это маскировало реальные проблемы backend.
- **Решение:** Все `catchError(() => of(getMock*()))` заменены на `throwError()` с понятными русскоязычными сообщениями:
  - `getAllServices`, `getServices`, `getMyServices` — «Не удалось загрузить услуги»
  - `addService`, `updateService` — «Не удалось создать/обновить услугу»
  - `getClientAppointments` — «Не удалось загрузить записи»
  - `rescheduleAppointment` — «Не удалось перенести запись»
  - `getReviews`, `updateReview`, `addReview` — «Не удалось загрузить/обновить/отправить отзыв»
  - `getAllMasters`, `getMasterById` — «Не удалось загрузить мастеров/профиль»
  - `addPortfolioItem`, `updatePortfolioItem` — «Не удалось добавить/обновить работу»
  - `sendMessage` — «Не удалось отправить сообщение»
  - `getChatWithMaster` — «Не удалось загрузить чат»
  - `addTodo` — «Не удалось создать задачу»
- **Оставлены допустимые fallbacks:** пустые массивы `of([])` для списков (chats, todos, appointments), `of(void 0)` для delete-операций, `of(false)` для typing-индикаторов

---

### Известные проблемы (не исправлены — требуют отдельной итерации)

#### Backend
| # | Проблема | Файл | Приоритет |
|---|----------|------|-----------|
| 1 | Авто-продление подписок не реализовано (поле `auto_renew` есть, задачи нет) | `apps/subscriptions/` | HIGH |
| 2 | Webhook без проверки идемпотентности | `apps/subscriptions/views.py` | HIGH |
| 3 | `Wallet.pending_balance` vs `hold_balance` — неясное разделение | `apps/payments/models.py` | LOW |
| 4 | Нет агрегации рейтинга мастера из отзывов | `apps/appointments/` | MEDIUM |

#### Frontend
| # | Проблема | Файл | Приоритет |
|---|----------|------|-----------|
| 1 | Chat через polling (3 сек) вместо WebSocket | `client-chat.component.ts` | HIGH |
| 2 | Yandex Maps: race condition при инициализации | `master-search.component.ts:44` | MEDIUM |
| 3 | Использования типа `any` в data.service.ts | `data.service.ts` | LOW |

#### Инфраструктура
| # | Проблема | Файл | Приоритет |
|---|----------|------|-----------|
| 1 | `.env.prod` с секретами в репозитории | `.env.prod` | CRITICAL |
| 2 | SSL отключён на проде (HTTP only, port 80) | `nginx/conf.d/prod.conf` | CRITICAL |
| 3 | Старый IP (37.77.104.201) в dev nginx конфиге | `nginx/conf.d/dev.conf` | MEDIUM |
| 4 | CI/CD: хардкод IP сервера, нет rollback | `.gitlab-ci.yml` | MEDIUM |
| 5 | Frontend Dockerfile: `sleep infinity` вместо нормального exit | `apps/web/Dockerfile` | LOW |

---

### Файлы затронутые этим обновлением

**Backend (изменены):**
- `backend/config/celery.py` — удалено дублирующее расписание
- `backend/apps/subscriptions/views.py` — добавлено логирование
- `backend/apps/chat/views.py` — добавлено логирование
- `backend/apps/users/views.py` — добавлено логирование, N+1 fix
- `backend/apps/payments/models.py` — добавлено логирование
- `backend/apps/payments/views.py` — N+1 fix (select_related)
- `backend/apps/payments/services.py` — исправлен idempotency_key возвратов
- `backend/apps/appointments/views.py` — добавлено логирование, endpoint update-materials
- `backend/apps/appointments/models.py` — поля used_materials, materials_cost
- `backend/apps/appointments/serializers.py` — новые поля в сериализаторе
- `backend/apps/ai/services.py` — добавлено логирование
- `backend/apps/services/models.py` — добавлена модель `PortfolioLike`
- `backend/apps/services/views.py` — переработаны методы like/unlike
- `backend/apps/users/serializers.py` — write-fields для experience_years, is_available

**Backend (созданы):**
- `backend/apps/services/migrations/0005_add_portfolio_like.py`
- `backend/apps/appointments/migrations/0004_appointment_materials.py`

**Frontend (изменены):**
- `apps/web/src/app/core/services/data.service.ts` — удалены mock fallbacks, throwError, маппинги, удалён generateMockSlots
- `apps/web/src/app/core/services/api.service.ts` — метод updateAppointmentMaterials
- `apps/web/src/app/core/models/user.model.ts` — experienceYears, isAvailable
- `apps/web/src/app/features/client/booking/booking-calendar.component.ts` — реальная оплата YooKassa, обработка ошибок слотов
- `apps/web/src/app/features/client/my-appointments/my-appointments.component.ts` — fix memory leak
- `apps/web/src/app/features/master/settings/settings.component.ts` — поля опыта и доступности
- `apps/web/src/app/features/master/settings/settings.component.html` — UI для опыта и доступности
- `apps/web/src/app/features/master/appointments/modals/reschedule-modal.component.ts` — обработка ошибок слотов
