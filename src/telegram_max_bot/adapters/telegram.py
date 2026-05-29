import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from telegram_max_bot.core.bot import Bot
from telegram_max_bot.core.models import IncomingMessage, OutgoingMessage, PreviewCard
from telegram_max_bot.core.topics import TOPICS, get_topic_by_code
from telegram_max_bot.db import get_topic_counts
from telegram_max_bot.rss_import import import_from_rss_url


CB_HOME = "nav:home"
CB_ABOUT = "nav:about"
CB_TOPICS = "nav:topics"
CB_RANDOM = "nav:random"
CB_NOOP = "nav:noop"
CB_LATEST_PREFIX = "nav:latest:"
CB_TOP_PREFIX = "nav:top:"
CB_TOPIC_PREFIX = "nav:topic:"


@dataclass(frozen=True)
class NavigationScreen:
    text: str
    parse_mode: Optional[str] = None
    photo_path: Optional[str] = None
    reply_markup: Optional[InlineKeyboardMarkup] = None


class TelegramAdapter:
    """Telegram API integration."""

    def __init__(
        self,
        token: str,
        rss_url: Optional[str] = None,
        check_interval_seconds: int = 0,
        web_base_url: Optional[str] = None,
        bot: Optional[Bot] = None,
    ) -> None:
        self._token = token
        self._rss_url = rss_url
        self._check_interval_seconds = max(0, check_interval_seconds)
        self._bot = bot or Bot(web_base_url=web_base_url)
        self._rss_import_task: Optional[asyncio.Task] = None
        self._application: Optional[Application] = None

    def run(self) -> None:
        application = (
            Application.builder()
            .token(self._token)
            .post_init(self._post_init)
            .post_shutdown(self._post_shutdown)
            .build()
        )
        application.add_handler(CommandHandler("start", self._handle_start))
        application.add_handler(CommandHandler("help", self._handle_help))
        application.add_handler(CommandHandler("about", self._handle_about))
        application.add_handler(CommandHandler("articles", self._handle_articles))
        application.add_handler(CommandHandler("top", self._handle_top))
        application.add_handler(CommandHandler("random", self._handle_random))
        application.add_handler(CommandHandler("topics", self._handle_topics))
        application.add_handler(CommandHandler("topic", self._handle_topic))
        application.add_handler(
            CommandHandler(
                [f"topic_{topic.code}" for topic in TOPICS],
                self._handle_topic_shortcut,
            )
        )
        application.add_handler(CommandHandler("check", self._handle_check))
        application.add_handler(CallbackQueryHandler(self._handle_navigation))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_text))
        self._application = application
        application.run_polling()

    async def _post_init(self, application: Application) -> None:
        del application
        if not self._rss_url or self._check_interval_seconds <= 0:
            return
        self._rss_import_task = asyncio.create_task(self._rss_import_loop())

    async def _post_shutdown(self, application: Application) -> None:
        del application
        if not self._rss_import_task:
            return
        self._rss_import_task.cancel()
        try:
            await self._rss_import_task
        except asyncio.CancelledError:
            pass

    async def _rss_import_loop(self) -> None:
        while True:
            await asyncio.sleep(self._check_interval_seconds)
            try:
                stats = await asyncio.to_thread(import_from_rss_url, self._rss_url)
                print(
                    "Auto RSS import: "
                    f"received={stats.total} created={stats.created} "
                    f"updated={stats.updated} unchanged={stats.unchanged}"
                )
            except Exception as error:  # pragma: no cover - defensive log path
                print(f"Auto RSS import failed: {error}")

    async def _handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        del context
        message = self._to_incoming_message(update)
        screen = self._build_start_screen(message)
        await self._send_screen_from_update(update, screen)

    async def _handle_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        del context
        response = self._bot.handle_help()
        screen = NavigationScreen(
            text=response.text,
            parse_mode=response.parse_mode,
            reply_markup=self._main_menu_keyboard(),
        )
        await self._send_screen_from_update(update, screen)

    async def _handle_about(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        del context
        screen = self._build_about_screen()
        await self._send_screen_from_update(update, screen)

    async def _handle_articles(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        del context
        screen = self._build_articles_screen(index=0)
        await self._send_screen_from_update(update, screen)

    async def _handle_top(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        del context
        screen = self._build_top_screen(index=0)
        await self._send_screen_from_update(update, screen)

    async def _handle_random(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        del context
        screen = self._build_random_screen()
        await self._send_screen_from_update(update, screen)

    async def _handle_topics(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        del context
        screen = self._build_topics_screen()
        await self._send_screen_from_update(update, screen)

    async def _handle_topic(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        topic_code = context.args[0] if context.args else ""
        screen = self._build_topic_screen(topic_code=topic_code, index=0)
        await self._send_screen_from_update(update, screen)

    async def _handle_topic_shortcut(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        del context
        command = (update.effective_message.text or "").split()[0].split("@")[0]
        topic_code = command.removeprefix("/topic_")
        screen = self._build_topic_screen(topic_code=topic_code, index=0)
        await self._send_screen_from_update(update, screen)

    async def _handle_check(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        del context

        if not self._rss_url:
            response = self._bot.handle_check_result(
                stats=None,
                error_message="SOURCE_RSS_URL не задан в .env",
            )
            await self._reply(update, response)
            return

        try:
            stats = await asyncio.to_thread(import_from_rss_url, self._rss_url)
            response = self._bot.handle_check_result(stats=stats)
        except Exception as error:
            response = self._bot.handle_check_result(stats=None, error_message=str(error))

        await self._reply(update, response)

    async def _handle_navigation(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        del context
        query = update.callback_query
        if query is None:
            return

        data = query.data or ""
        screen = self._build_navigation_screen(data)
        await query.answer()

        if screen is None:
            return

        await self._replace_callback_message(update, screen)

    async def _handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        del context
        message = self._to_incoming_message(update)
        response = self._bot.handle_text(message)
        await self._reply(update, response)

    def _build_navigation_screen(self, data: str) -> Optional[NavigationScreen]:
        if data == CB_NOOP:
            return None
        if data == CB_HOME:
            return self._build_home_screen()
        if data == CB_ABOUT:
            return self._build_about_screen()
        if data == CB_TOPICS:
            return self._build_topics_screen()
        if data == CB_RANDOM:
            return self._build_random_screen()
        if data.startswith(CB_LATEST_PREFIX):
            return self._build_articles_screen(index=self._parse_index(data, CB_LATEST_PREFIX))
        if data.startswith(CB_TOP_PREFIX):
            return self._build_top_screen(index=self._parse_index(data, CB_TOP_PREFIX))
        if data.startswith(CB_TOPIC_PREFIX):
            parts = data.split(":")
            if len(parts) != 4:
                return self._build_topics_screen()
            topic_code = parts[2]
            index = self._safe_int(parts[3], default=0)
            return self._build_topic_screen(topic_code=topic_code, index=index)
        return self._build_home_screen()

    def _build_home_screen(self) -> NavigationScreen:
        return self._build_start_screen(
            IncomingMessage(text="/start", user_id="", username=None)
        )

    def _build_start_screen(self, message: IncomingMessage) -> NavigationScreen:
        response = self._bot.handle_start(message)
        if not response.cards:
            return NavigationScreen(
                text=response.text,
                parse_mode=response.parse_mode,
                reply_markup=self._main_menu_keyboard(),
            )
        return self._screen_from_card(response.cards[0], reply_markup=self._main_menu_keyboard())

    def _build_about_screen(self) -> NavigationScreen:
        response = self._bot.handle_about()
        return NavigationScreen(
            text=response.text,
            parse_mode=response.parse_mode,
            reply_markup=self._main_menu_keyboard(),
        )

    def _build_articles_screen(self, index: int) -> NavigationScreen:
        response = self._bot.handle_articles()
        return self._screen_from_card_list(
            response=response,
            index=index,
            prev_data=lambda i: f"{CB_LATEST_PREFIX}{i}",
            next_data=lambda i: f"{CB_LATEST_PREFIX}{i}",
        )

    def _build_top_screen(self, index: int) -> NavigationScreen:
        response = self._bot.handle_top()
        return self._screen_from_card_list(
            response=response,
            index=index,
            prev_data=lambda i: f"{CB_TOP_PREFIX}{i}",
            next_data=lambda i: f"{CB_TOP_PREFIX}{i}",
        )

    def _build_random_screen(self) -> NavigationScreen:
        response = self._bot.handle_random()
        if not response.cards:
            return NavigationScreen(
                text=response.text,
                parse_mode=response.parse_mode,
                reply_markup=self._main_menu_keyboard(),
            )
        return self._screen_from_card(
            response.cards[0],
            reply_markup=self._random_keyboard(),
        )

    def _build_topics_screen(self) -> NavigationScreen:
        topic_counts = [(topic, count) for topic, count in get_topic_counts() if count > 0]
        if not topic_counts:
            return NavigationScreen(
                text="Рубрики пока не собраны: в базе нет размеченных статей.",
                reply_markup=self._main_menu_keyboard(),
            )

        rows: list[list[InlineKeyboardButton]] = []
        for topic, count in topic_counts:
            rows.append(
                [
                    InlineKeyboardButton(
                        text=f"{topic.title} ({count})",
                        callback_data=f"{CB_TOPIC_PREFIX}{topic.code}:0",
                    )
                ]
            )
        rows.append([InlineKeyboardButton("🏠 Меню", callback_data=CB_HOME)])
        return NavigationScreen(
            text="Выбери рубрику:",
            reply_markup=InlineKeyboardMarkup(rows),
        )

    def _build_topic_screen(self, topic_code: str, index: int) -> NavigationScreen:
        topic = get_topic_by_code(topic_code or "")
        if topic is None:
            return NavigationScreen(
                text="Не знаю такую рубрику. Нажми «Рубрики», чтобы выбрать из списка.",
                reply_markup=self._topics_only_keyboard(),
            )

        response = self._bot.handle_topic(topic_code)
        if not response.cards:
            return NavigationScreen(
                text=response.text,
                parse_mode=response.parse_mode,
                reply_markup=self._topics_only_keyboard(),
            )

        return self._screen_from_card_list(
            response=response,
            index=index,
            prev_data=lambda i: f"{CB_TOPIC_PREFIX}{topic_code}:{i}",
            next_data=lambda i: f"{CB_TOPIC_PREFIX}{topic_code}:{i}",
        )

    def _screen_from_card_list(
        self,
        response: OutgoingMessage,
        index: int,
        prev_data,
        next_data,
    ) -> NavigationScreen:
        cards = response.cards
        if not cards:
            return NavigationScreen(
                text=response.text,
                parse_mode=response.parse_mode,
                reply_markup=self._main_menu_keyboard(),
            )

        max_index = len(cards) - 1
        current_index = max(0, min(index, max_index))
        card = cards[current_index]

        return self._screen_from_card(
            card=card,
            reply_markup=self._article_keyboard(
                index=current_index,
                total=len(cards),
                prev_data=prev_data(max(0, current_index - 1)),
                next_data=next_data(min(max_index, current_index + 1)),
            ),
        )

    def _screen_from_card(
        self,
        card: PreviewCard,
        reply_markup: InlineKeyboardMarkup,
    ) -> NavigationScreen:
        return NavigationScreen(
            text=card.text,
            parse_mode=card.parse_mode,
            photo_path=card.photo_path,
            reply_markup=reply_markup,
        )

    def _main_menu_keyboard(self) -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("📚 Последние", callback_data=f"{CB_LATEST_PREFIX}0"),
                    InlineKeyboardButton("🔥 Топ", callback_data=f"{CB_TOP_PREFIX}0"),
                ],
                [
                    InlineKeyboardButton("🎲 Случайная", callback_data=CB_RANDOM),
                    InlineKeyboardButton("🗂 Рубрики", callback_data=CB_TOPICS),
                ],
                [InlineKeyboardButton("ℹ️ О боте", callback_data=CB_ABOUT)],
            ]
        )

    def _article_keyboard(
        self,
        index: int,
        total: int,
        prev_data: str,
        next_data: str,
    ) -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("⬅️", callback_data=prev_data),
                    InlineKeyboardButton(f"{index + 1}/{total}", callback_data=CB_NOOP),
                    InlineKeyboardButton("➡️", callback_data=next_data),
                ],
                [
                    InlineKeyboardButton("🏠 Меню", callback_data=CB_HOME),
                    InlineKeyboardButton("🗂 Рубрики", callback_data=CB_TOPICS),
                ],
                [
                    InlineKeyboardButton("📚 Последние", callback_data=f"{CB_LATEST_PREFIX}0"),
                    InlineKeyboardButton("🔥 Топ", callback_data=f"{CB_TOP_PREFIX}0"),
                    InlineKeyboardButton("🎲 Случайная", callback_data=CB_RANDOM),
                ],
            ]
        )

    def _random_keyboard(self) -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("🔄 Другая случайная", callback_data=CB_RANDOM)],
                [
                    InlineKeyboardButton("📚 Последние", callback_data=f"{CB_LATEST_PREFIX}0"),
                    InlineKeyboardButton("🔥 Топ", callback_data=f"{CB_TOP_PREFIX}0"),
                ],
                [
                    InlineKeyboardButton("🗂 Рубрики", callback_data=CB_TOPICS),
                    InlineKeyboardButton("🏠 Меню", callback_data=CB_HOME),
                ],
            ]
        )

    def _topics_only_keyboard(self) -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("🗂 Рубрики", callback_data=CB_TOPICS)],
                [InlineKeyboardButton("🏠 Меню", callback_data=CB_HOME)],
            ]
        )

    def _parse_index(self, data: str, prefix: str) -> int:
        return self._safe_int(data.removeprefix(prefix), default=0)

    def _safe_int(self, value: str, default: int) -> int:
        try:
            return int(value)
        except ValueError:
            return default

    async def _send_screen_from_update(self, update: Update, screen: NavigationScreen) -> None:
        message = update.effective_message
        if message is None:
            return
        await self._send_screen(chat_id=message.chat_id, screen=screen)

    async def _replace_callback_message(self, update: Update, screen: NavigationScreen) -> None:
        query = update.callback_query
        message = query.message if query is not None else None
        if message is None:
            return

        await self._send_screen(chat_id=message.chat_id, screen=screen)
        try:
            await message.delete()
        except Exception:
            pass

    async def _send_screen(self, chat_id: int, screen: NavigationScreen) -> None:
        if self._application is None:
            raise RuntimeError("Telegram application is not initialized")

        bot_api = self._application.bot
        photo_path = self._resolve_photo_path(screen.photo_path)
        if photo_path is not None:
            with photo_path.open("rb") as photo_file:
                await bot_api.send_photo(
                    chat_id=chat_id,
                    photo=photo_file,
                    caption=screen.text,
                    parse_mode=screen.parse_mode,
                    reply_markup=screen.reply_markup,
                )
            return

        await bot_api.send_message(
            chat_id=chat_id,
            text=screen.text,
            parse_mode=screen.parse_mode,
            reply_markup=screen.reply_markup,
            disable_web_page_preview=True,
        )

    async def _reply(self, update: Update, response: OutgoingMessage) -> None:
        if response.cards:
            if response.text:
                await self._reply_message(
                    update,
                    text=response.text,
                    parse_mode=response.parse_mode,
                    buttons=response.buttons,
                    photo_path=response.photo_path,
                )
            for card in response.cards:
                await self._reply_message(
                    update,
                    text=card.text,
                    parse_mode=card.parse_mode,
                    buttons=card.buttons,
                    photo_path=card.photo_path,
                )
            return

        await self._reply_message(
            update,
            text=response.text,
            parse_mode=response.parse_mode,
            buttons=response.buttons,
            photo_path=response.photo_path,
        )

    async def _reply_message(
        self,
        update: Update,
        text: str,
        parse_mode: Optional[str],
        buttons,
        photo_path: Optional[str],
    ) -> None:
        reply_markup = None
        if buttons:
            reply_markup = InlineKeyboardMarkup(
                [[InlineKeyboardButton(button.text, url=button.url)] for button in buttons]
            )

        resolved_photo_path = self._resolve_photo_path(photo_path)
        if resolved_photo_path is not None:
            await update.effective_message.reply_photo(
                photo=resolved_photo_path,
                caption=text,
                parse_mode=parse_mode,
                reply_markup=reply_markup,
            )
            return

        await update.effective_message.reply_text(
            text,
            parse_mode=parse_mode,
            reply_markup=reply_markup,
            disable_web_page_preview=True,
        )

    def _resolve_photo_path(self, photo_path: Optional[str]) -> Optional[Path]:
        if not photo_path:
            return None

        candidate = Path(photo_path)
        if not candidate.is_absolute():
            candidate = Path.cwd() / candidate

        if candidate.is_file():
            return candidate

        return None

    def _to_incoming_message(self, update: Update) -> IncomingMessage:
        user = update.effective_user
        message = update.effective_message

        return IncomingMessage(
            text=message.text or "",
            user_id=str(user.id) if user else "",
            username=user.first_name if user else None,
        )
