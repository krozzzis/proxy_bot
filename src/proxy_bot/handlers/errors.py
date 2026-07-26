from __future__ import annotations

import contextlib
import logging

from aiogram.types import ErrorEvent

logger = logging.getLogger(__name__)


async def on_unknown_dialog_event(event: ErrorEvent, i18n) -> None:
    """Handles stale dialog callbacks/state, e.g. after a bot restart.

    Registered directly on the Dispatcher's `errors` observer (not a nested
    Router) so it runs inside aiogram-dialog's IntentErrorMiddleware, which
    repairs the corrupted dialog stack before this handler notifies the user.
    """
    logger.warning("Stale dialog event: %s", event.exception)

    update = event.update
    bot = None
    chat_id = None
    if update.callback_query is not None:
        bot = update.callback_query.bot
        with contextlib.suppress(Exception):
            await update.callback_query.answer()
        if update.callback_query.message is not None:
            chat_id = update.callback_query.message.chat.id
    elif update.message is not None:
        bot = update.message.bot
        chat_id = update.message.chat.id

    if bot is not None and chat_id is not None:
        with contextlib.suppress(Exception):
            await bot.send_message(chat_id, i18n.get("dialog-unknown-intent"))
