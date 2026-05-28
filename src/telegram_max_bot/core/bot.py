from html import unescape
import re
from typing import Optional

from telegram_max_bot.core.models import ImportStats, IncomingMessage, OutgoingMessage
from telegram_max_bot.db import get_latest_posts, get_random_post, get_top_posts


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
                "/top - самые читаемые статьи\n"
                "/random - случайная статья\n"
                "/check - импортировать RSS\n"
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
                "/top - самые читаемые статьи из базы\n"
                "/random - случайная статья из базы\n"
                "/check - импортировать RSS сейчас\n"
                "/help - список команд\n"
                "/about - информация о боте"
            )
        )

    def handle_about(self) -> OutgoingMessage:
        return OutgoingMessage(
            text=(
                "Это тестовый Telegram-бот для проверки связки VSCode, Codex, GitHub Actions, "
                "VPS и Docker.!!!!!!!!!!!!!!!!!!!!???---"
            )
        )

    def handle_articles(self) -> OutgoingMessage:
        posts = get_latest_posts(limit=5)

        if not posts:
            return OutgoingMessage(
                text=(
                    "В базе пока нет статей.\n\n"
                    "Сначала запусти импорт RSS.\n"
                    "Проверь SOURCE_RSS_URL в .env и выполни:\n"
                    "PYTHONPATH=src python -m telegram_max_bot.rss_import"
                )
            )

        lines = ["Последние статьи:\n"]

        for index, post in enumerate(posts, start=1):
            lines.append(f"{index}. {self._format_post(post)}")

        return OutgoingMessage(text="\n".join(lines))

    def handle_top(self) -> OutgoingMessage:
        posts = get_top_posts(limit=5)

        if not posts:
            return OutgoingMessage(text="В базе пока нет статей.")

        lines = ["Самые читаемые статьи:\n"]
        for index, post in enumerate(posts, start=1):
            views_count = post["views_count"]
            views_text = f"Просмотры: {views_count}\n" if views_count is not None else ""
            lines.append(f"{index}. {views_text}{self._format_post(post)}")

        return OutgoingMessage(text="\n".join(lines))

    def handle_random(self) -> OutgoingMessage:
        post = get_random_post()

        if post is None:
            return OutgoingMessage(text="В базе пока нет статей.")

        return OutgoingMessage(text="Случайная статья:\n\n" + self._format_post(post))

    def handle_check_result(
        self,
        stats: Optional[ImportStats],
        error_message: Optional[str] = None,
    ) -> OutgoingMessage:
        if error_message:
            return OutgoingMessage(text=f"Ошибка импорта RSS: {error_message}")

        if stats is None:
            return OutgoingMessage(text="Импорт не выполнен: нет данных.")

        return OutgoingMessage(
            text=(
                "Импорт RSS завершен.\n\n"
                f"Получено записей: {stats.total}\n"
                f"Новых: {stats.created}\n"
                f"Обновлено: {stats.updated}\n"
                f"Без изменений: {stats.unchanged}"
            )
        )

    def handle_text(self, message: IncomingMessage) -> OutgoingMessage:
        text = (message.text or "").strip()

        if text == "/articles":
            return self.handle_articles()
        if text == "/top":
            return self.handle_top()
        if text == "/random":
            return self.handle_random()

        return OutgoingMessage(text=f"Я получил сообщение: {message.text}")

    def _format_post(self, post) -> str:
        summary = clean_html(post["summary"], limit=180)
        return (
            f"{post['title']}\n"
            f"{summary}\n"
            f"{post['link']}\n"
        )
