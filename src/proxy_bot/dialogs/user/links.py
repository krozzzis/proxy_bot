from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup
from aiogram_dialog import Dialog, DialogManager, Window
from aiogram_dialog.widgets.kbd import Button, Cancel, Column, Select, SwitchTo
from aiogram_dialog.widgets.style.base import ButtonStyle
from aiogram_dialog.widgets.text import Case, Format, Multi

from proxy_bot.storage import Storage
from proxy_bot.storage.models import Code, User
from proxy_bot.utils.formatting import format_links
from proxy_bot.utils.html import esc
from proxy_bot.utils.subscription_display import fetch_subscription_lines

from ..common import BRANDED_LOGO_MEDIA, branded_logo_getter, icon
from ..widgets import I18N
from .enter_code import EnterCode


class Links(StatesGroup):
    main = State()
    detail = State()


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


async def _build_detail(
    db_user: User, code_record: Code, subscription_info: dict[str, str] | None
) -> dict[str, str]:
    links = list(code_record.links)
    # An admin's remnawave_disabled override (per-code or per-user) hides
    # the Remnawave link/expiry/traffic here even though the account itself
    # (and its squad grant, if any) is left untouched - see
    # services.remnawave_sync.compute_remnawave_squads.
    remnawave_active = not code_record.remnawave_disabled and not db_user.remnawave_disabled
    has_remnawave = bool(code_record.remnawave_squads) and remnawave_active and subscription_info is not None
    if code_record.remnawave_squads and remnawave_active and db_user.remnawave_subscription_url:
        links.append(db_user.remnawave_subscription_url)
    return {
        "code": esc(code_record.code),
        "description": esc(code_record.description or code_record.code),
        "links": format_links(links),
        "expiry": subscription_info["expiry"] if has_remnawave else "",
        "traffic": subscription_info["traffic"] if has_remnawave else "",
        "banned": db_user.banned,
    }


async def _subscription_info(dialog_manager: DialogManager, db_user: User, i18n) -> dict[str, str] | None:
    remnawave = dialog_manager.middleware_data.get("remnawave")
    show_traffic = dialog_manager.middleware_data.get("show_traffic_usage", False)
    return await fetch_subscription_lines(remnawave, db_user.remnawave_uuid, i18n, show_traffic=show_traffic)


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
        subscription_info = await _subscription_info(dialog_manager, db_user, i18n)
        base.update(await _build_detail(db_user, code_records[0], subscription_info))
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

    subscription_info = await _subscription_info(dialog_manager, db_user, i18n)
    return await _build_detail(db_user, code_record, subscription_info)


async def open_enter_code(_callback, _button, manager: DialogManager) -> None:
    await manager.start(EnterCode.main)


async def on_code_selected(_callback, _select, manager: DialogManager, item_id: str) -> None:
    manager.dialog_data["selected_code"] = item_id
    await manager.switch_to(Links.detail)


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
                style=icon("small_blue_diamond"),
            ),
            when="multi",
        ),
        Button(
            I18N("menu-btn-enter-code"),
            id="open_enter_code_from_links",
            on_click=open_enter_code,
            style=icon("heavy_plus_sign", ButtonStyle.PRIMARY),
        ),
        Cancel(I18N("menu-btn-back"), style=icon("arrow_backward")),
        state=Links.main,
        getter=[links_getter, branded_logo_getter],
    ),
    Window(
        BRANDED_LOGO_MEDIA,
        _DETAIL_CONTENT,
        SwitchTo(I18N("menu-btn-back"), id="back_to_list", state=Links.main, style=icon("arrow_backward")),
        state=Links.detail,
        getter=[detail_getter, branded_logo_getter],
    ),
    on_start=on_start,
    on_process_result=on_enter_code_result,
)
