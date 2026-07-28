from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup
from aiogram_dialog import Dialog, DialogManager, Window
from aiogram_dialog.widgets.kbd import Button, Cancel
from aiogram_dialog.widgets.text import Format

from proxy_bot.storage import Storage
from proxy_bot.utils.formatting import format_links
from proxy_bot.utils.html import esc

from ..common import icon
from .enter_code import EnterCode


class Links(StatesGroup):
    main = State()


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


async def links_getter(dialog_manager: DialogManager, i18n, **kwargs) -> dict:
    storage: Storage = dialog_manager.middleware_data["storage"]
    user = dialog_manager.middleware_data["event_from_user"]
    db_user = await storage.users.get_or_create(user.id, user.username, user.full_name)

    if not db_user.codes:
        title = i18n.get("link-none")
    else:
        lines = [i18n.get("link-header")]
        for code in db_user.codes:
            code_record = await storage.codes.get(code)
            if code_record is None:
                continue
            lines.append(
                i18n.get(
                    "link-item",
                    description=esc(code_record.description or code_record.code),
                    code=esc(code_record.code),
                    links=format_links(code_record.links),
                )
            )
        title = "\n\n".join(lines)

    banner = dialog_manager.dialog_data.pop("banner", None)
    if banner:
        title = f"{banner}\n\n{title}"

    return {
        "title": title,
        "btn_enter_code": i18n.get("menu-btn-enter-code"),
        "back": i18n.get("menu-btn-back"),
    }


async def open_enter_code(_callback, _button, manager: DialogManager) -> None:
    await manager.start(EnterCode.main)


links_dialog = Dialog(
    Window(
        Format("{title}"),
        Button(
            Format("{btn_enter_code}"),
            id="open_enter_code_from_links",
            on_click=open_enter_code,
            style=icon("heavy_plus_sign"),
        ),
        Cancel(Format("{back}"), style=icon("arrow_backward")),
        state=Links.main,
        getter=links_getter,
    ),
    on_start=on_start,
    on_process_result=on_enter_code_result,
)
