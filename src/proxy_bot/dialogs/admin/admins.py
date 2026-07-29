from __future__ import annotations

import logging

from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from aiogram_dialog import Dialog, DialogManager, Window
from aiogram_dialog.widgets.input import ManagedTextInput, TextInput
from aiogram_dialog.widgets.kbd import Button, Cancel, Column, Select, SwitchTo
from aiogram_dialog.widgets.style.base import ButtonStyle
from aiogram_dialog.widgets.text import List, Multi

from proxy_bot.commands import set_admin_commands
from proxy_bot.storage import Storage
from proxy_bot.utils.audit import actor, actor_id
from proxy_bot.utils.html import esc

from ..common import icon, not_a_command
from ..widgets import I18N
from .access import ensure_admin, leave_admin_area

logger = logging.getLogger(__name__)


async def on_dialog_start(_start_data: object, manager: DialogManager) -> None:
    if not await ensure_admin(manager):
        await leave_admin_area(manager)


class AdminAdmins(StatesGroup):
    list = State()
    enter_id = State()


async def admins_list_getter(dialog_manager: DialogManager, **kwargs) -> dict:
    storage: Storage = dialog_manager.middleware_data["storage"]
    admins = await storage.admins.all()
    items = [
        {"name": esc(f"@{admin.username}" if admin.username else str(admin.user_id)), "id": str(admin.user_id)}
        for admin in admins
    ]
    # The root admin comes from config (ROOT_ADMIN_ID), not the TOML file -
    # AdminRepo.remove() only ever touches TOML entries, so a remove button
    # for that row would be a dead click. Leave it out instead of rendering
    # a button that can never do anything.
    removable = [item for item, admin in zip(items, admins) if admin.user_id != storage.admins.root_admin_id]
    return {"count": len(admins), "admins": items, "removable_admins": removable}


async def enter_id_getter(dialog_manager: DialogManager, **kwargs) -> dict:
    return {"id_error": dialog_manager.dialog_data.get("id_error", False)}


async def on_id_error(message: Message, widget: ManagedTextInput, manager: DialogManager, error: ValueError) -> None:
    manager.dialog_data["id_error"] = True


async def on_id_entered(message: Message, widget: ManagedTextInput, manager: DialogManager, user_id: int) -> None:
    if not await ensure_admin(manager):
        await leave_admin_area(manager)
        return

    storage: Storage = manager.middleware_data["storage"]
    i18n = manager.middleware_data["i18n"]
    admin = manager.middleware_data["event_from_user"]

    manager.dialog_data["id_error"] = False
    target_user = await storage.users.get(user_id)
    target = actor_id(user_id, target_user.username if target_user else None)

    added = await storage.admins.add(user_id, username=None, added_by=admin.id)
    if not added:
        logger.info("%s tried to grant admin rights to %s, who already is one", actor(admin), target)
        await message.answer(i18n.get("admin-add-admin-already"))
    else:
        logger.info("%s granted admin rights to %s", actor(admin), target)
        await set_admin_commands(manager.middleware_data["bot"], user_id)
        await message.answer(i18n.get("admin-add-admin-done", id=str(user_id)))
    await manager.switch_to(AdminAdmins.list)


async def open_enter_id(_callback: CallbackQuery, _button: Button, manager: DialogManager) -> None:
    manager.dialog_data["id_error"] = False
    await manager.switch_to(AdminAdmins.enter_id)


async def on_admin_removed(callback: CallbackQuery, _select, manager: DialogManager, item_id: str) -> None:
    if not await ensure_admin(manager):
        await leave_admin_area(manager)
        return

    storage: Storage = manager.middleware_data["storage"]
    i18n = manager.middleware_data["i18n"]
    admin = manager.middleware_data["event_from_user"]

    try:
        target_id = int(item_id)
    except ValueError:
        return

    removed = await storage.admins.remove(target_id)
    if not removed:
        return
    target_user = await storage.users.get(target_id)
    target = actor_id(target_id, target_user.username if target_user else None)
    logger.info("%s revoked admin rights from %s", actor(admin), target)
    await callback.answer(i18n.get("admin-remove-admin-done", id=str(target_id)), show_alert=True)


admins_dialog = Dialog(
    Window(
        Multi(
            I18N("admin-admins-title"),
            List(I18N("admin-admins-item", name="{item[name]}", id="{item[id]}"), items="admins", sep="\n"),
            sep="\n\n",
        ),
        Column(
            Select(
                I18N("admin-remove-admin-btn", name="{item[name]}"),
                id="remove_admin_select",
                item_id_getter=lambda item: item["id"],
                items="removable_admins",
                on_click=on_admin_removed,
                style=icon("x", ButtonStyle.DANGER),
            ),
        ),
        Button(I18N("admin-btn-add-admin"), id="add_admin", on_click=open_enter_id, style=icon("heavy_plus_sign")),
        Cancel(I18N("admin-btn-back"), style=icon("arrow_backward")),
        state=AdminAdmins.list,
        getter=admins_list_getter,
    ),
    Window(
        Multi(I18N("admin-add-admin-invalid", when="id_error"), I18N("admin-add-admin-prompt"), sep="\n\n"),
        TextInput(
            id="admin_id_input",
            type_factory=int,
            on_success=on_id_entered,
            on_error=on_id_error,
            filter=not_a_command,
        ),
        SwitchTo(I18N("admin-btn-cancel"), id="back_to_list", state=AdminAdmins.list, style=icon("x", ButtonStyle.DANGER)),
        state=AdminAdmins.enter_id,
        getter=enter_id_getter,
    ),
    on_start=on_dialog_start,
)
