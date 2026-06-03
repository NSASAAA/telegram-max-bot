from html import escape
from pathlib import Path
import re
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse

from telegram_max_bot.db import get_article_images, get_db_path, get_post_by_id


app = FastAPI(title="Telegram MAX Bot Web Reader")


@app.get("/healthz", response_class=PlainTextResponse)
def healthz() -> str:
    return "ok"


@app.get("/articles/{post_id}", response_class=HTMLResponse)
def article_page(post_id: int) -> str:
    post = get_post_by_id(post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="Article not found")

    images = get_article_images(post_id)
    cover = next((image for image in images if image["role"] == "cover"), None)
    inline_images = [image for image in images if image["role"] != "cover"]
    paragraphs = _paragraphs(post["content_text"] or post["summary"] or "")

    return _render_article(
        title=post["title"] or "Статья",
        published_label=post["published_label"] or post["published"] or "",
        reading_time_minutes=post["reading_time_minutes"],
        cover_path=cover["local_path"] if cover else post["cover_image_path"],
        inline_images=inline_images,
        paragraphs=paragraphs,
        dzen_link=post.get("link") or "",
    )


@app.get("/media/{media_path:path}")
def media_file(media_path: str) -> FileResponse:
    media_root = _data_root() / "media"
    requested_path = (media_root / media_path).resolve()

    if media_root.resolve() not in requested_path.parents:
        raise HTTPException(status_code=404, detail="Media not found")

    if not requested_path.is_file():
        raise HTTPException(status_code=404, detail="Media not found")

    return FileResponse(requested_path)


def _render_article(
    *,
    title: str,
    published_label: str,
    reading_time_minutes: Optional[int],
    cover_path: Optional[str],
    inline_images: list,
    paragraphs: list[str],
    dzen_link: str = "",
) -> str:
    safe_title = escape(title)
    meta_items = []
    if published_label:
        meta_items.append(escape(published_label))
    if reading_time_minutes:
        meta_items.append(f"{reading_time_minutes} мин чтения")

    meta_html = ""
    if meta_items:
        meta_html = f"<div class=\"article-meta\">{' · '.join(meta_items)}</div>"

    cover_html = _image_html(cover_path, css_class="cover") if cover_path else ""
    body_html = _body_html(paragraphs, inline_images)

    return f"""<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{safe_title}</title>
  <script src="https://telegram.org/js/telegram-web-app.js"></script>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f6f2eb;
      --paper: #fffdf8;
      --text: #241f1a;
      --muted: #75695d;
      --line: #e4d8ca;
      --accent: #356859;
    }}

    * {{
      box-sizing: border-box;
    }}

    body {{
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      font-size: 18px;
      line-height: 1.65;
    }}

    main {{
      width: min(760px, 100%);
      margin: 0 auto;
      padding: 20px 16px 44px;
    }}

    article {{
      background: var(--paper);
      border: 1px solid var(--line);
      border-radius: 8px;
      overflow: hidden;
      box-shadow: 0 18px 45px rgba(73, 54, 33, 0.08);
    }}

    .article-inner {{
      padding: 22px 18px 30px;
    }}

    h1 {{
      margin: 0 0 10px;
      font-size: clamp(28px, 7vw, 44px);
      line-height: 1.12;
      letter-spacing: 0;
    }}

    .article-meta {{
      margin-bottom: 22px;
      color: var(--muted);
      font-size: 15px;
    }}

    p {{
      margin: 0 0 18px;
    }}

    img {{
      display: block;
      width: 100%;
      height: auto;
    }}

    figure {{
      margin: 26px 0;
    }}

    .cover {{
      max-height: 520px;
      object-fit: cover;
      border-bottom: 1px solid var(--line);
    }}

    .inline-image {{
      border-radius: 8px;
      border: 1px solid var(--line);
    }}

    .footer-note {{
      margin-top: 32px;
      padding-top: 18px;
      border-top: 1px solid var(--line);
      color: var(--muted);
      font-size: 14px;
    }}

    .footer-note a {{
      color: var(--accent);
      text-decoration: none;
    }}

    .footer-note a:hover {{
      text-decoration: underline;
    }}
  </style>
</head>
<body>
  <main>
    <article>
      {cover_html}
      <div class="article-inner">
        <h1>{safe_title}</h1>
        {meta_html}
        {body_html}
        <div class="footer-note">Текст сохранен в архиве автора.{f' <a href="{escape(dzen_link)}" target="_blank" rel="noopener">Читать на Яндекс Дзен →</a>' if dzen_link else ''}</div>
      </div>
    </article>
  </main>
  <script>
    if (window.Telegram && window.Telegram.WebApp) {{
      window.Telegram.WebApp.ready();
      window.Telegram.WebApp.expand();
    }}
  </script>
</body>
</html>"""


def _body_html(paragraphs: list[str], inline_images: list) -> str:
    if not paragraphs:
        return "<p>Текст статьи пока недоступен.</p>"

    image_slots = _image_slots(len(paragraphs), inline_images)
    parts: list[str] = []
    for index, paragraph in enumerate(paragraphs, start=1):
        parts.append(f"<p>{escape(paragraph)}</p>")
        image = image_slots.get(index)
        if image:
            parts.append(_image_html(image["local_path"], css_class="inline-image"))

    return "\n".join(parts)


def _image_slots(paragraph_count: int, images: list) -> dict[int, object]:
    if paragraph_count <= 0 or not images:
        return {}

    interval = max(3, paragraph_count // (len(images) + 1))
    slots: dict[int, object] = {}
    for index, image in enumerate(images, start=1):
        slot = min(paragraph_count, interval * index)
        slots[slot] = image

    return slots


def _image_html(local_path: Optional[str], css_class: str) -> str:
    media_url = _media_url(local_path or "")
    if not media_url:
        return ""

    return f"<figure><img class=\"{css_class}\" src=\"{escape(media_url)}\" alt=\"\"></figure>"


def _media_url(local_path: str) -> str:
    normalized_path = Path(local_path)
    parts = normalized_path.parts

    if "media" not in parts:
        return ""

    media_index = parts.index("media")
    media_parts = parts[media_index + 1 :]
    if not media_parts:
        return ""

    return "/media/" + "/".join(escape(part) for part in media_parts)


def _paragraphs(text: str) -> list[str]:
    cleaned_text = re.sub(r"\r\n?", "\n", text or "")
    paragraphs = [line.strip() for line in re.split(r"\n{2,}", cleaned_text)]
    return [paragraph for paragraph in paragraphs if paragraph]


def _data_root() -> Path:
    return get_db_path().parent.resolve()
