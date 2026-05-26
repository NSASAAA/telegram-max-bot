from dataclasses import dataclass
from typing import List

import feedparser


@dataclass
class RssPost:
    title: str
    link: str
    published: str
    summary: str
    author: str
    categories: list[str]


def fetch_rss_posts(rss_url: str) -> List[RssPost]:
    feed = feedparser.parse(rss_url)

    if feed.bozo:
        raise RuntimeError(f"RSS parse error: {feed.bozo_exception}")

    posts: list[RssPost] = []

    for entry in feed.entries:
        posts.append(
            RssPost(
                title=entry.get("title", ""),
                link=entry.get("link", ""),
                published=entry.get("published", ""),
                summary=entry.get("summary", ""),
                author=entry.get("author", ""),
                categories=[tag.get("term", "") for tag in entry.get("tags", [])],
            )
        )

    return posts
