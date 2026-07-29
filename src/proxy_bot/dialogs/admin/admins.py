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
    choose_method = State()
    enter_id = State()
    enter_username = State()


def _is_super_admin(manager: DialogManager) -> bool:
    """Only the root admin (config's ROOT_ADMIN_ID) may grant admin rights -
    an ordinary admin could otherwise mint an arbitrary number of peers with
    equal standing, including themselves after a demotion."""
    storage: Storage = manager.middleware_data["storage"]
    admin = manager.middleware_data["event_from_user"]
    return admin.id == storage.admins.root_admin_id


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
    return {
        "count": len(admins),
        "admins": items,
        "removable_admins": removable,
        "is_super_admin": _is_super_admin(dialog_manager),
    }


async def enter_id_getter(dialog_manager: DialogManager, **kwargs) -> dict:
    return {"id_error": dialog_manager.dialog_data.get("id_error", False)}


async def enter_username_getter(dialog_manager: DialogManager, **kwargs) -> dict:
    return {"username_error": dialog_manager.dialog_data.get("username_error", False)}


async def on_id_error(message: Message, widget: ManagedTextInput, manager: DialogManager, error: ValueError) -> None:
    manager.dialog_data["id_error"] = True


async def _grant_admin(message: Message, user_id: int, manager: DialogManager) -> None:
    storage: Storage = manager.middleware_data["storage"]
    i18n = manager.middleware_data["i18n"]
    admin = manager.middleware_data["event_from_user"]

    target_user = await storage.users.get(user_id)
    target = actor_id(user_id, target_user.username if target_user else None)

    added = await storage.admins.add(user_id, username=target_user.username if target_user else None, added_by=admin.id)
    if not added:
        logger.info("%s tried to grant admin rights to %s, who already is one", actor(admin), target)
        await message.answer(i18n.get("admin-add-admin-already"))
    else:
        logger.info("%s granted admin rights to %s", actor(admin), target)
        await set_admin_commands(manager.middleware_data["bot"], user_id)
        await message.answer(i18n.get("admin-add-admin-done", id=str(user_id)))
    await manager.switch_to(AdminAdmins.list)


async def on_id_entered(message: Message, widget: ManagedTextInput, manager: DialogManager, user_id: int) -> None:
    if not await ensure_admin(manager):
        await leave_admin_area(manager)
        return
    if not _is_super_admin(manager):
        await manager.switch_to(AdminAdmins.list)
        return

    manager.dialog_data["id_error"] = False
    await _grant_admin(message, user_id, manager)


async def on_username_entered(message: Message, widget: ManagedTextInput, manager: DialogManager, raw: str) -> None:
    if not await ensure_admin(manager):
        await leave_admin_area(manager)
        return
    if not _is_super_admin(manager):
        await manager.switch_to(AdminAdmins.list)
        return

    storage: Storage = manager.middleware_data["storage"]
    username = raw.strip().lstrip("@").lower()
    target_user = next(
        (u for u in await storage.users.all() if u.username and u.username.lower() == username),
        None,
    )
    if target_user is None:
        manager.dialog_data["username_error"] = True
        return

    manager.dialog_data["username_error"] = False
    await _grant_admin(message, target_user.user_id, manager)


async def open_choose_method(_callback: CallbackQuery, _button: Button, manager: DialogManager) -> None:
    if not await ensure_admin(manager):
        await leave_admin_area(manager)
        return
    if not _is_super_admin(manager):
        return
    await manager.switch_to(AdminAdmins.choose_method)


async def open_enter_id(_callback: CallbackQuery, _button: Button, manager: DialogManager) -> None:
    manager.dialog_data["id_error"] = False
    await manager.switch_to(AdminAdmins.enter_id)


async def open_enter_username(_callback: CallbackQuery, _button: Button, manager: DialogManager) -> None:
    manager.dialog_data["username_error"] = False
    await manager.switch_to(AdminAdmins.enter_username)


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
        Button(
            I18N("admin-btn-add-admin"),
            id="add_admin",
            on_click=open_choose_method,
            when="is_super_admin",
            style=icon("heavy_plus_sign"),
        ),
        Cancel(I18N("admin-btn-back"), style=icon("arrow_backward")),
        state=AdminAdmins.list,
        getter=admins_list_getter,
    ),
    Window(
        I18N("admin-add-admin-choose-method-prompt"),
        Button(I18N("admin-add-admin-method-id"), id="method_id", on_click=open_enter_id, style=icon("pencil2")),
        Button(
            I18N("admin-add-admin-method-username"),
            id="method_username",
            on_click=open_enter_username,
            style=icon("bust_in_silhouette"),
        ),
        SwitchTo(I18N("admin-btn-cancel"), id="back_to_list_from_method", state=AdminAdmins.list, style=icon("x", ButtonStyle.DANGER)),
        state=AdminAdmins.choose_method,
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
        SwitchTo(
            I18N("admin-btn-cancel"), id="back_to_method_from_id", state=AdminAdmins.choose_method, style=icon("x", ButtonStyle.DANGER)
        ),
        state=AdminAdmins.enter_id,
        getter=enter_id_getter,
    ),
    Window(
        Multi(I18N("admin-add-admin-username-invalid", when="username_error"), I18N("admin-add-admin-prompt-username"), sep="\n\n"),
        TextInput(
            id="admin_username_input",
            on_success=on_username_entered,
            filter=not_a_command,
        ),
        SwitchTo(
            I18N("admin-btn-cancel"),
            id="back_to_method_from_username",
            state=AdminAdmins.choose_method,
            style=icon("x", ButtonStyle.DANGER),
        ),
        state=AdminAdmins.enter_username,
        getter=enter_username_getter,
    ),
    on_start=on_dialog_start,
)
