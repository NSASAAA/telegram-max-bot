import asyncio
from pathlib import Path
from typing import Optional

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from telegram_max_bot.core.bot import Bot
from telegram_max_bot.core.models import IncomingMessage, OutgoingMessage
from telegram_max_bot.core.topics import TOPICS
from telegram_max_bot.rss_import import import_from_rss_url


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
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_text))
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
        response = self._bot.handle_start(message)
        await self._reply(update, response)

    async def _handle_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        del context
        response = self._bot.handle_help()
        await self._reply(update, response)

    async def _handle_about(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        del context
        response = self._bot.handle_about()
        await self._reply(update, response)

    async def _handle_articles(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        del context
        response = self._bot.handle_articles()
        await self._reply(update, response)

    async def _handle_top(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        del context
        response = self._bot.handle_top()
        await self._reply(update, response)

    async def _handle_random(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        del context
        response = self._bot.handle_random()
        await self._reply(update, response)

    async def _handle_topics(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        del context
        response = self._bot.handle_topics()
        await self._reply(update, response)

    async def _handle_topic(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        topic_code = context.args[0] if context.args else ""
        response = self._bot.handle_topic(topic_code)
        await self._reply(update, response)

    async def _handle_topic_shortcut(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        del context
        command = (update.effective_message.text or "").split()[0].split("@")[0]
        topic_code = command.removeprefix("/topic_")
        response = self._bot.handle_topic(topic_code)
        await self._reply(update, response)

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

    async def _handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        del context
        message = self._to_incoming_message(update)
        response = self._bot.handle_text(message)
        await self._reply(update, response)

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
