from __future__ import annotations

import logging

from aiogram.fsm.state import State, StatesGroup
from aiogram_dialog import Dialog, DialogManager, Window
from aiogram_dialog.widgets.style.base import ButtonStyle
from aiogram_dialog.widgets.kbd import Button, Group
from aiogram_dialog.widgets.text import Case

from proxy_bot.storage import Storage
from proxy_bot.utils.audit import actor
from proxy_bot.utils.html import esc
from proxy_bot.utils.i18n import popup_text

from ..common import BRANDED_LOGO_MEDIA, branded_logo_getter, icon
from ..widgets import I18N
from .activation import activate_code
from .enter_code import EnterCode
from .help import Help
from .links import Links
from .settings import Settings

logger = logging.getLogger(__name__)


class UserMenu(StatesGroup):
    main = State()


async def on_dialog_start(start_data: object, dialog_manager: DialogManager) -> None:
    storage: Storage = dialog_manager.middleware_data["storage"]
    remnawave = dialog_manager.middleware_data.get("remnawave")
    user = dialog_manager.middleware_data["event_from_user"]
    await storage.users.get_or_create(user.id, user.username, user.full_name)

    if not isinstance(start_data, dict):
        return

    if start_data.get("greet"):
        dialog_manager.dialog_data["greet"] = True

    auto_code = start_data.get("auto_code")
    if not auto_code:
        return

    status, _code_record = await activate_code(storage, remnawave, user, auto_code)
    if status in ("banned", "invalid"):
        await dialog_manager.start(EnterCode.main, data={"error": status})
    else:
        banner_key = "code-already-added" if status == "already" else "code-accepted"
        await dialog_manager.start(Links.main, data={"banner": banner_key})


async def on_enter_code_result(_start_data: object, result: object, manager: DialogManager) -> None:
    # enter_code hands back {"banner": ...} on a successful activation - show
    # it as part of the links screen instead of a message of its own.
    if isinstance(result, dict) and result.get("banner"):
        await manager.start(Links.main, data={"banner": result["banner"]})


async def open_enter_code(_callback, _button: Button, manager: DialogManager) -> None:
    await manager.start(EnterCode.main)


async def open_links(_callback, _button: Button, manager: DialogManager) -> None:
    await manager.start(Links.main)


async def open_help(_callback, _button: Button, manager: DialogManager) -> None:
    await manager.start(Help.main)


async def open_settings(_callback, _button: Button, manager: DialogManager) -> None:
    await manager.start(Settings.main)


async def open_admin_panel(callback, _button: Button, manager: DialogManager) -> None:
    # The button itself is only rendered when is_admin (see
    # main_menu_getter below), but that's a display condition, not an
    # access check - aiogram_dialog still matches and processes a click on
    # this widget id if one arrives some other way (e.g. an admin demoted
    # while this exact menu message, with a still-live "open_admin" button,
    # sits open in their chat). Re-check here rather than trusting that the
    # button was legitimately shown to whoever clicked it.
    storage: Storage = manager.middleware_data["storage"]
    user = manager.middleware_data["event_from_user"]
    if not await storage.admins.is_admin(user.id):
        logger.warning("%s tried to open the admin panel via a stale button", actor(user))
        await callback.answer(popup_text(manager.middleware_data["i18n"], "admin-only"), show_alert=True)
        return

    # Imported here, not at module level: dialogs.admin.menu imports
    # UserMenu from this module to return to the user menu, so a
    # top-level import back would be circular.
    from ..admin.menu import AdminMenu

    await manager.start(AdminMenu.main)


async def main_menu_getter(
    dialog_manager: DialogManager, event_from_user, storage: Storage, **kwargs
) -> dict:
    db_user = await storage.users.get_or_create(event_from_user.id, event_from_user.username, event_from_user.full_name)
    # Count only codes that still exist - db_user.codes can outlive a code
    # that an admin later deleted (see links_getter in dialogs/user/links.py,
    # which already skips those the same way when rendering the list
    # itself), so this keeps the count honest even for stale records left
    # over from before that cascade was in place.
    live_codes = [code for code in db_user.codes if await storage.codes.exists(code)]
    has_codes = bool(live_codes)

    # Shown once, right after a fresh /start - not on every return to this
    # window, so the greeting doesn't repeat every time the user navigates
    # back to the main menu.
    greeting = dialog_manager.dialog_data.pop("greet", False)

    return {
        "greeting": greeting,
        "name": esc(event_from_user.full_name),
        "count": len(live_codes),
        "has_codes": has_codes,
        "no_codes": not has_codes,
        "is_admin": await storage.admins.is_admin(event_from_user.id),
    }


user_menu_dialog = Dialog(
    Window(
        BRANDED_LOGO_MEDIA,
        Case(
            {True: I18N("menu-title-greeting"), False: I18N("menu-title")},
            selector="greeting",
        ),
        # Passed directly to Window (not wrapped in Column, which is
        # Group(width=1) and would flatten every button below into its
        # own row regardless of the nested Group's width - Window
        # combines top-level keyboard widgets via Group(width=None)
        # instead, which preserves each one's own row layout).
        #
        # The primary slot always holds the one action that matters
        # most right now - "my links" once the user has any, "enter
        # code" while they don't - mirroring how Liberty VPN swaps its
        # single main-menu button between "Test" and "Manage
        # subscription" depending on account state.
        Button(I18N("menu-btn-links"), id="primary_links", on_click=open_links, when="has_codes", style=icon("key", ButtonStyle.PRIMARY)),
        Button(
            I18N("menu-btn-enter-code"),
            id="primary_enter_code",
            on_click=open_enter_code,
            when="no_codes",
            style=icon("heavy_plus_sign", ButtonStyle.PRIMARY),
        ),
        Group(
            Button(
                I18N("menu-btn-enter-code"),
                id="open_enter_code",
                on_click=open_enter_code,
                when="has_codes",
                style=icon("heavy_plus_sign"),
            ),
            Button(I18N("menu-btn-links"), id="open_links", on_click=open_links, when="no_codes", style=icon("key")),
            Button(I18N("menu-btn-help"), id="open_help", on_click=open_help, style=icon("question")),
            width=2,
        ),
        Button(I18N("menu-btn-settings"), id="open_settings", on_click=open_settings, style=icon("gear")),
        Button(I18N("menu-btn-admin"), id="open_admin", on_click=open_admin_panel, when="is_admin", style=icon("shield")),
        state=UserMenu.main,
        getter=[main_menu_getter, branded_logo_getter],
    ),
    on_start=on_dialog_start,
    on_process_result=on_enter_code_result,
)
