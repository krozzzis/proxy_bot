from __future__ import annotations

import logging
import time
from typing import Literal

from aiogram.types import User

from proxy_bot.remnawave import RemnawaveRegistry
from proxy_bot.services.remnawave_sync import sync_remnawave_access
from proxy_bot.storage import Code, Storage
from proxy_bot.storage.models import LINK_TYPE_REMNAWAVE
from proxy_bot.utils.audit import actor

logger = logging.getLogger(__name__)

ActivationStatus = Literal["banned", "invalid", "already", "added", "locked"]

# Code guessing defence: too many wrong codes in a row from the same user
# locks further attempts out for a while, rather than letting them retry
# unlimited codes back-to-back (flagged, unimplemented, in
# docs/security-audit-2026-07-29.md). In-memory and per-process, same
# tradeoff as RateLimitMiddleware - resets on restart, which is fine since
# this guards live guessing traffic, not something that needs to survive a
# deploy.
_MAX_FAILED_ATTEMPTS = 5
_ATTEMPT_WINDOW_SECONDS = 300.0
_LOCKOUT_SECONDS = 300.0


class _CodeAttemptLimiter:
    def __init__(self, max_attempts: int, window: float, lockout: float) -> None:
        self._max_attempts = max_attempts
        self._window = window
        self._lockout = lockout
        self._failures: dict[int, list[float]] = {}
        self._locked_until: dict[int, float] = {}

    def is_locked(self, user_id: int) -> bool:
        until = self._locked_until.get(user_id)
        if until is None:
            return False
        if time.monotonic() >= until:
            del self._locked_until[user_id]
            return False
        return True

    def record_invalid(self, user_id: int) -> None:
        now = time.monotonic()
        attempts = [t for t in self._failures.get(user_id, []) if now - t < self._window]
        attempts.append(now)
        if len(attempts) >= self._max_attempts:
            self._locked_until[user_id] = now + self._lockout
            attempts = []
        self._failures[user_id] = attempts

    def record_valid(self, user_id: int) -> None:
        # Only called for a genuinely new activation (see activate_code) -
        # clears the slate instead of leaving a stale near-lockout hanging
        # over the user's next typo. NOT called for a replayed already-held
        # code, which would otherwise let it launder unlimited guesses.
        self._failures.pop(user_id, None)
        self._locked_until.pop(user_id, None)


_attempt_limiter = _CodeAttemptLimiter(
    max_attempts=_MAX_FAILED_ATTEMPTS, window=_ATTEMPT_WINDOW_SECONDS, lockout=_LOCKOUT_SECONDS
)


async def activate_code(
    storage: Storage, remnawave: RemnawaveRegistry | None, user: User, code_text: str
) -> tuple[ActivationStatus, Code | None]:
    """Try to activate `code_text` for `user`. Shared by manual entry
    (enter_code.on_code_entered) and /start deep-link auto-activation
    (menu.on_dialog_start).
    """
    db_user = await storage.users.get_or_create(user.id, user.username, user.full_name)
    if db_user.banned:
        logger.info("Banned %s tried to enter code %r", actor(user), code_text.strip())
        return "banned", None

    if _attempt_limiter.is_locked(user.id):
        logger.info("%s is locked out of code entry after too many invalid attempts", actor(user))
        return "locked", None

    code = code_text.strip()
    code_record = await storage.codes.get(code)
    if code_record is None or not code_record.active:
        _attempt_limiter.record_invalid(user.id)
        logger.info("%s entered unknown code %r", actor(user), code)
        return "invalid", None

    added = await storage.users.add_code(user.id, code)
    if not added:
        # Deliberately NOT a record_valid() here - a code the user already
        # holds is trivially replayable, so treating replay as a "success"
        # would let 4-wrong-guesses-then-replay-my-own-code reset the
        # counter forever and defeat the lockout entirely. Only a genuinely
        # new activation (below) - which consumes that code and can't be
        # replayed the same way - earns a reset.
        logger.info("%s re-entered already-activated code %r", actor(user), code)
        return "already", code_record

    _attempt_limiter.record_valid(user.id)
    logger.info("%s activated code %r", actor(user), code)
    if any(link.type == LINK_TYPE_REMNAWAVE for link in code_record.links):
        await sync_remnawave_access(storage, remnawave, user.id)
    return "added", code_record
