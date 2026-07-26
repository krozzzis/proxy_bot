from __future__ import annotations

from aiogram.filters import BaseFilter
from aiogram.types import TelegramObject, User

from proxy_bot.storage import Storage


class IsAdmin(BaseFilter):
    async def __call__(self, event: TelegramObject, event_from_user: User, storage: Storage) -> bool:
        return await storage.admins.is_admin(event_from_user.id)
