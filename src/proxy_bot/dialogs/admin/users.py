from __future__ import annotations

import logging

from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery
from aiogram_dialog import Dialog, DialogManager, Window
from aiogram_dialog.widgets.kbd import Button, Cancel, Column, Row, Select
from aiogram_dialog.widgets.style.base import ButtonStyle
from aiogram_dialog.widgets.text import Case, Multi

from proxy_bot.storage import Storage
from proxy_bot.utils.audit import actor, actor_id
from proxy_bot.utils.html import esc

from ..common import icon
from ..widgets import I18N
from .access import ensure_admin, leave_admin_area


async def on_dialog_start(_start_data: object, manager: DialogManager) -> None:
    if not await ensure_admin(manager):
        await leave_admin_area(manager)


class AdminUsers(StatesGroup):
    list = State()
    detail = State()


# Ban/unban share one button slot whose icon+color follow the user's
# current state - unbanning (banned=True) reads as the positive action.
_BAN_TOGGLE_STYLE = icon("no_entry_sign", ButtonStyle.DANGER, when="not_banned") | icon(
    "white_check_mark", ButtonStyle.SUCCESS, when="banned"
)

logger = logging.getLogger(__name__)

PAGE_SIZE = 8


def _display_name(username: str | None, full_name: str, user_id: int) -> str:
    if username:
        return f"@{username}"
    return full_name or str(user_id)


async def users_list_getter(dialog_manager: DialogManager, **kwargs) -> dict:
    storage: Storage = dialog_manager.middleware_data["storage"]
    users = await storage.users.all()
    users.sort(key=lambda u: u.first_seen, reverse=True)

    total_pages = max(1, (len(users) + PAGE_SIZE - 1) // PAGE_SIZE)
    page = max(0, min(dialog_manager.dialog_data.get("page", 0), total_pages - 1))
    dialog_manager.dialog_data["page"] = page

    chunk = users[page * PAGE_SIZE : (page + 1) * PAGE_SIZE]
    items = [
        {
            "id": str(u.user_id),
            "name": esc(_display_name(u.username, u.full_name, u.user_id)),
            "count": len(u.codes),
        }
        for u in chunk
    ]
    return {
        "has_users": bool(users),
        "count": len(users),
        "has_pages": total_pages > 1,
        "page": page + 1,
        "total": total_pages,
        "users": items,
    }


async def on_user_selected(_callback: CallbackQuery, _select, manager: DialogManager, item_id: str) -> None:
    # item_id is a Select item id echoed back verbatim from callback_data,
    # not re-validated against the currently rendered user list - guard the
    # cast rather than assume it's still one of this window's own ids.
    try:
        selected_user_id = int(item_id)
    except ValueError:
        return
    manager.dialog_data["selected_user_id"] = selected_user_id
    await manager.switch_to(AdminUsers.detail)


async def on_prev_page(_callback: CallbackQuery, _button: Button, manager: DialogManager) -> None:
    manager.dialog_data["page"] = max(0, manager.dialog_data.get("page", 0) - 1)


async def on_next_page(_callback: CallbackQuery, _button: Button, manager: DialogManager) -> None:
    manager.dialog_data["page"] = manager.dialog_data.get("page", 0) + 1


async def users_detail_getter(dialog_manager: DialogManager, i18n, **kwargs) -> dict:
    storage: Storage = dialog_manager.middleware_data["storage"]
    user_id = dialog_manager.dialog_data.get("selected_user_id")
    user = await storage.users.get(user_id) if user_id is not None else None

    if user is None:
        return {"found": False, "banned": False, "not_banned": True}

    name = _display_name(user.username, user.full_name, user.user_id)
    codes = [{"id": code, "code": code} for code in user.codes]
    return {
        "found": True,
        "name": esc(name),
        "id": str(user.user_id),
        # Fed into `admin-user-detail-title`'s `$banned` var below - kept as
        # a python-side i18n.get() since it's a nested argument value, not
        # window text (a single I18N call can't itself embed another).
        "banned_label": i18n.get("yes") if user.banned else i18n.get("no"),
        "has_codes": bool(codes),
        "no_codes": not codes,
        "codes": codes,
        "banned": user.banned,
        "not_banned": not user.banned,
    }


async def on_revoke_code(callback: CallbackQuery, _select, manager: DialogManager, item_id: str) -> None:
    if not await ensure_admin(manager):
        await leave_admin_area(manager)
        return

    storage: Storage = manager.middleware_data["storage"]
    i18n = manager.middleware_data["i18n"]
    admin = manager.middleware_data["event_from_user"]
    user_id = manager.dialog_data.get("selected_user_id")

    removed = await storage.users.remove_code(user_id, item_id)
    if removed:
        target_user = await storage.users.get(user_id)
        target = actor_id(user_id, target_user.username if target_user else None)
        logger.info("%s revoked code %r from %s", actor(admin), item_id, target)
        await callback.answer(i18n.get("admin-user-revoke-done", code=item_id, id=str(user_id)), show_alert=True)


async def back_to_list(_callback: CallbackQuery, _button: Button, manager: DialogManager) -> None:
    await manager.switch_to(AdminUsers.list)


async def on_toggle_ban(callback: CallbackQuery, _button: Button, manager: DialogManager) -> None:
    if not await ensure_admin(manager):
        await leave_admin_area(manager)
        return

    storage: Storage = manager.middleware_data["storage"]
    i18n = manager.middleware_data["i18n"]
    admin = manager.middleware_data["event_from_user"]
    user_id = manager.dialog_data.get("selected_user_id")

    user = await storage.users.get(user_id)
    if user is None:
        return
    new_state = not user.banned
    # is_admin() doesn't consult the banned flag (see filters.IsAdmin), so
    # a banned admin would keep full panel access while only losing code
    # activation (activation.activate_code) - a confusing half-banned
    # state with no real security benefit. Refuse the ban transition for a
    # fellow admin instead; unbanning is always allowed.
    if new_state and await storage.admins.is_admin(user_id):
        await callback.answer(i18n.get("admin-user-ban-admin-denied"), show_alert=True)
        return
    await storage.users.set_banned(user_id, new_state)
    target = actor_id(user_id, user.username)
    action = "banned" if new_state else "unbanned"
    logger.info("%s %s %s", actor(admin), action, target)
    await callback.answer()


users_dialog = Dialog(
    Window(
        Case(
            {
                True: Multi(I18N("admin-users-title"), I18N("admin-page-indicator", when="has_pages"), sep=" "),
                False: I18N("admin-users-empty"),
            },
            selector="has_users",
        ),
        Column(
            Select(
                I18N("admin-users-item", name="{item[name]}", id="{item[id]}", count="{item[count]}"),
                id="user_select",
                item_id_getter=lambda item: item["id"],
                items="users",
                on_click=on_user_selected,
                style=icon("bust_in_silhouette"),
            ),
        ),
        Row(
            Button(I18N("admin-btn-prev"), id="prev_page", on_click=on_prev_page, style=icon("chevron_left")),
            Button(I18N("admin-btn-next"), id="next_page", on_click=on_next_page, style=icon("chevron_right")),
        ),
        Cancel(I18N("admin-btn-back"), style=icon("arrow_backward")),
        state=AdminUsers.list,
        getter=users_list_getter,
    ),
    Window(
        Case(
            {
                True: Multi(
                    I18N("admin-user-detail-title", banned="{banned_label}"),
                    I18N("admin-user-codes-none", when="no_codes"),
                    sep="\n\n",
                ),
                False: I18N("admin-users-empty"),
            },
            selector="found",
        ),
        Column(
            Select(
                I18N("admin-user-revoke-btn", code="{item[code]}"),
                id="revoke_select",
                item_id_getter=lambda item: item["id"],
                items="codes",
                on_click=on_revoke_code,
                style=icon("x", ButtonStyle.DANGER),
            ),
        ),
        Button(
            Case({True: I18N("admin-user-unban-btn"), False: I18N("admin-user-ban-btn")}, selector="banned"),
            id="toggle_ban",
            on_click=on_toggle_ban,
            when="found",
            style=_BAN_TOGGLE_STYLE,
        ),
        Button(I18N("admin-btn-back"), id="back_to_list", on_click=back_to_list, style=icon("arrow_backward")),
        state=AdminUsers.detail,
        getter=users_detail_getter,
    ),
    on_start=on_dialog_start,
)
