from __future__ import annotations

import contextlib
import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject, User

from proxy_bot.utils.audit import actor

logger = logging.getLogger("proxy_bot.rate_limit")

# Minimum gap between two processed events of the same kind from the same
# user - guards handler/storage load against a single user (flood, mis-tap-
# and-hold, or deliberate abuse) driving unbounded traffic. Kept separate
# per event kind (rather than one combined budget) because they have very
# different natural cadences: quickly tapping chevron_left/right to page
# through an admin list is normal use and would otherwise trip a message-
# sized budget. "You're going too fast" notices are throttled far more
# loosely (_NOTICE_INTERVAL) so a burst of drops doesn't also become a
# burst of replies.
_MESSAGE_MIN_INTERVAL = 0.5
_CALLBACK_MIN_INTERVAL = 0.25
_NOTICE_INTERVAL = 3.0


class RateLimitMiddleware(BaseMiddleware):
    """Outer middleware registered on both dp.message and dp.callback_query
    (same instance for both - message and callback cadence are tracked
    separately, see the interval constants above, but notice throttling is
    shared so a user flooding both at once doesn't get double the notices).
    Per-user timestamps live in plain dicts for the life of the process -
    fine for a bot-sized user base, and resetting on restart is the desired
    behaviour: a flood is a live-traffic problem, not state that should
    outlive the process the way e.g. ban status does.

    Internally-generated re-feeds (handlers/errors.py's stale-dialog
    recovery, which synthesizes a fresh "/start" Message and pushes it back
    through dispatcher.feed_update) must not be judged against the user's
    real traffic - they pass skip_rate_limit=True as a feed_update kwarg,
    which aiogram merges straight into this middleware's `data`.
    """

    def __init__(
        self,
        message_min_interval: float = _MESSAGE_MIN_INTERVAL,
        callback_min_interval: float = _CALLBACK_MIN_INTERVAL,
        notice_interval: float = _NOTICE_INTERVAL,
    ) -> None:
        self._message_min_interval = message_min_interval
        self._callback_min_interval = callback_min_interval
        self._notice_interval = notice_interval
        self._last_processed: dict[tuple[int, str], float] = {}
        self._last_notice: dict[int, float] = {}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if data.get("skip_rate_limit"):
            return await handler(event, data)

        user: User | None = getattr(event, "from_user", None)
        if user is None:
            return await handler(event, data)

        if isinstance(event, CallbackQuery):
            kind, min_interval = "callback", self._callback_min_interval
        elif isinstance(event, Message):
            kind, min_interval = "message", self._message_min_interval
        else:
            return await handler(event, data)

        now = time.monotonic()
        key = (user.id, kind)
        last = self._last_processed.get(key)
        if last is not None and now - last < min_interval:
            await self._throttle(event, data, user, now)
            return None

        self._last_processed[key] = now
        return await handler(event, data)

    async def _throttle(self, event: TelegramObject, data: dict[str, Any], user: User, now: float) -> None:
        last_notice = self._last_notice.get(user.id)
        should_notify = last_notice is None or now - last_notice >= self._notice_interval
        if should_notify:
            self._last_notice[user.id] = now
        logger.info("Throttled %s (notify=%s)", actor(user), should_notify)

        i18n = data.get("i18n")
        text = i18n.get("rate-limited") if i18n is not None else None

        if isinstance(event, CallbackQuery):
            # Always answered (even with no text) so the client's loading
            # spinner on the tapped button clears - this fires before
            # aiogram-dialog's own middleware ever sees the update, so
            # nothing else is going to answer it for us.
            with contextlib.suppress(Exception):
                await event.answer(text=text if should_notify else None)
        elif isinstance(event, Message) and should_notify and text is not None:
            with contextlib.suppress(Exception):
                await event.answer(text)
