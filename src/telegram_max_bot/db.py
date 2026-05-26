import sqlite3
from pathlib import Path
from typing import Iterable

from telegram_max_bot.rss_client import RssPost


DB_PATH = Path("data/bot.db")


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                link TEXT NOT NULL UNIQUE,
                published TEXT,
                summary TEXT,
                author TEXT,
                categories TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


def save_posts(posts: Iterable[RssPost]) -> int:
    saved_count = 0

    with get_connection() as connection:
        for post in posts:
            categories = ", ".join(post.categories)

            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO posts (
                    title,
                    link,
                    published,
                    summary,
                    author,
                    categories
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    post.title,
                    post.link,
                    post.published,
                    post.summary,
                    post.author,
                    categories,
                ),
            )

            if cursor.rowcount > 0:
                saved_count += 1

    return saved_count


def get_latest_posts(limit: int = 10) -> list[sqlite3.Row]:

    with get_connection() as connection:

        cursor = connection.execute(

            """

            SELECT id, title, link, published, summary, author, categories

            FROM posts

            ORDER BY id DESC

            LIMIT ?

            """,

            (limit,),

        )

        return list(cursor.fetchall())