from __future__ import annotations

import logging

from aiogram_dialog import DialogManager, StartMode

from proxy_bot.storage import Storage
from proxy_bot.utils.audit import actor

logger = logging.getLogger(__name__)


async def ensure_admin(manager: DialogManager) -> bool:
    """Re-check admin status at the point of use, not just at menu-render
    time.

    A button's `when` condition only hides it from the rendered keyboard -
    aiogram_dialog still matches and processes a click on that widget id if
    one somehow arrives (see Keyboard.process_callback: it checks
    `callback.data == self.widget_id`, not the `when` condition). So the
    admin-only buttons across this dialog tree are not themselves a
    permission boundary; every admin dialog's on_start, and every handler
    that mutates state, calls this first. The case this actually guards
    against: an admin gets demoted (or banned) while an admin-panel message
    they already opened is still sitting in their chat with live buttons -
    those buttons carry a perfectly valid, current intent id, so nothing
    about the callback itself looks wrong.
    """
    storage: Storage = manager.middleware_data["storage"]
    user = manager.middleware_data["event_from_user"]
    if await storage.admins.is_admin(user.id):
        return True
    logger.warning("%s reached an admin-only action without permission", actor(user))
    return False


async def leave_admin_area(manager: DialogManager) -> None:
    """Back out of the admin dialog tree after ensure_admin() fails.

    Mirrors admin.menu.close_menu's own logic: with something beneath the
    current dialog on the stack (the usual case - opened from the merged
    user menu, or nested deeper inside the admin panel), pop back to it.
    Opened as the only thing on the stack (a bare /admin entry - already
    gated by the IsAdmin command filter, so this branch is a defensive
    fallback rather than a live path), there's nothing to pop back to, so
    land on the user menu instead.
    """
    if len(manager.current_stack().intents) > 1:
        await manager.done()
    else:
        from ..user.menu import UserMenu

        await manager.start(UserMenu.main, mode=StartMode.RESET_STACK)
