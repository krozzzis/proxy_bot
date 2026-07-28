from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery
from aiogram_dialog import Dialog, DialogManager, StartMode, Window
from aiogram_dialog.widgets.kbd import Button, Group
from aiogram_dialog.widgets.text import Format

from ..common import icon
from .admins import AdminAdmins
from .broadcast import AdminBroadcast
from .codes import AdminCodes
from .create_code import AdminCreateCode
from .users import AdminUsers


class AdminMenu(StatesGroup):
    main = State()


async def on_child_result(_start_data: object, result: object, manager: DialogManager) -> None:
    # create_code (and any future child that finishes with a confirmation)
    # hands back {"banner": ...} - show it as part of this re-render
    # instead of a message of its own, sent separately and out of order.
    if isinstance(result, dict) and result.get("banner"):
        manager.dialog_data["banner"] = result["banner"]


async def admin_menu_getter(dialog_manager: DialogManager, i18n, **kwargs) -> dict:
    title = i18n.get("admin-menu-title")
    banner = dialog_manager.dialog_data.pop("banner", None)
    if banner:
        title = f"{banner}\n\n{title}"
    return {
        "title": title,
        "btn_create_code": i18n.get("admin-btn-create-code"),
        "btn_codes": i18n.get("admin-btn-codes"),
        "btn_users": i18n.get("admin-btn-users"),
        "btn_admins": i18n.get("admin-btn-admins"),
        "btn_broadcast": i18n.get("admin-btn-broadcast"),
        "btn_close": i18n.get("admin-btn-close"),
    }


async def open_create_code(_callback: CallbackQuery, _button: Button, manager: DialogManager) -> None:
    await manager.start(AdminCreateCode.enter_code)


async def open_codes(_callback: CallbackQuery, _button: Button, manager: DialogManager) -> None:
    await manager.start(AdminCodes.list)


async def open_users(_callback: CallbackQuery, _button: Button, manager: DialogManager) -> None:
    await manager.start(AdminUsers.list)


async def open_admins(_callback: CallbackQuery, _button: Button, manager: DialogManager) -> None:
    await manager.start(AdminAdmins.list)


async def open_broadcast(_callback: CallbackQuery, _button: Button, manager: DialogManager) -> None:
    await manager.start(AdminBroadcast.choose_target)


async def close_menu(_callback: CallbackQuery, _button: Button, manager: DialogManager) -> None:
    # Opened from the merged user menu, the admin panel sits on top of a
    # UserMenu.main dialog on the stack, so done() pops back to it. Opened
    # directly via /admin, the admin panel is the only thing on the stack
    # (a single-message entry point), so there's nothing beneath it to pop
    # back to - start the user menu explicitly in that case instead.
    if len(manager.current_stack().intents) > 1:
        await manager.done()
    else:
        # Imported here, not at module level: dialogs.user.menu imports
        # AdminMenu from this module to open the admin panel, so a
        # top-level import back would be circular.
        from ..user.menu import UserMenu

        await manager.start(UserMenu.main, mode=StartMode.RESET_STACK)


admin_menu_dialog = Dialog(
    Window(
        Format("{title}"),
        Group(
            Button(Format("{btn_create_code}"), id="create_code", on_click=open_create_code, style=icon("heavy_plus_sign")),
            Button(Format("{btn_codes}"), id="codes", on_click=open_codes, style=icon("package")),
            Button(Format("{btn_users}"), id="users", on_click=open_users, style=icon("bust_in_silhouette")),
            Button(Format("{btn_admins}"), id="admins", on_click=open_admins, style=icon("shield")),
            Button(Format("{btn_broadcast}"), id="broadcast", on_click=open_broadcast, style=icon("loudspeaker")),
            width=2,
        ),
        Button(Format("{btn_close}"), id="close", on_click=close_menu, style=icon("arrow_backward")),
        state=AdminMenu.main,
        getter=admin_menu_getter,
    ),
    on_process_result=on_child_result,
)
