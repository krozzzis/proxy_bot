from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup
from aiogram_dialog import Dialog, Window
from aiogram_dialog.widgets.kbd import Cancel
from aiogram_dialog.widgets.text import Format

from proxy_bot.storage import Storage

from ..common import icon


class Help(StatesGroup):
    main = State()


async def help_getter(i18n, storage: Storage, event_from_user, **kwargs) -> dict:
    text = i18n.get("help-text")
    if await storage.admins.is_admin(event_from_user.id):
        text += "\n\n" + i18n.get("help-admin-suffix")
    return {"title": text, "back": i18n.get("menu-btn-back")}


help_dialog = Dialog(
    Window(
        Format("{title}"),
        Cancel(Format("{back}"), style=icon("arrow_backward")),
        state=Help.main,
        getter=help_getter,
    ),
)
