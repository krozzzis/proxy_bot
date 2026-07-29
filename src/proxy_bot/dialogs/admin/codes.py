from __future__ import annotations

import logging

from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from aiogram_dialog import Dialog, DialogManager, Window
from aiogram_dialog.widgets.input import ManagedTextInput, TextInput
from aiogram_dialog.widgets.kbd import Button, Cancel, Column, Row, Select, SwitchTo
from aiogram_dialog.widgets.style.base import ButtonStyle
from aiogram_dialog.widgets.text import Case, Format, List, Multi

from proxy_bot.storage import Storage
from proxy_bot.utils.audit import actor
from proxy_bot.utils.html import esc

from ..common import icon, not_a_command
from ..widgets import I18N

logger = logging.getLogger(__name__)


class AdminCodes(StatesGroup):
    list = State()
    detail = State()
    enter_link = State()
    edit_description = State()

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
    }


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

    # Links can be far longer than Telegram's 64-byte callback_data limit,
    # so the remove-link buttons address links by position, not by value.
    link_items = [{"id": str(idx), "n": idx + 1} for idx in range(len(code.links))]
    return {
        "found": True,
        "code": esc(code.code),
        "description": esc(code.description or "—"),
        "has_links": bool(code.links),
        "links": [esc(link) for link in code.links],
        "link_items": link_items,
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


codes_dialog = Dialog(
    Window(
        Case(
            {
                True: Multi(I18N("admin-codes-title"), I18N("admin-page-indicator", when="has_pages"), sep=" "),
                False: I18N("admin-codes-empty"),
            },
            selector="has_codes",
        ),
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
                    Case(
                        {
                            True: List(Format("{pos}. <code>{item}</code>"), items="links", sep="\n"),
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
            I18N("admin-btn-edit-description"),
            id="edit_description",
            on_click=open_edit_description,
            when="found",
            style=icon("pencil2"),
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
        I18N("admin-code-add-link-prompt"),
        TextInput(id="add_link_input", on_success=on_link_entered, filter=not_a_command),
        SwitchTo(I18N("admin-btn-back"), id="back_to_detail", state=AdminCodes.detail, style=icon("arrow_backward")),
        state=AdminCodes.enter_link,
    ),
    Window(
        I18N("admin-code-edit-description-prompt"),
        TextInput(id="edit_description_input", on_success=on_description_entered, filter=not_a_command),
        SwitchTo(I18N("admin-btn-back"), id="back_to_detail2", state=AdminCodes.detail, style=icon("arrow_backward")),
        state=AdminCodes.edit_description,
    ),
)
