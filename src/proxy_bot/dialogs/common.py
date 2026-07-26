from aiogram.types import Message


def not_a_command(message: Message) -> bool:
    """TextInput filter: reject slash-commands so they fall through to command handlers."""
    return not (message.text or "").startswith("/")
