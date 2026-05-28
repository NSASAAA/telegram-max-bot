import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from hashlib import sha256
import json
import mimetypes
import os
from pathlib import Path
import re
from typing import Any, Optional
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from telegram_max_bot.core.models import ImportStats
from telegram_max_bot.db import get_connection, init_db


DEFAULT_RAW_PATH = Path("data/raw/dzen_1234elena/articles_full.jsonl")
DEFAULT_DB_PATH = Path("data/dzen_bot.db")
DEFAULT_MEDIA_ROOT = Path("data/media/dzen_1234elena")
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)


@dataclass(frozen=True)
class DzenImageCandidate:
    source_url: str
    alt_text: str
    position: int
    role: str


@dataclass(frozen=True)
class DzenImageRecord:
    article_source_id: str
    article_link: str
    article_title: str
    source_url: str
    local_path: str
    position: int
    role: str
    alt_text: str
    mime_type: str
    file_size: int
    sha256: str
    download_status: str
    error: str


@dataclass(frozen=True)
class DzenArticle:
    article_source_id: str
    source_order: int
    title: str
    link: str
    published_label: str
    views_count: Optional[int]
    reading_time_minutes: Optional[int]
    comments_count: Optional[int]
    content_text: str
    channel_name: str
    content_hash: str
    images: list[DzenImageRecord]


def _load_rows(raw_path: Path, limit: Optional[int] = None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with raw_path.open("r", encoding="utf-8") as file:
        for line in file:
            if not line.strip():
                continue
            rows.append(json.loads(line))
            if limit and len(rows) >= limit:
                break
    return rows


def _parse_article_id(url: str) -> str:
    parsed = urlparse(url)
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) >= 2 and parts[-2] == "a":
        return _safe_name(parts[-1])
    return sha256(url.encode("utf-8")).hexdigest()[:16]


def _safe_name(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("._")
    return cleaned or "unknown"


def _parse_views(label: str) -> Optional[int]:
    text = (label or "").replace("\xa0", " ").strip().lower()
    match = re.search(r"(\d+(?:[,.]\d+)?)", text)
    if not match:
        return None

    number = float(match.group(1).replace(",", "."))
    if "тыс" in text or "k" in text:
        number *= 1000
    return int(round(number))


def _parse_reading_time(label: str) -> Optional[int]:
    text = (label or "").replace("\xa0", " ").strip().lower()
    match = re.search(r"(\d+)", text)
    if not match:
        return None
    return int(match.group(1))


def _parse_comments_count(raw_text: str) -> Optional[int]:
    matches = re.findall(r"Комментарии\s*(\d+)", raw_text or "")
    if not matches:
        return None
    return int(matches[0])


def _content_hash(title: str, link: str, text: str) -> str:
    payload = "\n".join([title or "", link or "", text or ""])
    return sha256(payload.encode("utf-8")).hexdigest()


def _is_candidate_image(source_url: str) -> bool:
    parsed = urlparse(source_url)
    if parsed.scheme not in {"http", "https"}:
        return False
    if parsed.netloc != "avatars.dzeninfra.ru":
        return False
    if "/get-zen_doc/" not in parsed.path:
        return False

    lowered = source_url.lower()
    skip_markers = ("emoji", "favicon", "icon", "mradx", "yabs")
    return not any(marker in lowered for marker in skip_markers)


def _image_variant_score(source_url: str) -> int:
    variant = urlparse(source_url).path.rsplit("/", 1)[-1]
    if variant.startswith("scale_"):
        match = re.search(r"scale_(\d+)", variant)
        return 1000 + int(match.group(1)) if match else 1000
    if variant.startswith("smart_crop"):
        return 100
    return 10


def _select_image_candidates(raw_images: list[Any]) -> list[DzenImageCandidate]:
    grouped: dict[str, tuple[int, str, str, int]] = {}

    for index, raw_image in enumerate(raw_images):
        if not isinstance(raw_image, dict):
            continue
        source_url = raw_image.get("src", "")
        alt_text = raw_image.get("alt", "")
        if not source_url or not _is_candidate_image(source_url):
            continue

        group_key = source_url.rsplit("/", 1)[0]
        score = _image_variant_score(source_url)
        existing = grouped.get(group_key)
        if existing is None or score > existing[3]:
            grouped[group_key] = (index, source_url, alt_text, score)

    selected = sorted(grouped.values(), key=lambda item: item[0])
    candidates: list[DzenImageCandidate] = []
    for position, (_index, source_url, alt_text, _score) in enumerate(selected, start=1):
        role = "cover" if position == 1 else "inline"
        candidates.append(
            DzenImageCandidate(
                source_url=source_url,
                alt_text=alt_text,
                position=position,
                role=role,
            )
        )
    return candidates


def _extension_for_mime_type(mime_type: str) -> str:
    if mime_type == "image/jpeg":
        return ".jpg"
    extension = mimetypes.guess_extension(mime_type or "")
    if extension in {".jpe", ".jpeg"}:
        return ".jpg"
    return extension or ".img"


def _download_image(
    article_source_id: str,
    article_link: str,
    article_title: str,
    candidate: DzenImageCandidate,
    media_root: Path,
    timeout_seconds: int,
) -> DzenImageRecord:
    article_dir = media_root / "articles" / article_source_id
    article_dir.mkdir(parents=True, exist_ok=True)

    filename_prefix = f"{candidate.position:03d}-{candidate.role}"
    existing_files = sorted(article_dir.glob(f"{filename_prefix}.*"))
    if existing_files:
        image_path = existing_files[0]
        data = image_path.read_bytes()
        mime_type = mimetypes.guess_type(image_path.name)[0] or ""
        return DzenImageRecord(
            article_source_id=article_source_id,
            article_link=article_link,
            article_title=article_title,
            source_url=candidate.source_url,
            local_path=image_path.as_posix(),
            position=candidate.position,
            role=candidate.role,
            alt_text=candidate.alt_text,
            mime_type=mime_type,
            file_size=len(data),
            sha256=sha256(data).hexdigest(),
            download_status="downloaded",
            error="",
        )

    request = Request(candidate.source_url, headers={"User-Agent": USER_AGENT})

    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            data = response.read()
            mime_type = response.headers.get_content_type()

        digest = sha256(data).hexdigest()
        extension = _extension_for_mime_type(mime_type)
        image_path = article_dir / f"{filename_prefix}{extension}"
        image_path.write_bytes(data)

        return DzenImageRecord(
            article_source_id=article_source_id,
            article_link=article_link,
            article_title=article_title,
            source_url=candidate.source_url,
            local_path=image_path.as_posix(),
            position=candidate.position,
            role=candidate.role,
            alt_text=candidate.alt_text,
            mime_type=mime_type,
            file_size=len(data),
            sha256=digest,
            download_status="downloaded",
            error="",
        )
    except (OSError, URLError, TimeoutError) as error:
        return DzenImageRecord(
            article_source_id=article_source_id,
            article_link=article_link,
            article_title=article_title,
            source_url=candidate.source_url,
            local_path="",
            position=candidate.position,
            role=candidate.role,
            alt_text=candidate.alt_text,
            mime_type="",
            file_size=0,
            sha256="",
            download_status="failed",
            error=str(error),
        )


def _build_articles(
    rows: list[dict[str, Any]],
    media_root: Path,
    skip_download: bool,
    workers: int,
    timeout_seconds: int,
) -> list[DzenArticle]:
    image_tasks: list[tuple[str, str, str, DzenImageCandidate]] = []
    rows_by_article_id: dict[str, dict[str, Any]] = {}

    for source_order, row in enumerate(rows, start=1):
        link = row.get("url", "")
        article_source_id = _parse_article_id(link)
        row["_source_order"] = source_order
        rows_by_article_id[article_source_id] = row
        candidates = _select_image_candidates(row.get("images") or [])
        for candidate in candidates:
            image_tasks.append((article_source_id, link, row.get("title", ""), candidate))

    records_by_article_id: dict[str, list[DzenImageRecord]] = {
        article_id: [] for article_id in rows_by_article_id
    }

    if skip_download:
        for article_source_id, link, title, candidate in image_tasks:
            records_by_article_id[article_source_id].append(
                DzenImageRecord(
                    article_source_id=article_source_id,
                    article_link=link,
                    article_title=title,
                    source_url=candidate.source_url,
                    local_path="",
                    position=candidate.position,
                    role=candidate.role,
                    alt_text=candidate.alt_text,
                    mime_type="",
                    file_size=0,
                    sha256="",
                    download_status="skipped",
                    error="",
                )
            )
    else:
        with ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
            future_to_article_id = {
                executor.submit(
                    _download_image,
                    article_source_id,
                    link,
                    title,
                    candidate,
                    media_root,
                    timeout_seconds,
                ): article_source_id
                for article_source_id, link, title, candidate in image_tasks
            }
            for future in as_completed(future_to_article_id):
                article_source_id = future_to_article_id[future]
                records_by_article_id[article_source_id].append(future.result())

    articles: list[DzenArticle] = []
    for article_source_id, row in rows_by_article_id.items():
        link = row.get("url", "")
        title = row.get("title", "").strip()
        content_text = (row.get("content_text_guess") or "").strip()
        image_records = sorted(
            records_by_article_id[article_source_id],
            key=lambda record: record.position,
        )
        articles.append(
            DzenArticle(
                article_source_id=article_source_id,
                source_order=int(row.get("_source_order", 0)),
                title=title,
                link=link,
                published_label=row.get("published_label", ""),
                views_count=_parse_views(row.get("views_label", "")),
                reading_time_minutes=_parse_reading_time(row.get("reading_time_label", "")),
                comments_count=_parse_comments_count(row.get("raw_main_text", "")),
                content_text=content_text,
                channel_name=row.get("channel_name", ""),
                content_hash=_content_hash(title, link, content_text),
                images=image_records,
            )
        )
    return articles


def _summary_text(content_text: str, limit: int = 700) -> str:
    if len(content_text) <= limit:
        return content_text
    return content_text[:limit].rstrip() + "..."


def _save_articles(articles: list[DzenArticle]) -> ImportStats:
    created = 0
    updated = 0
    unchanged = 0

    with get_connection() as connection:
        for article in articles:
            cover = next(
                (image for image in article.images if image.role == "cover" and image.local_path),
                None,
            )
            existing_post = connection.execute(
                "SELECT id, content_hash FROM posts WHERE link = ?",
                (article.link,),
            ).fetchone()

            values = (
                article.title,
                article.link,
                article.article_source_id,
                article.published_label,
                "",
                _summary_text(article.content_text),
                "",
                "",
                article.content_text,
                cover.source_url if cover else "",
                article.views_count,
                article.reading_time_minutes,
                article.comments_count,
                cover.local_path if cover else "",
                article.published_label,
                article.source_order,
                article.channel_name,
                "",
                "dzen",
                article.article_source_id,
                "",
                article.content_hash,
            )

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
                        views_count,
                        reading_time_minutes,
                        comments_count,
                        cover_image_path,
                        published_label,
                        source_order,
                        author,
                        categories,
                        source,
                        source_guid,
                        updated_at_from_feed,
                        content_hash
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    values,
                )
                created += 1
            else:
                post_id = existing_post["id"]
                existing_hash = existing_post["content_hash"] or ""
                if existing_hash != article.content_hash:
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
                            views_count = ?,
                            reading_time_minutes = ?,
                            comments_count = ?,
                            cover_image_path = ?,
                            published_label = ?,
                            source_order = ?,
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
                            article.title,
                            article.article_source_id,
                            article.published_label,
                            "",
                            _summary_text(article.content_text),
                            "",
                            "",
                            article.content_text,
                            cover.source_url if cover else "",
                            article.views_count,
                            article.reading_time_minutes,
                            article.comments_count,
                            cover.local_path if cover else "",
                            article.published_label,
                            article.source_order,
                            article.channel_name,
                            "",
                            "dzen",
                            article.article_source_id,
                            "",
                            article.content_hash,
                            post_id,
                        ),
                    )
                    updated += 1
                else:
                    connection.execute(
                        """
                        UPDATE posts
                        SET
                            views_count = ?,
                            reading_time_minutes = ?,
                            comments_count = ?,
                            cover_image_path = ?,
                            image_url = ?,
                            source_order = ?,
                            last_seen_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                        """,
                        (
                            article.views_count,
                            article.reading_time_minutes,
                            article.comments_count,
                            cover.local_path if cover else "",
                            cover.source_url if cover else "",
                            article.source_order,
                            post_id,
                        ),
                    )
                    unchanged += 1

            post = connection.execute(
                "SELECT id FROM posts WHERE link = ?",
                (article.link,),
            ).fetchone()
            post_id = post["id"]
            connection.execute("DELETE FROM article_images WHERE article_link = ?", (article.link,))

            for image in article.images:
                connection.execute(
                    """
                    INSERT INTO article_images (
                        post_id,
                        article_link,
                        article_source_id,
                        source_url,
                        local_path,
                        position,
                        role,
                        alt_text,
                        mime_type,
                        file_size,
                        sha256,
                        download_status,
                        error
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        post_id,
                        image.article_link,
                        image.article_source_id,
                        image.source_url,
                        image.local_path,
                        image.position,
                        image.role,
                        image.alt_text,
                        image.mime_type,
                        image.file_size,
                        image.sha256,
                        image.download_status,
                        image.error,
                    ),
                )

    return ImportStats(created=created, updated=updated, unchanged=unchanged)


def _write_manifest(articles: list[DzenArticle], manifest_path: Path) -> None:
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with manifest_path.open("w", encoding="utf-8") as file:
        for article in articles:
            for image in article.images:
                file.write(json.dumps(image.__dict__, ensure_ascii=False) + "\n")


def import_dzen_archive(
    raw_path: Path = DEFAULT_RAW_PATH,
    db_path: Path = DEFAULT_DB_PATH,
    media_root: Path = DEFAULT_MEDIA_ROOT,
    skip_download: bool = False,
    workers: int = 6,
    timeout_seconds: int = 30,
    limit: Optional[int] = None,
) -> tuple[ImportStats, list[DzenArticle]]:
    os.environ["DATABASE_PATH"] = db_path.as_posix()
    rows = _load_rows(raw_path, limit=limit)
    articles = _build_articles(
        rows=rows,
        media_root=media_root,
        skip_download=skip_download,
        workers=workers,
        timeout_seconds=timeout_seconds,
    )

    init_db()
    stats = _save_articles(articles)
    _write_manifest(articles, media_root / "images_manifest.jsonl")
    return stats, articles


def main() -> None:
    parser = argparse.ArgumentParser(description="Import local Dzen archive into SQLite.")
    parser.add_argument("--raw-path", type=Path, default=DEFAULT_RAW_PATH)
    parser.add_argument("--db-path", type=Path, default=DEFAULT_DB_PATH)
    parser.add_argument("--media-root", type=Path, default=DEFAULT_MEDIA_ROOT)
    parser.add_argument("--skip-download", action="store_true")
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--timeout-seconds", type=int, default=30)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    stats, articles = import_dzen_archive(
        raw_path=args.raw_path,
        db_path=args.db_path,
        media_root=args.media_root,
        skip_download=args.skip_download,
        workers=args.workers,
        timeout_seconds=args.timeout_seconds,
        limit=args.limit,
    )

    image_records = [image for article in articles for image in article.images]
    downloaded = sum(1 for image in image_records if image.download_status == "downloaded")
    failed = sum(1 for image in image_records if image.download_status == "failed")
    skipped = sum(1 for image in image_records if image.download_status == "skipped")
    with_cover = sum(
        1
        for article in articles
        if any(image.role == "cover" and image.local_path for image in article.images)
    )

    print("Dzen import finished.")
    print(f"Articles received: {len(articles)}")
    print(f"Posts created: {stats.created}")
    print(f"Posts updated: {stats.updated}")
    print(f"Posts unchanged: {stats.unchanged}")
    print(f"Image records: {len(image_records)}")
    print(f"Images downloaded: {downloaded}")
    print(f"Images failed: {failed}")
    print(f"Images skipped: {skipped}")
    print(f"Articles with cover: {with_cover}")
    print(f"Database: {args.db_path}")
    print(f"Manifest: {args.media_root / 'images_manifest.jsonl'}")


if __name__ == "__main__":
    main()
