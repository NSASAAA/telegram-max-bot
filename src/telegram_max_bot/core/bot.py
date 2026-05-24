from telegram_max_bot.core.models import IncomingMessage, OutgoingMessage


class Bot:
    """Shared bot business logic independent from messenger APIs."""

    def handle_start(self, message: IncomingMessage) -> OutgoingMessage:
        name = message.username or "пользователь"
        return OutgoingMessage(text=f"Привет, {name}! Я универсальный бот Telegram/MAX.")

    def handle_help(self) -> OutgoingMessage:
        return OutgoingMessage(
            text=(
                "Доступные команды:\n"
                "/start - приветствие\n"
                "/help - список команд\n"
                "Любой текст - повтор сообщения"
            )
        )

    def handle_text(self, message: IncomingMessage) -> OutgoingMessage:
        return OutgoingMessage(text=f"Я получил сообщение: {message.text}")
