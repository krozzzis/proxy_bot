from __future__ import annotations

import asyncio
import contextlib
import logging

from aiogram import Bot, Dispatcher
from aiogram.types import ErrorEvent, Message, Update
from aiogram_dialog.api.entities import Stack
from aiogram_dialog.context.storage import StorageProxy

logger = logging.getLogger(__name__)


async def _reopen_main_menu(dispatcher: Dispatcher, bot: Bot, fake_update: Update) -> None:
    try:
        await dispatcher.feed_update(bot=bot, update=fake_update)
    except Exception:
        logger.exception("Failed to reopen main menu after a stale dialog event")


async def on_unknown_dialog_event(
    event: ErrorEvent,
    bot: Bot,
    dispatcher: Dispatcher,
    aiogd_stack: Stack | None = None,
    aiogd_storage_proxy: StorageProxy | None = None,
) -> None:
    """Handles stale dialog callbacks/state, e.g. after a bot restart, a
    RESET_STACK elsewhere leaving an older message's buttons pointing at a
    now-invalid intent, or a code change that renamed/removed a dialog
    state a user was sitting in.

    Registered directly on the Dispatcher's `errors` observer (not a nested
    Router) so it runs inside aiogram-dialog's IntentErrorMiddleware, which
    injects `aiogd_stack`/`aiogd_storage_proxy` into this handler's data -
    and, for UnknownIntent/OutdatedIntent, repairs the corrupted stack
    itself. It does NOT do that for UnknownState (see
    IntentErrorMiddleware.__call__: `context = None` is set but the broken
    stack is saved back unchanged) - so without the explicit reset below,
    the synthetic "/start" fed at the end of this handler hits the exact
    same UnknownState on the exact same stale stack and re-triggers this
    handler again, forever.

    Rather than showing an error message, just reopen the main menu - the
    user shouldn't have to know or care that their old message went stale.
    This feeds a synthetic "/start" message through the normal dispatcher
    pipeline (same as a real /start), rather than aiogram-dialog's own
    BgManager: BgManager builds a bare DialogUpdate that aiogram's own
    UserContextMiddleware doesn't recognize, so it resolves to an empty
    EventContext, FSMContextMiddleware then skips setting "state", and
    aiogram-i18n's locale lookup (which requires "state") crashes.
    """
    logger.warning("Stale dialog event: %s", event.exception)

    if aiogd_stack is not None and aiogd_storage_proxy is not None:
        while not aiogd_stack.empty():
            await aiogd_storage_proxy.remove_context(aiogd_stack.pop())
        await aiogd_storage_proxy.save_stack(aiogd_stack)

    update = event.update
    if update.callback_query is not None:
        with contextlib.suppress(Exception):
            await update.callback_query.answer()
        message = update.callback_query.message
        from_user = update.callback_query.from_user
    elif update.message is not None:
        message = update.message
        from_user = update.message.from_user
    else:
        return

    if message is None or from_user is None:
        return

    fake_message = Message(
        message_id=message.message_id,
        date=message.date,
        chat=message.chat,
        from_user=from_user,
        text="/start",
    )
    fake_update = Update(update_id=update.update_id, message=fake_message)

    # Scheduled, not awaited: this handler runs nested inside the original
    # update's own FSM lock (SimpleEventIsolation, keyed by chat/user), so
    # synchronously feeding a new update for the same user here would
    # deadlock trying to re-acquire that same lock. Deferring lets the
    # current update finish and release it first.
    asyncio.create_task(_reopen_main_menu(dispatcher, bot, fake_update))
