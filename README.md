# Telegram MAX Bot

Python-бот для Telegram с перспективой добавления MAX.

Сейчас работает Telegram-версия: бот отвечает на команды, читает статьи из SQLite-базы и показывает последние импортированные материалы из RSS. MAX-адаптер пока оставлен заглушкой.

## Что сейчас умеет бот

- Работает в Telegram через `python-telegram-bot`.
- Загружает настройки из `.env`.
- Читает RSS через `feedparser`.
- Сохраняет статьи в SQLite-базу `data/bot.db`.
- Показывает последние статьи командой `/articles`.
- Запускается локально и через Docker Compose.

## Команды бота

- `/start` - приветствие и основные команды
- `/help` - список команд
- `/about` - информация о боте
- `/articles` - последние статьи из базы
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
SOURCE_RSS_URL=your_rss_feed_url_here
CHECK_INTERVAL_SECONDS=300
```

Реальные токены нельзя коммитить в Git. Файл `.env` должен оставаться локальным.

## Локальный запуск

Создать виртуальное окружение:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Установить зависимости:

```bash
pip install -r requirements.txt
```

Запустить Telegram-бота:

```bash
PYTHONPATH=src python -m telegram_max_bot.main
```

Если на Mac команда `python` недоступна, использовать:

```bash
PYTHONPATH=src python3 -m telegram_max_bot.main
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

RSS-импорт можно запускать вручную и автоматически.

Локально:

```bash
PYTHONPATH=src python -m telegram_max_bot.rss_import
```

Через Docker:

```bash
docker compose exec -T bot python -m telegram_max_bot.rss_import
```

На VPS из папки проекта:

```bash
cd /opt/bots/telegram-max-bot
docker compose exec -T bot python -m telegram_max_bot.rss_import
```

После импорта создается или обновляется база:

```text
data/bot.db
```

Повторный импорт не создает дубликаты, потому что статьи сохраняются по уникальной ссылке.

Автоматический импорт:

- если `SOURCE_RSS_URL` задан
- и `CHECK_INTERVAL_SECONDS > 0`
- бот выполняет периодический импорт в фоне с указанным интервалом.

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

## Текущие ограничения

- RSS-импорт пока не автоматический.
- `/articles` показывает только то, что уже есть в базе.
- Автопубликации новых статей в Telegram-канал пока нет.
- MAX пока не реализован.
- Текущая RSS-лента тестовая, позже будет заменена на RSS заказчика.

## Ближайшие планы

- Автоматизировать RSS-импорт по расписанию.
- Улучшить модель базы для отслеживания изменений статей.
- Добавить ручную команду проверки RSS.
- Позже добавить автопубликацию новых статей.
- Позже добавить MAX-адаптер.
