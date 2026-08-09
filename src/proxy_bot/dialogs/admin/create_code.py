from __future__ import annotations

import logging
from typing import Annotated

from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from aiogram_dialog import Dialog, DialogManager, Window
from aiogram_dialog.widgets.input import ManagedTextInput, TextInput
from aiogram_dialog.widgets.kbd import Button, Cancel, Column, Multiselect
from aiogram_dialog.widgets.style.base import ButtonStyle
from aiogram_dialog.widgets.text import Case, Format, List, Multi
from pydantic import StringConstraints, TypeAdapter

from proxy_bot.remnawave import RemnawaveError
from proxy_bot.storage import Storage
from proxy_bot.storage.models import LINK_TYPE_FIX, LINK_TYPE_REMNAWAVE, Link
from proxy_bot.utils.audit import actor
from proxy_bot.utils.html import esc

from ..common import icon, not_a_command
from ..forms import FormField, build_field_window
from ..widgets import I18N
from .access import ensure_admin, leave_admin_area
from .links_common import has_remnawave_link, link_row

logger = logging.getLogger(__name__)

_SQUADS_SELECT_ID = "cc_squads_select"


class AdminCreateCode(StatesGroup):
    enter_code = State()
    enter_links = State()
    enter_description = State()
    enter_squads = State()


_CANCEL_STYLE = icon("x", ButtonStyle.DANGER)

# Codes end up as Select callback_data (Telegram caps callback_data at 64
# bytes total, and aiogram-dialog adds its own widget/intent-id prefix on
# top), so keep codes well short of that ceiling. The lower bound guards
# against online brute-forcing through enter_code.on_code_entered, which
# has no attempt limit of its own - 8 chars from this alphabet is ~2.8e14
# combinations, vs. ~2.6e5 for the old 3-char floor.
_CODE_ADAPTER = TypeAdapter(Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9_-]{8,32}$")])
_DESCRIPTION_ADAPTER = TypeAdapter(str)


async def _code_is_unique(code: str, manager: DialogManager) -> str | None:
    storage: Storage = manager.middleware_data["storage"]
    if await storage.codes.exists(code):
        return "admin-create-code-exists"
    return None


CODE_FIELD = FormField(
    name="code",
    type_adapter=_CODE_ADAPTER,
    prompt="admin-create-code-prompt-code",
    invalid_label="admin-create-code-invalid",
    check=_code_is_unique,
)

DESCRIPTION_FIELD = FormField(
    name="description",
    type_adapter=_DESCRIPTION_ADAPTER,
    prompt="admin-create-code-prompt-description",
    invalid_label="admin-create-code-invalid",  # unreachable: a bare str never fails validation
    optional=True,
    skip_label="admin-btn-skip",
    default="",
)


async def step_links_getter(dialog_manager: DialogManager, i18n, **kwargs) -> dict:
    links: list[Link] = dialog_manager.dialog_data.get("new_links", [])
    remnawave_configured = dialog_manager.middleware_data.get("remnawave") is not None
    return {
        "has_links": bool(links),
        "count": len(links),
        "rows": [link_row(link, i18n) for link in links],
        "can_add_remnawave": remnawave_configured and not has_remnawave_link(links),
    }


async def on_code_done(code: str, manager: DialogManager) -> None:
    manager.dialog_data["new_code"] = code
    await manager.next()


async def on_link_added(message: Message, widget: ManagedTextInput, manager: DialogManager, link_text: str) -> None:
    link = link_text.strip()
    if not link:
        return
    manager.dialog_data.setdefault("new_links", []).append(Link(type=LINK_TYPE_FIX, url=link))


async def on_add_remnawave_link(_callback: CallbackQuery, _button: Button, manager: DialogManager) -> None:
    links: list[Link] = manager.dialog_data.setdefault("new_links", [])
    # `when="can_add_remnawave"` already hides the button once one exists -
    # guard here too since aiogram_dialog doesn't re-validate a stale
    # render against current state before delivering the click.
    if has_remnawave_link(links):
        return
    links.append(Link(type=LINK_TYPE_REMNAWAVE))


async def on_undo_last_link(_callback: CallbackQuery, _button: Button, manager: DialogManager) -> None:
    links = manager.dialog_data.get("new_links", [])
    if links:
        links.pop()


async def on_links_done(_callback: CallbackQuery, _button: Button, manager: DialogManager) -> None:
    if manager.dialog_data.get("new_links"):
        await manager.next()


async def on_dialog_start(_start_data: object, manager: DialogManager) -> None:
    if not await ensure_admin(manager):
        await leave_admin_area(manager)


async def _finalize_creation(manager: DialogManager, squads: list[str]) -> None:
    storage: Storage = manager.middleware_data["storage"]
    user = manager.middleware_data["event_from_user"]

    code = manager.dialog_data["new_code"]
    links = manager.dialog_data.get("new_links", [])
    description = manager.dialog_data.get("new_description", "")
    await storage.codes.create(
        code=code, links=links, description=description, created_by=user.id, remnawave_squads=squads
    )
    logger.info(
        "%s created code %r with %d link(s) and %d remnawave squad(s)",
        actor(user),
        code,
        len(links),
        len(squads),
    )

    # Handed to the admin menu's on_process_result, so the confirmation
    # renders as part of that same re-render instead of a message of its
    # own sent separately (and, since it edits a much older message,
    # out of order relative to it).
    await manager.done(result={"banner": "admin-create-code-done", "code": esc(code)})


async def on_description_done(description: str, manager: DialogManager) -> None:
    if not await ensure_admin(manager):
        await leave_admin_area(manager)
        return

    manager.dialog_data["new_description"] = description
    remnawave = manager.middleware_data.get("remnawave")
    if remnawave is None:
        # Feature not configured for this deployment - skip straight to a
        # plain fixed-link code, same as before this feature existed.
        await _finalize_creation(manager, [])
        return
    await manager.next()


async def enter_squads_getter(dialog_manager: DialogManager, **kwargs) -> dict:
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


async def on_squads_done(_callback: CallbackQuery, _button: Button, manager: DialogManager) -> None:
    if not await ensure_admin(manager):
        await leave_admin_area(manager)
        return

    multiselect = manager.find(_SQUADS_SELECT_ID)
    squads = multiselect.get_checked() if multiselect is not None else []
    await _finalize_creation(manager, squads)


create_code_dialog = Dialog(
    build_field_window(
        CODE_FIELD, AdminCreateCode.enter_code, on_code_done, Cancel(I18N("admin-btn-cancel"), style=_CANCEL_STYLE)
    ),
    Window(
        Multi(
            I18N("admin-create-code-prompt-link"),
            Multi(
                I18N("admin-create-code-links-added"),
                List(Format("{pos}. {item}"), items="rows", sep="\n"),
                sep="\n",
                when="has_links",
            ),
            sep="\n\n",
        ),
        TextInput(id="cc_link", on_success=on_link_added, filter=not_a_command),
        Button(
            I18N("admin-btn-add-remnawave-link"),
            id="add_remnawave_link",
            on_click=on_add_remnawave_link,
            when="can_add_remnawave",
            style=icon("shield"),
        ),
        Button(I18N("admin-btn-undo"), id="undo_link", on_click=on_undo_last_link, when="has_links", style=icon("leftwards_arrow_with_hook")),
        Button(I18N("admin-btn-done"), id="links_done", on_click=on_links_done, when="has_links", style=icon("white_check_mark", ButtonStyle.SUCCESS)),
        Cancel(I18N("admin-btn-cancel"), style=_CANCEL_STYLE),
        state=AdminCreateCode.enter_links,
        getter=step_links_getter,
    ),
    build_field_window(
        DESCRIPTION_FIELD,
        AdminCreateCode.enter_description,
        on_description_done,
        Cancel(I18N("admin-btn-cancel"), style=_CANCEL_STYLE),
    ),
    Window(
        Case(
            {
                True: I18N("admin-create-code-prompt-squads"),
                False: I18N("admin-create-code-squads-empty"),
            },
            selector="has_squads",
        ),
        Column(
            Multiselect(
                I18N("admin-create-code-squad-item", name="{item[name]}"),
                I18N("admin-create-code-squad-item", name="{item[name]}"),
                id=_SQUADS_SELECT_ID,
                item_id_getter=lambda item: item["id"],
                items="squads",
                checked_style=icon("check"),
                unchecked_style=icon("shield"),
            ),
        ),
        Button(I18N("admin-btn-done"), id="squads_done", on_click=on_squads_done, style=icon("white_check_mark", ButtonStyle.SUCCESS)),
        Cancel(I18N("admin-btn-cancel"), style=_CANCEL_STYLE),
        state=AdminCreateCode.enter_squads,
        getter=enter_squads_getter,
    ),
    on_start=on_dialog_start,
)
