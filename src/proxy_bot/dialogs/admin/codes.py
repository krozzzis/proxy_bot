from __future__ import annotations

import logging

from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery
from aiogram_dialog import Dialog, DialogManager, Window
from aiogram_dialog.widgets.kbd import Button, Cancel, Column, Multiselect, Row, Select, SwitchTo
from aiogram_dialog.widgets.style.base import ButtonStyle
from aiogram_dialog.widgets.text import Case, Format, List, Multi
from pydantic import TypeAdapter

from proxy_bot.remnawave import RemnawaveError
from proxy_bot.services.remnawave_sync import sync_remnawave_access
from proxy_bot.storage import Storage
from proxy_bot.storage.models import LINK_TYPE_FIX, LINK_TYPE_REMNAWAVE, Link
from proxy_bot.utils.audit import actor
from proxy_bot.utils.html import esc
from proxy_bot.utils.i18n import popup_text

from ..common import icon
from ..forms import FormField, build_field_window
from ..widgets import I18N
from .access import ensure_admin, leave_admin_area
from .create_code import _CODE_ADAPTER, AdminCreateCode
from .links_common import has_remnawave_link, link_row

logger = logging.getLogger(__name__)

_CODE_SQUADS_SELECT_ID = "code_squads_select"

# Same pattern as dialogs.admin.users._REMNAWAVE_TOGGLE_STYLE.
_REMNAWAVE_TOGGLE_STYLE = icon("no_entry_sign", ButtonStyle.DANGER, when="remnawave_not_disabled") | icon(
    "white_check_mark", ButtonStyle.SUCCESS, when="remnawave_disabled"
)


async def on_dialog_start(_start_data: object, manager: DialogManager) -> None:
    if not await ensure_admin(manager):
        await leave_admin_area(manager)


class AdminCodes(StatesGroup):
    list = State()
    detail = State()
    links = State()
    enter_link = State()
    enter_link_name = State()
    edit_description = State()
    edit_squads = State()
    edit_code = State()

PAGE_SIZE = 8


async def codes_list_getter(dialog_manager: DialogManager, **kwargs) -> dict:
    storage: Storage = dialog_manager.middleware_data["storage"]
    codes = await storage.codes.all()
    codes.sort(key=lambda c: c.created_at, reverse=True)

    total_pages = max(1, (len(codes) + PAGE_SIZE - 1) // PAGE_SIZE)
    page = max(0, min(dialog_manager.dialog_data.get("page", 0), total_pages - 1))
    dialog_manager.dialog_data["page"] = page

    chunk = codes[page * PAGE_SIZE : (page + 1) * PAGE_SIZE]
    items = [
        {
            "id": c.code,
            "code": c.code,
            "description": esc(c.description or "—"),
            "count": len(c.links),
        }
        for c in chunk
    ]
    return {
        "has_codes": bool(codes),
        "count": len(codes),
        "has_pages": total_pages > 1,
        "page": page + 1,
        "total": total_pages,
        "codes": items,
        **dialog_manager.dialog_data.pop("banner_args", {"banner": None}),
    }


async def on_child_result(_start_data: object, result: object, manager: DialogManager) -> None:
    # create_code (started from the add_code button below) hands back
    # {"banner": ..., ...its Fluent args} on success - stash it so the next
    # render of the list window (which is where the dialog stack returns to
    # once the child calls manager.done()) can show it as part of the title.
    if isinstance(result, dict) and result.get("banner"):
        manager.dialog_data["banner_args"] = result


async def open_add_code(_callback: CallbackQuery, _button: Button, manager: DialogManager) -> None:
    if not await ensure_admin(manager):
        await leave_admin_area(manager)
        return
    await manager.start(AdminCreateCode.enter_code)


async def on_code_selected(_callback: CallbackQuery, _select, manager: DialogManager, item_id: str) -> None:
    manager.dialog_data["selected_code"] = item_id
    await manager.switch_to(AdminCodes.detail)


async def on_prev_page(_callback: CallbackQuery, _button: Button, manager: DialogManager) -> None:
    manager.dialog_data["page"] = max(0, manager.dialog_data.get("page", 0) - 1)


async def on_next_page(_callback: CallbackQuery, _button: Button, manager: DialogManager) -> None:
    manager.dialog_data["page"] = manager.dialog_data.get("page", 0) + 1


async def codes_detail_getter(dialog_manager: DialogManager, **kwargs) -> dict:
    storage: Storage = dialog_manager.middleware_data["storage"]
    code_id = dialog_manager.dialog_data.get("selected_code")
    code = await storage.codes.get(code_id) if code_id else None

    if code is None:
        return {"found": False}

    remnawave_available = dialog_manager.middleware_data.get("remnawave") is not None
    return {
        "found": True,
        "code": esc(code.code),
        "description": esc(code.description or "—"),
        "links_count": len(code.links),
        "remnawave_available": remnawave_available,
        "has_squads": bool(code.remnawave_squads),
        "squad_count": len(code.remnawave_squads),
        "remnawave_disabled": code.remnawave_disabled,
        "remnawave_not_disabled": not code.remnawave_disabled,
    }


async def open_links_menu(_callback: CallbackQuery, _button: Button, manager: DialogManager) -> None:
    await manager.switch_to(AdminCodes.links)


async def code_links_getter(dialog_manager: DialogManager, i18n, **kwargs) -> dict:
    storage: Storage = dialog_manager.middleware_data["storage"]
    code_id = dialog_manager.dialog_data.get("selected_code")
    code = await storage.codes.get(code_id) if code_id else None

    if code is None:
        return {"found": False}

    # Links can be far longer than Telegram's 64-byte callback_data limit,
    # so the remove/reorder buttons address links by position, not by value.
    link_items = [{"id": str(idx), "n": idx + 1} for idx in range(len(code.links))]
    # A link at either end of the list has no "up"/"down" to move to -
    # trimming these here (rather than showing every button and no-op'ing
    # out-of-range moves) keeps the boundary from ever needing an error
    # popup explaining why a tap did nothing.
    remnawave_available = dialog_manager.middleware_data.get("remnawave") is not None
    return {
        "found": True,
        "code": esc(code.code),
        "has_links": bool(code.links),
        "links": [link_row(link, i18n) for link in code.links],
        "link_items": link_items,
        "up_items": link_items[1:],
        "down_items": link_items[:-1],
        "can_add_remnawave_link": remnawave_available and not has_remnawave_link(code.links),
    }


async def on_remove_link(callback: CallbackQuery, _select, manager: DialogManager, item_id: str) -> None:
    if not await ensure_admin(manager):
        await leave_admin_area(manager)
        return

    storage: Storage = manager.middleware_data["storage"]
    i18n = manager.middleware_data["i18n"]
    admin = manager.middleware_data["event_from_user"]
    code_id = manager.dialog_data.get("selected_code")

    # item_id is a Select item id echoed back verbatim from callback_data,
    # not re-validated against the currently rendered link_items by
    # aiogram_dialog - guard the cast rather than assume it's still one of
    # the positions this window last rendered.
    try:
        index = int(item_id)
    except ValueError:
        return
    if not await storage.codes.remove_link_at(code_id, index):
        return
    logger.info("%s removed a link from code %r", actor(admin), code_id)
    await callback.answer(popup_text(i18n, "admin-code-link-removed"))


async def _move_link(manager: DialogManager, item_id: str, offset: int) -> None:
    storage: Storage = manager.middleware_data["storage"]
    admin = manager.middleware_data["event_from_user"]
    code_id = manager.dialog_data.get("selected_code")

    # Same "id is an unvalidated echo of the last render" caveat as
    # on_remove_link - up_items/down_items already exclude the boundary
    # this offset would run past, but only for the render that produced
    # this click, not necessarily the current state.
    try:
        index = int(item_id)
    except ValueError:
        return
    if await storage.codes.move_link(code_id, index, offset):
        logger.info("%s reordered a link in code %r", actor(admin), code_id)


async def on_move_link_up(_callback: CallbackQuery, _select, manager: DialogManager, item_id: str) -> None:
    if not await ensure_admin(manager):
        await leave_admin_area(manager)
        return
    await _move_link(manager, item_id, -1)


async def on_move_link_down(_callback: CallbackQuery, _select, manager: DialogManager, item_id: str) -> None:
    if not await ensure_admin(manager):
        await leave_admin_area(manager)
        return
    await _move_link(manager, item_id, 1)


async def open_add_link(_callback: CallbackQuery, _button: Button, manager: DialogManager) -> None:
    await manager.switch_to(AdminCodes.enter_link)


LINK_FIELD = FormField(
    name="code_link",
    type_adapter=TypeAdapter(str),
    prompt="admin-code-add-link-prompt",
    invalid_label="admin-code-add-link-prompt",  # unreachable: a bare str never fails validation
    optional=True,
    default="",
)

LINK_NAME_FIELD = FormField(
    name="code_link_name",
    type_adapter=TypeAdapter(str),
    prompt="admin-code-link-name-prompt",
    invalid_label="admin-code-link-name-prompt",  # unreachable: a bare str never fails validation
    optional=True,
    skip_label="admin-btn-skip",
    default="",
)


async def on_link_done(link: str, manager: DialogManager) -> None:
    if not await ensure_admin(manager):
        await leave_admin_area(manager)
        return

    if not link:
        await manager.switch_to(AdminCodes.links)
        return
    manager.dialog_data["pending_link"] = {"type": LINK_TYPE_FIX, "url": link}
    await manager.switch_to(AdminCodes.enter_link_name)


async def on_add_remnawave_link(_callback: CallbackQuery, _button: Button, manager: DialogManager) -> None:
    if not await ensure_admin(manager):
        await leave_admin_area(manager)
        return

    storage: Storage = manager.middleware_data["storage"]
    code_id = manager.dialog_data.get("selected_code")

    code = await storage.codes.get(code_id)
    # `when="can_add_remnawave_link"` already hides the button once one
    # exists - guard here too since aiogram_dialog doesn't re-validate a
    # stale render against current state before delivering the click.
    if code is None or has_remnawave_link(code.links):
        return
    manager.dialog_data["pending_link"] = {"type": LINK_TYPE_REMNAWAVE, "url": ""}
    await manager.switch_to(AdminCodes.enter_link_name)


async def on_link_name_cancel(_callback: CallbackQuery, _button: Button, manager: DialogManager) -> None:
    manager.dialog_data.pop("pending_link", None)
    await manager.switch_to(AdminCodes.links)


async def on_link_name_done(name: str, manager: DialogManager) -> None:
    if not await ensure_admin(manager):
        await leave_admin_area(manager)
        return

    pending = manager.dialog_data.pop("pending_link", None)
    if pending is not None:
        storage: Storage = manager.middleware_data["storage"]
        i18n = manager.middleware_data["i18n"]
        bot = manager.middleware_data["bot"]
        admin = manager.middleware_data["event_from_user"]
        code_id = manager.dialog_data.get("selected_code")
        await storage.codes.add_link(code_id, Link(type=pending["type"], name=name, url=pending["url"]))
        logger.info("%s added a %s link to code %r", actor(admin), pending["type"], code_id)
        await bot.send_message(admin.id, i18n.get("admin-code-link-added"))
    await manager.switch_to(AdminCodes.links)


async def open_edit_description(_callback: CallbackQuery, _button: Button, manager: DialogManager) -> None:
    await manager.switch_to(AdminCodes.edit_description)


DESCRIPTION_FIELD = FormField(
    name="code_description",
    type_adapter=TypeAdapter(str),
    prompt="admin-code-edit-description-prompt",
    invalid_label="admin-code-edit-description-prompt",  # unreachable: a bare str never fails validation
    optional=True,
    default="",
)


async def on_description_done(description: str, manager: DialogManager) -> None:
    if not await ensure_admin(manager):
        await leave_admin_area(manager)
        return

    storage: Storage = manager.middleware_data["storage"]
    i18n = manager.middleware_data["i18n"]
    bot = manager.middleware_data["bot"]
    admin = manager.middleware_data["event_from_user"]
    code_id = manager.dialog_data.get("selected_code")

    await storage.codes.set_description(code_id, description)
    logger.info("%s changed description of code %r", actor(admin), code_id)
    await bot.send_message(admin.id, i18n.get("admin-code-description-updated"))
    await manager.switch_to(AdminCodes.detail)


async def open_edit_code(_callback: CallbackQuery, _button: Button, manager: DialogManager) -> None:
    await manager.switch_to(AdminCodes.edit_code)


async def _validate_code_rename(new_code: str, manager: DialogManager) -> str | None:
    storage: Storage = manager.middleware_data["storage"]
    old_code = manager.dialog_data.get("selected_code")
    if new_code != old_code and await storage.codes.exists(new_code):
        return "admin-create-code-exists"
    return None


RENAME_FIELD = FormField(
    name="code_rename",
    type_adapter=_CODE_ADAPTER,
    prompt="admin-code-edit-name-prompt",
    invalid_label="admin-create-code-invalid",
    check=_validate_code_rename,
)


async def on_code_renamed_done(new_code: str, manager: DialogManager) -> None:
    if not await ensure_admin(manager):
        await leave_admin_area(manager)
        return

    old_code = manager.dialog_data.get("selected_code")
    if new_code == old_code:
        await manager.switch_to(AdminCodes.detail)
        return

    storage: Storage = manager.middleware_data["storage"]
    i18n = manager.middleware_data["i18n"]
    bot = manager.middleware_data["bot"]
    admin = manager.middleware_data["event_from_user"]

    if await storage.codes.rename(old_code, new_code):
        # codes.toml keys the entry by the code string itself, and every
        # user who redeemed it holds that same string in their own `codes`
        # list (see storage/users.py) - both must move together or holders
        # would silently lose access under the old name.
        await storage.users.rename_code(old_code, new_code)
        manager.dialog_data["selected_code"] = new_code
        logger.info("%s renamed code %r to %r", actor(admin), old_code, new_code)
        await bot.send_message(admin.id, i18n.get("admin-code-renamed", old=old_code, new=new_code))
    await manager.switch_to(AdminCodes.detail)


async def open_edit_squads(_callback: CallbackQuery, _button: Button, manager: DialogManager) -> None:
    storage: Storage = manager.middleware_data["storage"]
    code_id = manager.dialog_data.get("selected_code")
    code = await storage.codes.get(code_id) if code_id else None

    await manager.switch_to(AdminCodes.edit_squads)
    multiselect = manager.find(_CODE_SQUADS_SELECT_ID)
    if multiselect is not None and code is not None:
        for squad in code.remnawave_squads:
            await multiselect.set_checked(squad, True)


async def edit_squads_getter(dialog_manager: DialogManager, **kwargs) -> dict:
    remnawave = dialog_manager.middleware_data.get("remnawave")
    squads = []
    if remnawave is not None:
        try:
            squads = await remnawave.list_internal_squads()
        except RemnawaveError:
            logger.warning("Failed to list Remnawave squads", exc_info=True)
    return {
        "has_squads": bool(squads),
        "squads": [{"id": s.uuid, "name": esc(s.name)} for s in squads],
    }


async def on_squads_saved(callback: CallbackQuery, _button: Button, manager: DialogManager) -> None:
    if not await ensure_admin(manager):
        await leave_admin_area(manager)
        return

    storage: Storage = manager.middleware_data["storage"]
    i18n = manager.middleware_data["i18n"]
    admin = manager.middleware_data["event_from_user"]
    code_id = manager.dialog_data.get("selected_code")

    multiselect = manager.find(_CODE_SQUADS_SELECT_ID)
    squads = multiselect.get_checked() if multiselect is not None else []
    await storage.codes.set_remnawave_squads(code_id, squads)
    logger.info("%s set Remnawave squads of code %r to %s", actor(admin), code_id, squads)
    await callback.answer(popup_text(i18n, "admin-code-squads-updated"))
    await manager.switch_to(AdminCodes.detail)


async def on_delete_code(callback: CallbackQuery, _button: Button, manager: DialogManager) -> None:
    if not await ensure_admin(manager):
        await leave_admin_area(manager)
        return

    storage: Storage = manager.middleware_data["storage"]
    i18n = manager.middleware_data["i18n"]
    admin = manager.middleware_data["event_from_user"]
    remnawave = manager.middleware_data.get("remnawave")
    code_id = manager.dialog_data.get("selected_code")

    if await storage.codes.delete(code_id):
        # storage.codes.delete only drops the codes.toml entry - without
        # this, every user who'd redeemed the code kept it in their own
        # `codes` list forever, so their subscription count and links list
        # never noticed the code was gone.
        for holder in await storage.users.users_with_code(code_id):
            await storage.users.remove_code(holder.user_id, code_id)
            await sync_remnawave_access(storage, remnawave, holder.user_id)
        logger.info("%s deleted code %r", actor(admin), code_id)
        await callback.answer(popup_text(i18n, "admin-code-deleted", code=code_id), show_alert=True)
    await manager.switch_to(AdminCodes.list)


async def on_toggle_remnawave_disabled(callback: CallbackQuery, _button: Button, manager: DialogManager) -> None:
    if not await ensure_admin(manager):
        await leave_admin_area(manager)
        return

    storage: Storage = manager.middleware_data["storage"]
    i18n = manager.middleware_data["i18n"]
    admin = manager.middleware_data["event_from_user"]
    remnawave = manager.middleware_data.get("remnawave")
    code_id = manager.dialog_data.get("selected_code")

    code = await storage.codes.get(code_id)
    if code is None:
        return

    new_state = not code.remnawave_disabled
    await storage.codes.set_remnawave_disabled(code_id, new_state)
    # Every current holder's squad grant depends on this flag (see
    # services.remnawave_sync.compute_remnawave_squads) - resync them all
    # now instead of waiting for each one's next unrelated code grant/revoke.
    for holder in await storage.users.users_with_code(code_id):
        await sync_remnawave_access(storage, remnawave, holder.user_id)

    action = "disabled" if new_state else "enabled"
    logger.info("%s %s Remnawave integration for code %r", actor(admin), action, code_id)
    popup_key = "admin-code-remnawave-disabled-done" if new_state else "admin-code-remnawave-enabled-done"
    await callback.answer(popup_text(i18n, popup_key, code=code_id), show_alert=True)


codes_dialog = Dialog(
    Window(
        Multi(
            I18N("{banner}", when="banner"),
            Case(
                {
                    True: Multi(I18N("admin-codes-title"), I18N("admin-page-indicator", when="has_pages"), sep=" "),
                    False: I18N("admin-codes-empty"),
                },
                selector="has_codes",
            ),
            sep="\n\n",
        ),
        Button(I18N("admin-btn-create-code"), id="add_code", on_click=open_add_code, style=icon("heavy_plus_sign")),
        Column(
            Select(
                I18N("admin-codes-item", code="{item[code]}", description="{item[description]}", count="{item[count]}"),
                id="code_select",
                item_id_getter=lambda item: item["id"],
                items="codes",
                on_click=on_code_selected,
                style=icon("package"),
            ),
        ),
        Row(
            Button(I18N("admin-btn-prev"), id="prev_page", on_click=on_prev_page, style=icon("chevron_left")),
            Button(I18N("admin-btn-next"), id="next_page", on_click=on_next_page, style=icon("chevron_right")),
        ),
        Cancel(I18N("admin-btn-back"), style=icon("arrow_backward")),
        state=AdminCodes.list,
        getter=codes_list_getter,
    ),
    Window(
        Case(
            {
                True: Multi(
                    I18N("admin-code-detail-title"),
                    I18N("admin-code-links-count", count="{links_count}"),
                    I18N("admin-code-squads-count", count="{squad_count}", when="has_squads"),
                    sep="\n\n",
                ),
                False: I18N("admin-codes-empty"),
            },
            selector="found",
        ),
        Button(I18N("admin-btn-manage-links"), id="open_links", on_click=open_links_menu, when="found", style=icon("link")),
        Button(
            I18N("admin-btn-edit-code"),
            id="edit_code",
            on_click=open_edit_code,
            when="found",
            style=icon("pencil2"),
        ),
        Button(
            I18N("admin-btn-edit-description"),
            id="edit_description",
            on_click=open_edit_description,
            when="found",
            style=icon("pencil2"),
        ),
        Button(
            I18N("admin-btn-edit-squads"),
            id="edit_squads",
            on_click=open_edit_squads,
            when="remnawave_available",
            style=icon("shield"),
        ),
        Button(
            Case(
                {True: I18N("admin-btn-enable-remnawave"), False: I18N("admin-btn-disable-remnawave")},
                selector="remnawave_disabled",
            ),
            id="toggle_code_remnawave_disabled",
            on_click=on_toggle_remnawave_disabled,
            when="remnawave_available",
            style=_REMNAWAVE_TOGGLE_STYLE,
        ),
        Button(
            I18N("admin-btn-delete-code"),
            id="delete_code",
            on_click=on_delete_code,
            when="found",
            style=icon("wastebasket", ButtonStyle.DANGER),
        ),
        SwitchTo(I18N("admin-btn-back"), id="back_to_list", state=AdminCodes.list, style=icon("arrow_backward")),
        state=AdminCodes.detail,
        getter=codes_detail_getter,
    ),
    Window(
        Case(
            {
                True: Multi(
                    I18N("admin-code-links-title", code="{code}"),
                    Case(
                        {
                            True: List(Format("{pos}. {item}"), items="links", sep="\n"),
                            False: I18N("admin-code-no-links"),
                        },
                        selector="has_links",
                    ),
                    sep="\n\n",
                ),
                False: I18N("admin-codes-empty"),
            },
            selector="found",
        ),
        Column(
            Select(
                I18N("admin-code-move-link-up-btn", n="{item[n]}"),
                id="move_link_up_select",
                item_id_getter=lambda item: item["id"],
                items="up_items",
                on_click=on_move_link_up,
            ),
        ),
        Column(
            Select(
                I18N("admin-code-move-link-down-btn", n="{item[n]}"),
                id="move_link_down_select",
                item_id_getter=lambda item: item["id"],
                items="down_items",
                on_click=on_move_link_down,
            ),
        ),
        Column(
            Select(
                I18N("admin-code-remove-link-btn", n="{item[n]}"),
                id="remove_link_select",
                item_id_getter=lambda item: item["id"],
                items="link_items",
                on_click=on_remove_link,
                style=icon("x", ButtonStyle.DANGER),
            ),
        ),
        Button(I18N("admin-btn-add-link"), id="add_link", on_click=open_add_link, when="found", style=icon("heavy_plus_sign")),
        Button(
            I18N("admin-btn-add-remnawave-link"),
            id="add_remnawave_link",
            on_click=on_add_remnawave_link,
            when="can_add_remnawave_link",
            style=icon("shield"),
        ),
        SwitchTo(I18N("admin-btn-back"), id="back_to_detail_from_links", state=AdminCodes.detail, style=icon("arrow_backward")),
        state=AdminCodes.links,
        getter=code_links_getter,
    ),
    build_field_window(
        LINK_FIELD,
        AdminCodes.enter_link,
        on_link_done,
        SwitchTo(I18N("admin-btn-back"), id="back_to_links", state=AdminCodes.links, style=icon("arrow_backward")),
    ),
    build_field_window(
        LINK_NAME_FIELD,
        AdminCodes.enter_link_name,
        on_link_name_done,
        Button(I18N("admin-btn-back"), id="link_name_back", on_click=on_link_name_cancel, style=icon("arrow_backward")),
    ),
    build_field_window(
        DESCRIPTION_FIELD,
        AdminCodes.edit_description,
        on_description_done,
        SwitchTo(I18N("admin-btn-back"), id="back_to_detail2", state=AdminCodes.detail, style=icon("arrow_backward")),
    ),
    build_field_window(
        RENAME_FIELD,
        AdminCodes.edit_code,
        on_code_renamed_done,
        SwitchTo(I18N("admin-btn-back"), id="back_to_detail4", state=AdminCodes.detail, style=icon("arrow_backward")),
    ),
    Window(
        Case(
            {
                True: I18N("admin-code-edit-squads-prompt"),
                False: I18N("admin-create-code-squads-empty"),
            },
            selector="has_squads",
        ),
        Column(
            Multiselect(
                I18N("admin-create-code-squad-item", name="{item[name]}"),
                I18N("admin-create-code-squad-item", name="{item[name]}"),
                id=_CODE_SQUADS_SELECT_ID,
                item_id_getter=lambda item: item["id"],
                items="squads",
                checked_style=icon("check"),
                unchecked_style=icon("shield"),
            ),
        ),
        Button(I18N("admin-btn-done"), id="squads_saved", on_click=on_squads_saved, style=icon("white_check_mark", ButtonStyle.SUCCESS)),
        SwitchTo(I18N("admin-btn-back"), id="back_to_detail3", state=AdminCodes.detail, style=icon("arrow_backward")),
        state=AdminCodes.edit_squads,
        getter=edit_squads_getter,
    ),
    on_start=on_dialog_start,
    on_process_result=on_child_result,
)
