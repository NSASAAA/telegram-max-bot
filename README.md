# Telegram MAX Bot

Python-бот для Telegram с перспективой добавления MAX.

Сейчас работает Telegram-версия на VPS: бот отвечает на команды, читает статьи Дзена из SQLite-базы и показывает материалы пользователю. MAX-адаптер пока оставлен заглушкой.

## Что сейчас умеет бот

- Работает в Telegram через `python-telegram-bot`.
- Загружает настройки из `.env`.
- Работает с импортированным архивом Дзена.
- Сохраняет статьи в SQLite-базу `data/bot.db`.
- Показывает последние статьи командой `/articles`.
- Запускается на VPS через Docker Compose.

## Команды бота

- `/start` - приветствие и основные команды
- `/help` - список команд
- `/about` - информация о боте
- `/articles` - последние статьи из базы
- `/top` - самые читаемые статьи из базы
- `/random` - случайная статья из базы
- `/check` - импортировать RSS прямо сейчас
- любой текст - ответ `Я получил сообщение: <текст>`

## Переменные окружения

Создать `.env` на основе `.env.example`:

```bash
cp .env.example .env
```

Минимально нужно заполнить:

```env
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
APP_ENV=development
SOURCE_RSS_URL=
CHECK_INTERVAL_SECONDS=0
DATABASE_PATH=data/bot.db
```

Реальные токены нельзя коммитить в Git. Файл `.env` должен оставаться локальным.

## Локальная разработка

Создать виртуальное окружение:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Установить зависимости:

```bash
pip install -r requirements.txt
```

Проверить синтаксис кода:

```bash
PYTHONPATH=src python -m compileall src
```

Telegram-бота локально сейчас не запускаем, потому что VPS-экземпляр использует тот же Telegram token и работает через polling. Новые изменения проверяются так:

```text
локально пишем код
→ commit
→ push
→ GitHub Actions
→ VPS
→ проверяем команды в Telegram
```

## Запуск через Docker

Собрать и запустить контейнер:

```bash
docker compose up -d --build
```

Посмотреть статус:

```bash
docker compose ps
```

Посмотреть логи:

```bash
docker compose logs -f
```

Остановить контейнер:

```bash
docker compose down
```

## RSS-импорт

RSS-импорт был реализован и проверен на раннем этапе проекта, но сейчас не является рабочим источником данных. Хабр больше не используется.

Код RSS-импорта оставлен как заготовка на будущее. Если он снова понадобится, его можно запускать вручную:

```bash
PYTHONPATH=src python -m telegram_max_bot.rss_import
```

Автоматический RSS-импорт включается только если:

- если `SOURCE_RSS_URL` задан
- и `CHECK_INTERVAL_SECONDS > 0`
- бот выполняет периодический импорт в фоне с указанным интервалом.

Текущий режим после перехода на Дзен:

```env
SOURCE_RSS_URL=
CHECK_INTERVAL_SECONDS=0
```

## Импорт архива Дзена

Для локальной подготовки реального корпуса заказчика используется сырой архив:

```text
data/raw/dzen_1234elena/articles_full.jsonl
```

Импорт статей, метрик и изображений в отдельную локальную базу:

```bash
PYTHONPATH=src python -m telegram_max_bot.dzen_import
```

Локальный результат подготовки:

```text
data/dzen_bot.db
data/media/dzen_1234elena/
```

На VPS эта база перенесена как:

```text
/opt/bots/telegram-max-bot/data/bot.db
/opt/bots/telegram-max-bot/data/media/dzen_1234elena/
```

В SQLite хранятся тексты, метрики и пути к картинкам. Сами изображения лежат файлами в `data/media/`.

## База данных

Сейчас используется SQLite.

Файл базы:

```text
data/bot.db
```

В Docker Compose папка `data/` подключена как volume:

```yaml
volumes:
  - ./data:/app/data
```

Это значит, что база хранится на сервере рядом с проектом и не пропадает при пересборке контейнера.

## Деплой

Деплой на VPS выполняется через GitHub Actions после push в `main`.

Схема:

```text
git push
→ GitHub Actions
→ SSH на VPS
→ deploy.sh
→ docker compose up -d --build
```

На VPS проект находится здесь:

```text
/opt/bots/telegram-max-bot
```

В `deploy.yml` настроен `paths-ignore`: изменения только в `README.md`, `PROJECT_CONTEXT.md` и `.env.example` не запускают деплой.

## Текущие ограничения

- `/articles` показывает только то, что уже есть в базе.
- Автопубликации новых статей в Telegram-канал пока нет.
- MAX пока не реализован.
- RSS-источник Хабра больше не используется.

## Ближайшие планы

- Добавить тематическую разметку статей Дзена.
- Добавить навигацию по рубрикам.
- Позже добавить автопубликацию новых статей.
- Позже добавить MAX-адаптер.
