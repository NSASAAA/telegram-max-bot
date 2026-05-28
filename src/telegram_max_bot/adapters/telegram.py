import asyncio
from typing import Optional

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from telegram_max_bot.core.bot import Bot
from telegram_max_bot.core.models import IncomingMessage
from telegram_max_bot.rss_import import import_from_rss_url


class TelegramAdapter:
    """Telegram API integration."""

    def __init__(
        self,
        token: str,
        rss_url: Optional[str] = None,
        check_interval_seconds: int = 0,
        bot: Optional[Bot] = None,
    ) -> None:
        self._token = token
        self._rss_url = rss_url
        self._check_interval_seconds = max(0, check_interval_seconds)
        self._bot = bot or Bot()
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
        await update.effective_message.reply_text(response.text)

    async def _handle_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        del context
        response = self._bot.handle_help()
        await update.effective_message.reply_text(response.text)

    async def _handle_about(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        del context
        response = self._bot.handle_about()
        await update.effective_message.reply_text(response.text)

    async def _handle_articles(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        del context
        response = self._bot.handle_articles()
        await update.effective_message.reply_text(response.text)

    async def _handle_top(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        del context
        response = self._bot.handle_top()
        await update.effective_message.reply_text(response.text)

    async def _handle_random(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        del context
        response = self._bot.handle_random()
        await update.effective_message.reply_text(response.text)

    async def _handle_check(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        del context

        if not self._rss_url:
            response = self._bot.handle_check_result(
                stats=None,
                error_message="SOURCE_RSS_URL не задан в .env",
            )
            await update.effective_message.reply_text(response.text)
            return

        try:
            stats = await asyncio.to_thread(import_from_rss_url, self._rss_url)
            response = self._bot.handle_check_result(stats=stats)
        except Exception as error:
            response = self._bot.handle_check_result(stats=None, error_message=str(error))

        await update.effective_message.reply_text(response.text)

    async def _handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        del context
        message = self._to_incoming_message(update)
        response = self._bot.handle_text(message)
        await update.effective_message.reply_text(response.text)

    def _to_incoming_message(self, update: Update) -> IncomingMessage:
        user = update.effective_user
        message = update.effective_message

        return IncomingMessage(
            text=message.text or "",
            user_id=str(user.id) if user else "",
            username=user.first_name if user else None,
        )
