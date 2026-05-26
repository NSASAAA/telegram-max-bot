from html import unescape
import re

from telegram_max_bot.core.models import IncomingMessage, OutgoingMessage
from telegram_max_bot.db import get_latest_posts


def clean_html(raw_html: str, limit: int = 250) -> str:
    text = re.sub(r"<[^>]+>", " ", raw_html or "")
    text = unescape(text)
    text = re.sub(r"\s+", " ", text).strip()

    if len(text) > limit:
        return text[:limit].rstrip() + "..."

    return text


class Bot:
    """Shared bot business logic independent from messenger APIs."""

    def handle_start(self, message: IncomingMessage) -> OutgoingMessage:
        name = message.username or "пользователь"
        return OutgoingMessage(
            text=(
                f"Привет, {name}!\n\n"
                "Я бот-навигатор по статьям автора.\n\n"
                "Команды:\n"
                "/articles - последние статьи\n"
                "/help - помощь\n"
                "/about - о боте"
            )
        )

    def handle_help(self) -> OutgoingMessage:
        return OutgoingMessage(
            text=(
                "Доступные команды:\n"
                "/start - приветствие\n"
                "/articles - последние статьи из базы\n"
                "/help - список команд\n"
                "/about - информация о боте"
            )
        )

    def handle_about(self) -> OutgoingMessage:
        return OutgoingMessage(
            text=(
                "Это тестовая версия бота для работы со статьями из RSS.\n"
                "Сейчас бот уже умеет читать статьи из базы данных и показывать последние публикации."
            )
        )

    def handle_articles(self) -> OutgoingMessage:
        posts = get_latest_posts(limit=5)

        if not posts:
            return OutgoingMessage(
                text=(
                    "В базе пока нет статей.\n\n"
                    "Сначала запусти импорт:\n"
                    "SOURCE_RSS_URL=https://habr.com/ru/rss/articles/ "
                    "PYTHONPATH=src python -m telegram_max_bot.rss_import"
                )
            )

        lines = ["Последние статьи:\n"]

        for index, post in enumerate(posts, start=1):
            summary = clean_html(post["summary"], limit=180)

            lines.append(
                f"{index}. {post['title']}\n"
                f"{summary}\n"
                f"{post['link']}\n"
            )

        return OutgoingMessage(text="\n".join(lines))

    def handle_text(self, message: IncomingMessage) -> OutgoingMessage:
        text = (message.text or "").strip()

        if text == "/articles":
            return self.handle_articles()

        return OutgoingMessage(text=f"Я получил сообщение: {message.text}")
