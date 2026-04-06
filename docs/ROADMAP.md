# Belvra — Дорожная карта

> Дата: 2026-04-05
> Статус: Production, 6 пользователей (early adopters)

---

## Текущее состояние

| Метрика | Значение |
|---------|----------|
| Пользователей | 6 (3 мастера, 3 клиента) |
| Все верифицированы | Да |
| Все early adopters | Да (пожизненный PRO) |
| Записей | 1 (0 завершённых) |
| Подписок | 6 active PRO |
| T-Bank | Подключён (реальный ключ) |
| AI (Perplexity) | НЕ настроен |
| Firebase Push | НЕ настроен |
| Тесты | 278/296 passed (94%) |
| Лендинг | Есть |
| SEO | Базовый (robots.txt, sitemap, OG-теги) |

---

## ФАЗА 1: Подготовка к запуску (1-2 дня)

### 1.1 Починить 16 падающих тестов

- 7 в appointments (фикстуры не создают MasterService/WorkSchedule)
- 3 в appointments/tasks (mark_no_show логика)
- 1 в subscriptions (counter logic)
- 2 в users (формат ответа регистрации)
- 2 в test_tbank (нужен реальный payment_id — skip)
- 1 в chat (duplicate — flaky)

Цель: 294/296 passed + 2 skipped (tbank)

### 1.2 Настроить AI (Perplexity)

```bash
ssh root@89.223.126.31
echo 'PERPLEXITY_API_KEY=pplx-xxxxxxxx' >> /opt/belvra/prod/.env.prod
cd /opt/belvra/prod && cp .env.prod .env
docker compose -f docker-compose.prod.yml restart backend
```

Получить ключ: https://www.perplexity.ai/ → Settings → API
Стоимость: ~$5/мес.

Включит: AI-поиск мастеров + подсказки в чате (PRO).

### 1.3 Настроить Firebase Push

1. Firebase Console → создать проект "Belvra"
2. Project Settings → Service Accounts → Generate Key
3. Скопировать JSON на сервер:
```bash
scp firebase-credentials.json root@89.223.126.31:/opt/belvra/prod/
echo 'FIREBASE_CREDENTIALS_PATH=/app/firebase-credentials.json' >> /opt/belvra/prod/.env.prod
```
4. Перезапустить бэкенд

### 1.4 Content-Security-Policy

Добавить в nginx/conf.d/prod.conf:
```nginx
add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' mc.yandex.ru api-maps.yandex.ru; style-src 'self' 'unsafe-inline' fonts.googleapis.com; font-src 'self' fonts.gstatic.com; img-src 'self' data: blob:; connect-src 'self' wss://belvra.ru api-maps.yandex.ru mc.yandex.ru;" always;
```

### 1.5 MAX_PAGE_SIZE

В settings/base.py создать кастомный пагинатор с max_page_size=100.

---

## ФАЗА 2: Привлечение первых пользователей (1-2 недели)

### 2.1 Контент-маркетинг

Промо-тексты готовы (promo/post-text.md — 6 вариантов):

1. VK: пост для мастеров + для клиентов → бьюти-группы города
2. Telegram: короткий пост в чаты мастеров красоты
3. Instagram*: сторис + reels
4. Early adopter пост: "Первые 50 — PRO навсегда"

### 2.2 Зарегистрировать 10-20 мастеров

- Найти реальных мастеров в городе
- Предложить пожизненный PRO (early adopter)
- Помочь заполнить профиль и загрузить портфолио
- Попросить поделиться ссылкой с клиентами

**Без мастеров на платформе клиентам незачем приходить.**

### 2.3 SEO

Уже есть: robots.txt, sitemap.xml, мета-теги, OG-теги.

Добавить:
- Яндекс.Вебмастер — добавить сайт
- Google Search Console — добавить сайт
- Яндекс.Бизнес / 2ГИС — карточка организации

---

## ФАЗА 3: Монетизация (после 50+ пользователей)

### 3.1 T-Bank оплата подписок

Ключ уже есть. Проверить:
- Webhook URL в личном кабинете T-Bank: https://belvra.ru/api/v1/subscriptions/webhook/
- Тестовый платёж
- Рекуррентные платежи (автопродление)

### 3.2 Ценообразование

Рекомендация для запуска:
- PRO мастер: **499 ₽/мес** (снижен порог входа)
- PRO клиент: **бесплатно первые 6 мес**, потом 199 ₽/мес
- Early adopters: PRO навсегда (уже работает)

Создать планы: Django Admin → Планы подписок.

### 3.3 Реферальная программа

Уже реализована. Промотировать:
"Пригласи друга — получи месяц PRO бесплатно"

---

## ФАЗА 4: Мобильное приложение (2-4 недели)

### 4.1 Android

- Google Play Developer ($25 один раз)
- Сборка: `npx cap sync && npx cap open android`
- Скриншоты, описание, иконка

### 4.2 iOS

- Apple Developer Program ($99/год)
- Bundle ID: ru.belvra.app
- Review: 1-7 дней

### 4.3 Альтернатива — PWA

PWA уже работает. Добавить баннер "Установить приложение" на лендинге.

---

## ФАЗА 5: Масштабирование (после 200+ пользователей)

- Кэширование (Redis, 5 мин TTL)
- PostGIS для геопоиска
- CDN для медиа (Cloudflare R2)
- SMS-уведомления
- Telegram-бот для записи
- Виджет записи для сайтов мастеров
- Яндекс.Метрика цели (регистрация, запись, покупка PRO)

---

## ФАЗА 6: AI (после стабилизации)

- Vision: Google Gemini API (бесплатный tier)
- Умные рекомендации мастеров
- Персонализированная сортировка

---

## Чеклист — что делать ЗАВТРА

- [ ] Получить Perplexity API key → настроить
- [ ] Создать Firebase проект → настроить push
- [ ] Найти 5 мастеров → зарегистрировать → заполнить профили
- [ ] Опубликовать early adopter пост в 3-5 чатов
- [ ] Создать PRO планы в Django Admin
- [ ] Проверить T-Bank тестовый платёж
- [ ] Подать сайт в Яндекс.Вебмастер

---

\* *Instagram принадлежит компании Meta, признанной экстремистской организацией на территории РФ.*
