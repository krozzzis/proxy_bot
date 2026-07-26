from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from .models import Admin
from .toml_file import TomlFile


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


class AdminRepo:
    """Admin registry, backed by TOML plus a hard-coded root admin from config.

    The root admin id always counts as an admin, even before the TOML file
    exists, so there is always at least one way in to bootstrap the panel.
    """

    def __init__(self, path: Path, root_admin_id: int) -> None:
        self._file = TomlFile(path, default={"admins": {}})
        self.root_admin_id = root_admin_id

    async def is_admin(self, user_id: int) -> bool:
        if user_id == self.root_admin_id:
            return True
        data = await self._file.read()
        return str(user_id) in data.get("admins", {})

    async def all(self) -> list[Admin]:
        data = await self._file.read()
        admins = [Admin(user_id=int(key), **raw) for key, raw in data.get("admins", {}).items()]
        if not any(a.user_id == self.root_admin_id for a in admins):
            admins.insert(0, Admin(user_id=self.root_admin_id, username=None, added_by=0, added_at=""))
        return admins

    async def add(self, user_id: int, username: str | None, added_by: int) -> bool:
        """Returns False if the user is already an admin."""

        def mutate(data: dict) -> bool:
            admins = data.setdefault("admins", {})
            key = str(user_id)
            if key in admins or user_id == self.root_admin_id:
                return False
            admins[key] = {
                "username": username or "",
                "added_by": added_by,
                "added_at": _now(),
            }
            return True

        return await self._file.update(mutate)

    async def remove(self, user_id: int) -> bool:
        def mutate(data: dict) -> bool:
            admins = data.get("admins", {})
            key = str(user_id)
            if key not in admins:
                return False
            del admins[key]
            return True

        return await self._file.update(mutate)
