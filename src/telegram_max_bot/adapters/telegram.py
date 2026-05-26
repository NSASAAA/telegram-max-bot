from typing import Optional

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from telegram_max_bot.core.bot import Bot
from telegram_max_bot.core.models import IncomingMessage


class TelegramAdapter:
    """Telegram API integration."""

    def __init__(self, token: str, bot: Optional[Bot] = None) -> None:
        self._token = token
        self._bot = bot or Bot()

    def run(self) -> None:
        application = Application.builder().token(self._token).build()
        application.add_handler(CommandHandler("start", self._handle_start))
        application.add_handler(CommandHandler("help", self._handle_help))
        application.add_handler(CommandHandler("about", self._handle_about))
        application.add_handler(CommandHandler("articles", self._handle_articles))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_text))
        application.run_polling()

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
