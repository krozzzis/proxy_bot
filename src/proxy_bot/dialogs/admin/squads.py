from __future__ import annotations

import asyncio
import logging
from typing import Annotated

from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery
from aiogram_dialog import Dialog, DialogManager, Window
from aiogram_dialog.widgets.kbd import Button, Cancel, Column, Multiselect, Row, Select, SwitchTo
from aiogram_dialog.widgets.style.base import ButtonStyle
from aiogram_dialog.widgets.text import Case, Multi
from pydantic import StringConstraints, TypeAdapter

from proxy_bot.remnawave import RemnawaveError, RemnawaveRegistry
from proxy_bot.services.remnawave_sync import sync_remnawave_access
from proxy_bot.storage import Storage
from proxy_bot.storage.models import LINK_TYPE_REMNAWAVE
from proxy_bot.utils.audit import actor
from proxy_bot.utils.html import esc
from proxy_bot.utils.i18n import popup_text

from ..common import icon
from ..forms import FormField, build_field_window
from ..widgets import I18N
from .access import ensure_admin, leave_admin_area

logger = logging.getLogger(__name__)

_CANCEL_STYLE = icon("x", ButtonStyle.DANGER)
_ADD_INTERNAL_SQUADS_SELECT_ID = "squad_add_internal_select"
_EDIT_INTERNAL_SQUADS_SELECT_ID = "squad_edit_internal_select"

PAGE_SIZE = 8

_NAME_ADAPTER = TypeAdapter(Annotated[str, StringConstraints(min_length=1, strip_whitespace=True)])


class AdminSquads(StatesGroup):
    list = State()
    add_choose_server = State()
    add_enter_name = State()
    add_choose_internal_squads = State()
    detail = State()
    edit_name = State()
    edit_internal_squads = State()


async def on_dialog_start(_start_data: object, manager: DialogManager) -> None:
    if not await ensure_admin(manager):
        await leave_admin_area(manager)


async def squads_list_getter(dialog_manager: DialogManager, **kwargs) -> dict:
    storage: Storage = dialog_manager.middleware_data["storage"]
    squads = await storage.squads.all()
    squads.sort(key=lambda s: s.name.lower())

    total_pages = max(1, (len(squads) + PAGE_SIZE - 1) // PAGE_SIZE)
    page = max(0, min(dialog_manager.dialog_data.get("page", 0), total_pages - 1))
    dialog_manager.dialog_data["page"] = page

    chunk = squads[page * PAGE_SIZE : (page + 1) * PAGE_SIZE]
    items = [{"id": s.id, "name": esc(s.name), "server": esc(s.server)} for s in chunk]
    return {
        "has_squads": bool(squads),
        "count": len(squads),
        "has_pages": total_pages > 1,
        "page": page + 1,
        "total": total_pages,
        "squads": items,
    }


async def on_prev_page(_callback: CallbackQuery, _button: Button, manager: DialogManager) -> None:
    manager.dialog_data["page"] = max(0, manager.dialog_data.get("page", 0) - 1)


async def on_next_page(_callback: CallbackQuery, _button: Button, manager: DialogManager) -> None:
    manager.dialog_data["page"] = manager.dialog_data.get("page", 0) + 1


async def on_squad_selected(_callback: CallbackQuery, _select, manager: DialogManager, item_id: str) -> None:
    manager.dialog_data["selected_squad"] = item_id
    await manager.switch_to(AdminSquads.detail)


async def open_add_squad(_callback: CallbackQuery, _button: Button, manager: DialogManager) -> None:
    if not await ensure_admin(manager):
        await leave_admin_area(manager)
        return
    remnawave = manager.middleware_data.get("remnawave")
    servers = remnawave.names() if remnawave is not None else []
    if len(servers) > 1:
        await manager.switch_to(AdminSquads.add_choose_server)
        return
    manager.dialog_data["new_server"] = servers[0] if servers else ""
    await manager.switch_to(AdminSquads.add_enter_name)


async def choose_server_getter(dialog_manager: DialogManager, **kwargs) -> dict:
    remnawave = dialog_manager.middleware_data.get("remnawave")
    servers = remnawave.names() if remnawave is not None else []
    return {"servers": [{"id": name, "name": esc(name)} for name in servers]}


async def on_server_chosen(_callback: CallbackQuery, _select, manager: DialogManager, item_id: str) -> None:
    manager.dialog_data["new_server"] = item_id
    await manager.switch_to(AdminSquads.add_enter_name)


async def _name_extra_getter(manager: DialogManager) -> dict:
    return {"server": esc(manager.dialog_data.get("new_server", ""))}


NAME_FIELD = FormField(
    name="squad_name",
    type_adapter=_NAME_ADAPTER,
    prompt="admin-squad-create-prompt-name",
    invalid_label="admin-squad-name-invalid",
    extra_getter=_name_extra_getter,
)


async def on_name_done(name: str, manager: DialogManager) -> None:
    if not await ensure_admin(manager):
        await leave_admin_area(manager)
        return
    manager.dialog_data["new_name"] = name
    await manager.switch_to(AdminSquads.add_choose_internal_squads)


async def _list_internal_squads(manager: DialogManager, server: str) -> list[dict]:
    """Internal squads for `server`, as Multiselect items with a short
    positional id ("0", "1", ...) - a raw Remnawave internal-squad UUID
    (36 chars) is too long to use directly: once aiogram_dialog adds its
    own widget/intent-id prefix on top, the resulting callback_data blows
    Telegram's 64-byte cap and every tap fails with BUTTON_DATA_INVALID.
    The id -> real uuid mapping is stashed in dialog_data so
    on_create_done/on_edit_internal_squads_done can translate the checked
    short ids back."""
    remnawave = manager.middleware_data.get("remnawave")
    client = remnawave.get(server) if remnawave is not None else None
    if client is None:
        return []
    try:
        squads = await client.list_internal_squads()
    except RemnawaveError:
        logger.warning("Failed to list internal squads for server %r", server, exc_info=True)
        return []
    manager.dialog_data["internal_squad_uuids"] = {str(idx): s.uuid for idx, s in enumerate(squads)}
    return [{"id": str(idx), "name": esc(s.name)} for idx, s in enumerate(squads)]


def _checked_internal_squad_uuids(manager: DialogManager, checked_ids: list[str]) -> list[str]:
    uuid_map = manager.dialog_data.get("internal_squad_uuids", {})
    return [uuid_map[i] for i in checked_ids if i in uuid_map]


async def _affected_user_ids(storage: Storage, squad_id: str) -> set[int]:
    """Every user who holds a code with a `remnawave`-type link attached to
    this Squad - changing (or removing) the Squad changes what
    services.remnawave_sync.compute_remnawave_grants computes for them."""
    codes = await storage.codes.all()
    affected_codes = [
        code.code
        for code in codes
        if any(link.type == LINK_TYPE_REMNAWAVE and link.squad_id == squad_id for link in code.links)
    ]
    user_ids: set[int] = set()
    for code in affected_codes:
        for user in await storage.users.users_with_code(code):
            user_ids.add(user.user_id)
    return user_ids


async def _resync_affected_users(storage: Storage, remnawave: RemnawaveRegistry | None, user_ids: set[int]) -> None:
    """Fire-and-forget background sweep: a Squad edit/delete can affect an
    arbitrary number of holders, and each sync_remnawave_access() call is
    its own round trip to the panel - run these after the triggering
    handler has already returned and the admin has their confirmation,
    rather than making them wait on however many users are affected."""
    for user_id in user_ids:
        try:
            await sync_remnawave_access(storage, remnawave, user_id)
        except Exception:
            logger.exception("Failed to resync Remnawave access for user %s after a Squad change", user_id)


async def add_choose_internal_squads_getter(dialog_manager: DialogManager, **kwargs) -> dict:
    server = dialog_manager.dialog_data.get("new_server", "")
    internal_squads = await _list_internal_squads(dialog_manager, server)
    return {"has_internal_squads": bool(internal_squads), "internal_squads": internal_squads}


async def on_create_done(callback: CallbackQuery, _button: Button, manager: DialogManager) -> None:
    if not await ensure_admin(manager):
        await leave_admin_area(manager)
        return

    storage: Storage = manager.middleware_data["storage"]
    i18n = manager.middleware_data["i18n"]
    admin = manager.middleware_data["event_from_user"]
    name = manager.dialog_data.pop("new_name", "")
    server = manager.dialog_data.pop("new_server", "")

    multiselect = manager.find(_ADD_INTERNAL_SQUADS_SELECT_ID)
    checked_ids = multiselect.get_checked() if multiselect is not None else []
    internal_squad_uuids = _checked_internal_squad_uuids(manager, checked_ids)

    squad = await storage.squads.create(name, server, internal_squad_uuids)
    logger.info(
        "%s created Squad %r (%r) on server %r with %d internal squad(s)",
        actor(admin), squad.id, name, server, len(internal_squad_uuids),
    )
    if multiselect is not None:
        await multiselect.reset_checked()
    await manager.switch_to(AdminSquads.list)
    await callback.answer(popup_text(i18n, "admin-squad-created-done", name=esc(name)), show_alert=True)


async def squad_detail_getter(dialog_manager: DialogManager, **kwargs) -> dict:
    storage: Storage = dialog_manager.middleware_data["storage"]
    squad_id = dialog_manager.dialog_data.get("selected_squad")
    squad = await storage.squads.get(squad_id) if squad_id else None
    if squad is None:
        return {"found": False}
    return {
        "found": True,
        "id": squad.id,
        "name": esc(squad.name),
        "server": esc(squad.server),
        "count": len(squad.internal_squad_uuids),
    }


async def open_edit_name(_callback: CallbackQuery, _button: Button, manager: DialogManager) -> None:
    await manager.switch_to(AdminSquads.edit_name)


async def edit_name_extra_getter(manager: DialogManager) -> dict:
    storage: Storage = manager.middleware_data["storage"]
    squad_id = manager.dialog_data.get("selected_squad")
    squad = await storage.squads.get(squad_id) if squad_id else None
    return {"server": esc(squad.server if squad is not None else "")}


EDIT_NAME_FIELD = FormField(
    name="squad_edit_name",
    type_adapter=_NAME_ADAPTER,
    prompt="admin-squad-edit-name-prompt",
    invalid_label="admin-squad-name-invalid",
    extra_getter=edit_name_extra_getter,
)


async def on_edit_name_done(name: str, manager: DialogManager) -> None:
    if not await ensure_admin(manager):
        await leave_admin_area(manager)
        return

    storage: Storage = manager.middleware_data["storage"]
    i18n = manager.middleware_data["i18n"]
    bot = manager.middleware_data["bot"]
    admin = manager.middleware_data["event_from_user"]
    squad_id = manager.dialog_data.get("selected_squad")

    if await storage.squads.set_name(squad_id, name):
        logger.info("%s renamed Squad %r to %r", actor(admin), squad_id, name)
        await bot.send_message(admin.id, i18n.get("admin-squad-renamed"))
    await manager.switch_to(AdminSquads.detail)


async def open_edit_internal_squads(_callback: CallbackQuery, _button: Button, manager: DialogManager) -> None:
    storage: Storage = manager.middleware_data["storage"]
    squad_id = manager.dialog_data.get("selected_squad")
    squad = await storage.squads.get(squad_id) if squad_id else None

    if squad is not None:
        # DialogManager.switch_to() only updates the FSM state - it does
        # NOT render (aiogram_dialog's middleware renders after this whole
        # handler returns), so edit_internal_squads_getter and its
        # short-id -> uuid mapping wouldn't exist yet if we waited for
        # switch_to below to produce it. Populate it ourselves first.
        await _list_internal_squads(manager, squad.server)

    await manager.switch_to(AdminSquads.edit_internal_squads)
    multiselect = manager.find(_EDIT_INTERNAL_SQUADS_SELECT_ID)
    if multiselect is not None and squad is not None:
        uuid_map = manager.dialog_data.get("internal_squad_uuids", {})
        short_ids = {uuid: short_id for short_id, uuid in uuid_map.items()}
        for uuid in squad.internal_squad_uuids:
            short_id = short_ids.get(uuid)
            if short_id is not None:
                await multiselect.set_checked(short_id, True)


async def edit_internal_squads_getter(dialog_manager: DialogManager, **kwargs) -> dict:
    storage: Storage = dialog_manager.middleware_data["storage"]
    squad_id = dialog_manager.dialog_data.get("selected_squad")
    squad = await storage.squads.get(squad_id) if squad_id else None
    if squad is None:
        return {"found": False, "has_internal_squads": False, "internal_squads": []}
    internal_squads = await _list_internal_squads(dialog_manager, squad.server)
    return {"found": True, "has_internal_squads": bool(internal_squads), "internal_squads": internal_squads}


async def on_edit_internal_squads_done(callback: CallbackQuery, _button: Button, manager: DialogManager) -> None:
    if not await ensure_admin(manager):
        await leave_admin_area(manager)
        return

    storage: Storage = manager.middleware_data["storage"]
    i18n = manager.middleware_data["i18n"]
    admin = manager.middleware_data["event_from_user"]
    squad_id = manager.dialog_data.get("selected_squad")

    multiselect = manager.find(_EDIT_INTERNAL_SQUADS_SELECT_ID)
    checked_ids = multiselect.get_checked() if multiselect is not None else []
    internal_squad_uuids = _checked_internal_squad_uuids(manager, checked_ids)
    await storage.squads.set_internal_squad_uuids(squad_id, internal_squad_uuids)
    logger.info("%s set internal squads of Squad %r to %s", actor(admin), squad_id, internal_squad_uuids)

    remnawave = manager.middleware_data.get("remnawave")
    user_ids = await _affected_user_ids(storage, squad_id)
    if user_ids:
        asyncio.create_task(_resync_affected_users(storage, remnawave, user_ids))
        logger.info("%s triggered a background Remnawave resync for %d holder(s) of Squad %r", actor(admin), len(user_ids), squad_id)

    await callback.answer(popup_text(i18n, "admin-squad-internal-squads-updated"))
    await manager.switch_to(AdminSquads.detail)


async def on_delete_squad(callback: CallbackQuery, _button: Button, manager: DialogManager) -> None:
    if not await ensure_admin(manager):
        await leave_admin_area(manager)
        return

    storage: Storage = manager.middleware_data["storage"]
    i18n = manager.middleware_data["i18n"]
    admin = manager.middleware_data["event_from_user"]
    squad_id = manager.dialog_data.get("selected_squad")

    user_ids = await _affected_user_ids(storage, squad_id)
    if await storage.squads.delete(squad_id):
        logger.info("%s deleted Squad %r", actor(admin), squad_id)
        if user_ids:
            remnawave = manager.middleware_data.get("remnawave")
            asyncio.create_task(_resync_affected_users(storage, remnawave, user_ids))
            logger.info("%s triggered a background Remnawave resync for %d holder(s) of deleted Squad %r", actor(admin), len(user_ids), squad_id)
        await callback.answer(popup_text(i18n, "admin-squad-deleted-done"), show_alert=True)
    await manager.switch_to(AdminSquads.list)


squads_dialog = Dialog(
    Window(
        Case(
            {
                True: Multi(I18N("admin-squads-title"), I18N("admin-page-indicator", when="has_pages"), sep=" "),
                False: I18N("admin-squads-empty"),
            },
            selector="has_squads",
        ),
        Button(I18N("admin-btn-create-squad"), id="add_squad", on_click=open_add_squad, style=icon("heavy_plus_sign")),
        Column(
            Select(
                I18N("admin-squads-item", name="{item[name]}", server="{item[server]}"),
                id="squad_select",
                item_id_getter=lambda item: item["id"],
                items="squads",
                on_click=on_squad_selected,
                style=icon("shield"),
            ),
        ),
        Row(
            Button(I18N("admin-btn-prev"), id="prev_page", on_click=on_prev_page, style=icon("chevron_left")),
            Button(I18N("admin-btn-next"), id="next_page", on_click=on_next_page, style=icon("chevron_right")),
        ),
        Cancel(I18N("admin-btn-back"), style=icon("arrow_backward")),
        state=AdminSquads.list,
        getter=squads_list_getter,
    ),
    Window(
        I18N("admin-squad-create-choose-server-prompt"),
        Column(
            Select(
                I18N("admin-squad-server-item", server="{item[name]}"),
                id="squad_server_select",
                item_id_getter=lambda item: item["id"],
                items="servers",
                on_click=on_server_chosen,
                style=icon("shield"),
            ),
        ),
        SwitchTo(I18N("admin-btn-cancel"), id="cancel_choose_server", state=AdminSquads.list, style=_CANCEL_STYLE),
        state=AdminSquads.add_choose_server,
    ),
    build_field_window(
        NAME_FIELD,
        AdminSquads.add_enter_name,
        on_name_done,
        Cancel(I18N("admin-btn-cancel"), style=_CANCEL_STYLE),
    ),
    Window(
        Case(
            {
                True: I18N("admin-squad-create-prompt-internal-squads"),
                False: I18N("admin-squad-internal-squads-empty"),
            },
            selector="has_internal_squads",
        ),
        Column(
            Multiselect(
                I18N("admin-squad-internal-squad-item", name="{item[name]}"),
                I18N("admin-squad-internal-squad-item", name="{item[name]}"),
                id=_ADD_INTERNAL_SQUADS_SELECT_ID,
                item_id_getter=lambda item: item["id"],
                items="internal_squads",
                checked_style=icon("check"),
                unchecked_style=icon("shield"),
            ),
        ),
        Button(I18N("admin-btn-done"), id="create_done", on_click=on_create_done, style=icon("white_check_mark", ButtonStyle.SUCCESS)),
        Cancel(I18N("admin-btn-cancel"), style=_CANCEL_STYLE),
        state=AdminSquads.add_choose_internal_squads,
        getter=add_choose_internal_squads_getter,
    ),
    Window(
        Case(
            {
                True: Multi(
                    I18N("admin-squad-detail-title", name="{name}"),
                    I18N("admin-squad-detail-server", server="{server}"),
                    I18N("admin-squad-detail-count", count="{count}"),
                    sep="\n\n",
                ),
                False: I18N("admin-squads-empty"),
            },
            selector="found",
        ),
        Button(I18N("admin-btn-edit-squad-name"), id="edit_squad_name", on_click=open_edit_name, when="found", style=icon("pencil2")),
        Button(
            I18N("admin-btn-edit-squad-internal-squads"),
            id="edit_squad_internal_squads",
            on_click=open_edit_internal_squads,
            when="found",
            style=icon("shield"),
        ),
        Button(
            I18N("admin-btn-delete-squad"),
            id="delete_squad",
            on_click=on_delete_squad,
            when="found",
            style=icon("wastebasket", ButtonStyle.DANGER),
        ),
        SwitchTo(I18N("admin-btn-back"), id="back_to_squads_list", state=AdminSquads.list, style=icon("arrow_backward")),
        state=AdminSquads.detail,
        getter=squad_detail_getter,
    ),
    build_field_window(
        EDIT_NAME_FIELD,
        AdminSquads.edit_name,
        on_edit_name_done,
        SwitchTo(I18N("admin-btn-back"), id="back_to_squad_detail", state=AdminSquads.detail, style=icon("arrow_backward")),
    ),
    Window(
        Case(
            {
                True: I18N("admin-squad-edit-internal-squads-prompt"),
                False: I18N("admin-squad-internal-squads-empty"),
            },
            selector="has_internal_squads",
        ),
        Column(
            Multiselect(
                I18N("admin-squad-internal-squad-item", name="{item[name]}"),
                I18N("admin-squad-internal-squad-item", name="{item[name]}"),
                id=_EDIT_INTERNAL_SQUADS_SELECT_ID,
                item_id_getter=lambda item: item["id"],
                items="internal_squads",
                checked_style=icon("check"),
                unchecked_style=icon("shield"),
            ),
        ),
        Button(I18N("admin-btn-done"), id="edit_internal_squads_done", on_click=on_edit_internal_squads_done, style=icon("white_check_mark", ButtonStyle.SUCCESS)),
        SwitchTo(I18N("admin-btn-back"), id="back_to_squad_detail2", state=AdminSquads.detail, style=icon("arrow_backward")),
        state=AdminSquads.edit_internal_squads,
        getter=edit_internal_squads_getter,
    ),
    on_start=on_dialog_start,
)
