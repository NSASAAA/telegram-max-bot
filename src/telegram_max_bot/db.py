import sqlite3
import os
from pathlib import Path
from typing import Iterable, Optional

from telegram_max_bot.core.models import ImportStats, Topic
from telegram_max_bot.core.topics import (
    TOPIC_CLASSIFIER_VERSION,
    TOPICS,
    classify_topics,
)
from telegram_max_bot.rss_client import RssPost


ARTICLE_TOPICS_META_KEY = "article_topics_signature"
WELCOME_TITLE_CANDIDATES = (
    "Привет. Давайте знакомиться",
    "Привет, давайте знакомиться",
    "Привет давайте знакомиться",
)


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
                is_welcome_article INTEGER DEFAULT 0,
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
        _refresh_welcome_article_marker(connection)
        _ensure_article_images_table(connection)
        _ensure_article_topics_table(connection)
        _ensure_app_meta_table(connection)


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
        "is_welcome_article": "INTEGER DEFAULT 0",
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


def _refresh_welcome_article_marker(connection: sqlite3.Connection) -> None:
    welcome_post_id = _find_welcome_post_id(connection)
    if welcome_post_id is None:
        return

    current_rows = connection.execute(
        """
        SELECT id
        FROM posts
        WHERE COALESCE(is_welcome_article, 0) = 1
        """
    ).fetchall()
    current_ids = [int(row["id"]) for row in current_rows]

    if current_ids == [welcome_post_id]:
        return

    if current_ids:
        connection.execute(
            """
            UPDATE posts
            SET is_welcome_article = 0
            WHERE COALESCE(is_welcome_article, 0) = 1
            """
        )

    connection.execute(
        """
        UPDATE posts
        SET is_welcome_article = 1
        WHERE id = ?
        """,
        (welcome_post_id,),
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


def _ensure_article_topics_table(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS article_topics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER NOT NULL,
            topic_code TEXT NOT NULL,
            score INTEGER NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(post_id, topic_code),
            FOREIGN KEY (post_id) REFERENCES posts(id)
        )
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_article_topics_topic_code
        ON article_topics(topic_code)
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_article_topics_post_id
        ON article_topics(post_id)
        """
    )


def _ensure_app_meta_table(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS app_meta (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
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
                published_label,
                summary,
                author,
                categories,
                views_count,
                comments_count,
                cover_image_path
            FROM posts
            WHERE COALESCE(is_welcome_article, 0) = 0
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
                published_label,
                summary,
                author,
                categories,
                views_count,
                comments_count,
                cover_image_path
            FROM posts
            WHERE COALESCE(is_welcome_article, 0) = 0
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
                published_label,
                summary,
                author,
                categories,
                views_count,
                comments_count,
                cover_image_path
            FROM posts
            WHERE COALESCE(is_welcome_article, 0) = 0
            ORDER BY RANDOM()
            LIMIT 1
            """
        ).fetchone()


def get_welcome_post() -> Optional[sqlite3.Row]:
    init_db()
    with get_connection() as connection:
        select_columns = """
            SELECT
                id,
                title,
                link,
                published,
                published_label,
                summary,
                author,
                categories,
                views_count,
                comments_count,
                cover_image_path
            FROM posts
        """
        flagged_post = connection.execute(
            f"""
            {select_columns}
            WHERE COALESCE(is_welcome_article, 0) = 1
            ORDER BY id ASC
            LIMIT 1
            """
        ).fetchone()
        if flagged_post is not None:
            return flagged_post

        sort_clause = """
            ORDER BY
                CASE
                    WHEN source_order IS NULL THEN 1
                    ELSE 0
                END,
                source_order ASC,
                id ASC
        """

        for candidate_title in WELCOME_TITLE_CANDIDATES:
            exact_match = connection.execute(
                f"""
                {select_columns}
                WHERE TRIM(title) = ?
                {sort_clause}
                LIMIT 1
                """,
                (candidate_title,),
            ).fetchone()
            if exact_match is not None:
                return exact_match

        early_posts = connection.execute(
            f"""
            {select_columns}
            {sort_clause}
            LIMIT 100
            """
        ).fetchall()
        for post in early_posts:
            normalized_title = _normalize_search_text(post["title"] or "")
            if "привет" in normalized_title and "знаком" in normalized_title:
                return post

        return None


def _find_welcome_post_id(connection: sqlite3.Connection) -> Optional[int]:
    for candidate_title in WELCOME_TITLE_CANDIDATES:
        row = connection.execute(
            """
            SELECT id
            FROM posts
            WHERE TRIM(title) = ?
            ORDER BY
                CASE
                    WHEN source_order IS NULL THEN 1
                    ELSE 0
                END,
                source_order ASC,
                id ASC
            LIMIT 1
            """,
            (candidate_title,),
        ).fetchone()
        if row is not None:
            return int(row["id"])

    early_posts = connection.execute(
        """
        SELECT id, title
        FROM posts
        ORDER BY
            CASE
                WHEN source_order IS NULL THEN 1
                ELSE 0
            END,
            source_order ASC,
            id ASC
        LIMIT 100
        """
    ).fetchall()
    for post in early_posts:
        normalized_title = _normalize_search_text(post["title"] or "")
        if "привет" in normalized_title and "знаком" in normalized_title:
            return int(post["id"])

    return None


def _normalize_search_text(value: str) -> str:
    text = value.casefold().replace("ё", "е")
    for symbol in (".", ",", "!", "?", ";", ":", "—", "-", "(", ")"):
        text = text.replace(symbol, " ")
    return " ".join(text.split())


def get_post_by_id(post_id: int) -> Optional[sqlite3.Row]:
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
                content_text,
                author,
                categories,
                views_count,
                reading_time_minutes,
                comments_count,
                cover_image_path,
                published_label
            FROM posts
            WHERE id = ?
            LIMIT 1
            """,
            (post_id,),
        ).fetchone()


def get_article_images(post_id: int) -> list[sqlite3.Row]:
    init_db()
    with get_connection() as connection:
        cursor = connection.execute(
            """
            SELECT
                id,
                post_id,
                local_path,
                position,
                role,
                alt_text,
                mime_type,
                file_size
            FROM article_images
            WHERE post_id = ?
                AND download_status = 'downloaded'
                AND local_path IS NOT NULL
                AND local_path != ''
            ORDER BY position ASC, id ASC
            """,
            (post_id,),
        )
        return list(cursor.fetchall())


def get_topic_counts() -> list[tuple[Topic, int]]:
    init_db()
    _ensure_article_topics_index()

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT article_topics.topic_code, COUNT(*) AS posts_count
            FROM article_topics
            JOIN posts ON posts.id = article_topics.post_id
            WHERE COALESCE(posts.is_welcome_article, 0) = 0
            GROUP BY topic_code
            """
        ).fetchall()

    counts = {row["topic_code"]: row["posts_count"] for row in rows}
    return [(topic, counts.get(topic.code, 0)) for topic in TOPICS]


def get_posts_count_by_topic(topic_code: str) -> int:
    init_db()
    _ensure_article_topics_index()

    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT COUNT(*) AS posts_count
            FROM article_topics
            JOIN posts ON posts.id = article_topics.post_id
            WHERE topic_code = ?
                AND COALESCE(posts.is_welcome_article, 0) = 0
            """,
            (topic_code,),
        ).fetchone()
        return int(row["posts_count"]) if row else 0


def get_posts_by_topic(topic_code: str, limit: int = 10, offset: int = 0) -> list[sqlite3.Row]:
    init_db()
    _ensure_article_topics_index()

    with get_connection() as connection:
        cursor = connection.execute(
            """
            SELECT
                posts.id,
                posts.title,
                posts.link,
                posts.published,
                posts.published_label,
                posts.summary,
                posts.author,
                posts.categories,
                posts.views_count,
                posts.comments_count,
                posts.cover_image_path,
                article_topics.score AS topic_score
            FROM posts
            JOIN article_topics ON article_topics.post_id = posts.id
            WHERE article_topics.topic_code = ?
                AND COALESCE(posts.is_welcome_article, 0) = 0
            ORDER BY
                article_topics.score DESC,
                COALESCE(posts.views_count, 0) DESC,
                CASE
                    WHEN posts.source_order IS NULL THEN 1
                    ELSE 0
                END,
                posts.source_order ASC,
                posts.id DESC
            LIMIT ?
            OFFSET ?
            """,
            (topic_code, max(0, limit), max(0, offset)),
        )
        return list(cursor.fetchall())


def refresh_article_topics() -> int:
    init_db()
    with get_connection() as connection:
        assignments_count = _rebuild_article_topics(connection)
        signature = _current_posts_signature(connection)
        _save_meta_value(connection, ARTICLE_TOPICS_META_KEY, signature)
        return assignments_count


def _ensure_article_topics_index() -> int:
    with get_connection() as connection:
        signature = _current_posts_signature(connection)
        stored_signature = _get_meta_value(connection, ARTICLE_TOPICS_META_KEY)
        topic_rows_count = connection.execute(
            "SELECT COUNT(*) AS rows_count FROM article_topics"
        ).fetchone()["rows_count"]
        posts_count = connection.execute(
            "SELECT COUNT(*) AS posts_count FROM posts"
        ).fetchone()["posts_count"]

        if stored_signature == signature and (topic_rows_count > 0 or posts_count == 0):
            return 0

        assignments_count = _rebuild_article_topics(connection)
        _save_meta_value(connection, ARTICLE_TOPICS_META_KEY, signature)
        return assignments_count


def _current_posts_signature(connection: sqlite3.Connection) -> str:
    row = connection.execute(
        """
        SELECT
            COUNT(*) AS posts_count,
            COALESCE(MAX(id), 0) AS max_id,
            COALESCE(MAX(last_changed_at), '') AS max_last_changed_at
        FROM posts
        """
    ).fetchone()
    return (
        f"{TOPIC_CLASSIFIER_VERSION}:"
        f"{row['posts_count']}:"
        f"{row['max_id']}:"
        f"{row['max_last_changed_at']}"
    )


def _rebuild_article_topics(connection: sqlite3.Connection) -> int:
    connection.execute("DELETE FROM article_topics")
    posts = connection.execute(
        """
        SELECT id, title, summary, content_text, categories
        FROM posts
        """
    ).fetchall()

    assignments_count = 0
    for post in posts:
        matches = classify_topics(
            title=post["title"] or "",
            summary=post["summary"] or "",
            content_text=post["content_text"] or "",
            categories=post["categories"] or "",
        )
        for topic, score in matches:
            connection.execute(
                """
                INSERT INTO article_topics (post_id, topic_code, score)
                VALUES (?, ?, ?)
                """,
                (post["id"], topic.code, score),
            )
            assignments_count += 1

    return assignments_count


def _get_meta_value(connection: sqlite3.Connection, key: str) -> Optional[str]:
    row = connection.execute(
        "SELECT value FROM app_meta WHERE key = ?",
        (key,),
    ).fetchone()
    if row is None:
        return None
    return row["value"]


def _save_meta_value(connection: sqlite3.Connection, key: str, value: str) -> None:
    connection.execute(
        """
        INSERT INTO app_meta (key, value, updated_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(key) DO UPDATE SET
            value = excluded.value,
            updated_at = CURRENT_TIMESTAMP
        """,
        (key, value),
    )
