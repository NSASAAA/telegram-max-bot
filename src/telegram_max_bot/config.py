from dataclasses import dataclass
from os import getenv
from typing import Optional

from dotenv import load_dotenv


@dataclass(frozen=True)
class Config:
    telegram_bot_token: str
    source_rss_url: Optional[str]
    check_interval_seconds: int
    web_base_url: Optional[str]


def load_config() -> Config:
    load_dotenv()

    telegram_bot_token = getenv("TELEGRAM_BOT_TOKEN")
    if not telegram_bot_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN environment variable is required")

    source_rss_url = getenv("SOURCE_RSS_URL")
    web_base_url = (getenv("WEB_BASE_URL") or "").strip() or None
    web_domain = (getenv("WEB_DOMAIN") or "").strip()
    if not web_base_url and web_domain:
        web_base_url = f"https://{web_domain}"
    raw_interval = getenv("CHECK_INTERVAL_SECONDS", "0")
    try:
        check_interval_seconds = max(0, int(raw_interval))
    except ValueError:
        check_interval_seconds = 0

    return Config(
        telegram_bot_token=telegram_bot_token,
        source_rss_url=source_rss_url,
        check_interval_seconds=check_interval_seconds,
        web_base_url=web_base_url,
    )
