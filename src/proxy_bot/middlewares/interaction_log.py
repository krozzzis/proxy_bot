from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from proxy_bot.utils.audit import actor

logger = logging.getLogger("proxy_bot.interaction")

_MAX_LOGGED_TEXT = 200


def _truncate(text: str) -> str:
    if len(text) <= _MAX_LOGGED_TEXT:
        return text
    return f"{text[:_MAX_LOGGED_TEXT]}…"


class InteractionLoggingMiddleware(BaseMiddleware):
    """Outer middleware logging every incoming command, free-text message and
    inline-button click, regardless of which handler (if any) ends up
    processing it - business-logic log lines only cover specific outcomes
    (code activated, user banned, ...), not every interaction on their own.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if isinstance(event, Message) and event.from_user is not None:
            text = event.text or event.caption
            if text:
                kind = "command" if text.startswith("/") else "message"
                logger.info("%s sent %s: %r", actor(event.from_user), kind, _truncate(text))
        elif isinstance(event, CallbackQuery) and event.from_user is not None:
            logger.info("%s clicked button: %r", actor(event.from_user), event.data)
        return await handler(event, data)
