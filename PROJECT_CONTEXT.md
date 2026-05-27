# Project Context

## Проект

`telegram-max-bot` — Python-проект бота для Telegram с перспективой добавления MAX.

Текущий практический фокус: Telegram-бот, который работает с RSS-лентой статей, сохраняет материалы в SQLite и показывает их пользователю через команды.

Долгосрочная цель: сделать не просто репостер статей, а коммуникационную систему вокруг автора и его аудитории.

## Продуктовая идея

Изначальная идея: автоматически перепубликовывать статьи из Яндекс Дзена в Telegram, а позже в MAX.

После обсуждения концепция расширена: бот должен стать точкой контакта между автором и читателями. Статьи являются поводом для общения, а не конечной целью.

Будущий бот должен помогать:

- показывать новые статьи;
- находить материалы автора;
- собирать вопросы читателей;
- принимать отклики на статьи;
- собирать предложения тем;
- принимать истории читателей;
- показывать ответы автора;
- поддерживать проект.

Тематика автора: вера, семья, воспитание, материнство, боль, личные границы, психологическая зрелость, социальные роли, феминизм, свобода от разрушительных установок.

Бот не должен превращаться в простой "православный календарь" или пассивный архив. Более точное позиционирование: проводник по текстам автора и канал живой обратной связи.

## Архитектурный принцип

Бизнес-логика не должна зависеть напрямую от Telegram или MAX.

Правильная схема:

```text
Telegram API ─┐
              ├── adapters → core → storage/services
MAX API      ─┘
```

`core/` содержит общую бизнес-логику.

`adapters/telegram.py` только принимает Telegram-события, преобразует их во внутренние модели и отправляет ответы.

`adapters/max.py` пока остается заглушкой. MAX будет добавлен позже как второй транспорт.

## Текущая структура

```text
telegram-max-bot/
├── README.md
├── PROJECT_CONTEXT.md
├── .env.example
├── .gitignore
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── deploy.sh
├── .github/
│   └── workflows/
│       └── deploy.yml
├── data/
│   └── bot.db
├── src/
│   └── telegram_max_bot/
│       ├── __init__.py
│       ├── main.py
│       ├── config.py
│       ├── db.py
│       ├── rss_client.py
│       ├── rss_import.py
│       ├── core/
│       │   ├── __init__.py
│       │   ├── bot.py
│       │   └── models.py
│       └── adapters/
│           ├── __init__.py
│           ├── telegram.py
│           └── max.py
└── tests/
    └── __init__.py
```

## Текущее состояние приложения

Сейчас работает Telegram-бот через `python-telegram-bot`.

Команды:

- `/start` — приветствие и основные команды;
- `/help` — список команд;
- `/about` — описание тестовой версии бота;
- `/articles` — последние статьи из SQLite-базы;
- обычный текст — простой ответ о полученном сообщении.

`main.py` только загружает конфиг и запускает `TelegramAdapter`.

`config.py` загружает `.env` через `python-dotenv` и требует `TELEGRAM_BOT_TOKEN`.

`core/bot.py` содержит бизнес-логику команд.

`adapters/telegram.py` содержит Telegram-интеграцию и маршрутизацию команд.

`adapters/max.py` пока заглушка.

## RSS и база данных

Реализован контур:

```text
RSS → rss_import.py → SQLite → /articles
```

Тестовая RSS-лента сейчас:

```text
https://habr.com/ru/rss/articles/
```

Модули:

- `rss_client.py` читает RSS через `feedparser`;
- `rss_import.py` импортирует статьи из RSS;
- `db.py` работает с SQLite-базой `data/bot.db`.

Текущая модель статьи в базе:

```text
id
title
link
published
summary
author
categories
created_at
```

Сейчас защита от дублей сделана через уникальный `link` и `INSERT OR IGNORE`.

Повторный импорт не создает дубликаты.

## Важное будущее решение по RSS

Текущий импорт добавляет только новые статьи. В будущем нужно заменить его на полноценную синхронизацию RSS.

Нужная логика:

```text
если статья новая → сохранить
если статья уже есть, но изменилась → обновить
если статья уже есть и не изменилась → обновить last_seen_at
```

Для этого понадобятся поля:

```text
source
source_guid
published_at
updated_at_from_feed
summary_html
content_html
content_text
image_url
author
categories
content_hash
first_seen_at
last_seen_at
last_changed_at
```

Изменения статьи лучше отслеживать через `sha256` по значимым полям, например `title + content_html + summary_html`.

Импорт должен показывать статистику:

```text
Posts received: 40
New posts saved: 2
Posts updated: 1
Posts unchanged: 37
```

## Что пока не реализовано

Пока нет:

- автоматической проверки RSS по расписанию;
- автопубликации новых статей в Telegram-канал;
- полноценного обновления измененных статей;
- хранения полного текста статьи;
- поиска по статьям;
- случайной статьи;
- пользовательского меню с кнопками;
- сбора вопросов, откликов и историй читателей;
- MAX-интеграции.

## Инфраструктура

Код хранится в GitHub:

```text
NSASAAA/telegram-max-bot
```

Локальный проект на Mac:

```text
/Users/aleksandr_maraenko/Desktop/telegram-max-bot
```

Проект на VPS:

```text
/opt/bots/telegram-max-bot
```

Деплой идет через GitHub Actions.

Схема:

```text
Mac / VSCode
→ git commit
→ git push
→ GitHub Actions
→ SSH на VPS
→ deploy.sh
→ git pull
→ docker compose up -d --build
```

`deploy.sh` выполняет:

```text
git pull
docker compose up -d --build
docker compose ps
docker compose logs --tail=50
```

GitHub Actions использует `appleboy/ssh-action`.

Секреты хранятся в GitHub Secrets, не в коде.

## Docker

Бот запускается через Docker Compose.

Важные настройки:

```yaml
restart: unless-stopped
mem_limit: 256m
cpus: "0.50"
```

Нужно закрепить SQLite-базу через volume:

```yaml
volumes:
  - ./data:/app/data
```

Это важно, чтобы `data/bot.db` не пропадала после пересборки контейнера.

## Переменные окружения

Реальные секреты хранятся только в `.env`.

`.env` не должен попадать в Git.

`.env.example` должен содержать только шаблонные значения.

Текущие/будущие переменные:

```env
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
APP_ENV=development
SOURCE_RSS_URL=https://habr.com/ru/rss/articles/
DATABASE_PATH=data/bot.db
TELEGRAM_TARGET_CHAT_ID=
CHECK_INTERVAL_SECONDS=300
MAX_BOT_TOKEN=
MAX_TARGET_CHAT_ID=
```

Не хранить в Git:

```text
.env
реальные Telegram/MAX токены
SSH-ключи
IP/секреты деплоя
пароли
cookies
```

## MAX

MAX пока не реализован.

Стратегия:

1. Сначала довести Telegram-версию.
2. Параллельно решать административные вопросы регистрации MAX.
3. После получения токена добавить MAX-адаптер.
4. Не менять `core`, если можно обойтись адаптером.

MAX должен использовать те же внутренние модели и бизнес-логику, что и Telegram.

## Рекомендуемый рабочий процесс

Разработка ведется локально на Mac.

VPS используется в основном для диагностики и проверки деплоя.

Обычный цикл:

```text
1. Сформулировать маленькую задачу.
2. Изменить код.
3. Проверить локально.
4. Проверить git status.
5. Сделать commit.
6. Сделать push.
7. Дождаться GitHub Actions.
8. Проверить работу бота.
```

Команды локально:

```bash
cd /Users/aleksandr_maraenko/Desktop/telegram-max-bot
git status
PYTHONPATH=src python -m telegram_max_bot.main
docker compose up -d --build
docker compose logs -f
git add .
git commit -m "message"
git push
```

Для локальной разработки желательно использовать отдельного dev-бота Telegram, чтобы не конфликтовать с production-ботом на VPS при long polling.

## Ближайшие задачи

1. Добавить Docker volume для `data/`.
2. Убедиться, что база сохраняется после пересборки контейнера.
3. Обновить README под текущее состояние `/articles` и RSS.
4. Улучшить модель базы для будущей RSS-синхронизации.
5. Переделать `save_posts()` с `INSERT OR IGNORE` на `created / updated / unchanged`.
6. Добавить ручную команду проверки RSS, например `/check`.
7. Добавить автоматический импорт RSS по расписанию.
8. Позже добавить автопубликацию новых статей в Telegram-канал.
9. После получения реальной RSS-ленты заказчика проверить, отдает ли она полный текст.
10. После накопления корпуса статей сделать анализ тем и сценариев общения.

## Что не делать

- Не коммитить `.env`.
- Не хранить реальные токены в `.env.example`.
- Не смешивать бизнес-логику с Telegram-обработчиками.
- Не превращать проект в Telegram-only.
- Не добавлять MAX до готовности Telegram/RSS-ядра.
- Не делать большие изменения без маленьких проверяемых шагов.
- Не править вручную код на VPS, кроме экстренной диагностики.
- Не считать текущий RSS-импорт финальной синхронизацией.
