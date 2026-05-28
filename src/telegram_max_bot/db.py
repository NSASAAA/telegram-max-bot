import sqlite3
import os
from pathlib import Path
from typing import Iterable, Optional

from telegram_max_bot.core.models import ImportStats
from telegram_max_bot.rss_client import RssPost


def get_db_path() -> Path:
    return Path(os.getenv("DATABASE_PATH", "data/bot.db"))


def get_connection() -> sqlite3.Connection:
    db_path = get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
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
                guid TEXT,
                published TEXT,
                updated TEXT,
                summary TEXT,
                summary_html TEXT,
                content_html TEXT,
                content_text TEXT,
                image_url TEXT,
                views_count INTEGER,
                reading_time_minutes INTEGER,
                comments_count INTEGER,
                cover_image_path TEXT,
                published_label TEXT,
                source_order INTEGER,
                author TEXT,
                categories TEXT,
                source TEXT DEFAULT 'rss',
                source_guid TEXT,
                updated_at_from_feed TEXT,
                content_hash TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                first_seen_at TEXT DEFAULT CURRENT_TIMESTAMP,
                last_seen_at TEXT DEFAULT CURRENT_TIMESTAMP,
                last_changed_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        _ensure_posts_columns(connection)
        _ensure_article_images_table(connection)


def _ensure_posts_columns(connection: sqlite3.Connection) -> None:
    cursor = connection.execute("PRAGMA table_info(posts)")
    existing_columns = {row["name"] for row in cursor.fetchall()}
    required_columns: dict[str, str] = {
        "guid": "TEXT",
        "updated": "TEXT",
        "summary_html": "TEXT",
        "content_html": "TEXT",
        "content_text": "TEXT",
        "image_url": "TEXT",
        "views_count": "INTEGER",
        "reading_time_minutes": "INTEGER",
        "comments_count": "INTEGER",
        "cover_image_path": "TEXT",
        "published_label": "TEXT",
        "source_order": "INTEGER",
        "source": "TEXT DEFAULT 'rss'",
        "source_guid": "TEXT",
        "updated_at_from_feed": "TEXT",
        "content_hash": "TEXT",
        "first_seen_at": "TEXT",
        "last_seen_at": "TEXT",
        "last_changed_at": "TEXT",
    }

    for column_name, column_type in required_columns.items():
        if column_name in existing_columns:
            continue
        connection.execute(f"ALTER TABLE posts ADD COLUMN {column_name} {column_type}")

    connection.execute(
        """
        UPDATE posts
        SET
            first_seen_at = COALESCE(first_seen_at, created_at, CURRENT_TIMESTAMP),
            last_seen_at = COALESCE(last_seen_at, created_at, CURRENT_TIMESTAMP),
            last_changed_at = COALESCE(last_changed_at, created_at, CURRENT_TIMESTAMP)
        """
    )


def _ensure_article_images_table(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS article_images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER,
            article_link TEXT NOT NULL,
            article_source_id TEXT,
            source_url TEXT NOT NULL,
            local_path TEXT,
            position INTEGER NOT NULL,
            role TEXT NOT NULL,
            alt_text TEXT,
            mime_type TEXT,
            file_size INTEGER,
            sha256 TEXT,
            download_status TEXT NOT NULL,
            error TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (post_id) REFERENCES posts(id)
        )
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_article_images_post_id
        ON article_images(post_id)
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_article_images_article_link
        ON article_images(article_link)
        """
    )


def save_posts(posts: Iterable[RssPost], source: str = "rss") -> ImportStats:
    created_count = 0
    updated_count = 0
    unchanged_count = 0

    with get_connection() as connection:
        for post in posts:
            categories = ", ".join(post.categories)
            existing_post = connection.execute(
                "SELECT id, content_hash FROM posts WHERE link = ?",
                (post.link,),
            ).fetchone()

            if existing_post is None:
                connection.execute(
                    """
                    INSERT INTO posts (
                        title,
                        link,
                        guid,
                        published,
                        updated,
                        summary,
                        summary_html,
                        content_html,
                        content_text,
                        image_url,
                        author,
                        categories,
                        source,
                        source_guid,
                        updated_at_from_feed,
                        content_hash
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        post.title,
                        post.link,
                        post.guid,
                        post.published,
                        post.updated,
                        post.summary,
                        post.summary_html,
                        post.content_html,
                        post.content_text,
                        post.image_url,
                        post.author,
                        categories,
                        source,
                        post.guid,
                        post.updated,
                        post.content_hash,
                    ),
                )
                created_count += 1
                continue

            existing_hash = existing_post["content_hash"] or ""
            has_changes = existing_hash != post.content_hash

            if has_changes:
                connection.execute(
                    """
                    UPDATE posts
                    SET
                        title = ?,
                        guid = ?,
                        published = ?,
                        updated = ?,
                        summary = ?,
                        summary_html = ?,
                        content_html = ?,
                        content_text = ?,
                        image_url = ?,
                        author = ?,
                        categories = ?,
                        source = ?,
                        source_guid = ?,
                        updated_at_from_feed = ?,
                        content_hash = ?,
                        last_seen_at = CURRENT_TIMESTAMP,
                        last_changed_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (
                        post.title,
                        post.guid,
                        post.published,
                        post.updated,
                        post.summary,
                        post.summary_html,
                        post.content_html,
                        post.content_text,
                        post.image_url,
                        post.author,
                        categories,
                        source,
                        post.guid,
                        post.updated,
                        post.content_hash,
                        existing_post["id"],
                    ),
                )
                updated_count += 1
            else:
                connection.execute(
                    """
                    UPDATE posts
                    SET
                        last_seen_at = CURRENT_TIMESTAMP,
                        updated_at_from_feed = ?
                    WHERE id = ?
                    """,
                    (post.updated, existing_post["id"]),
                )
                unchanged_count += 1

    return ImportStats(
        created=created_count,
        updated=updated_count,
        unchanged=unchanged_count,
    )


def get_latest_posts(limit: int = 10) -> list[sqlite3.Row]:
    init_db()
    with get_connection() as connection:
        cursor = connection.execute(
            """
            SELECT
                id,
                title,
                link,
                published,
                summary,
                author,
                categories,
                views_count,
                comments_count,
                cover_image_path
            FROM posts
            ORDER BY
                CASE
                    WHEN source_order IS NULL THEN 1
                    ELSE 0
                END,
                source_order ASC,
                id DESC
            LIMIT ?
            """,
            (limit,),
        )
        return list(cursor.fetchall())


def get_top_posts(limit: int = 10) -> list[sqlite3.Row]:
    init_db()
    with get_connection() as connection:
        cursor = connection.execute(
            """
            SELECT
                id,
                title,
                link,
                published,
                summary,
                author,
                categories,
                views_count,
                comments_count,
                cover_image_path
            FROM posts
            ORDER BY
                COALESCE(views_count, 0) DESC,
                id DESC
            LIMIT ?
            """,
            (limit,),
        )
        return list(cursor.fetchall())


def get_random_post() -> Optional[sqlite3.Row]:
    init_db()
    with get_connection() as connection:
        return connection.execute(
            """
            SELECT
                id,
                title,
                link,
                published,
                summary,
                author,
                categories,
                views_count,
                comments_count,
                cover_image_path
            FROM posts
            ORDER BY RANDOM()
            LIMIT 1
            """
        ).fetchone()
