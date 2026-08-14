from __future__ import annotations

import time
from typing import Protocol

from .client import RemnawaveRegistry

# How long a resolved (server, telegram_id) -> panel account id mapping is
# trusted before the next lookup re-resolves it via the panel's
# telegramId-filtered listing (RemnawaveClient.get_user_by_telegram_id) -
# long enough that routine dialog renders and the grant-sync sweep don't
# hammer the panel, short enough that an account deleted/recreated on the
# panel self-heals within about an hour rather than needing a bot restart.
_TTL_SECONDS = 3600


class RemnawaveAccountCache(Protocol):
    """(server, telegram user id) -> panel account id (the numeric `id` a
    3.x+ Remnawave panel identifies a user by). This is a cache, not a
    source of truth - storage.User.remnawave_accounts keeps the
    display-only metadata (subscription_url/username/linked_manually), and
    a miss here just costs one extra get_user_by_telegram_id round trip
    (see resolve_account_id), never a wrong answer."""

    async def get(self, server: str, user_id: int) -> int | None: ...

    async def set(self, server: str, user_id: int, account_id: int) -> None: ...

    async def invalidate(self, server: str, user_id: int) -> None: ...


class MemoryRemnawaveAccountCache:
    """In-process fallback for deployments without Redis (local dev via
    FSM_BACKEND=sqlite) - lost on restart, which is harmless since a miss
    just re-resolves via the panel instead of failing."""

    def __init__(self) -> None:
        self._entries: dict[tuple[str, int], tuple[int, float]] = {}

    async def get(self, server: str, user_id: int) -> int | None:
        entry = self._entries.get((server, user_id))
        if entry is None:
            return None
        account_id, expires_at = entry
        if expires_at < time.monotonic():
            del self._entries[(server, user_id)]
            return None
        return account_id

    async def set(self, server: str, user_id: int, account_id: int) -> None:
        self._entries[(server, user_id)] = (account_id, time.monotonic() + _TTL_SECONDS)

    async def invalidate(self, server: str, user_id: int) -> None:
        self._entries.pop((server, user_id), None)


class RedisRemnawaveAccountCache:
    """Redis-backed cache, keyed independently of the aiogram FSM storage's
    own keyspace (see fsm/factory.py) - a different concern, on its own
    connection, so a change to one doesn't imply a change to the other."""

    def __init__(self, redis: object) -> None:
        self._redis = redis

    @staticmethod
    def _key(server: str, user_id: int) -> str:
        return f"remnawave_account:{server}:{user_id}"

    async def get(self, server: str, user_id: int) -> int | None:
        value = await self._redis.get(self._key(server, user_id))
        return int(value) if value is not None else None

    async def set(self, server: str, user_id: int, account_id: int) -> None:
        await self._redis.set(self._key(server, user_id), account_id, ex=_TTL_SECONDS)

    async def invalidate(self, server: str, user_id: int) -> None:
        await self._redis.delete(self._key(server, user_id))


async def resolve_account_id(
    cache: RemnawaveAccountCache, remnawave: RemnawaveRegistry, server: str, user_id: int
) -> int | None:
    """The read-only half of account resolution, shared by every caller
    that just needs *an* id to query with (subscription display, the
    ban-state pull sweep, the admin ban/unban push) - cache hit first, else
    a live telegramId lookup (cached for next time). None if the panel
    genuinely has no account for this telegram id, or `server` isn't
    configured; callers that should provision one on a miss (services.
    remnawave_sync.sync_remnawave_access) do that themselves rather than
    through this helper, since creation is only appropriate where there's a
    grant to fulfill.

    Takes the registry rather than an already-`.get(server)`-resolved
    client on purpose - the cache key is `(server, user_id)`, so resolving
    the client from the same `server` here (instead of trusting a caller to
    have paired them correctly) rules out a mismatched pair silently
    poisoning the cache with a wrong server's id.

    Raises RemnawaveError on a panel/network failure - callers already sit
    inside their own try/except RemnawaveError for the surrounding work, so
    this doesn't swallow it itself.
    """
    account_id = await cache.get(server, user_id)
    if account_id is not None:
        return account_id
    client = remnawave.get(server)
    if client is None:
        return None
    rw_user = await client.get_user_by_telegram_id(user_id)
    if rw_user is None:
        return None
    await cache.set(server, user_id, rw_user.id)
    return rw_user.id


__all__ = [
    "MemoryRemnawaveAccountCache",
    "RedisRemnawaveAccountCache",
    "RemnawaveAccountCache",
    "resolve_account_id",
]
