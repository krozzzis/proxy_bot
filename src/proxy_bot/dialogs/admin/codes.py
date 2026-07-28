from __future__ import annotations

import logging

from aiogram.types import CallbackQuery, Message
from aiogram_dialog import Dialog, DialogManager, Window
from aiogram_dialog.widgets.input import ManagedTextInput, TextInput
from aiogram_dialog.widgets.kbd import Button, Cancel, Column, Row, Select, SwitchTo
from aiogram_dialog.widgets.style.base import ButtonStyle
from aiogram_dialog.widgets.text import Format

from proxy_bot.storage import Storage
from proxy_bot.utils.audit import actor
from proxy_bot.utils.html import esc

from ..common import icon, not_a_command
from ..states import AdminCodes

logger = logging.getLogger(__name__)

PAGE_SIZE = 8


async def codes_list_getter(dialog_manager: DialogManager, i18n, **kwargs) -> dict:
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
            "label": i18n.get(
                "admin-codes-item",
                code=c.code,
                description=c.description or "—",
                count=len(c.links),
            ),
        }
        for c in chunk
    ]
    if codes:
        title = f"{i18n.get('admin-codes-title', count=len(codes))}  ({page + 1}/{total_pages})"
    else:
        title = i18n.get("admin-codes-empty")
    return {
        "title": title,
        "codes": items,
        "back": i18n.get("admin-btn-back"),
        "prev": i18n.get("admin-btn-prev"),
        "next": i18n.get("admin-btn-next"),
    }


async def on_code_selected(_callback: CallbackQuery, _select, manager: DialogManager, item_id: str) -> None:
    manager.dialog_data["selected_code"] = item_id
    await manager.switch_to(AdminCodes.detail)


async def on_prev_page(_callback: CallbackQuery, _button: Button, manager: DialogManager) -> None:
    manager.dialog_data["page"] = max(0, manager.dialog_data.get("page", 0) - 1)


async def on_next_page(_callback: CallbackQuery, _button: Button, manager: DialogManager) -> None:
    manager.dialog_data["page"] = manager.dialog_data.get("page", 0) + 1


async def codes_detail_getter(dialog_manager: DialogManager, i18n, **kwargs) -> dict:
    storage: Storage = dialog_manager.middleware_data["storage"]
    code_id = dialog_manager.dialog_data.get("selected_code")
    code = await storage.codes.get(code_id) if code_id else None

    if code is None:
        return {
            "title": i18n.get("admin-codes-empty"),
            "link_items": [],
            "back": i18n.get("admin-btn-back"),
            "add_link": "",
            "edit_description": "",
            "delete_code": "",
        }

    lines = [i18n.get("admin-code-detail-title", code=esc(code.code), description=esc(code.description or "—"))]
    if code.links:
        lines.append("")
        lines.extend(f"{idx}. <code>{esc(link)}</code>" for idx, link in enumerate(code.links, start=1))
    else:
        lines.append("")
        lines.append(i18n.get("admin-code-no-links"))

    # Links can be far longer than Telegram's 64-byte callback_data limit,
    # so the remove-link buttons address links by position, not by value.
    link_items = [
        {"id": str(idx), "label": i18n.get("admin-code-remove-link-btn", n=idx + 1)}
        for idx in range(len(code.links))
    ]
    return {
        "title": "\n".join(lines),
        "link_items": link_items,
        "add_link": i18n.get("admin-btn-add-link"),
        "edit_description": i18n.get("admin-btn-edit-description"),
        "delete_code": i18n.get("admin-btn-delete-code"),
        "back": i18n.get("admin-btn-back"),
    }


async def on_remove_link(callback: CallbackQuery, _select, manager: DialogManager, item_id: str) -> None:
    storage: Storage = manager.middleware_data["storage"]
    i18n = manager.middleware_data["i18n"]
    admin = manager.middleware_data["event_from_user"]
    code_id = manager.dialog_data.get("selected_code")

    code = await storage.codes.get(code_id)
    if code is None:
        return
    index = int(item_id)
    if not (0 <= index < len(code.links)):
        return
    link = code.links[index]
    await storage.codes.remove_link(code_id, link)
    logger.info("%s removed a link from code %r", actor(admin), code_id)
    await callback.answer(i18n.get("admin-code-link-removed"))


async def open_add_link(_callback: CallbackQuery, _button: Button, manager: DialogManager) -> None:
    await manager.switch_to(AdminCodes.enter_link)


async def enter_link_getter(i18n, **kwargs) -> dict:
    return {"prompt": i18n.get("admin-code-add-link-prompt"), "back": i18n.get("admin-btn-back")}


async def on_link_entered(message: Message, widget: ManagedTextInput, manager: DialogManager, link_text: str) -> None:
    storage: Storage = manager.middleware_data["storage"]
    i18n = manager.middleware_data["i18n"]
    admin = manager.middleware_data["event_from_user"]
    code_id = manager.dialog_data.get("selected_code")

    link = link_text.strip()
    if link:
        await storage.codes.add_link(code_id, link)
        logger.info("%s added a link to code %r", actor(admin), code_id)
        await message.answer(i18n.get("admin-code-link-added"))
    await manager.switch_to(AdminCodes.detail)


async def open_edit_description(_callback: CallbackQuery, _button: Button, manager: DialogManager) -> None:
    await manager.switch_to(AdminCodes.edit_description)


async def edit_description_getter(i18n, **kwargs) -> dict:
    return {"prompt": i18n.get("admin-code-edit-description-prompt"), "back": i18n.get("admin-btn-back")}


async def on_description_entered(
    message: Message, widget: ManagedTextInput, manager: DialogManager, description_text: str
) -> None:
    storage: Storage = manager.middleware_data["storage"]
    i18n = manager.middleware_data["i18n"]
    admin = manager.middleware_data["event_from_user"]
    code_id = manager.dialog_data.get("selected_code")

    description = description_text.strip()
    if description == "-":
        description = ""
    await storage.codes.set_description(code_id, description)
    logger.info("%s changed description of code %r", actor(admin), code_id)
    await message.answer(i18n.get("admin-code-description-updated"))
    await manager.switch_to(AdminCodes.detail)


async def on_delete_code(callback: CallbackQuery, _button: Button, manager: DialogManager) -> None:
    storage: Storage = manager.middleware_data["storage"]
    i18n = manager.middleware_data["i18n"]
    admin = manager.middleware_data["event_from_user"]
    code_id = manager.dialog_data.get("selected_code")

    await storage.codes.delete(code_id)
    logger.info("%s deleted code %r", actor(admin), code_id)
    await callback.answer(i18n.get("admin-code-deleted", code=code_id), show_alert=True)
    await manager.switch_to(AdminCodes.list)


def codes_dialog() -> Dialog:
    return Dialog(
        Window(
            Format("{title}"),
            Column(
                Select(
                    Format("{item[label]}"),
                    id="code_select",
                    item_id_getter=lambda item: item["id"],
                    items="codes",
                    on_click=on_code_selected,
                    style=icon("package"),
                ),
            ),
            Row(
                Button(Format("{prev}"), id="prev_page", on_click=on_prev_page, style=icon("chevron_left")),
                Button(Format("{next}"), id="next_page", on_click=on_next_page, style=icon("chevron_right")),
            ),
            Cancel(Format("{back}"), style=icon("arrow_backward")),
            state=AdminCodes.list,
            getter=codes_list_getter,
        ),
        Window(
            Format("{title}"),
            Column(
                Select(
                    Format("{item[label]}"),
                    id="remove_link_select",
                    item_id_getter=lambda item: item["id"],
                    items="link_items",
                    on_click=on_remove_link,
                    style=icon("x", ButtonStyle.DANGER),
                ),
            ),
            Button(Format("{add_link}"), id="add_link", on_click=open_add_link, style=icon("heavy_plus_sign")),
            Button(Format("{edit_description}"), id="edit_description", on_click=open_edit_description, style=icon("pencil2")),
            Button(Format("{delete_code}"), id="delete_code", on_click=on_delete_code, style=icon("wastebasket", ButtonStyle.DANGER)),
            SwitchTo(Format("{back}"), id="back_to_list", state=AdminCodes.list, style=icon("arrow_backward")),
            state=AdminCodes.detail,
            getter=codes_detail_getter,
        ),
        Window(
            Format("{prompt}"),
            TextInput(id="add_link_input", on_success=on_link_entered, filter=not_a_command),
            SwitchTo(Format("{back}"), id="back_to_detail", state=AdminCodes.detail, style=icon("arrow_backward")),
            state=AdminCodes.enter_link,
            getter=enter_link_getter,
        ),
        Window(
            Format("{prompt}"),
            TextInput(id="edit_description_input", on_success=on_description_entered, filter=not_a_command),
            SwitchTo(Format("{back}"), id="back_to_detail2", state=AdminCodes.detail, style=icon("arrow_backward")),
            state=AdminCodes.edit_description,
            getter=edit_description_getter,
        ),
    )
