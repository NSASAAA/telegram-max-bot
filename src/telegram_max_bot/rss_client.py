from dataclasses import dataclass
from hashlib import sha256
from html import unescape
import re
from typing import Any, List

import feedparser


@dataclass
class RssPost:
    title: str
    link: str
    guid: str
    published: str
    updated: str
    summary: str
    summary_html: str
    content_html: str
    content_text: str
    image_url: str
    author: str
    categories: list[str]
    content_hash: str


def _clean_html(raw_html: str) -> str:
    text = re.sub(r"<[^>]+>", " ", raw_html or "")
    text = unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _extract_content_html(entry: dict[str, Any], summary_html: str) -> str:
    content_items = entry.get("content", [])

    if content_items and isinstance(content_items, list):
        first_item = content_items[0]
        if isinstance(first_item, dict):
            return first_item.get("value", "") or summary_html

    return summary_html


def _extract_image_url(entry: dict[str, Any]) -> str:
    media_items = entry.get("media_content", [])
    if media_items and isinstance(media_items, list):
        first_media = media_items[0]
        if isinstance(first_media, dict):
            media_url = first_media.get("url")
            if media_url:
                return media_url

    links = entry.get("links", [])
    for link_item in links:
        if isinstance(link_item, dict):
            link_type = link_item.get("type", "")
            href = link_item.get("href", "")
            if link_type.startswith("image/") and href:
                return href

    return ""


def _build_content_hash(
    title: str,
    link: str,
    guid: str,
    published: str,
    updated: str,
    summary_html: str,
    content_html: str,
) -> str:
    payload = "\n".join(
        [
            title or "",
            link or "",
            guid or "",
            published or "",
            updated or "",
            summary_html or "",
            content_html or "",
        ]
    )
    return sha256(payload.encode("utf-8")).hexdigest()


def fetch_rss_posts(rss_url: str) -> List[RssPost]:
    feed = feedparser.parse(rss_url)

    if feed.bozo:
        raise RuntimeError(f"RSS parse error: {feed.bozo_exception}")

    posts: list[RssPost] = []

    for entry in feed.entries:
        title = entry.get("title", "")
        link = entry.get("link", "")
        guid = entry.get("id", "") or entry.get("guid", "") or link
        published = entry.get("published", "")
        updated = entry.get("updated", "")
        summary_html = entry.get("summary", "")
        content_html = _extract_content_html(entry, summary_html)
        content_text = _clean_html(content_html or summary_html)
        image_url = _extract_image_url(entry)
        author = entry.get("author", "")
        categories = [tag.get("term", "") for tag in entry.get("tags", [])]
        content_hash = _build_content_hash(
            title=title,
            link=link,
            guid=guid,
            published=published,
            updated=updated,
            summary_html=summary_html,
            content_html=content_html,
        )

        posts.append(
            RssPost(
                title=title,
                link=link,
                guid=guid,
                published=published,
                updated=updated,
                summary=content_text,
                summary_html=summary_html,
                content_html=content_html,
                content_text=content_text,
                image_url=image_url,
                author=author,
                categories=categories,
                content_hash=content_hash,
            )
        )

    return posts
