from __future__ import annotations

import logging
import re

from aiogram.types import CallbackQuery, Message
from aiogram_dialog import Dialog, DialogManager, Window
from aiogram_dialog.widgets.input import ManagedTextInput, TextInput
from aiogram_dialog.widgets.kbd import Button, Cancel
from aiogram_dialog.widgets.style.base import ButtonStyle
from aiogram_dialog.widgets.text import Format

from proxy_bot.storage import Storage
from proxy_bot.utils.audit import actor
from proxy_bot.utils.html import esc

from ..common import icon, not_a_command
from ..states import AdminCreateCode

logger = logging.getLogger(__name__)

# Codes end up as Select callback_data (Telegram caps callback_data at 64
# bytes total, and aiogram-dialog adds its own widget/intent-id prefix on
# top), so keep codes well short of that ceiling.
CODE_RE = re.compile(r"^[A-Za-z0-9_-]{3,32}$")


async def step_code_getter(dialog_manager: DialogManager, i18n, **kwargs) -> dict:
    error = dialog_manager.dialog_data.get("code_error")
    prompt = i18n.get("admin-create-code-prompt-code")
    if error == "invalid":
        prompt = f"{i18n.get('admin-create-code-invalid')}\n\n{prompt}"
    elif error == "exists":
        prompt = f"{i18n.get('admin-create-code-exists')}\n\n{prompt}"
    return {"prompt": prompt, "cancel": i18n.get("admin-btn-cancel")}


async def step_links_getter(dialog_manager: DialogManager, i18n, **kwargs) -> dict:
    links = dialog_manager.dialog_data.get("new_links", [])
    lines = [i18n.get("admin-create-code-prompt-link")]
    if links:
        lines.append("")
        lines.append(i18n.get("admin-create-code-links-added", count=len(links)))
        lines.extend(f"{idx}. <code>{esc(link)}</code>" for idx, link in enumerate(links, start=1))
    return {
        "prompt": "\n".join(lines),
        "cancel": i18n.get("admin-btn-cancel"),
        "done": i18n.get("admin-btn-done"),
        "undo": i18n.get("admin-btn-undo"),
        "has_links": bool(links),
    }


async def step_description_getter(i18n, **kwargs) -> dict:
    return {"prompt": i18n.get("admin-create-code-prompt-description"), "cancel": i18n.get("admin-btn-cancel")}


async def on_code_input(message: Message, widget: ManagedTextInput, manager: DialogManager, code_text: str) -> None:
    storage: Storage = manager.middleware_data["storage"]
    code = code_text.strip()
    if not CODE_RE.match(code):
        manager.dialog_data["code_error"] = "invalid"
        return
    if await storage.codes.exists(code):
        manager.dialog_data["code_error"] = "exists"
        return
    manager.dialog_data["code_error"] = None
    manager.dialog_data["new_code"] = code
    await manager.next()


async def on_link_added(message: Message, widget: ManagedTextInput, manager: DialogManager, link_text: str) -> None:
    link = link_text.strip()
    if not link:
        return
    manager.dialog_data.setdefault("new_links", []).append(link)


async def on_undo_last_link(_callback: CallbackQuery, _button: Button, manager: DialogManager) -> None:
    links = manager.dialog_data.get("new_links", [])
    if links:
        links.pop()


async def on_links_done(_callback: CallbackQuery, _button: Button, manager: DialogManager) -> None:
    if manager.dialog_data.get("new_links"):
        await manager.next()


async def on_description_input(
    message: Message, widget: ManagedTextInput, manager: DialogManager, description_text: str
) -> None:
    storage: Storage = manager.middleware_data["storage"]
    i18n = manager.middleware_data["i18n"]
    user = manager.middleware_data["event_from_user"]

    description = description_text.strip()
    if description == "-":
        description = ""

    code = manager.dialog_data["new_code"]
    links = manager.dialog_data.get("new_links", [])
    await storage.codes.create(code=code, links=links, description=description, created_by=user.id)
    logger.info("%s created code %r with %d link(s)", actor(user), code, len(links))
    await message.answer(i18n.get("admin-create-code-done", code=esc(code)))
    await manager.done()


def create_code_dialog() -> Dialog:
    return Dialog(
        Window(
            Format("{prompt}"),
            TextInput(id="cc_code", on_success=on_code_input, filter=not_a_command),
            Cancel(Format("{cancel}"), style=icon("x", ButtonStyle.DANGER)),
            state=AdminCreateCode.enter_code,
            getter=step_code_getter,
        ),
        Window(
            Format("{prompt}"),
            TextInput(id="cc_link", on_success=on_link_added, filter=not_a_command),
            Button(Format("{undo}"), id="undo_link", on_click=on_undo_last_link, when="has_links", style=icon("leftwards_arrow_with_hook")),
            Button(Format("{done}"), id="links_done", on_click=on_links_done, when="has_links", style=icon("white_check_mark", ButtonStyle.SUCCESS)),
            Cancel(Format("{cancel}"), style=icon("x", ButtonStyle.DANGER)),
            state=AdminCreateCode.enter_links,
            getter=step_links_getter,
        ),
        Window(
            Format("{prompt}"),
            TextInput(id="cc_desc", on_success=on_description_input, filter=not_a_command),
            Cancel(Format("{cancel}"), style=icon("x", ButtonStyle.DANGER)),
            state=AdminCreateCode.enter_description,
            getter=step_description_getter,
        ),
    )
