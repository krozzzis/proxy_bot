from __future__ import annotations

import logging

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import BotCommand, BotCommandScopeChat, BotCommandScopeDefault

from proxy_bot.storage import Storage

logger = logging.getLogger(__name__)

USER_COMMANDS = [
    BotCommand(command="start", description="Начать работу с ботом"),
    BotCommand(command="help", description="Список доступных команд"),
    BotCommand(command="link", description="Получить свои подписки"),
    BotCommand(command="code", description="Ввести ещё один код"),
]

ADMIN_COMMANDS = [
    *USER_COMMANDS,
    BotCommand(command="admin", description="Открыть админ-панель"),
]


async def set_admin_commands(bot: Bot, user_id: int) -> None:
    try:
        await bot.set_my_commands(ADMIN_COMMANDS, scope=BotCommandScopeChat(chat_id=user_id))
    except TelegramBadRequest:
        # The user has never opened a chat with the bot yet; the scope
        # will be (re)applied the next time commands are synced at startup.
        logger.info("Could not set admin command scope for %s yet", user_id)


async def setup_bot_commands(bot: Bot, storage: Storage) -> None:
    await bot.set_my_commands(USER_COMMANDS, scope=BotCommandScopeDefault())
    for admin in await storage.admins.all():
        await set_admin_commands(bot, admin.user_id)
