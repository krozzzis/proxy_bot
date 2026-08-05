from __future__ import annotations

import logging

from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery
from aiogram_dialog import Dialog, DialogManager, Window
from aiogram_dialog.widgets.kbd import Button, Cancel, Column, Multiselect, SwitchTo
from aiogram_dialog.widgets.style.base import ButtonStyle
from aiogram_dialog.widgets.text import Case
from pydantic import TypeAdapter

from proxy_bot.services.remnawave_sync import sync_remnawave_access
from proxy_bot.storage import Storage
from proxy_bot.utils.audit import actor, actor_id
from proxy_bot.utils.html import esc
from proxy_bot.utils.i18n import popup_text

from ..common import icon
from ..forms import FormField, build_field_window
from ..widgets import I18N
from .access import ensure_admin, leave_admin_area
from .link_remnawave import LinkRemnawave

logger = logging.getLogger(__name__)

_SUBS_SELECT_ID = "subs_select"
_CANCEL_STYLE = icon("x", ButtonStyle.DANGER)


class AdminAddUser(StatesGroup):
    enter_identifier = State()
    choose_subscriptions = State()


async def on_dialog_start(_start_data: object, manager: DialogManager) -> None:
    if not await ensure_admin(manager):
        await leave_admin_area(manager)


async def _resolve_identifier(identifier: str, manager: DialogManager) -> str | None:
    storage: Storage = manager.middleware_data["storage"]

    if identifier.startswith("@"):
        body, is_id = identifier[1:], False
    else:
        body, is_id = identifier, identifier.isdigit()

    if is_id:
        # Any numeric id is accepted at this point without checking whether
        # a row for it exists yet - creating that row is deferred to
        # on_confirm(), so a typo here (or a Cancel right after) doesn't
        # leave a permanent phantom entry in users.toml with no way to
        # remove it (UserRepo has no delete()).
        target_user_id = int(body)
    else:
        # A username alone carries no id - it can only be resolved against
        # users this bot has already seen (storage.users), since Telegram's
        # Bot API has no general username->id lookup for private chats.
        username = body.lower()
        target_user = next(
            (u for u in await storage.users.all() if u.username and u.username.lower() == username),
            None,
        )
        target_user_id = target_user.user_id if target_user else None

    if target_user_id is None:
        return "admin-add-user-invalid"

    manager.dialog_data["target_user_id"] = target_user_id
    return None


IDENTIFIER_FIELD = FormField(
    name="add_user_identifier",
    type_adapter=TypeAdapter(str),
    prompt="admin-add-user-prompt",
    invalid_label="admin-add-user-invalid",  # unreachable: a bare str never fails validation
    check=_resolve_identifier,
)


async def on_identifier_done(_identifier: str, manager: DialogManager) -> None:
    if not await ensure_admin(manager):
        await leave_admin_area(manager)
        return

    # A previous run through this window (Cancel from choose_subscriptions,
    # then a different id/username) must not carry over ticks made for the
    # last target - Multiselect keeps its checked set in widget_data for as
    # long as this dialog's intent lives, across state switches.
    multiselect = manager.find(_SUBS_SELECT_ID)
    if multiselect is not None:
        await multiselect.reset_checked()
    await manager.switch_to(AdminAddUser.choose_subscriptions)


def _target_label(user_id: int, username: str | None, full_name: str) -> str:
    if username:
        return f"@{username}"
    return full_name or str(user_id)


async def choose_subscriptions_getter(dialog_manager: DialogManager, **kwargs) -> dict:
    storage: Storage = dialog_manager.middleware_data["storage"]
    user_id = dialog_manager.dialog_data.get("target_user_id")
    target_user = await storage.users.get(user_id) if user_id is not None else None
    codes = await storage.codes.all()

    items = [{"id": c.code, "code": esc(c.code), "description": esc(c.description or "—")} for c in codes]
    name = (
        _target_label(user_id, target_user.username, target_user.full_name)
        if target_user is not None
        else str(user_id)
    )
    return {
        "id": str(user_id) if user_id is not None else "",
        "name": esc(name),
        "has_codes": bool(codes),
        "codes": items,
        "remnawave_available": dialog_manager.middleware_data.get("remnawave") is not None,
    }


async def open_link_remnawave(_callback: CallbackQuery, _button: Button, manager: DialogManager) -> None:
    if not await ensure_admin(manager):
        await leave_admin_area(manager)
        return
    user_id = manager.dialog_data.get("target_user_id")
    await manager.start(LinkRemnawave.enter_username, data={"user_id": user_id})


async def on_confirm(callback: CallbackQuery, _button: Button, manager: DialogManager) -> None:
    if not await ensure_admin(manager):
        await leave_admin_area(manager)
        return

    storage: Storage = manager.middleware_data["storage"]
    i18n = manager.middleware_data["i18n"]
    admin = manager.middleware_data["event_from_user"]
    user_id = manager.dialog_data.get("target_user_id")

    target_user = await storage.users.get(user_id)
    if target_user is None:
        # First contact with this id happens right here, on confirm - not
        # while the admin was still typing/could still Cancel - so
        # get_or_create()'s placeholder username/full_name only ever lands
        # in users.toml once the grant is actually going through.
        target_user = await storage.users.get_or_create(user_id, username=None, full_name="")

    multiselect = manager.find(_SUBS_SELECT_ID)
    codes = multiselect.get_checked()
    for code in codes:
        await storage.users.add_code(user_id, code)
    if codes:
        remnawave = manager.middleware_data.get("remnawave")
        await sync_remnawave_access(storage, remnawave, user_id)

    target = actor_id(user_id, target_user.username if target_user else None)
    logger.info("%s manually added user %s with subscriptions %s", actor(admin), target, codes)
    await callback.answer(popup_text(i18n, "admin-add-user-done", id=str(user_id), count=len(codes)), show_alert=True)
    await manager.done()


add_user_dialog = Dialog(
    build_field_window(
        IDENTIFIER_FIELD,
        AdminAddUser.enter_identifier,
        on_identifier_done,
        Cancel(I18N("admin-btn-cancel"), style=_CANCEL_STYLE),
    ),
    Window(
        Case(
            {
                True: I18N("admin-add-user-subs-title", id="{id}", name="{name}"),
                False: I18N("admin-add-user-subs-empty"),
            },
            selector="has_codes",
        ),
        Column(
            Multiselect(
                I18N("admin-add-user-sub-item", code="{item[code]}", description="{item[description]}"),
                I18N("admin-add-user-sub-item", code="{item[code]}", description="{item[description]}"),
                id=_SUBS_SELECT_ID,
                item_id_getter=lambda item: item["id"],
                items="codes",
                checked_style=icon("white_check_mark", ButtonStyle.SUCCESS),
                unchecked_style=icon("package"),
            ),
        ),
        Button(I18N("admin-btn-done"), id="confirm_subs", on_click=on_confirm, style=icon("white_check_mark", ButtonStyle.SUCCESS)),
        Button(
            I18N("admin-btn-link-remnawave"),
            id="link_remnawave",
            on_click=open_link_remnawave,
            when="remnawave_available",
            style=icon("shield"),
        ),
        SwitchTo(
            I18N("admin-btn-back"),
            id="back_to_identifier",
            state=AdminAddUser.enter_identifier,
            style=icon("arrow_backward"),
        ),
        state=AdminAddUser.choose_subscriptions,
        getter=choose_subscriptions_getter,
    ),
    on_start=on_dialog_start,
)
