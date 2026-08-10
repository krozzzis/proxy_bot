from __future__ import annotations

import logging
from typing import Literal

from aiogram.types import User

from proxy_bot.remnawave import RemnawaveRegistry
from proxy_bot.services.remnawave_sync import sync_remnawave_access
from proxy_bot.storage import Code, Storage
from proxy_bot.storage.models import LINK_TYPE_REMNAWAVE
from proxy_bot.utils.audit import actor

logger = logging.getLogger(__name__)

ActivationStatus = Literal["banned", "invalid", "already", "added"]


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

    code = code_text.strip()
    code_record = await storage.codes.get(code)
    if code_record is None or not code_record.active:
        logger.info("%s entered unknown code %r", actor(user), code)
        return "invalid", None

    added = await storage.users.add_code(user.id, code)
    if not added:
        logger.info("%s re-entered already-activated code %r", actor(user), code)
        return "already", code_record

    logger.info("%s activated code %r", actor(user), code)
    if any(link.type == LINK_TYPE_REMNAWAVE for link in code_record.links):
        await sync_remnawave_access(storage, remnawave, user.id)
    return "added", code_record
