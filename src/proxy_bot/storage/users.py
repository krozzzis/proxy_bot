from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path

from proxy_bot.utils.audit import actor_id

from .models import RemnawaveAccount, User
from .toml_file import TomlFile

logger = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _user_from_raw(user_id: int, raw: dict) -> User:
    """Build a User from its raw `users.toml` dict, unpacking the nested
    `remnawave_accounts` table into RemnawaveAccount instances (a plain
    `User(user_id=user_id, **raw)` can't do this itself - the dataclass
    field is `dict[str, RemnawaveAccount]`, not `dict[str, dict]`).

    Drops a stray `uuid` key from each account entry - RemnawaveAccount
    carried one until the Remnawave 3.x migration moved account
    identification to remnawave.cache.RemnawaveAccountCache (see
    services.remnawave_sync); a record written before that change still has
    the key on disk/in Redis; ``RemnawaveAccount(**account)`` would
    otherwise raise on it every time this user loads."""
    data = dict(raw)
    raw_accounts = data.pop("remnawave_accounts", {})
    accounts = {
        server: RemnawaveAccount(**{k: v for k, v in account.items() if k != "uuid"})
        for server, account in raw_accounts.items()
    }
    return User(user_id=user_id, remnawave_accounts=accounts, **data)


class UserRepo:
    def __init__(self, path: Path) -> None:
        self._file = TomlFile(path, default={"users": {}})

    async def get(self, user_id: int) -> User | None:
        data = await self._file.read()
        raw = data.get("users", {}).get(str(user_id))
        if raw is None:
            return None
        return _user_from_raw(user_id, raw)

    async def all(self) -> list[User]:
        data = await self._file.read()
        return [_user_from_raw(int(key), raw) for key, raw in data.get("users", {}).items()]

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
            return _user_from_raw(user_id, users[key])

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

    async def rename_code(self, old_code: str, new_code: str) -> None:
        """Replace `old_code` with `new_code` in every user's code list.
        Used when an admin renames a code, so existing holders keep access
        under the new name instead of silently losing it."""

        def mutate(data: dict) -> None:
            for user in data.get("users", {}).values():
                codes = user.get("codes", [])
                if old_code not in codes:
                    continue
                if new_code in codes:
                    codes.remove(old_code)
                else:
                    codes[codes.index(old_code)] = new_code

        await self._file.update(mutate)

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

    async def set_locale(self, user_id: int, locale: str) -> bool:
        def mutate(data: dict) -> bool:
            users = data.get("users", {})
            key = str(user_id)
            if key not in users:
                return False
            users[key]["locale"] = locale
            return True

        return await self._file.update(mutate)

    async def set_remnawave_account(
        self,
        user_id: int,
        server: str,
        subscription_url: str | None,
        username: str | None = None,
        *,
        manual: bool = False,
        unlink: bool = False,
    ) -> bool:
        """Link (or unlink, if `unlink` is set) this user's Remnawave
        account on `server`. `manual` distinguishes an admin's explicit
        "Link Remnawave" pick (dialogs/admin/link_remnawave.py) from an
        automatic provision/match (services/remnawave_sync.py) - shown on
        the admin user-detail page so an admin can tell the two apart.

        Only display metadata - the panel's own account id is resolved on
        demand and cached separately (see remnawave.cache), not persisted
        here (see RemnawaveAccount's docstring for why)."""

        def mutate(data: dict) -> bool:
            users = data.get("users", {})
            key = str(user_id)
            if key not in users:
                return False
            accounts = users[key].setdefault("remnawave_accounts", {})
            if unlink:
                accounts.pop(server, None)
            else:
                accounts[server] = {
                    "subscription_url": subscription_url or "",
                    "username": username or "",
                    "linked_manually": manual,
                }
            return True

        return await self._file.update(mutate)

    async def set_remnawave_disabled(self, user_id: int, disabled: bool) -> bool:
        def mutate(data: dict) -> bool:
            users = data.get("users", {})
            key = str(user_id)
            if key not in users:
                return False
            users[key]["remnawave_disabled"] = disabled
            return True

        return await self._file.update(mutate)
