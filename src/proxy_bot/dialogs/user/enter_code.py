from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message
from aiogram_dialog import Dialog, DialogManager, Window
from aiogram_dialog.widgets.input import ManagedTextInput, TextInput
from aiogram_dialog.widgets.kbd import Cancel
from aiogram_dialog.widgets.text import Case, Multi

from proxy_bot.storage import Storage

from ..common import BRANDED_LOGO_MEDIA, branded_logo_getter, icon, not_a_command
from ..widgets import I18N
from .activation import activate_code


class EnterCode(StatesGroup):
    main = State()


async def on_start(start_data: object, dialog_manager: DialogManager) -> None:
    if isinstance(start_data, dict) and start_data.get("error"):
        dialog_manager.dialog_data["error"] = start_data["error"]


async def enter_code_getter(dialog_manager: DialogManager, **kwargs) -> dict:
    return {"error": dialog_manager.dialog_data.get("error")}


async def on_code_entered(
    message: Message,
    widget: ManagedTextInput,
    dialog_manager: DialogManager,
    code_text: str,
) -> None:
    storage: Storage = dialog_manager.middleware_data["storage"]
    remnawave = dialog_manager.middleware_data.get("remnawave")
    user = message.from_user

    status, _code_record = await activate_code(storage, remnawave, user, code_text)
    if status in ("banned", "invalid"):
        dialog_manager.dialog_data["error"] = status
        return

    banner_key = "code-already-added" if status == "already" else "code-accepted"
    # Handed to whichever dialog started us (the main menu, or the links
    # screen itself) via its on_process_result, so the confirmation renders
    # as part of THEIR next message instead of a message of its own - one
    # extra message per activation, sent out of order, is what this avoids.
    await dialog_manager.done(result={"banner": banner_key})


enter_code_dialog = Dialog(
    Window(
        BRANDED_LOGO_MEDIA,
        Case(
            {
                "invalid": Multi(I18N("code-invalid"), I18N("code-prompt-again"), sep="\n\n"),
                "banned": I18N("code-banned"),
                None: I18N("start-prompt-code"),
            },
            selector="error",
        ),
        TextInput(
            id="code_input",
            on_success=on_code_entered,
            filter=not_a_command,
        ),
        Cancel(I18N("menu-btn-back"), style=icon("arrow_backward")),
        state=EnterCode.main,
        getter=[enter_code_getter, branded_logo_getter],
    ),
    on_start=on_start,
)
