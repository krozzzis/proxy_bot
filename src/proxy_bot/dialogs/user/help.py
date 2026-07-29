from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup
from aiogram_dialog import Dialog, Window
from aiogram_dialog.widgets.kbd import Cancel
from aiogram_dialog.widgets.text import Multi

from proxy_bot.storage import Storage

from ..common import icon
from ..widgets import I18N


class Help(StatesGroup):
    main = State()


async def help_getter(storage: Storage, event_from_user, **kwargs) -> dict:
    return {"is_admin": await storage.admins.is_admin(event_from_user.id)}


help_dialog = Dialog(
    Window(
        Multi(I18N("help-text"), I18N("help-admin-suffix", when="is_admin"), sep="\n\n"),
        Cancel(I18N("menu-btn-back"), style=icon("arrow_backward")),
        state=Help.main,
        getter=help_getter,
    ),
)
