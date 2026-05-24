from telegram_max_bot.config import load_config
from telegram_max_bot.adapters.telegram import TelegramAdapter


def main() -> None:
    config = load_config()
    TelegramAdapter(token=config.telegram_bot_token).run()


if __name__ == "__main__":
    main()
