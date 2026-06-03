from html import escape, unescape
import re
from typing import Optional

from telegram_max_bot.core.models import (
    ImportStats,
    IncomingMessage,
    LinkButton,
    OutgoingMessage,
    PreviewCard,
)
from telegram_max_bot.core.topics import (
    get_topic_by_code,
    get_topic_code_from_command,
    get_topic_command,
)
from telegram_max_bot.db import (
    get_feed_posts,
    get_feed_posts_count,
    get_latest_posts,
    get_posts_count_by_topic,
    get_posts_by_topic,
    get_random_post,
    get_top_posts,
    get_topic_counts,
    get_welcome_post,
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
        welcome_post = get_welcome_post()

        if welcome_post is None:
            return OutgoingMessage(
                text=(
                    f"Привет, {name}!\n\n"
                    "Я бот-навигатор по статьям автора.\n\n"
                    "Команды:\n"
                    "/feed - лента всех статей\n"
                    "/articles - последние статьи\n"
                    "/top - самые читаемые статьи\n"
                    "/random - случайная статья\n"
                    "/topics - рубрики статей\n"
                    "/help - помощь\n"
                    "/about - о боте"
                )
            )

        return OutgoingMessage(
            text="",
            cards=(self._preview_card(welcome_post),),
        )

    def handle_help(self) -> OutgoingMessage:
        return OutgoingMessage(
            text=(
                "Доступные команды:\n"
                "/start - приветствие\n"
                "/feed - лента всех статей\n"
                "/articles - последние статьи из базы\n"
                "/top - самые читаемые статьи из базы\n"
                "/random - случайная статья из базы\n"
                "/topics - список рубрик\n"
                "/topic_rs_life - пример рубрики\n"
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

        return OutgoingMessage(
            text="Последние статьи:",
            cards=self._preview_cards(posts),
        )

    def handle_top(self) -> OutgoingMessage:
        posts = get_top_posts(limit=5)

        if not posts:
            return OutgoingMessage(text="В базе пока нет статей.")

        return OutgoingMessage(
            text="Самые читаемые статьи:",
            cards=self._preview_cards(posts),
        )

    def handle_feed(self, index: int = 0) -> OutgoingMessage:
        total_posts = get_feed_posts_count()
        if total_posts <= 0:
            return OutgoingMessage(text="В базе пока нет статей.")

        safe_index = max(0, min(index, total_posts - 1))
        posts = get_feed_posts(limit=1, offset=safe_index)
        if not posts:
            return OutgoingMessage(text="В базе пока нет статей.")

        return OutgoingMessage(
            text=f"Лента: {safe_index + 1}/{total_posts}",
            cards=self._preview_cards(posts),
        )

    def handle_random(self) -> OutgoingMessage:
        post = get_random_post()

        if post is None:
            return OutgoingMessage(text="В базе пока нет статей.")

        return OutgoingMessage(
            text="Случайная статья:",
            cards=(self._preview_card(post),),
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

    def handle_topic(self, topic_code: str, offset: int = 0, limit: int = 5) -> OutgoingMessage:
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

        total_posts = get_posts_count_by_topic(topic.code)
        if total_posts <= 0:
            return OutgoingMessage(
                text=(
                    f"В рубрике «{topic.title}» пока нет статей.\n\n"
                    "Посмотри другие рубрики командой /topics."
                )
            )

        page_size = max(1, limit)
        max_offset = max(0, total_posts - 1)
        safe_offset = max(0, min(offset, max_offset))
        page_offset = (safe_offset // page_size) * page_size

        posts = get_posts_by_topic(topic.code, limit=page_size, offset=page_offset)

        if not posts:
            return OutgoingMessage(
                text=(
                    f"В рубрике «{topic.title}» пока нет статей.\n\n"
                    "Посмотри другие рубрики командой /topics."
                )
            )

        shown_from = page_offset + 1
        shown_to = page_offset + len(posts)

        return OutgoingMessage(
            text=(
                f"{topic.title}\n"
                f"{topic.description}\n\n"
                f"Показано {shown_from}-{shown_to} из {total_posts}"
            ),
            cards=self._preview_cards(posts),
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
        if text == "/feed":
            return self.handle_feed(index=0)
        if text == "/topics":
            return self.handle_topics()
        if text == "/topic":
            return self.handle_topics()
        if text.startswith("/topic "):
            return self.handle_topic(text.removeprefix("/topic ").strip(), offset=0)
        topic_code = get_topic_code_from_command(text)
        if topic_code:
            return self.handle_topic(topic_code, offset=0)

        return OutgoingMessage(text=f"Я получил сообщение: {message.text}")

    def _preview_cards(
        self,
        posts,
    ) -> tuple[PreviewCard, ...]:
        return tuple(self._preview_card(post) for post in posts)

    def _preview_card(
        self,
        post,
    ) -> PreviewCard:
        title = escape(str(post["title"] or "Без названия"))
        summary = escape(clean_html(post["summary"], limit=180) or "Описание недоступно.")
        published_label = self._published_label(post)

        dzen_link = str(post["link"] or "").strip() if "link" in post.keys() else ""
        dzen_suffix = f'\n\n<a href="{dzen_link}">Читать на Яндекс Дзен →</a>' if dzen_link else ""
        body = f"{escape(published_label)}\n\n{summary}{dzen_suffix}"

        buttons = self._article_buttons([post], single_label="Читать")
        if dzen_link:
            buttons = buttons + (LinkButton(text="Яндекс Дзен →", url=dzen_link),)

        return PreviewCard(
            text=f"<b>{title}</b>\n\n{body}",
            buttons=buttons,
            parse_mode="HTML",
            photo_path=self._cover_image_path(post),
        )

    def _published_label(self, post) -> str:
        if "published_label" in post.keys():
            published_label = str(post["published_label"] or "").strip()
            if published_label:
                return published_label

        published = str(post["published"] or "").strip()
        if not published:
            return "не указана"

        return published

    def _cover_image_path(self, post) -> Optional[str]:
        cover_path = post["cover_image_path"] if "cover_image_path" in post.keys() else ""
        if not cover_path:
            return None
        return str(cover_path)

    def _article_buttons(
        self,
        posts,
        single_label: str = "",
    ) -> tuple[LinkButton, ...]:
        if not self._web_base_url:
            return ()

        use_web_app = self._web_base_url.startswith("https://")
        buttons: list[LinkButton] = []
        for index, post in enumerate(posts, start=1):
            label = single_label or f"Читать {index}"
            buttons.append(
                LinkButton(
                    text=label,
                    url=f"{self._web_base_url}/articles/{post['id']}",
                    open_in_webapp=use_web_app,
                )
            )

        return tuple(buttons)
