from __future__ import annotations

import logging

from aiogram.types import Message
from aiogram_dialog import Dialog, DialogManager, Window
from aiogram_dialog.widgets.input import ManagedTextInput, TextInput
from aiogram_dialog.widgets.kbd import Column, SwitchTo
from aiogram_dialog.widgets.text import Format

from proxy_bot.storage import Storage
from proxy_bot.utils.audit import actor
from proxy_bot.utils.formatting import format_links
from proxy_bot.utils.html import esc

from .common import not_a_command
from .states import UserMenu

logger = logging.getLogger(__name__)


async def on_dialog_start(start_data, dialog_manager: DialogManager) -> None:
    storage: Storage = dialog_manager.middleware_data["storage"]
    user = dialog_manager.middleware_data["event_from_user"]
    await storage.users.get_or_create(user.id, user.username, user.full_name)
    if isinstance(start_data, dict) and start_data.get("greet"):
        dialog_manager.dialog_data["greet"] = True


async def on_open_enter_code(_callback, _widget, manager: DialogManager) -> None:
    # enter_code is a long-lived state in this menu, not a fresh dialog per
    # visit, so a leftover error from a previous failed attempt must be
    # cleared on the way in - clearing it in the getter would instead erase
    # the error before the user who just triggered it gets to see it.
    manager.dialog_data.pop("error", None)


async def main_menu_getter(dialog_manager: DialogManager, i18n, event_from_user, **kwargs) -> dict:
    # Shown once, right after a fresh /start - not on every return to this
    # window, so the greeting doesn't repeat every time the user navigates
    # back to the main menu.
    if dialog_manager.dialog_data.pop("greet", False):
        title = i18n.get("menu-title-greeting", name=esc(event_from_user.full_name))
    else:
        title = i18n.get("menu-title")
    return {
        "title": title,
        "btn_enter_code": i18n.get("menu-btn-enter-code"),
        "btn_links": i18n.get("menu-btn-links"),
        "btn_help": i18n.get("menu-btn-help"),
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

    db_user = await storage.users.get_or_create(user.id, user.username, user.full_name)
    if db_user.banned:
        dialog_manager.dialog_data["error"] = "banned"
        logger.info("Banned %s tried to enter code %r", actor(user), code_text.strip())
        return

    code = code_text.strip()
    code_record = await storage.codes.get(code)
    if code_record is None or not code_record.active:
        dialog_manager.dialog_data["error"] = "invalid"
        logger.info("%s entered unknown code %r", actor(user), code)
        return

    dialog_manager.dialog_data.pop("error", None)
    added = await storage.users.add_code(user.id, code)
    if not added:
        await message.answer(i18n.get("code-already-added"))
        logger.info("%s re-entered already-activated code %r", actor(user), code)
    else:
        await message.answer(f"{i18n.get('code-accepted')}\n\n{format_links(code_record.links)}")
        logger.info("%s activated code %r", actor(user), code)
    await dialog_manager.switch_to(UserMenu.main)


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
        text += i18n.get("help-admin-suffix")
    return {"title": text, "back": i18n.get("menu-btn-back")}


def user_menu_dialog() -> Dialog:
    return Dialog(
        Window(
            Format("{title}"),
            Column(
                SwitchTo(
                    Format("{btn_enter_code}"),
                    id="open_enter_code",
                    state=UserMenu.enter_code,
                    on_click=on_open_enter_code,
                ),
                SwitchTo(Format("{btn_links}"), id="open_links", state=UserMenu.links),
                SwitchTo(Format("{btn_help}"), id="open_help", state=UserMenu.help),
            ),
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
            SwitchTo(Format("{back}"), id="back_to_menu", state=UserMenu.main),
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
            ),
            SwitchTo(Format("{back}"), id="back_to_menu2", state=UserMenu.main),
            state=UserMenu.links,
            getter=links_getter,
        ),
        Window(
            Format("{title}"),
            SwitchTo(Format("{back}"), id="back_to_menu3", state=UserMenu.main),
            state=UserMenu.help,
            getter=help_getter,
        ),
        on_start=on_dialog_start,
    )
