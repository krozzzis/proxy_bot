from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message
from aiogram_dialog import Dialog, DialogManager, Window
from aiogram_dialog.widgets.input import ManagedTextInput, TextInput
from aiogram_dialog.widgets.kbd import Cancel
from aiogram_dialog.widgets.text import Format

from proxy_bot.storage import Storage

from ..common import icon, not_a_command
from .activation import activate_code


class EnterCode(StatesGroup):
    main = State()


async def on_start(start_data: object, dialog_manager: DialogManager) -> None:
    if isinstance(start_data, dict) and start_data.get("error"):
        dialog_manager.dialog_data["error"] = start_data["error"]


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

    status, _code_record = await activate_code(storage, user, code_text)
    if status in ("banned", "invalid"):
        dialog_manager.dialog_data["error"] = status
        return

    banner = i18n.get("code-already-added") if status == "already" else i18n.get("code-accepted")
    # Handed to whichever dialog started us (the main menu, or the links
    # screen itself) via its on_process_result, so the confirmation renders
    # as part of THEIR next message instead of a message of its own - one
    # extra message per activation, sent out of order, is what this avoids.
    await dialog_manager.done(result={"banner": banner})


enter_code_dialog = Dialog(
    Window(
        Format("{prompt}"),
        TextInput(
            id="code_input",
            on_success=on_code_entered,
            filter=not_a_command,
        ),
        Cancel(Format("{back}"), style=icon("arrow_backward")),
        state=EnterCode.main,
        getter=enter_code_getter,
    ),
    on_start=on_start,
)
