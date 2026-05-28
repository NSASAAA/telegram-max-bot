from html import unescape
import re
from typing import Optional

from telegram_max_bot.core.models import (
    ImportStats,
    IncomingMessage,
    LinkButton,
    OutgoingMessage,
)
from telegram_max_bot.core.topics import (
    get_topic_by_code,
    get_topic_code_from_command,
    get_topic_command,
)
from telegram_max_bot.db import (
    get_latest_posts,
    get_posts_by_topic,
    get_random_post,
    get_top_posts,
    get_topic_counts,
)


def clean_html(raw_html: str, limit: int = 250) -> str:
    text = re.sub(r"<[^>]+>", " ", raw_html or "")
    text = unescape(text)
    text = re.sub(r"\s+", " ", text).strip()

    if len(text) > limit:
        return text[:limit].rstrip() + "..."

    return text


class Bot:
    """Shared bot business logic independent from messenger APIs."""

    def __init__(self, web_base_url: Optional[str] = None) -> None:
        self._web_base_url = (web_base_url or "").rstrip("/")

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
                "/topics - рубрики статей\n"
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
                "/topics - список рубрик\n"
                "/topic_rs - пример рубрики\n"
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

        return OutgoingMessage(
            text="\n".join(lines),
            buttons=self._article_buttons(posts),
        )

    def handle_top(self) -> OutgoingMessage:
        posts = get_top_posts(limit=5)

        if not posts:
            return OutgoingMessage(text="В базе пока нет статей.")

        lines = ["Самые читаемые статьи:\n"]
        for index, post in enumerate(posts, start=1):
            views_count = post["views_count"]
            views_text = f"Просмотры: {views_count}\n" if views_count is not None else ""
            lines.append(f"{index}. {views_text}{self._format_post(post)}")

        return OutgoingMessage(
            text="\n".join(lines),
            buttons=self._article_buttons(posts),
        )

    def handle_random(self) -> OutgoingMessage:
        post = get_random_post()

        if post is None:
            return OutgoingMessage(text="В базе пока нет статей.")

        return OutgoingMessage(
            text="Случайная статья:\n\n" + self._format_post(post),
            buttons=self._article_buttons([post], single_label="Читать"),
        )

    def handle_topics(self) -> OutgoingMessage:
        topic_counts = get_topic_counts()
        visible_topics = [(topic, count) for topic, count in topic_counts if count > 0]

        if not visible_topics:
            return OutgoingMessage(text="Рубрики пока не собраны: в базе нет размеченных статей.")

        lines = ["Рубрики статей:\n"]
        for topic, count in visible_topics:
            lines.append(f"{get_topic_command(topic.code)} - {topic.title} ({count})")

        return OutgoingMessage(text="\n".join(lines))

    def handle_topic(self, topic_code: str) -> OutgoingMessage:
        if not topic_code:
            return self.handle_topics()

        topic = get_topic_by_code(topic_code or "")

        if topic is None:
            return OutgoingMessage(
                text=(
                    "Не знаю такую рубрику.\n\n"
                    "Посмотри список доступных рубрик командой /topics."
                )
            )

        posts = get_posts_by_topic(topic.code, limit=5)

        if not posts:
            return OutgoingMessage(
                text=(
                    f"В рубрике «{topic.title}» пока нет статей.\n\n"
                    "Посмотри другие рубрики командой /topics."
                )
            )

        lines = [f"{topic.title}\n{topic.description}\n"]
        for index, post in enumerate(posts, start=1):
            lines.append(f"{index}. {self._format_post(post)}")

        return OutgoingMessage(
            text="\n".join(lines),
            buttons=self._article_buttons(posts),
        )

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
        if text == "/topics":
            return self.handle_topics()
        if text == "/topic":
            return self.handle_topics()
        if text.startswith("/topic "):
            return self.handle_topic(text.removeprefix("/topic ").strip())
        topic_code = get_topic_code_from_command(text)
        if topic_code:
            return self.handle_topic(topic_code)

        return OutgoingMessage(text=f"Я получил сообщение: {message.text}")

    def _format_post(self, post) -> str:
        summary = clean_html(post["summary"], limit=180)
        return (
            f"{post['title']}\n"
            f"{summary}\n"
        )

    def _article_buttons(
        self,
        posts,
        single_label: str = "",
    ) -> tuple[LinkButton, ...]:
        if not self._web_base_url:
            return ()

        buttons: list[LinkButton] = []
        for index, post in enumerate(posts, start=1):
            label = single_label or f"Читать {index}"
            buttons.append(
                LinkButton(
                    text=label,
                    url=f"{self._web_base_url}/articles/{post['id']}",
                )
            )

        return tuple(buttons)
