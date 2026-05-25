# Telegram MAX Bot

Проект универсального бота для Telegram и MAX.

Сейчас реализован минимальный Telegram-бот. MAX-адаптер пока оставлен заглушкой.

## Команды бота

- `/start` - приветствие пользователя
- `/help` - список команд
- любой текст - ответ `Я получил сообщение: <текст>`

## Локальный запуск

1. Создать виртуальное окружение:

```bash
python -m venv .venv
source .venv/bin/activate
```

2. Установить зависимости:

```bash
pip install -r requirements.txt
```

3. Создать `.env` на основе `.env.example` и указать токен:

```bash
cp .env.example .env
```

В `.env` нужно заполнить:

```env
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
```

4. Запустить бота:

```bash
PYTHONPATH=src python -m telegram_max_bot.main
```

## Запуск через Docker

1. Создать `.env` на основе `.env.example` и указать `TELEGRAM_BOT_TOKEN`.

2. Запустить контейнер:

```bash
docker compose up --build
```

