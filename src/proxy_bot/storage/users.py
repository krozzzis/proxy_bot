from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path

from proxy_bot.utils.audit import actor_id

from .models import User
from .toml_file import TomlFile

logger = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


class UserRepo:
    def __init__(self, path: Path) -> None:
        self._file = TomlFile(path, default={"users": {}})

    async def get(self, user_id: int) -> User | None:
        data = await self._file.read()
        raw = data.get("users", {}).get(str(user_id))
        if raw is None:
            return None
        return User(user_id=user_id, **raw)

    async def all(self) -> list[User]:
        data = await self._file.read()
        return [User(user_id=int(key), **raw) for key, raw in data.get("users", {}).items()]

    async def users_with_code(self, code: str) -> list[User]:
        return [u for u in await self.all() if code in u.codes]

    async def get_or_create(self, user_id: int, username: str | None, full_name: str) -> User:
        is_new = False

        def mutate(data: dict) -> User:
            nonlocal is_new
            users = data.setdefault("users", {})
            key = str(user_id)
            # TOML has no null; store "" for an absent Telegram username.
            if key not in users:
                is_new = True
                users[key] = {
                    "username": username or "",
                    "full_name": full_name,
                    "first_seen": _now(),
                    "banned": False,
                    "codes": [],
                }
            else:
                users[key]["username"] = username or ""
                users[key]["full_name"] = full_name
            return User(user_id=user_id, **users[key])

        user = await self._file.update(mutate)
        if is_new:
            logger.info("New user registered: %s", actor_id(user_id, username))
        return user

    async def add_code(self, user_id: int, code: str) -> bool:
        """Attach a code to a user. Returns False if already attached."""

        def mutate(data: dict) -> bool:
            users = data.setdefault("users", {})
            key = str(user_id)
            if key not in users:
                return False
            codes = users[key].setdefault("codes", [])
            if code in codes:
                return False
            codes.append(code)
            return True

        return await self._file.update(mutate)

    async def set_banned(self, user_id: int, banned: bool) -> bool:
        def mutate(data: dict) -> bool:
            users = data.get("users", {})
            key = str(user_id)
            if key not in users:
                return False
            users[key]["banned"] = banned
            return True

        return await self._file.update(mutate)

    async def remove_code(self, user_id: int, code: str) -> bool:
        def mutate(data: dict) -> bool:
            users = data.get("users", {})
            key = str(user_id)
            if key not in users:
                return False
            codes = users[key].get("codes", [])
            if code not in codes:
                return False
            codes.remove(code)
            return True

        return await self._file.update(mutate)
