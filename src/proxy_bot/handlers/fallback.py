from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.types import Message

logger = logging.getLogger(__name__)

router = Router(name="fallback")


@router.message(F.text.startswith("/"))
async def unknown_command(message: Message, i18n) -> None:
    logger.info("Unknown command from %s: %r", message.from_user.id, message.text)
    await message.answer(i18n.get("unknown-command"))


@router.message()
async def unknown_message(message: Message, i18n) -> None:
    logger.info("Unhandled message from %s", message.from_user.id)
    await message.answer(i18n.get("unknown-message"))
