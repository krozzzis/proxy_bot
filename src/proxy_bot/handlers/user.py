from __future__ import annotations

import logging
from pathlib import Path

from aiogram import F, Router
from aiogram.dispatcher.event.bases import SkipHandler
from aiogram.enums import ChatType
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import Message
from aiogram_dialog import DialogManager, ShowMode, StartMode

from proxy_bot.dialogs.admin import AdminMenu
from proxy_bot.dialogs.common import not_a_command
from proxy_bot.dialogs.user import EnterCode, Help, Links, UserMenu
from proxy_bot.filters import IsAdmin
from proxy_bot.utils.audit import actor
from proxy_bot.utils.branding import send_before_mode_logo

logger = logging.getLogger(__name__)

router = Router(name="user")


async def _send_logo(
    message: Message,
    logo_path: Path | None,
    logo_mode: str,
    logo_overrides: dict[str, Path],
    locale: str,
) -> None:
    # Optional (BRANDED_LOGO_PATH, unset by default). Only this mode - a
    # plain, caption-less photo message of its own, immediately followed by
    # the menu message - is handled here; it mirrors how the Liberty VPN bot
    # opens /start. The other mode ("caption", attached to the menu message
    # itself) is handled by the dialog windows, not here - see
    # dialogs/common.py's BRANDED_LOGO_MEDIA widget. A later locale switch
    # (dialogs/user/settings.py) updates whatever gets sent here in place -
    # see utils/branding.py's send_before_mode_logo/update_before_mode_logo.
    if logo_path is None or logo_mode == "caption":
        return
    sent = await send_before_mode_logo(message, logo_path, logo_overrides, locale)
    if sent is None:
        logger.warning("No usable branded logo file for locale %r (BRANDED_LOGO_PATH=%s)", locale, logo_path)


@router.message(F.chat.type == ChatType.PRIVATE, not_a_command)
async def resync_before_mode_logo(
    message: Message,
    dialog_manager: DialogManager,
    logo_path: Path | None,
    logo_mode: str,
    logo_path_overrides: dict[str, Path],
    i18n,
) -> None:
    # aiogram_dialog can't edit a dialog message "into place" below a
    # message the user just sent (Telegram has no such API) - for a
    # private chat it always resends the current window as a brand new
    # message instead (see aiogram_dialog.manager.manager.DialogManager.
    # _calc_show_mode: ShowMode.SEND whenever the triggering event is a
    # Message), regardless of which dialog/state is open or whether that
    # window's own TextInput ends up consuming the text.
    #
    # The "before"-mode logo (see _send_logo above) is a separate, plain
    # message sent once at /start - it isn't part of that resend, so
    # without this it's left behind above the chat while whatever menu is
    # open keeps reappearing at the bottom, no longer looking like the
    # same splash. Resending it here on every such resend (not just
    # UserMenu.main) keeps the pair together wherever the admin/user
    # happens to be.
    if dialog_manager.has_context():
        await _send_logo(message, logo_path, logo_mode, logo_path_overrides, i18n.locale)
    # Never actually "handles" the message - just resyncs the logo as a
    # side effect, then lets the normal command/dialog/fallback routing
    # underneath process it as if this handler didn't exist.
    raise SkipHandler


@router.message(CommandStart(deep_link=True))
async def cmd_start_with_code(
    message: Message,
    dialog_manager: DialogManager,
    command: CommandObject,
    logo_path: Path | None,
    logo_mode: str,
    logo_path_overrides: dict[str, Path],
    i18n,
) -> None:
    await _send_logo(message, logo_path, logo_mode, logo_path_overrides, i18n.locale)
    # Deep link: t.me/<bot>?start=<code> auto-activates <code>, same as typing
    # it manually into "Ввести код" (see dialogs/user/menu.py: on_dialog_start).
    await dialog_manager.start(
        UserMenu.main, mode=StartMode.RESET_STACK, data={"greet": True, "auto_code": command.args}
    )


@router.message(CommandStart())
async def cmd_start(
    message: Message,
    dialog_manager: DialogManager,
    logo_path: Path | None,
    logo_mode: str,
    logo_path_overrides: dict[str, Path],
    i18n,
) -> None:
    await _send_logo(message, logo_path, logo_mode, logo_path_overrides, i18n.locale)
    await dialog_manager.start(UserMenu.main, mode=StartMode.RESET_STACK, data={"greet": True})


@router.message(Command("code"))
async def cmd_code(
    message: Message,
    dialog_manager: DialogManager,
    logo_path: Path | None,
    logo_mode: str,
    logo_path_overrides: dict[str, Path],
    i18n,
) -> None:
    await _send_logo(message, logo_path, logo_mode, logo_path_overrides, i18n.locale)
    # enter_code is a sub-dialog of the main menu now, not one of its states -
    # start the menu underneath first so Cancel has somewhere to land. Its
    # own render is suppressed (NO_UPDATE) since only the sub-dialog on top
    # of it should actually produce a message - otherwise the menu flashes
    # as a message of its own before enter_code's.
    await dialog_manager.start(UserMenu.main, mode=StartMode.RESET_STACK, show_mode=ShowMode.NO_UPDATE)
    await dialog_manager.start(EnterCode.main, show_mode=ShowMode.SEND)


@router.message(Command("link"))
async def cmd_link(
    message: Message,
    dialog_manager: DialogManager,
    logo_path: Path | None,
    logo_mode: str,
    logo_path_overrides: dict[str, Path],
    i18n,
) -> None:
    await _send_logo(message, logo_path, logo_mode, logo_path_overrides, i18n.locale)
    await dialog_manager.start(UserMenu.main, mode=StartMode.RESET_STACK, show_mode=ShowMode.NO_UPDATE)
    await dialog_manager.start(Links.main, show_mode=ShowMode.SEND)


@router.message(Command("help"))
async def cmd_help(
    message: Message,
    dialog_manager: DialogManager,
    logo_path: Path | None,
    logo_mode: str,
    logo_path_overrides: dict[str, Path],
    i18n,
) -> None:
    await _send_logo(message, logo_path, logo_mode, logo_path_overrides, i18n.locale)
    await dialog_manager.start(UserMenu.main, mode=StartMode.RESET_STACK, show_mode=ShowMode.NO_UPDATE)
    await dialog_manager.start(Help.main, show_mode=ShowMode.SEND)


@router.message(Command("admin"), IsAdmin())
async def cmd_admin(
    message: Message,
    dialog_manager: DialogManager,
    logo_path: Path | None,
    logo_mode: str,
    logo_path_overrides: dict[str, Path],
    i18n,
) -> None:
    logger.info("%s opened the admin panel", actor(message.from_user))
    await _send_logo(message, logo_path, logo_mode, logo_path_overrides, i18n.locale)
    await dialog_manager.start(AdminMenu.main, mode=StartMode.RESET_STACK)


@router.message(Command("admin"))
async def cmd_admin_denied(message: Message, i18n) -> None:
    logger.info("%s tried to open the admin panel without permission", actor(message.from_user))
    await message.answer(i18n.get("admin-only"))
