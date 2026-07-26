from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from aiogram_dialog import DialogManager, StartMode

from proxy_bot.dialogs.states import AdminMenu, UserMenu
from proxy_bot.filters import IsAdmin

router = Router(name="user")


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
    await dialog_manager.start(AdminMenu.main, mode=StartMode.RESET_STACK)


@router.message(Command("admin"))
async def cmd_admin_denied(message: Message, i18n) -> None:
    await message.answer(i18n.get("admin-only"))
