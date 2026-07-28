from __future__ import annotations

import logging

from aiogram import Router
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import Message
from aiogram_dialog import DialogManager, ShowMode, StartMode

from proxy_bot.dialogs.admin import AdminMenu
from proxy_bot.dialogs.user import EnterCode, Help, Links, UserMenu
from proxy_bot.filters import IsAdmin
from proxy_bot.utils.audit import actor

logger = logging.getLogger(__name__)

router = Router(name="user")


@router.message(CommandStart(deep_link=True))
async def cmd_start_with_code(message: Message, dialog_manager: DialogManager, command: CommandObject) -> None:
    # Deep link: t.me/<bot>?start=<code> auto-activates <code>, same as typing
    # it manually into "Ввести код" (see dialogs/user/menu.py: on_dialog_start).
    await dialog_manager.start(
        UserMenu.main, mode=StartMode.RESET_STACK, data={"greet": True, "auto_code": command.args}
    )


@router.message(CommandStart())
async def cmd_start(message: Message, dialog_manager: DialogManager) -> None:
    await dialog_manager.start(UserMenu.main, mode=StartMode.RESET_STACK, data={"greet": True})


@router.message(Command("code"))
async def cmd_code(message: Message, dialog_manager: DialogManager) -> None:
    # enter_code is a sub-dialog of the main menu now, not one of its states -
    # start the menu underneath first so Cancel has somewhere to land. Its
    # own render is suppressed (NO_UPDATE) since only the sub-dialog on top
    # of it should actually produce a message - otherwise the menu flashes
    # as a message of its own before enter_code's.
    await dialog_manager.start(UserMenu.main, mode=StartMode.RESET_STACK, show_mode=ShowMode.NO_UPDATE)
    await dialog_manager.start(EnterCode.main, show_mode=ShowMode.SEND)


@router.message(Command("link"))
async def cmd_link(message: Message, dialog_manager: DialogManager) -> None:
    await dialog_manager.start(UserMenu.main, mode=StartMode.RESET_STACK, show_mode=ShowMode.NO_UPDATE)
    await dialog_manager.start(Links.main, show_mode=ShowMode.SEND)


@router.message(Command("help"))
async def cmd_help(message: Message, dialog_manager: DialogManager) -> None:
    await dialog_manager.start(UserMenu.main, mode=StartMode.RESET_STACK, show_mode=ShowMode.NO_UPDATE)
    await dialog_manager.start(Help.main, show_mode=ShowMode.SEND)


@router.message(Command("admin"), IsAdmin())
async def cmd_admin(message: Message, dialog_manager: DialogManager) -> None:
    logger.info("%s opened the admin panel", actor(message.from_user))
    await dialog_manager.start(AdminMenu.main, mode=StartMode.RESET_STACK)


@router.message(Command("admin"))
async def cmd_admin_denied(message: Message, i18n) -> None:
    logger.info("%s tried to open the admin panel without permission", actor(message.from_user))
    await message.answer(i18n.get("admin-only"))
