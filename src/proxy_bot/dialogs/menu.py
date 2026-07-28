from __future__ import annotations

import logging
from typing import Literal

from aiogram.types import Message, User
from aiogram_dialog import Dialog, DialogManager, Window
from aiogram_dialog.widgets.input import ManagedTextInput, TextInput
from aiogram_dialog.widgets.kbd import Button, Group, SwitchTo
from aiogram_dialog.widgets.text import Format

from proxy_bot.storage import Code, Storage
from proxy_bot.utils.audit import actor
from proxy_bot.utils.formatting import format_links
from proxy_bot.utils.html import esc

from .common import icon, not_a_command
from .states import AdminMenu, UserMenu

logger = logging.getLogger(__name__)

ActivationStatus = Literal["banned", "invalid", "already", "added"]


async def _activate_code(storage: Storage, user: User, code_text: str) -> tuple[ActivationStatus, Code | None]:
    """Try to activate `code_text` for `user`. Shared by manual entry
    (on_code_entered) and /start deep-link auto-activation (on_dialog_start).
    """
    db_user = await storage.users.get_or_create(user.id, user.username, user.full_name)
    if db_user.banned:
        logger.info("Banned %s tried to enter code %r", actor(user), code_text.strip())
        return "banned", None

    code = code_text.strip()
    code_record = await storage.codes.get(code)
    if code_record is None or not code_record.active:
        logger.info("%s entered unknown code %r", actor(user), code)
        return "invalid", None

    added = await storage.users.add_code(user.id, code)
    if not added:
        logger.info("%s re-entered already-activated code %r", actor(user), code)
        return "already", code_record

    logger.info("%s activated code %r", actor(user), code)
    return "added", code_record


async def on_dialog_start(start_data, dialog_manager: DialogManager) -> None:
    storage: Storage = dialog_manager.middleware_data["storage"]
    user = dialog_manager.middleware_data["event_from_user"]
    await storage.users.get_or_create(user.id, user.username, user.full_name)

    if not isinstance(start_data, dict):
        return

    if start_data.get("greet"):
        dialog_manager.dialog_data["greet"] = True

    auto_code = start_data.get("auto_code")
    if not auto_code:
        return

    i18n = dialog_manager.middleware_data["i18n"]
    bot = dialog_manager.middleware_data["bot"]
    chat_id = dialog_manager.middleware_data["event_chat"].id

    status, _code_record = await _activate_code(storage, user, auto_code)
    if status in ("banned", "invalid"):
        dialog_manager.dialog_data["error"] = status
        await dialog_manager.switch_to(UserMenu.enter_code)
    else:
        text = i18n.get("code-already-added") if status == "already" else i18n.get("code-accepted")
        await bot.send_message(chat_id, text)
        await dialog_manager.switch_to(UserMenu.links)


async def on_open_enter_code(_callback, _widget, manager: DialogManager) -> None:
    # enter_code is a long-lived state in this menu, not a fresh dialog per
    # visit, so a leftover error from a previous failed attempt must be
    # cleared on the way in - clearing it in the getter would instead erase
    # the error before the user who just triggered it gets to see it.
    manager.dialog_data.pop("error", None)


async def open_admin_panel(_callback, _button: Button, manager: DialogManager) -> None:
    await manager.start(AdminMenu.main)


async def main_menu_getter(
    dialog_manager: DialogManager, i18n, event_from_user, storage: Storage, **kwargs
) -> dict:
    db_user = await storage.users.get_or_create(event_from_user.id, event_from_user.username, event_from_user.full_name)
    has_codes = bool(db_user.codes)

    # Shown once, right after a fresh /start - not on every return to this
    # window, so the greeting doesn't repeat every time the user navigates
    # back to the main menu.
    if dialog_manager.dialog_data.pop("greet", False):
        title = i18n.get("menu-title-greeting", name=esc(event_from_user.full_name), count=len(db_user.codes))
    else:
        title = i18n.get("menu-title", count=len(db_user.codes))
    return {
        "title": title,
        "btn_enter_code": i18n.get("menu-btn-enter-code"),
        "btn_links": i18n.get("menu-btn-links"),
        "btn_help": i18n.get("menu-btn-help"),
        "btn_admin": i18n.get("menu-btn-admin"),
        "has_codes": has_codes,
        "no_codes": not has_codes,
        "is_admin": await storage.admins.is_admin(event_from_user.id),
    }


async def enter_code_getter(dialog_manager: DialogManager, i18n, **kwargs) -> dict:
    error = dialog_manager.dialog_data.get("error")
    if error == "invalid":
        prompt = f"{i18n.get('code-invalid')}\n\n{i18n.get('code-prompt-again')}"
    elif error == "banned":
        prompt = i18n.get("code-banned")
    else:
        prompt = i18n.get("start-prompt-code")
    return {"prompt": prompt, "back": i18n.get("menu-btn-back")}


async def on_code_entered(
    message: Message,
    widget: ManagedTextInput,
    dialog_manager: DialogManager,
    code_text: str,
) -> None:
    storage: Storage = dialog_manager.middleware_data["storage"]
    i18n = dialog_manager.middleware_data["i18n"]
    user = message.from_user

    status, _code_record = await _activate_code(storage, user, code_text)
    if status in ("banned", "invalid"):
        dialog_manager.dialog_data["error"] = status
        return

    dialog_manager.dialog_data.pop("error", None)
    if status == "already":
        await message.answer(i18n.get("code-already-added"))
    else:
        await message.answer(i18n.get("code-accepted"))
    await dialog_manager.switch_to(UserMenu.links)


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

    return {
        "title": title,
        "btn_enter_code": i18n.get("menu-btn-enter-code"),
        "back": i18n.get("menu-btn-back"),
    }


async def help_getter(i18n, storage: Storage, event_from_user, **kwargs) -> dict:
    text = i18n.get("help-text")
    if await storage.admins.is_admin(event_from_user.id):
        text += "\n" + i18n.get("help-admin-suffix")
    return {"title": text, "back": i18n.get("menu-btn-back")}


def user_menu_dialog() -> Dialog:
    return Dialog(
        Window(
            Format("{title}"),
            # Passed directly to Window (not wrapped in Column, which is
            # Group(width=1) and would flatten every button below into its
            # own row regardless of the nested Group's width - Window
            # combines top-level keyboard widgets via Group(width=None)
            # instead, which preserves each one's own row layout).
            #
            # The primary slot always holds the one action that matters
            # most right now - "my links" once the user has any, "enter
            # code" while they don't - mirroring how Liberty VPN swaps its
            # single main-menu button between "Test" and "Manage
            # subscription" depending on account state.
            SwitchTo(
                Format("{btn_links}"), id="primary_links", state=UserMenu.links, when="has_codes", style=icon("key")
            ),
            SwitchTo(
                Format("{btn_enter_code}"),
                id="primary_enter_code",
                state=UserMenu.enter_code,
                on_click=on_open_enter_code,
                when="no_codes",
                style=icon("heavy_plus_sign"),
            ),
            Group(
                SwitchTo(
                    Format("{btn_enter_code}"),
                    id="open_enter_code",
                    state=UserMenu.enter_code,
                    on_click=on_open_enter_code,
                    when="has_codes",
                    style=icon("heavy_plus_sign"),
                ),
                SwitchTo(
                    Format("{btn_links}"), id="open_links", state=UserMenu.links, when="no_codes", style=icon("key")
                ),
                SwitchTo(Format("{btn_help}"), id="open_help", state=UserMenu.help, style=icon("question")),
                width=2,
            ),
            Button(Format("{btn_admin}"), id="open_admin", on_click=open_admin_panel, when="is_admin", style=icon("gear")),
            state=UserMenu.main,
            getter=main_menu_getter,
        ),
        Window(
            Format("{prompt}"),
            TextInput(
                id="code_input",
                on_success=on_code_entered,
                filter=not_a_command,
            ),
            SwitchTo(Format("{back}"), id="back_to_menu", state=UserMenu.main, style=icon("arrow_backward")),
            state=UserMenu.enter_code,
            getter=enter_code_getter,
        ),
        Window(
            Format("{title}"),
            SwitchTo(
                Format("{btn_enter_code}"),
                id="open_enter_code_from_links",
                state=UserMenu.enter_code,
                on_click=on_open_enter_code,
                style=icon("heavy_plus_sign"),
            ),
            SwitchTo(Format("{back}"), id="back_to_menu2", state=UserMenu.main, style=icon("arrow_backward")),
            state=UserMenu.links,
            getter=links_getter,
        ),
        Window(
            Format("{title}"),
            SwitchTo(Format("{back}"), id="back_to_menu3", state=UserMenu.main, style=icon("arrow_backward")),
            state=UserMenu.help,
            getter=help_getter,
        ),
        on_start=on_dialog_start,
    )
