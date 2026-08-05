from __future__ import annotations

import logging

from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery
from aiogram_dialog import Dialog, DialogManager, Window
from aiogram_dialog.widgets.kbd import Button, Cancel, Column, Select, SwitchTo
from aiogram_dialog.widgets.style.base import ButtonStyle
from aiogram_dialog.widgets.text import List, Multi
from pydantic import TypeAdapter

from proxy_bot.commands import set_admin_commands
from proxy_bot.storage import Storage
from proxy_bot.utils.audit import actor, actor_id
from proxy_bot.utils.formatting import display_name
from proxy_bot.utils.html import esc
from proxy_bot.utils.i18n import popup_text

from ..common import icon
from ..forms import FormField, build_field_window
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
    items = []
    for admin in admins:
        # Admin.username is a snapshot from grant time (AdminRepo.add) and
        # never updated after - the linked User row (kept fresh by
        # get_or_create on every interaction) is the current username and
        # the only place full_name lives at all, so prefer it whenever the
        # admin has ever started the bot. Falls back to the stale snapshot
        # only for the edge case of an admin added by numeric ID who never
        # has (storage.users.get returns None).
        user = await storage.users.get(admin.user_id)
        username = user.username if user else admin.username
        full_name = user.full_name if user else ""
        items.append({"name": esc(display_name(username, full_name, admin.user_id)), "id": str(admin.user_id)})
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


_CANCEL_STYLE = icon("x", ButtonStyle.DANGER)


async def _grant_admin(user_id: int, manager: DialogManager) -> None:
    storage: Storage = manager.middleware_data["storage"]
    i18n = manager.middleware_data["i18n"]
    bot = manager.middleware_data["bot"]
    admin = manager.middleware_data["event_from_user"]

    target_user = await storage.users.get(user_id)
    target = actor_id(user_id, target_user.username if target_user else None)

    added = await storage.admins.add(user_id, username=target_user.username if target_user else None, added_by=admin.id)
    if not added:
        logger.info("%s tried to grant admin rights to %s, who already is one", actor(admin), target)
        await bot.send_message(admin.id, i18n.get("admin-add-admin-already"))
    else:
        logger.info("%s granted admin rights to %s", actor(admin), target)
        await set_admin_commands(bot, user_id)
        await bot.send_message(admin.id, i18n.get("admin-add-admin-done", id=str(user_id)))
    await manager.switch_to(AdminAdmins.list)


ID_FIELD = FormField(
    name="admin_id",
    type_adapter=TypeAdapter(int),
    prompt="admin-add-admin-prompt",
    invalid_label="admin-add-admin-invalid",
)


async def on_id_done(user_id: int, manager: DialogManager) -> None:
    if not await ensure_admin(manager):
        await leave_admin_area(manager)
        return
    if not _is_super_admin(manager):
        await manager.switch_to(AdminAdmins.list)
        return
    await _grant_admin(user_id, manager)


async def _resolve_admin_username(username: str, manager: DialogManager) -> str | None:
    storage: Storage = manager.middleware_data["storage"]
    normalized = username.lstrip("@").lower()
    target_user = next(
        (u for u in await storage.users.all() if u.username and u.username.lower() == normalized),
        None,
    )
    if target_user is None:
        return "admin-add-admin-username-invalid"
    manager.dialog_data["target_admin_user_id"] = target_user.user_id
    return None


USERNAME_FIELD = FormField(
    name="admin_username",
    type_adapter=TypeAdapter(str),
    prompt="admin-add-admin-prompt-username",
    invalid_label="admin-add-admin-username-invalid",  # unreachable: a bare str never fails validation
    check=_resolve_admin_username,
)


async def on_username_done(_username: str, manager: DialogManager) -> None:
    if not await ensure_admin(manager):
        await leave_admin_area(manager)
        return
    if not _is_super_admin(manager):
        await manager.switch_to(AdminAdmins.list)
        return
    await _grant_admin(manager.dialog_data["target_admin_user_id"], manager)


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
    await callback.answer(popup_text(i18n, "admin-remove-admin-done", id=str(target_id)), show_alert=True)


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
    build_field_window(
        ID_FIELD,
        AdminAdmins.enter_id,
        on_id_done,
        SwitchTo(I18N("admin-btn-cancel"), id="back_to_method_from_id", state=AdminAdmins.choose_method, style=_CANCEL_STYLE),
    ),
    build_field_window(
        USERNAME_FIELD,
        AdminAdmins.enter_username,
        on_username_done,
        SwitchTo(I18N("admin-btn-cancel"), id="back_to_method_from_username", state=AdminAdmins.choose_method, style=_CANCEL_STYLE),
    ),
    on_start=on_dialog_start,
)
