from __future__ import annotations

import logging
from pathlib import Path

from aiogram import Router
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import FSInputFile, Message
from aiogram_dialog import DialogManager, ShowMode, StartMode

from proxy_bot.dialogs.admin import AdminMenu
from proxy_bot.dialogs.user import EnterCode, Help, Links, UserMenu
from proxy_bot.filters import IsAdmin
from proxy_bot.utils.audit import actor
from proxy_bot.utils.branding import resolve_logo_path

logger = logging.getLogger(__name__)

router = Router(name="user")

# file_id Telegram hands back the first time a given (locale-resolved) logo
# file is uploaded, keyed by (path, mtime) so an operator swapping the file
# on disk busts the cache instead of the new image silently never being
# sent. Process-lifetime only - same tradeoff aiogram_dialog's own
# MediaIdStorage makes for "caption" mode (see dialogs/common.py) - a
# redeploy just re-uploads once per locale, then every /start after that
# reuses Telegram's cached copy instead of re-uploading the file from disk.
_logo_file_id_cache: dict[Path, tuple[float, str]] = {}


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
    # dialogs/common.py's BRANDED_LOGO_MEDIA widget.
    if logo_path is None or logo_mode == "caption":
        return
    resolved = resolve_logo_path(logo_path, logo_overrides, locale)
    if resolved is None or not resolved.is_file():
        logger.warning("No usable branded logo file for locale %r (looked at %s)", locale, resolved)
        return

    mtime = resolved.stat().st_mtime
    cached = _logo_file_id_cache.get(resolved)
    if cached is not None and cached[0] == mtime:
        sent = await message.answer_photo(cached[1])
    else:
        sent = await message.answer_photo(FSInputFile(resolved))
        if sent.photo:
            _logo_file_id_cache[resolved] = (mtime, sent.photo[-1].file_id)


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
