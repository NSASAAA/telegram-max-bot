from telegram_max_bot.core.models import IncomingMessage, OutgoingMessage


class Bot:
    """Shared bot business logic independent from messenger APIs."""

    def handle_start(self, message: IncomingMessage) -> OutgoingMessage:
        name = message.username or "пользователь"
        return OutgoingMessage(text=f"Привет, {name}! Привет! Я обновился через автодеплой с GitHub Actions.")

    def handle_help(self) -> OutgoingMessage:
        return OutgoingMessage(
            text=(
                "Доступные команды:\n"
                "/start - приветствие\n"
                "/help - список команд\n"
                "/about - информация о боте\n"
                "Любой текст - повтор сообщения"
            )
        )

    def handle_about(self) -> OutgoingMessage:
        return OutgoingMessage(
            text="Это тестовый Telegram-бот для проверки связки VSCode, Codex, GitHub Actions, VPS и Docker.!!!!!!!!!!!!!!!!!!!!"
        )

    def handle_text(self, message: IncomingMessage) -> OutgoingMessage:
        return OutgoingMessage(text=f"Я получил сообщение: {message.text}")
