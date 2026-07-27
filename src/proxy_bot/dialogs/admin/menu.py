from __future__ import annotations

from aiogram.types import CallbackQuery
from aiogram_dialog import Dialog, DialogManager, StartMode, Window
from aiogram_dialog.widgets.kbd import Button, Column
from aiogram_dialog.widgets.text import Format

from ..states import AdminAdmins, AdminBroadcast, AdminCodes, AdminCreateCode, AdminMenu, AdminUsers, UserMenu


async def admin_menu_getter(i18n, **kwargs) -> dict:
    return {
        "title": i18n.get("admin-menu-title"),
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
        await manager.start(UserMenu.main, mode=StartMode.RESET_STACK)


def admin_menu_window() -> Window:
    return Window(
        Format("{title}"),
        Column(
            Button(Format("{btn_create_code}"), id="create_code", on_click=open_create_code),
            Button(Format("{btn_codes}"), id="codes", on_click=open_codes),
            Button(Format("{btn_users}"), id="users", on_click=open_users),
            Button(Format("{btn_admins}"), id="admins", on_click=open_admins),
            Button(Format("{btn_broadcast}"), id="broadcast", on_click=open_broadcast),
            Button(Format("{btn_close}"), id="close", on_click=close_menu),
        ),
        state=AdminMenu.main,
        getter=admin_menu_getter,
    )


def admin_menu_dialog() -> Dialog:
    return Dialog(admin_menu_window())
