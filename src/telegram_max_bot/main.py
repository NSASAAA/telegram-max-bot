from telegram_max_bot.config import load_config
from telegram_max_bot.adapters.telegram import TelegramAdapter


def main() -> None:
    config = load_config()
    TelegramAdapter(
        token=config.telegram_bot_token,
        rss_url=config.source_rss_url,
        check_interval_seconds=config.check_interval_seconds,
        web_base_url=config.web_base_url,
    ).run()


if __name__ == "__main__":
    main()
