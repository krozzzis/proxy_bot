from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery
from aiogram_dialog import Dialog, DialogManager, Window
from aiogram_dialog.widgets.kbd import Button, Group

from ..common import BRANDED_LOGO_MEDIA, branded_logo_getter, icon
from ..widgets import I18N
from .access import ensure_admin, leave_admin_area
from .admins import AdminAdmins
from .broadcast import AdminBroadcast
from .codes import AdminCodes
from .squads import AdminSquads
from .users import AdminUsers


class AdminMenu(StatesGroup):
    main = State()


async def on_dialog_start(_start_data: object, manager: DialogManager) -> None:
    if not await ensure_admin(manager):
        await leave_admin_area(manager)


async def open_codes(_callback: CallbackQuery, _button: Button, manager: DialogManager) -> None:
    if not await ensure_admin(manager):
        await leave_admin_area(manager)
        return
    await manager.start(AdminCodes.list)


async def open_users(_callback: CallbackQuery, _button: Button, manager: DialogManager) -> None:
    if not await ensure_admin(manager):
        await leave_admin_area(manager)
        return
    await manager.start(AdminUsers.list)


async def open_admins(_callback: CallbackQuery, _button: Button, manager: DialogManager) -> None:
    if not await ensure_admin(manager):
        await leave_admin_area(manager)
        return
    await manager.start(AdminAdmins.list)


async def open_broadcast(_callback: CallbackQuery, _button: Button, manager: DialogManager) -> None:
    if not await ensure_admin(manager):
        await leave_admin_area(manager)
        return
    await manager.start(AdminBroadcast.choose_target)


async def open_squads(_callback: CallbackQuery, _button: Button, manager: DialogManager) -> None:
    if not await ensure_admin(manager):
        await leave_admin_area(manager)
        return
    await manager.start(AdminSquads.list)


async def close_menu(_callback: CallbackQuery, _button: Button, manager: DialogManager) -> None:
    await leave_admin_area(manager)


async def menu_getter(dialog_manager: DialogManager, **kwargs) -> dict:
    return {"remnawave_available": dialog_manager.middleware_data.get("remnawave") is not None}


admin_menu_dialog = Dialog(
    Window(
        BRANDED_LOGO_MEDIA,
        I18N("admin-menu-title"),
        Group(
            Button(I18N("admin-btn-codes"), id="codes", on_click=open_codes, style=icon("package")),
            Button(I18N("admin-btn-users"), id="users", on_click=open_users, style=icon("bust_in_silhouette")),
            Button(I18N("admin-btn-admins"), id="admins", on_click=open_admins, style=icon("shield")),
            Button(I18N("admin-btn-broadcast"), id="broadcast", on_click=open_broadcast, style=icon("loudspeaker")),
            Button(
                I18N("admin-btn-squads"),
                id="squads",
                on_click=open_squads,
                when="remnawave_available",
                style=icon("shield"),
            ),
            width=2,
        ),
        Button(I18N("admin-btn-close"), id="close", on_click=close_menu, style=icon("arrow_backward")),
        state=AdminMenu.main,
        getter=[menu_getter, branded_logo_getter],
    ),
    on_start=on_dialog_start,
)
