from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError, TelegramRetryAfter
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, ContentType, Message
from aiogram_dialog import Dialog, DialogManager, Window
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Button, Cancel, Select, SwitchTo
from aiogram_dialog.widgets.style.base import ButtonStyle
from aiogram_dialog.widgets.text import Case, Format
from pydantic import TypeAdapter

from proxy_bot.storage import Storage, User
from proxy_bot.utils.audit import actor, actor_id
from proxy_bot.utils.html import esc

from ..common import icon, not_a_command
from ..forms import FormField, build_field_window
from ..widgets import I18N
from .access import ensure_admin, leave_admin_area


class AdminBroadcast(StatesGroup):
    choose_target = State()
    choose_code = State()
    enter_content = State()
    edit_title = State()
    confirm = State()


logger = logging.getLogger(__name__)

THROTTLE_SECONDS = 0.05

_CANCEL_STYLE = icon("x", ButtonStyle.DANGER)

# Content types a broadcast can carry. Anything else (polls, locations,
# service messages, ...) simply isn't accepted by the enter_content window.
_CAPTION_CAPABLE = {
    ContentType.PHOTO,
    ContentType.VIDEO,
    ContentType.ANIMATION,
    ContentType.DOCUMENT,
    ContentType.AUDIO,
    ContentType.VOICE,
}
_BROADCASTABLE = _CAPTION_CAPABLE | {ContentType.TEXT, ContentType.VIDEO_NOTE, ContentType.STICKER}

_CONTENT_TYPE_LABELS = {
    ContentType.PHOTO: "admin-broadcast-type-photo",
    ContentType.VIDEO: "admin-broadcast-type-video",
    ContentType.ANIMATION: "admin-broadcast-type-animation",
    ContentType.DOCUMENT: "admin-broadcast-type-document",
    ContentType.AUDIO: "admin-broadcast-type-audio",
    ContentType.VOICE: "admin-broadcast-type-voice",
    ContentType.VIDEO_NOTE: "admin-broadcast-type-video-note",
    ContentType.STICKER: "admin-broadcast-type-sticker",
}

_FAILURE_KEYS = {
    "never_started": "admin-broadcast-fail-never-started",
    "blocked": "admin-broadcast-fail-blocked",
    "deactivated": "admin-broadcast-fail-deactivated",
    "other": "admin-broadcast-fail-other",
}


async def on_dialog_start(_start_data: object, manager: DialogManager) -> None:
    if not await ensure_admin(manager):
        await leave_admin_area(manager)


async def choose_all(_callback: CallbackQuery, _button: Button, manager: DialogManager) -> None:
    manager.dialog_data["target"] = "all"
    manager.dialog_data.pop("target_code", None)
    await manager.switch_to(AdminBroadcast.enter_content)


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
    await manager.switch_to(AdminBroadcast.enter_content)


async def on_content_entered(message: Message, _widget: MessageInput, manager: DialogManager) -> None:
    manager.dialog_data["content_type"] = message.content_type
    if message.content_type == ContentType.TEXT:
        manager.dialog_data["body_html"] = message.html_text
        manager.dialog_data.pop("source_chat_id", None)
        manager.dialog_data.pop("source_message_id", None)
    else:
        manager.dialog_data["source_chat_id"] = message.chat.id
        manager.dialog_data["source_message_id"] = message.message_id
        manager.dialog_data["caption_html"] = message.html_text if message.content_type in _CAPTION_CAPABLE else ""
        manager.dialog_data.pop("body_html", None)
    await manager.switch_to(AdminBroadcast.confirm)


async def _recipients(manager: DialogManager) -> list[User]:
    storage: Storage = manager.middleware_data["storage"]
    if manager.dialog_data.get("target") == "code":
        code = manager.dialog_data.get("target_code", "")
        return await storage.users.users_with_code(code)
    return await storage.users.all()


def _effective_prefix(dialog_data: dict, i18n) -> str:
    """The rich-HTML line that opens every broadcast: the admin's custom
    title if one was set (including an explicitly emptied ""), otherwise
    the default `broadcast-prefix` banner - icon and all."""
    title = dialog_data.get("title_html")
    return i18n.get("broadcast-prefix") if title is None else title


def _compose_text(dialog_data: dict, i18n) -> str:
    prefix = _effective_prefix(dialog_data, i18n)
    body = dialog_data.get("body_html", "")
    return f"{prefix}\n\n{body}" if prefix else body


def _compose_caption(dialog_data: dict, i18n) -> str | None:
    """The caption override to hand `copy_message`, or None to leave the
    original media's caption untouched (no title to prepend)."""
    prefix = _effective_prefix(dialog_data, i18n)
    if not prefix:
        return None
    caption = dialog_data.get("caption_html", "")
    return f"{prefix}\n\n{caption}" if caption else prefix


def _preview(dialog_data: dict, i18n) -> str:
    content_type = dialog_data.get("content_type")
    if content_type == ContentType.TEXT:
        return _compose_text(dialog_data, i18n)
    label = i18n.get(_CONTENT_TYPE_LABELS.get(content_type, "admin-broadcast-type-other"))
    if content_type in _CAPTION_CAPABLE:
        caption = _compose_caption(dialog_data, i18n)
        body = caption if caption is not None else dialog_data.get("caption_html", "")
        return f"{label}\n\n{body}" if body else label
    prefix = _effective_prefix(dialog_data, i18n)
    return f"{prefix}\n\n{label}" if prefix else label


async def confirm_getter(dialog_manager: DialogManager, **kwargs) -> dict:
    i18n = dialog_manager.middleware_data["i18n"]
    recipients = await _recipients(dialog_manager)
    return {"count": len(recipients), "preview": _preview(dialog_manager.dialog_data, i18n)}


async def open_edit_title(_callback: CallbackQuery, _button: Button, manager: DialogManager) -> None:
    await manager.switch_to(AdminBroadcast.edit_title)


async def _title_extra_getter(manager: DialogManager) -> dict:
    i18n = manager.middleware_data["i18n"]
    return {"current_title": esc(_effective_prefix(manager.dialog_data, i18n))}


async def on_title_done(title_html: str, manager: DialogManager) -> None:
    manager.dialog_data["title_html"] = title_html
    await manager.switch_to(AdminBroadcast.confirm)


_TITLE_FIELD = FormField(
    name="broadcast_title",
    type_adapter=TypeAdapter(str),
    prompt="admin-broadcast-title-prompt",
    invalid_label="admin-broadcast-title-prompt",  # unreachable: TypeAdapter(str) never fails
    optional=True,
    skip_label="admin-broadcast-title-empty-btn",
    default="",
    rich=True,
    extra_getter=_title_extra_getter,
)


@dataclass(frozen=True)
class _SendPlan:
    """What to send to every recipient, computed once before the loop -
    Fluent rendering (the default title) and HTML composition don't depend
    on who the recipient is."""

    content_type: str
    text: str | None = None  # ContentType.TEXT
    from_chat_id: int | None = None  # everything else: copy_message source
    message_id: int | None = None
    caption: str | None = None  # caption override for _CAPTION_CAPABLE types
    lead_text: str | None = None  # sent before the copy, for caption-less types


def _build_send_plan(dialog_data: dict, i18n) -> _SendPlan:
    content_type = dialog_data.get("content_type")
    if content_type == ContentType.TEXT:
        return _SendPlan(content_type=content_type, text=_compose_text(dialog_data, i18n))

    from_chat_id = dialog_data["source_chat_id"]
    message_id = dialog_data["source_message_id"]
    if content_type in _CAPTION_CAPABLE:
        return _SendPlan(
            content_type=content_type,
            from_chat_id=from_chat_id,
            message_id=message_id,
            caption=_compose_caption(dialog_data, i18n),
        )

    # Stickers, video notes, and anything else with no caption of its own -
    # a title can't be attached to the copy, so it goes out as its own
    # message right before it.
    return _SendPlan(
        content_type=content_type,
        from_chat_id=from_chat_id,
        message_id=message_id,
        lead_text=_effective_prefix(dialog_data, i18n) or None,
    )


async def _send_one(bot: Bot, chat_id: int, plan: _SendPlan) -> None:
    if plan.content_type == ContentType.TEXT:
        await bot.send_message(chat_id, plan.text)
        return
    if plan.lead_text:
        await bot.send_message(chat_id, plan.lead_text)
    await bot.copy_message(chat_id, from_chat_id=plan.from_chat_id, message_id=plan.message_id, caption=plan.caption)


async def on_confirm_send(callback: CallbackQuery, _button: Button, manager: DialogManager) -> None:
    if not await ensure_admin(manager):
        await leave_admin_area(manager)
        return

    i18n = manager.middleware_data["i18n"]
    bot: Bot = manager.middleware_data["bot"]
    admin = manager.middleware_data["event_from_user"]
    dialog_data = manager.dialog_data

    recipients = await _recipients(manager)
    if not recipients:
        await callback.message.answer(i18n.get("admin-broadcast-empty"))
        await manager.done()
        return

    plan = _build_send_plan(dialog_data, i18n)
    sent = 0
    failures = {"never_started": 0, "blocked": 0, "deactivated": 0, "other": 0}
    for user in recipients:
        target = actor_id(user.user_id, user.username)
        try:
            await _send_one(bot, user.user_id, plan)
            sent += 1
        except TelegramRetryAfter as exc:
            await asyncio.sleep(exc.retry_after)
            try:
                await _send_one(bot, user.user_id, plan)
                sent += 1
            except Exception:
                logger.warning("Broadcast message failed to reach %s after flood-wait retry", target, exc_info=True)
                failures["other"] += 1
        except TelegramForbiddenError as exc:
            bucket = "deactivated" if "deactivated" in str(exc).lower() else "blocked"
            logger.info("Broadcast message to %s classified as %r: %s", target, bucket, exc)
            failures[bucket] += 1
        except TelegramBadRequest as exc:
            if "chat not found" in str(exc).lower():
                logger.info("Broadcast message to %s classified as 'never_started': %s", target, exc)
                failures["never_started"] += 1
            else:
                logger.warning("Broadcast message failed to reach %s", target, exc_info=True)
                failures["other"] += 1
        except Exception:
            logger.warning("Broadcast message failed to reach %s", target, exc_info=True)
            failures["other"] += 1
        await asyncio.sleep(THROTTLE_SECONDS)

    failure_lines = [i18n.get(_FAILURE_KEYS[bucket], count=count) for bucket, count in failures.items() if count]
    failures_block = ("\n\n" + "\n".join(failure_lines)) if failure_lines else ""

    target_desc = "all users" if dialog_data.get("target") != "code" else f"code={dialog_data.get('target_code')}"
    logger.info(
        "%s broadcast (%s) to %s: %d sent, failures=%s",
        actor(admin),
        dialog_data.get("content_type"),
        target_desc,
        sent,
        {k: v for k, v in failures.items() if v},
    )
    await callback.message.answer(i18n.get("admin-broadcast-done", sent=sent, failures=failures_block))
    await manager.done()


broadcast_dialog = Dialog(
    Window(
        I18N("admin-broadcast-target-prompt"),
        Button(I18N("admin-broadcast-target-all"), id="target_all", on_click=choose_all, style=icon("bust_in_silhouette")),
        Button(I18N("admin-broadcast-target-code"), id="target_code", on_click=choose_by_code, style=icon("package")),
        Cancel(I18N("admin-btn-cancel"), style=_CANCEL_STYLE),
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
        I18N("admin-broadcast-prompt-content"),
        MessageInput(on_content_entered, content_types=list(_BROADCASTABLE), filter=not_a_command),
        SwitchTo(I18N("admin-btn-back"), id="back_to_target2", state=AdminBroadcast.choose_target, style=icon("arrow_backward")),
        state=AdminBroadcast.enter_content,
    ),
    build_field_window(
        _TITLE_FIELD,
        AdminBroadcast.edit_title,
        on_title_done,
        SwitchTo(I18N("admin-btn-cancel"), id="back_to_confirm_from_title", state=AdminBroadcast.confirm, style=_CANCEL_STYLE),
    ),
    Window(
        I18N("admin-broadcast-confirm"),
        Button(I18N("admin-btn-confirm"), id="confirm_send", on_click=on_confirm_send, style=icon("white_check_mark", ButtonStyle.SUCCESS)),
        Button(I18N("admin-broadcast-edit-title-btn"), id="edit_title", on_click=open_edit_title, style=icon("pencil2")),
        Cancel(I18N("admin-btn-cancel"), style=_CANCEL_STYLE),
        state=AdminBroadcast.confirm,
        getter=confirm_getter,
    ),
    on_start=on_dialog_start,
)
