from __future__ import annotations

import logging
from typing import Annotated

from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from aiogram_dialog import Dialog, DialogManager, Window
from aiogram_dialog.widgets.input import ManagedTextInput, TextInput
from aiogram_dialog.widgets.kbd import Button, Cancel, Column, Select, SwitchTo
from aiogram_dialog.widgets.style.base import ButtonStyle
from aiogram_dialog.widgets.text import Case, Format, List, Multi
from pydantic import StringConstraints, TypeAdapter

from proxy_bot.storage import Storage
from proxy_bot.storage.models import LINK_TYPE_FIX, LINK_TYPE_REMNAWAVE, parse_link
from proxy_bot.utils.audit import actor
from proxy_bot.utils.html import esc

from ..common import icon, not_a_command
from ..forms import FormField, build_field_window
from ..widgets import I18N
from .access import ensure_admin, leave_admin_area
from .links_common import available_squads, link_row

logger = logging.getLogger(__name__)


class AdminCreateCode(StatesGroup):
    enter_code = State()
    enter_links = State()
    choose_link_squad = State()
    enter_link_name = State()
    enter_description = State()


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

LINK_NAME_FIELD = FormField(
    name="link_name",
    type_adapter=TypeAdapter(str),
    prompt="admin-create-code-link-name-prompt",
    invalid_label="admin-create-code-link-name-prompt",  # unreachable: a bare str never fails validation
    optional=True,
    skip_label="admin-btn-skip",
    default="",
)


async def step_links_getter(dialog_manager: DialogManager, i18n, **kwargs) -> dict:
    # Stored in dialog_data as plain dump_link()-shaped dicts, not Link
    # instances - dialog_data gets JSON-serialized by this project's FSM
    # storage (see fsm/sqlite_storage.py), which a raw dataclass instance
    # can't survive.
    storage: Storage = dialog_manager.middleware_data["storage"]
    links = [parse_link(raw) for raw in dialog_manager.dialog_data.get("new_links", [])]
    all_squads = await storage.squads.all()
    squads_by_id = {s.id: s for s in all_squads}
    rows = [
        link_row(link, i18n, squads_by_id[link.squad_id].name if link.squad_id in squads_by_id else None)
        for link in links
    ]
    return {
        "has_links": bool(links),
        "count": len(links),
        "rows": rows,
        "can_add_remnawave": bool(available_squads(all_squads, links)),
    }


async def on_code_done(code: str, manager: DialogManager) -> None:
    manager.dialog_data["new_code"] = code
    await manager.next()


async def on_link_added(message: Message, widget: ManagedTextInput, manager: DialogManager, link_text: str) -> None:
    link = link_text.strip()
    if not link:
        return
    manager.dialog_data["pending_link"] = {"type": LINK_TYPE_FIX, "url": link}
    await manager.switch_to(AdminCreateCode.enter_link_name)


async def on_open_choose_link_squad(_callback: CallbackQuery, _button: Button, manager: DialogManager) -> None:
    storage: Storage = manager.middleware_data["storage"]
    links = [parse_link(raw) for raw in manager.dialog_data.get("new_links", [])]
    # `when="can_add_remnawave"` already hides the button once no Squad is
    # left to attach - guard here too since aiogram_dialog doesn't
    # re-validate a stale render against current state before delivering
    # the click.
    if not available_squads(await storage.squads.all(), links):
        return
    await manager.switch_to(AdminCreateCode.choose_link_squad)


async def choose_link_squad_getter(dialog_manager: DialogManager, **kwargs) -> dict:
    storage: Storage = dialog_manager.middleware_data["storage"]
    links = [parse_link(raw) for raw in dialog_manager.dialog_data.get("new_links", [])]
    squads = available_squads(await storage.squads.all(), links)
    return {
        "has_available_squads": bool(squads),
        "squads": [{"id": s.id, "name": esc(s.name)} for s in squads],
    }


async def on_link_squad_chosen(_callback: CallbackQuery, _select, manager: DialogManager, item_id: str) -> None:
    manager.dialog_data["pending_link"] = {"type": LINK_TYPE_REMNAWAVE, "url": "", "squad_id": item_id}
    await manager.switch_to(AdminCreateCode.enter_link_name)


async def on_link_name_cancel(_callback: CallbackQuery, _button: Button, manager: DialogManager) -> None:
    manager.dialog_data.pop("pending_link", None)
    await manager.switch_to(AdminCreateCode.enter_links)


async def on_link_name_done(name: str, manager: DialogManager) -> None:
    pending = manager.dialog_data.pop("pending_link", None)
    if pending is not None:
        # A plain dict, not a Link instance - see step_links_getter.
        links: list[dict] = manager.dialog_data.setdefault("new_links", [])
        links.append(
            {"type": pending["type"], "name": name, "url": pending["url"], "squad_id": pending.get("squad_id", "")}
        )
    await manager.switch_to(AdminCreateCode.enter_links)


async def on_undo_last_link(_callback: CallbackQuery, _button: Button, manager: DialogManager) -> None:
    links = manager.dialog_data.get("new_links", [])
    if links:
        links.pop()


async def on_links_done(_callback: CallbackQuery, _button: Button, manager: DialogManager) -> None:
    if manager.dialog_data.get("new_links"):
        # Not manager.next(): that advances by window *registration* order,
        # which put enter_link_name right after enter_links (see
        # create_code_dialog below) once naming was added - .next() from
        # here would land on the name prompt instead of the description one.
        await manager.switch_to(AdminCreateCode.enter_description)


async def on_dialog_start(_start_data: object, manager: DialogManager) -> None:
    if not await ensure_admin(manager):
        await leave_admin_area(manager)


async def _finalize_creation(manager: DialogManager) -> None:
    storage: Storage = manager.middleware_data["storage"]
    user = manager.middleware_data["event_from_user"]

    code = manager.dialog_data["new_code"]
    links = [parse_link(raw) for raw in manager.dialog_data.get("new_links", [])]
    description = manager.dialog_data.get("new_description", "")
    await storage.codes.create(code=code, links=links, description=description, created_by=user.id)
    logger.info("%s created code %r with %d link(s)", actor(user), code, len(links))

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
    await _finalize_creation(manager)


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
            on_click=on_open_choose_link_squad,
            when="can_add_remnawave",
            style=icon("shield"),
        ),
        Button(I18N("admin-btn-undo"), id="undo_link", on_click=on_undo_last_link, when="has_links", style=icon("leftwards_arrow_with_hook")),
        Button(I18N("admin-btn-done"), id="links_done", on_click=on_links_done, when="has_links", style=icon("white_check_mark", ButtonStyle.SUCCESS)),
        Cancel(I18N("admin-btn-cancel"), style=_CANCEL_STYLE),
        state=AdminCreateCode.enter_links,
        getter=step_links_getter,
    ),
    Window(
        Case(
            {
                True: I18N("admin-create-code-choose-squad-prompt"),
                False: I18N("admin-create-code-squads-empty"),
            },
            selector="has_available_squads",
        ),
        Column(
            Select(
                I18N("admin-create-code-squad-item", name="{item[name]}"),
                id="cc_squad_select",
                item_id_getter=lambda item: item["id"],
                items="squads",
                on_click=on_link_squad_chosen,
                style=icon("shield"),
            ),
        ),
        SwitchTo(
            I18N("admin-btn-back"), id="back_to_links_from_squad", state=AdminCreateCode.enter_links, style=icon("arrow_backward")
        ),
        state=AdminCreateCode.choose_link_squad,
        getter=choose_link_squad_getter,
    ),
    build_field_window(
        LINK_NAME_FIELD,
        AdminCreateCode.enter_link_name,
        on_link_name_done,
        Button(I18N("admin-btn-back"), id="link_name_back", on_click=on_link_name_cancel, style=icon("arrow_backward")),
    ),
    build_field_window(
        DESCRIPTION_FIELD,
        AdminCreateCode.enter_description,
        on_description_done,
        Cancel(I18N("admin-btn-cancel"), style=_CANCEL_STYLE),
    ),
    on_start=on_dialog_start,
)
