from __future__ import annotations

import asyncio
import logging

from aiogram import Bot
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from aiogram_dialog import Dialog, DialogManager, Window
from aiogram_dialog.widgets.input import ManagedTextInput, TextInput
from aiogram_dialog.widgets.kbd import Button, Cancel, Select, SwitchTo
from aiogram_dialog.widgets.style.base import ButtonStyle
from aiogram_dialog.widgets.text import Case, Format

from proxy_bot.storage import Storage, User
from proxy_bot.utils.audit import actor, actor_id
from proxy_bot.utils.html import esc

from ..common import icon, not_a_command
from ..widgets import I18N


class AdminBroadcast(StatesGroup):
    choose_target = State()
    choose_code = State()
    enter_text = State()
    confirm = State()

logger = logging.getLogger(__name__)

THROTTLE_SECONDS = 0.05


async def choose_all(_callback: CallbackQuery, _button: Button, manager: DialogManager) -> None:
    manager.dialog_data["target"] = "all"
    manager.dialog_data.pop("target_code", None)
    await manager.switch_to(AdminBroadcast.enter_text)


async def choose_by_code(_callback: CallbackQuery, _button: Button, manager: DialogManager) -> None:
    manager.dialog_data["target"] = "code"
    await manager.switch_to(AdminBroadcast.choose_code)


async def choose_code_getter(dialog_manager: DialogManager, **kwargs) -> dict:
    storage: Storage = dialog_manager.middleware_data["storage"]
    codes = await storage.codes.all()
    items = [{"id": c.code, "code": c.code, "description": esc(c.description) if c.description else ""} for c in codes]
    return {"has_codes": bool(codes), "codes": items}


async def on_code_chosen(_callback: CallbackQuery, _select, manager: DialogManager, item_id: str) -> None:
    manager.dialog_data["target_code"] = item_id
    await manager.switch_to(AdminBroadcast.enter_text)


async def on_text_entered(message: Message, widget: ManagedTextInput, manager: DialogManager, text: str) -> None:
    manager.dialog_data["broadcast_text"] = text.strip()
    await manager.switch_to(AdminBroadcast.confirm)


async def _recipients(manager: DialogManager) -> list[User]:
    storage: Storage = manager.middleware_data["storage"]
    if manager.dialog_data.get("target") == "code":
        code = manager.dialog_data.get("target_code", "")
        return await storage.users.users_with_code(code)
    return await storage.users.all()


async def confirm_getter(dialog_manager: DialogManager, **kwargs) -> dict:
    recipients = await _recipients(dialog_manager)
    text = dialog_manager.dialog_data.get("broadcast_text", "")
    return {"count": len(recipients), "text": esc(text)}


async def on_confirm_send(callback: CallbackQuery, _button: Button, manager: DialogManager) -> None:
    storage: Storage = manager.middleware_data["storage"]
    i18n = manager.middleware_data["i18n"]
    bot: Bot = manager.middleware_data["bot"]
    admin = manager.middleware_data["event_from_user"]

    recipients = await _recipients(manager)
    text = manager.dialog_data.get("broadcast_text", "")
    body = f"{i18n.get('broadcast-prefix')}\n\n{esc(text)}"

    if not recipients:
        await callback.message.answer(i18n.get("admin-broadcast-empty"))
        await manager.done()
        return

    sent = 0
    failed = 0
    for user in recipients:
        try:
            await bot.send_message(user.user_id, body)
            sent += 1
        except Exception:
            logger.warning("Broadcast message failed to reach %s", actor_id(user.user_id, user.username), exc_info=True)
            failed += 1
        await asyncio.sleep(THROTTLE_SECONDS)

    target = "all users" if manager.dialog_data.get("target") != "code" else f"code={manager.dialog_data.get('target_code')}"
    preview = text if len(text) <= 80 else f"{text[:77]}..."
    logger.info(
        "%s broadcast to %s (%d sent, %d failed): %r", actor(admin), target, sent, failed, preview
    )
    await callback.message.answer(i18n.get("admin-broadcast-done", sent=sent, failed=failed))
    await manager.done()


broadcast_dialog = Dialog(
    Window(
        I18N("admin-broadcast-target-prompt"),
        Button(I18N("admin-broadcast-target-all"), id="target_all", on_click=choose_all, style=icon("bust_in_silhouette")),
        Button(I18N("admin-broadcast-target-code"), id="target_code", on_click=choose_by_code, style=icon("package")),
        Cancel(I18N("admin-btn-cancel"), style=icon("x", ButtonStyle.DANGER)),
        state=AdminBroadcast.choose_target,
    ),
    Window(
        Case(
            {True: I18N("admin-broadcast-choose-code"), False: I18N("admin-broadcast-no-codes")},
            selector="has_codes",
        ),
        Select(
            Case(
                {True: Format("{item[code]} — {item[description]}"), False: Format("{item[code]}")},
                selector=lambda data, widget, manager: bool(data["item"]["description"]),
            ),
            id="code_select",
            item_id_getter=lambda item: item["id"],
            items="codes",
            on_click=on_code_chosen,
            style=icon("package"),
        ),
        SwitchTo(I18N("admin-btn-back"), id="back_to_target", state=AdminBroadcast.choose_target, style=icon("arrow_backward")),
        state=AdminBroadcast.choose_code,
        getter=choose_code_getter,
    ),
    Window(
        I18N("admin-broadcast-prompt-text"),
        TextInput(id="broadcast_text", on_success=on_text_entered, filter=not_a_command),
        SwitchTo(I18N("admin-btn-back"), id="back_to_target2", state=AdminBroadcast.choose_target, style=icon("arrow_backward")),
        state=AdminBroadcast.enter_text,
    ),
    Window(
        I18N("admin-broadcast-confirm"),
        Button(I18N("admin-btn-confirm"), id="confirm_send", on_click=on_confirm_send, style=icon("white_check_mark", ButtonStyle.SUCCESS)),
        Cancel(I18N("admin-btn-cancel"), style=icon("x", ButtonStyle.DANGER)),
        state=AdminBroadcast.confirm,
        getter=confirm_getter,
    ),
)
