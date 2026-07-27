from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.types import Message

from proxy_bot.utils.audit import actor

logger = logging.getLogger(__name__)

router = Router(name="fallback")


@router.message(F.text.startswith("/"))
async def unknown_command(message: Message, i18n) -> None:
    logger.info("Unknown command from %s: %r", actor(message.from_user), message.text)
    await message.answer(i18n.get("unknown-command"))


@router.message()
async def unknown_message(message: Message, i18n) -> None:
    logger.info("Unhandled message from %s", actor(message.from_user))
    await message.answer(i18n.get("unknown-message"))
