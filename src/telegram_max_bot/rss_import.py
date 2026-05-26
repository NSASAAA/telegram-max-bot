import os

from telegram_max_bot.db import get_latest_posts, init_db, save_posts
from telegram_max_bot.rss_client import fetch_rss_posts


def main() -> None:
    rss_url = os.getenv("SOURCE_RSS_URL")

    if not rss_url:
        raise RuntimeError("SOURCE_RSS_URL is not set")

    init_db()

    posts = fetch_rss_posts(rss_url)
    saved_count = save_posts(posts)

    print(f"Posts received from RSS: {len(posts)}")
    print(f"New posts saved: {saved_count}")
    print()

    latest_posts = get_latest_posts(limit=5)

    print("Latest posts in DB:")
    for post in latest_posts:
        print(f"- #{post['id']} {post['title']}")
        print(f"  {post['link']}")


if __name__ == "__main__":
    main()