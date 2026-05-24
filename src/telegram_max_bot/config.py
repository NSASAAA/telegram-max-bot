from dataclasses import dataclass
from os import getenv

from dotenv import load_dotenv


@dataclass(frozen=True)
class Config:
    telegram_bot_token: str


def load_config() -> Config:
    load_dotenv()

    telegram_bot_token = getenv("TELEGRAM_BOT_TOKEN")
    if not telegram_bot_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN environment variable is required")

    return Config(
        telegram_bot_token=telegram_bot_token,
    )
