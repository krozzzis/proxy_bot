from __future__ import annotations

import logging

from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery
from aiogram_dialog import Dialog, DialogManager, Window
from aiogram_dialog.widgets.kbd import Button, Cancel, SwitchTo
from aiogram_dialog.widgets.style.base import ButtonStyle
from pydantic import TypeAdapter

from proxy_bot.remnawave import RemnawaveError
from proxy_bot.services.remnawave_sync import retire_auto_provisioned_account, sync_remnawave_access
from proxy_bot.storage import Storage
from proxy_bot.utils.audit import actor, actor_id
from proxy_bot.utils.html import esc
from proxy_bot.utils.i18n import popup_text

from ..common import icon
from ..forms import FormField, build_field_window
from ..widgets import I18N
from .access import ensure_admin, leave_admin_area

logger = logging.getLogger(__name__)

_CANCEL_STYLE = icon("x", ButtonStyle.DANGER)


class LinkRemnawave(StatesGroup):
    enter_username = State()
    confirm = State()


async def on_dialog_start(start_data: object, manager: DialogManager) -> None:
    if not await ensure_admin(manager):
        await leave_admin_area(manager)
        return
    if not isinstance(start_data, dict) or "user_id" not in start_data:
        await manager.done()
        return
    if manager.middleware_data.get("remnawave") is None:
        # Defensive only - the "Link Remnawave" button that starts this
        # dialog is itself gated on remnawave being configured, so this
        # should be unreachable outside a race with a config change.
        await manager.done()
        return
    manager.dialog_data["user_id"] = start_data["user_id"]


async def _enter_username_extra_getter(manager: DialogManager) -> dict:
    return {"id": str(manager.dialog_data.get("user_id", ""))}


async def _resolve_remnawave_username(username_text: str, manager: DialogManager) -> str | None:
    remnawave = manager.middleware_data["remnawave"]
    username = username_text.lstrip("@")
    try:
        rw_user = await remnawave.get_user_by_username(username)
    except RemnawaveError:
        logger.warning("Remnawave lookup failed for username %r", username, exc_info=True)
        return "admin-link-remnawave-lookup-failed"

    if rw_user is None:
        return "admin-link-remnawave-not-found"

    manager.dialog_data["found_uuid"] = rw_user.uuid
    manager.dialog_data["found_username"] = rw_user.username
    manager.dialog_data["found_subscription_url"] = rw_user.subscription_url
    return None


USERNAME_FIELD = FormField(
    name="link_remnawave_username",
    type_adapter=TypeAdapter(str),
    prompt="admin-link-remnawave-prompt",
    invalid_label="admin-link-remnawave-not-found",  # unreachable: a bare str never fails validation
    check=_resolve_remnawave_username,
    extra_getter=_enter_username_extra_getter,
)


async def on_username_done(_username: str, manager: DialogManager) -> None:
    if not await ensure_admin(manager):
        await leave_admin_area(manager)
        return
    await manager.next()


async def confirm_getter(dialog_manager: DialogManager, **kwargs) -> dict:
    return {
        "id": str(dialog_manager.dialog_data.get("user_id", "")),
        "username": esc(dialog_manager.dialog_data.get("found_username", "")),
        "url": esc(dialog_manager.dialog_data.get("found_subscription_url") or ""),
    }


async def on_confirm(callback: CallbackQuery, _button: Button, manager: DialogManager) -> None:
    if not await ensure_admin(manager):
        await leave_admin_area(manager)
        return

    storage: Storage = manager.middleware_data["storage"]
    i18n = manager.middleware_data["i18n"]
    admin = manager.middleware_data["event_from_user"]
    user_id = manager.dialog_data["user_id"]
    uuid = manager.dialog_data["found_uuid"]
    found_username = manager.dialog_data.get("found_username")
    subscription_url = manager.dialog_data.get("found_subscription_url")

    # The target may never have /start-ed the bot yet - materialize their
    # row now, same as AdminAddUser.on_confirm does for a raw numeric id.
    target_user = await storage.users.get(user_id)
    if target_user is None:
        target_user = await storage.users.get_or_create(user_id, username=None, full_name="")

    await storage.users.set_remnawave_account(user_id, uuid, subscription_url, found_username, manual=True)
    remnawave = manager.middleware_data.get("remnawave")
    await sync_remnawave_access(storage, remnawave, user_id)

    target = actor_id(user_id, target_user.username)
    logger.info("%s linked Remnawave account %r to %s", actor(admin), found_username, target)

    retired = await retire_auto_provisioned_account(remnawave, target_user, keep_uuid=uuid)
    if retired is not None:
        logger.info("%s retired (%s) auto-provisioned Remnawave account for %s", actor(admin), retired, target)

    await callback.answer(popup_text(i18n, "admin-link-remnawave-done", id=str(user_id)), show_alert=True)
    await manager.done()


link_remnawave_dialog = Dialog(
    build_field_window(
        USERNAME_FIELD,
        LinkRemnawave.enter_username,
        on_username_done,
        Cancel(I18N("admin-btn-cancel"), style=_CANCEL_STYLE),
    ),
    Window(
        I18N("admin-link-remnawave-confirm", id="{id}", username="{username}", url="{url}"),
        Button(
            I18N("admin-btn-done"),
            id="confirm_link",
            on_click=on_confirm,
            style=icon("white_check_mark", ButtonStyle.SUCCESS),
        ),
        SwitchTo(
            I18N("admin-btn-cancel"), id="back_to_username", state=LinkRemnawave.enter_username, style=_CANCEL_STYLE
        ),
        state=LinkRemnawave.confirm,
        getter=confirm_getter,
    ),
    on_start=on_dialog_start,
)
