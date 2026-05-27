import os

from telegram_max_bot.core.models import ImportStats
from telegram_max_bot.db import get_latest_posts, init_db, save_posts
from telegram_max_bot.rss_client import fetch_rss_posts


def import_from_rss_url(rss_url: str) -> ImportStats:
    init_db()
    posts = fetch_rss_posts(rss_url)
    return save_posts(posts, source="rss")


def run_import_from_env() -> ImportStats:
    rss_url = os.getenv("SOURCE_RSS_URL")

    if not rss_url:
        raise RuntimeError("SOURCE_RSS_URL is not set")

    return import_from_rss_url(rss_url)


def main() -> None:
    stats = run_import_from_env()

    print(f"Posts received from RSS: {stats.total}")
    print(f"New posts saved: {stats.created}")
    print(f"Posts updated: {stats.updated}")
    print(f"Posts unchanged: {stats.unchanged}")
    print()

    latest_posts = get_latest_posts(limit=5)
    print("Latest posts in DB:")
    for post in latest_posts:
        print(f"- #{post['id']} {post['title']}")
        print(f"  {post['link']}")


if __name__ == "__main__":
    main()
