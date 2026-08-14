from __future__ import annotations

import logging

from aiogram.fsm.state import State, StatesGroup
from aiogram_dialog import Dialog, DialogManager, Window
from aiogram_dialog.widgets.kbd import Button, Cancel, Column, Select, SwitchTo
from aiogram_dialog.widgets.style.base import ButtonStyle
from aiogram_dialog.widgets.text import Case, Format, Multi

from proxy_bot.services.remnawave_sync import sync_remnawave_access
from proxy_bot.storage import Storage
from proxy_bot.storage.models import LINK_TYPE_FIX, LINK_TYPE_REMNAWAVE, Code, RemnawaveAccount, User
from proxy_bot.utils.audit import actor
from proxy_bot.utils.formatting import format_links
from proxy_bot.utils.html import esc
from proxy_bot.utils.subscription_display import fetch_subscription_lines

from ..common import BRANDED_LOGO_MEDIA, branded_logo_getter, icon
from ..widgets import I18N
from .enter_code import EnterCode

logger = logging.getLogger(__name__)


class Links(StatesGroup):
    main = State()
    detail = State()
    confirm_unsubscribe = State()


# Shared between Links.main (inline, when there's exactly one code - no
# point sending a user to a list of one) and Links.detail (reached via a
# button when there are several) - both getters below produce the same
# top-level keys (code/description/expiry/traffic/links), so this same
# widget renders either way without knowing which state it's in. Includes
# its own "Ваши подписки" title (link-header) rather than relying on an
# outer wrapper to supply it, since Links.detail is a separate Window with
# no such wrapper of its own.
_DETAIL_CONTENT = Multi(
    I18N("link-header"),
    I18N("link-banned-notice", when="banned"),
    I18N("link-detail-header", code="{code}", description="{description}"),
    Format("{expiry}"),
    Format("{traffic}"),
    Format("{links}"),
    I18N("link-help-hint"),
    sep="\n\n",
)


async def on_start(start_data: object, dialog_manager: DialogManager) -> None:
    if isinstance(start_data, dict) and start_data.get("banner"):
        dialog_manager.dialog_data["banner"] = start_data["banner"]


async def on_enter_code_result(_start_data: object, result: object, manager: DialogManager) -> None:
    # enter_code hands back {"banner": ...} on a successful activation - it
    # was opened from this very screen, so done() already returns here and
    # re-reads the (now updated) code list; stashing the banner just adds
    # the confirmation to that same re-render instead of a message of its own.
    if isinstance(result, dict) and result.get("banner"):
        manager.dialog_data["banner"] = result["banner"]


async def _remnawave_target(storage: Storage, db_user: User, squad_id: str) -> tuple[str, RemnawaveAccount] | None:
    """The (server, account) a `remnawave`-type link's `squad_id` resolves
    to for this holder - None if there's nothing to point at: no
    `squad_id`, a since-deleted Squad, or no account on that Squad's
    server yet (see storage.models.Link)."""
    if not squad_id:
        return None
    squad = await storage.squads.get(squad_id)
    if squad is None:
        return None
    account = db_user.remnawave_accounts.get(squad.server)
    if account is None or not account.subscription_url:
        return None
    return squad.server, account


async def _build_detail(dialog_manager: DialogManager, db_user: User, code_record: Code, i18n) -> dict[str, str]:
    # An admin's remnawave_disabled override (per-code or per-user) hides
    # every Remnawave link/expiry/traffic here even though the underlying
    # accounts (and their squad grants, if any) are left untouched - see
    # services.remnawave_sync.compute_remnawave_grants.
    remnawave_active = not code_record.remnawave_disabled and not db_user.remnawave_disabled
    storage: Storage = dialog_manager.middleware_data["storage"]
    remnawave = dialog_manager.middleware_data.get("remnawave")
    show_traffic = dialog_manager.middleware_data.get("show_traffic_usage", False)

    # Resolve each remnawave-type link's target up front - a code can now
    # carry several, each attached to its own Squad (possibly on a
    # different server), so each one may point at a different holder
    # account.
    targets: dict[int, tuple[str, RemnawaveAccount]] = {}
    if remnawave_active and remnawave is not None:
        for idx, link in enumerate(code_record.links):
            if link.type != LINK_TYPE_REMNAWAVE or link.disabled:
                continue
            target = await _remnawave_target(storage, db_user, link.squad_id)
            if target is not None:
                targets[idx] = target

    # Confirmed UX: at most one distinct account among this code's
    # remnawave links (the common case - one server, or several Squads on
    # the same server) keeps the old single aggregated expiry/traffic
    # block. Two or more distinct accounts means no single "the" expiry to
    # show up top - each link instead carries its own expiry inline (see
    # format_links's `suffix`), and traffic is dropped entirely rather than
    # picking one account's number to represent all of them.
    distinct_servers = {server for server, _ in targets.values()}
    aggregate_mode = len(distinct_servers) <= 1

    aggregate_info: dict[str, str] | None = None
    if aggregate_mode and targets:
        server, account = next(iter(targets.values()))
        aggregate_info = await fetch_subscription_lines(remnawave.get(server), account.uuid, i18n, show_traffic=show_traffic)

    entries: list[tuple[str, str, str]] = []
    for idx, link in enumerate(code_record.links):
        if link.disabled:
            continue
        if link.type == LINK_TYPE_FIX:
            entries.append((link.name, link.url, ""))
            continue
        target = targets.get(idx)
        if target is None:
            continue
        server, account = target
        suffix = ""
        if not aggregate_mode:
            # Traffic stays aggregate-only per the confirmed UX - only the
            # expiry line is worth repeating per link.
            info = await fetch_subscription_lines(remnawave.get(server), account.uuid, i18n, show_traffic=False)
            suffix = info["expiry"] if info else ""
        entries.append((link.name, account.subscription_url, suffix))

    show_aggregate = aggregate_mode and aggregate_info is not None
    return {
        "code": esc(code_record.code),
        "description": esc(code_record.description or code_record.code),
        "links": format_links(entries),
        "expiry": aggregate_info["expiry"] if show_aggregate else "",
        "traffic": aggregate_info["traffic"] if show_aggregate else "",
        "banned": db_user.banned,
    }


async def links_getter(dialog_manager: DialogManager, i18n, **kwargs) -> dict:
    storage: Storage = dialog_manager.middleware_data["storage"]
    user = dialog_manager.middleware_data["event_from_user"]
    db_user = await storage.users.get_or_create(user.id, user.username, user.full_name)

    code_records = []
    for code in db_user.codes:
        code_record = await storage.codes.get(code)
        if code_record is not None:
            code_records.append(code_record)

    base = {
        "banner": dialog_manager.dialog_data.pop("banner", None),
        "banned": db_user.banned,
        "has_links": bool(code_records),
        "no_links": not code_records,
        "single": len(code_records) == 1,
        "multi": len(code_records) > 1,
        "codes": [],
    }

    if len(code_records) == 1:
        base.update(await _build_detail(dialog_manager, db_user, code_records[0], i18n))
    elif code_records:
        base["codes"] = [{"id": cr.code, "code": esc(cr.code)} for cr in code_records]

    return base


async def detail_getter(dialog_manager: DialogManager, i18n, **kwargs) -> dict:
    storage: Storage = dialog_manager.middleware_data["storage"]
    user = dialog_manager.middleware_data["event_from_user"]
    db_user = await storage.users.get_or_create(user.id, user.username, user.full_name)

    code_id = dialog_manager.dialog_data.get("selected_code")
    code_record = await storage.codes.get(code_id) if code_id else None
    if code_record is None or code_id not in db_user.codes:
        # Revoked or renamed out from under this open message between
        # render and click - bounce back to the list rather than show a
        # detail view for a code this user no longer (or never did) hold.
        await dialog_manager.switch_to(Links.main)
        return {"code": "", "description": "", "links": "", "expiry": "", "traffic": "", "banned": False}

    return await _build_detail(dialog_manager, db_user, code_record, i18n)


async def open_enter_code(_callback, _button, manager: DialogManager) -> None:
    await manager.start(EnterCode.main)


async def on_code_selected(_callback, _select, manager: DialogManager, item_id: str) -> None:
    manager.dialog_data["selected_code"] = item_id
    await manager.switch_to(Links.detail)


async def on_open_unsubscribe_from_main(_callback, _button, manager: DialogManager) -> None:
    # Links.main only ever shows the "Unsubscribe" button under
    # `when="single"` (see links_getter), so there's exactly one held code
    # to target - re-derive it the same filtered way links_getter does
    # (a code since deleted from codes.toml doesn't count) rather than
    # trusting db_user.codes[0], which could point at a stale/gone one.
    storage: Storage = manager.middleware_data["storage"]
    user = manager.middleware_data["event_from_user"]
    db_user = await storage.users.get_or_create(user.id, user.username, user.full_name)
    live_codes = [code for code in db_user.codes if await storage.codes.get(code) is not None]
    if len(live_codes) != 1:
        return
    manager.dialog_data["unsubscribe_code"] = live_codes[0]
    await manager.switch_to(Links.confirm_unsubscribe)


async def on_open_unsubscribe_from_detail(_callback, _button, manager: DialogManager) -> None:
    code_id = manager.dialog_data.get("selected_code")
    if not code_id:
        return
    manager.dialog_data["unsubscribe_code"] = code_id
    await manager.switch_to(Links.confirm_unsubscribe)


async def confirm_unsubscribe_getter(dialog_manager: DialogManager, **kwargs) -> dict:
    storage: Storage = dialog_manager.middleware_data["storage"]
    user = dialog_manager.middleware_data["event_from_user"]
    db_user = await storage.users.get_or_create(user.id, user.username, user.full_name)

    code_id = dialog_manager.dialog_data.get("unsubscribe_code")
    code_record = await storage.codes.get(code_id) if code_id else None
    if code_record is None or code_id not in db_user.codes:
        # Revoked, renamed, or already given up between render and click -
        # same bounce-to-list guard as detail_getter.
        await dialog_manager.switch_to(Links.main)
        return {"code": "", "description": ""}

    return {
        "code": esc(code_record.code),
        "description": esc(code_record.description or code_record.code),
    }


async def on_confirm_unsubscribe(_callback, _button, manager: DialogManager) -> None:
    storage: Storage = manager.middleware_data["storage"]
    user = manager.middleware_data["event_from_user"]
    code_id = manager.dialog_data.pop("unsubscribe_code", None)
    if not code_id:
        await manager.switch_to(Links.main)
        return

    if await storage.users.remove_code(user.id, code_id):
        remnawave = manager.middleware_data.get("remnawave")
        await sync_remnawave_access(storage, remnawave, user.id)
        logger.info("%s gave up their own code %r", actor(user), code_id)
        manager.dialog_data["banner"] = "link-unsubscribed-done"
    manager.dialog_data.pop("selected_code", None)
    await manager.switch_to(Links.main)


async def on_cancel_unsubscribe(_callback, _button, manager: DialogManager) -> None:
    manager.dialog_data.pop("unsubscribe_code", None)
    await manager.switch_to(Links.main)


links_dialog = Dialog(
    Window(
        BRANDED_LOGO_MEDIA,
        Multi(
            I18N("{banner}", when="banner"),
            Case(
                {
                    True: _DETAIL_CONTENT,
                    False: Multi(
                        I18N("link-header"),
                        I18N("link-banned-notice", when="banned"),
                        I18N("link-choose-prompt"),
                        sep="\n\n",
                    ),
                },
                selector="single",
                when="has_links",
            ),
            Multi(I18N("link-banned-notice", when="banned"), I18N("link-none"), sep="\n\n", when="no_links"),
            sep="\n\n",
        ),
        Column(
            Select(
                Format("{item[code]}"),
                id="code_select",
                item_id_getter=lambda item: item["id"],
                items="codes",
                on_click=on_code_selected,
                style=icon("rocket"),
            ),
            when="multi",
        ),
        Button(
            I18N("menu-btn-enter-code"),
            id="open_enter_code_from_links",
            on_click=open_enter_code,
            style=icon("heavy_plus_sign", ButtonStyle.PRIMARY),
        ),
        Button(
            I18N("link-btn-unsubscribe"),
            id="open_unsubscribe_from_main",
            on_click=on_open_unsubscribe_from_main,
            when="single",
            style=icon("no_entry_sign", ButtonStyle.DANGER),
        ),
        Cancel(I18N("menu-btn-back"), style=icon("arrow_backward")),
        state=Links.main,
        getter=[links_getter, branded_logo_getter],
    ),
    Window(
        BRANDED_LOGO_MEDIA,
        _DETAIL_CONTENT,
        Button(
            I18N("link-btn-unsubscribe"),
            id="open_unsubscribe_from_detail",
            on_click=on_open_unsubscribe_from_detail,
            style=icon("no_entry_sign", ButtonStyle.DANGER),
        ),
        SwitchTo(I18N("menu-btn-back"), id="back_to_list", state=Links.main, style=icon("arrow_backward")),
        state=Links.detail,
        getter=[detail_getter, branded_logo_getter],
    ),
    Window(
        BRANDED_LOGO_MEDIA,
        I18N("link-unsubscribe-confirm", code="{code}", description="{description}"),
        Button(
            I18N("link-btn-unsubscribe-confirm"),
            id="confirm_unsubscribe",
            on_click=on_confirm_unsubscribe,
            style=icon("no_entry_sign", ButtonStyle.DANGER),
        ),
        Button(
            I18N("link-btn-unsubscribe-cancel"),
            id="cancel_unsubscribe",
            on_click=on_cancel_unsubscribe,
            style=icon("arrow_backward"),
        ),
        state=Links.confirm_unsubscribe,
        getter=[confirm_unsubscribe_getter, branded_logo_getter],
    ),
    on_start=on_start,
    on_process_result=on_enter_code_result,
)
