from __future__ import annotations

import logging

from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery
from aiogram_dialog import Dialog, DialogManager, Window
from aiogram_dialog.widgets.kbd import Button, Cancel, Column, Row, Select, SwitchTo
from aiogram_dialog.widgets.style.base import ButtonStyle
from aiogram_dialog.widgets.text import Case, Format, List, Multi

from proxy_bot.remnawave import RemnawaveError
from proxy_bot.services.remnawave_sync import sync_remnawave_access
from proxy_bot.storage import Storage
from proxy_bot.utils.audit import actor, actor_id
from proxy_bot.utils.formatting import display_name
from proxy_bot.utils.html import esc
from proxy_bot.utils.i18n import popup_text
from proxy_bot.utils.subscription_display import fetch_subscription_lines

from ..common import icon
from ..widgets import I18N
from .access import ensure_admin, leave_admin_area
from .add_user import AdminAddUser
from .link_remnawave import LinkRemnawave


async def on_dialog_start(_start_data: object, manager: DialogManager) -> None:
    if not await ensure_admin(manager):
        await leave_admin_area(manager)


class AdminUsers(StatesGroup):
    list = State()
    detail = State()
    subscriptions = State()


# Ban/unban share one button slot whose icon+color follow the user's
# current state - unbanning (banned=True) reads as the positive action.
_BAN_TOGGLE_STYLE = icon("no_entry_sign", ButtonStyle.DANGER, when="not_banned") | icon(
    "white_check_mark", ButtonStyle.SUCCESS, when="banned"
)
# Same pattern for the Remnawave-integration disable/enable toggle.
_REMNAWAVE_TOGGLE_STYLE = icon("no_entry_sign", ButtonStyle.DANGER, when="remnawave_not_disabled") | icon(
    "white_check_mark", ButtonStyle.SUCCESS, when="remnawave_disabled"
)

logger = logging.getLogger(__name__)

PAGE_SIZE = 8
# A user's subscription list gets its own paginated submenu (rather than
# being inlined into the detail window, like the old design) precisely
# because it has no upper bound - an admin who's granted a lot of codes to
# one user would otherwise blow the detail window's button list wide open.
SUB_PAGE_SIZE = 8


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
            "name": esc(display_name(u.username, u.full_name, u.user_id)),
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


async def open_add_user(_callback: CallbackQuery, _button: Button, manager: DialogManager) -> None:
    if not await ensure_admin(manager):
        await leave_admin_area(manager)
        return
    await manager.start(AdminAddUser.enter_identifier)


async def open_link_remnawave(_callback: CallbackQuery, _select, manager: DialogManager, item_id: str) -> None:
    if not await ensure_admin(manager):
        await leave_admin_area(manager)
        return
    user_id = manager.dialog_data.get("selected_user_id")
    await manager.start(LinkRemnawave.enter_username, data={"user_id": user_id, "server": item_id})


async def on_unlink_remnawave(callback: CallbackQuery, _select, manager: DialogManager, item_id: str) -> None:
    if not await ensure_admin(manager):
        await leave_admin_area(manager)
        return

    storage: Storage = manager.middleware_data["storage"]
    i18n = manager.middleware_data["i18n"]
    admin = manager.middleware_data["event_from_user"]
    user_id = manager.dialog_data.get("selected_user_id")
    server = item_id

    user = await storage.users.get(user_id)
    if user is None:
        return

    # Clears the manual link, not the account itself - if the user still
    # holds a squad-granting code on this server, sync_remnawave_access
    # below immediately re-matches the same account (by telegram id) and
    # re-marks it auto, rather than leaving them with no account at all.
    await storage.users.set_remnawave_account(user_id, server, None, None, None, manual=False)
    remnawave = manager.middleware_data.get("remnawave")
    await sync_remnawave_access(storage, remnawave, user_id)

    target = actor_id(user_id, user.username)
    logger.info("%s unlinked Remnawave account on server %r from %s", actor(admin), server, target)
    await callback.answer(popup_text(i18n, "admin-user-remnawave-unlinked-done", id=str(user_id)), show_alert=True)


async def on_toggle_remnawave_disabled(callback: CallbackQuery, _button: Button, manager: DialogManager) -> None:
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

    new_state = not user.remnawave_disabled
    await storage.users.set_remnawave_disabled(user_id, new_state)
    remnawave = manager.middleware_data.get("remnawave")
    await sync_remnawave_access(storage, remnawave, user_id)

    target = actor_id(user_id, user.username)
    action = "disabled" if new_state else "enabled"
    logger.info("%s %s Remnawave integration for %s", actor(admin), action, target)
    popup_key = "admin-user-remnawave-disabled-done" if new_state else "admin-user-remnawave-enabled-done"
    await callback.answer(popup_text(i18n, popup_key, id=str(user_id)), show_alert=True)


async def on_prev_page(_callback: CallbackQuery, _button: Button, manager: DialogManager) -> None:
    manager.dialog_data["page"] = max(0, manager.dialog_data.get("page", 0) - 1)


async def on_next_page(_callback: CallbackQuery, _button: Button, manager: DialogManager) -> None:
    manager.dialog_data["page"] = manager.dialog_data.get("page", 0) + 1


async def _account_rows_and_server_choices(
    dialog_manager: DialogManager, i18n, user, remnawave
) -> tuple[list[str], list[dict], list[dict]]:
    """Per-server Remnawave state for the user-detail screen: one rendered
    line per account with its own expiry/traffic (account_rows - empty
    while user.remnawave_disabled, mirroring the old single-account
    behavior of showing no Remnawave info at all when disabled), and the
    server lists driving the Link/Unlink Select rows. A server offers
    "Link" unless its account is already manually linked (so an admin can
    always force-link a different account over an auto-matched one), and
    "Unlink" only when it is - same per-server as the old single-account
    show_link_remnawave/show_unlink_remnawave split."""
    show_traffic = dialog_manager.middleware_data.get("show_traffic_usage", False)
    account_rows: list[str] = []
    link_servers: list[dict] = []
    unlink_servers: list[dict] = []
    for server in remnawave.names():
        account = user.remnawave_accounts.get(server)
        manually_linked = account is not None and account.linked_manually
        (unlink_servers if manually_linked else link_servers).append({"id": server, "name": esc(server)})
        if account is None or user.remnawave_disabled:
            continue
        subscription_info = await fetch_subscription_lines(
            remnawave.get(server), account.uuid, i18n, show_traffic=show_traffic
        )
        source = i18n.get(
            "admin-user-remnawave-link-source-manual" if account.linked_manually else "admin-user-remnawave-link-source-auto"
        )
        row = i18n.get(
            "admin-user-remnawave-linked",
            server=esc(server),
            username=esc(account.username) if account.username else "—",
            source=source,
        )
        # subscription_info's expiry/traffic are their own already-rendered
        # lines (see fetch_subscription_lines) - appended only when present,
        # same as the plain-string equivalent of _DETAIL_CONTENT's separate
        # Format("{expiry}")/Format("{traffic}") widgets skipping an empty
        # render, so a disabled-traffic deployment doesn't get a blank line.
        row = "\n".join(part for part in (row, *(subscription_info or {}).values()) if part)
        account_rows.append(row)
    return account_rows, link_servers, unlink_servers


async def users_detail_getter(dialog_manager: DialogManager, i18n, **kwargs) -> dict:
    storage: Storage = dialog_manager.middleware_data["storage"]
    user_id = dialog_manager.dialog_data.get("selected_user_id")
    user = await storage.users.get(user_id) if user_id is not None else None

    if user is None:
        return {"found": False, "banned": False, "not_banned": True}

    name = display_name(user.username, user.full_name, user.user_id)
    remnawave = dialog_manager.middleware_data.get("remnawave")
    remnawave_available = remnawave is not None

    account_rows: list[str] = []
    link_servers: list[dict] = []
    unlink_servers: list[dict] = []
    if remnawave_available:
        account_rows, link_servers, unlink_servers = await _account_rows_and_server_choices(
            dialog_manager, i18n, user, remnawave
        )

    return {
        "found": True,
        "name": esc(name),
        "id": str(user.user_id),
        # Fed into `admin-user-detail-title`'s `$banned` var below - kept as
        # a python-side i18n.get() since it's a nested argument value, not
        # window text (a single I18N call can't itself embed another).
        "banned_label": i18n.get("yes") if user.banned else i18n.get("no"),
        "has_codes": bool(user.codes),
        "no_codes": not user.codes,
        "codes_count": len(user.codes),
        "banned": user.banned,
        "not_banned": not user.banned,
        "remnawave_available": remnawave_available,
        "has_account_rows": bool(account_rows),
        "account_rows": account_rows,
        "link_servers": link_servers,
        "has_link_servers": bool(link_servers),
        "unlink_servers": unlink_servers,
        "has_unlink_servers": bool(unlink_servers),
        "remnawave_disabled": user.remnawave_disabled,
        "remnawave_not_disabled": not user.remnawave_disabled,
    }


async def open_subscriptions(_callback: CallbackQuery, _button: Button, manager: DialogManager) -> None:
    manager.dialog_data["sub_page"] = 0
    await manager.switch_to(AdminUsers.subscriptions)


async def on_sub_prev_page(_callback: CallbackQuery, _button: Button, manager: DialogManager) -> None:
    manager.dialog_data["sub_page"] = max(0, manager.dialog_data.get("sub_page", 0) - 1)


async def on_sub_next_page(_callback: CallbackQuery, _button: Button, manager: DialogManager) -> None:
    manager.dialog_data["sub_page"] = manager.dialog_data.get("sub_page", 0) + 1


async def user_subscriptions_getter(dialog_manager: DialogManager, **kwargs) -> dict:
    storage: Storage = dialog_manager.middleware_data["storage"]
    user_id = dialog_manager.dialog_data.get("selected_user_id")
    user = await storage.users.get(user_id) if user_id is not None else None
    codes = list(user.codes) if user is not None else []

    total_pages = max(1, (len(codes) + SUB_PAGE_SIZE - 1) // SUB_PAGE_SIZE)
    page = max(0, min(dialog_manager.dialog_data.get("sub_page", 0), total_pages - 1))
    dialog_manager.dialog_data["sub_page"] = page

    chunk = codes[page * SUB_PAGE_SIZE : (page + 1) * SUB_PAGE_SIZE]
    return {
        "id": str(user_id) if user_id is not None else "",
        "has_codes": bool(codes),
        "count": len(codes),
        "has_pages": total_pages > 1,
        "page": page + 1,
        "total": total_pages,
        "codes": [{"id": code, "code": code} for code in chunk],
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
        remnawave = manager.middleware_data.get("remnawave")
        await sync_remnawave_access(storage, remnawave, user_id)
        target_user = await storage.users.get(user_id)
        target = actor_id(user_id, target_user.username if target_user else None)
        logger.info("%s revoked code %r from %s", actor(admin), item_id, target)
        await callback.answer(popup_text(i18n, "admin-user-revoke-done", code=item_id, id=str(user_id)), show_alert=True)


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
        await callback.answer(popup_text(i18n, "admin-user-ban-admin-denied"), show_alert=True)
        return
    await storage.users.set_banned(user_id, new_state)
    target = actor_id(user_id, user.username)
    action = "banned" if new_state else "unbanned"
    logger.info("%s %s %s", actor(admin), action, target)

    # Push the ban/unban straight through to every linked Remnawave account
    # (one per server) - the reverse direction (a panel-side status change
    # flowing back into `banned`) is handled by the periodic sweep in
    # services.remnawave_sync, since nothing here would learn about an
    # out-of-band panel edit.
    remnawave = manager.middleware_data.get("remnawave")
    if remnawave is not None:
        for server, account in user.remnawave_accounts.items():
            client = remnawave.get(server)
            if client is None or not account.uuid:
                continue
            try:
                if new_state:
                    await client.disable_user(account.uuid)
                else:
                    await client.enable_user(account.uuid)
            except RemnawaveError:
                logger.warning("Failed to push ban state to Remnawave (server %r) for %s", server, target, exc_info=True)

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
        Button(I18N("admin-btn-add-user"), id="add_user", on_click=open_add_user, style=icon("heavy_plus_sign")),
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
                    List(Format("{item}"), items="account_rows", sep="\n\n", when="has_account_rows"),
                    sep="\n\n",
                ),
                False: I18N("admin-users-empty"),
            },
            selector="found",
        ),
        Button(
            I18N("admin-btn-subscriptions", count="{codes_count}"),
            id="open_subscriptions",
            on_click=open_subscriptions,
            when="has_codes",
            style=icon("key"),
        ),
        Button(
            Case({True: I18N("admin-user-unban-btn"), False: I18N("admin-user-ban-btn")}, selector="banned"),
            id="toggle_ban",
            on_click=on_toggle_ban,
            when="found",
            style=_BAN_TOGGLE_STYLE,
        ),
        Column(
            Select(
                I18N("admin-btn-link-remnawave-server", server="{item[name]}"),
                id="link_remnawave_select",
                item_id_getter=lambda item: item["id"],
                items="link_servers",
                on_click=open_link_remnawave,
                style=icon("shield"),
            ),
            when="has_link_servers",
        ),
        Column(
            Select(
                I18N("admin-btn-unlink-remnawave-server", server="{item[name]}"),
                id="unlink_remnawave_select",
                item_id_getter=lambda item: item["id"],
                items="unlink_servers",
                on_click=on_unlink_remnawave,
                style=icon("shield", ButtonStyle.DANGER),
            ),
            when="has_unlink_servers",
        ),
        Button(
            Case(
                {True: I18N("admin-btn-enable-remnawave"), False: I18N("admin-btn-disable-remnawave")},
                selector="remnawave_disabled",
            ),
            id="toggle_remnawave_disabled",
            on_click=on_toggle_remnawave_disabled,
            when="remnawave_available",
            style=_REMNAWAVE_TOGGLE_STYLE,
        ),
        Button(I18N("admin-btn-back"), id="back_to_list", on_click=back_to_list, style=icon("arrow_backward")),
        state=AdminUsers.detail,
        getter=users_detail_getter,
    ),
    Window(
        Case(
            {
                True: Multi(
                    I18N("admin-user-subscriptions-title", id="{id}", count="{count}"),
                    I18N("admin-page-indicator", when="has_pages"),
                    sep=" ",
                ),
                False: I18N("admin-user-codes-none"),
            },
            selector="has_codes",
        ),
        Column(
            Select(
                I18N("admin-user-revoke-btn", code="{item[code]}"),
                id="sub_revoke_select",
                item_id_getter=lambda item: item["id"],
                items="codes",
                on_click=on_revoke_code,
                style=icon("x", ButtonStyle.DANGER),
            ),
        ),
        Row(
            Button(I18N("admin-btn-prev"), id="sub_prev_page", on_click=on_sub_prev_page, style=icon("chevron_left")),
            Button(I18N("admin-btn-next"), id="sub_next_page", on_click=on_sub_next_page, style=icon("chevron_right")),
        ),
        SwitchTo(I18N("admin-btn-back"), id="back_to_detail_from_subs", state=AdminUsers.detail, style=icon("arrow_backward")),
        state=AdminUsers.subscriptions,
        getter=user_subscriptions_getter,
    ),
    on_start=on_dialog_start,
)
