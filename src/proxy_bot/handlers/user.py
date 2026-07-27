from __future__ import annotations

import logging

from aiogram import Router
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import Message
from aiogram_dialog import DialogManager, StartMode

from proxy_bot.dialogs.states import AdminMenu, UserMenu
from proxy_bot.filters import IsAdmin
from proxy_bot.utils.audit import actor

logger = logging.getLogger(__name__)

router = Router(name="user")


@router.message(CommandStart(deep_link=True))
async def cmd_start_with_code(message: Message, dialog_manager: DialogManager, command: CommandObject) -> None:
    # Deep link: t.me/<bot>?start=<code> auto-activates <code>, same as typing
    # it manually into "Ввести код" (see dialogs/menu.py: on_dialog_start).
    await dialog_manager.start(
        UserMenu.main, mode=StartMode.RESET_STACK, data={"greet": True, "auto_code": command.args}
    )


@router.message(CommandStart())
async def cmd_start(message: Message, dialog_manager: DialogManager) -> None:
    await dialog_manager.start(UserMenu.main, mode=StartMode.RESET_STACK, data={"greet": True})


@router.message(Command("code"))
async def cmd_code(message: Message, dialog_manager: DialogManager) -> None:
    await dialog_manager.start(UserMenu.enter_code, mode=StartMode.RESET_STACK)


@router.message(Command("link"))
async def cmd_link(message: Message, dialog_manager: DialogManager) -> None:
    await dialog_manager.start(UserMenu.links, mode=StartMode.RESET_STACK)


@router.message(Command("help"))
async def cmd_help(message: Message, dialog_manager: DialogManager) -> None:
    await dialog_manager.start(UserMenu.help, mode=StartMode.RESET_STACK)


@router.message(Command("admin"), IsAdmin())
async def cmd_admin(message: Message, dialog_manager: DialogManager) -> None:
    logger.info("%s opened the admin panel", actor(message.from_user))
    # Put the user menu under the admin panel on the stack (same as the
    # in-menu "admin panel" button) so closing it lands back on the main
    # menu instead of leaving nothing to return to.
    await dialog_manager.start(UserMenu.main, mode=StartMode.RESET_STACK)
    await dialog_manager.start(AdminMenu.main)


@router.message(Command("admin"))
async def cmd_admin_denied(message: Message, i18n) -> None:
    logger.info("%s tried to open the admin panel without permission", actor(message.from_user))
    await message.answer(i18n.get("admin-only"))
