from __future__ import annotations

import logging
from pathlib import Path

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import FSInputFile, InputMediaPhoto, Message

logger = logging.getLogger(__name__)


def resolve_logo_path(
    logo_path: Path | None,
    logo_overrides: dict[str, Path],
    locale: str,
) -> Path | None:
    """Pick which branded-logo file to use for `locale`.

    Priority: an explicit BRANDED_LOGO_PATH_<LOCALE> override, then an
    auto-detected `<stem>_<locale><suffix>` sibling of logo_path (e.g.
    logo.png -> logo_ru.png), then logo_path itself as the universal
    fallback. A configured override or auto-detected sibling that doesn't
    actually exist on disk is skipped rather than treated as an error -
    this whole feature is opt-in and forgiving by design (see config.py).
    """
    if logo_path is None:
        return None

    override = logo_overrides.get(locale)
    if override is not None and override.is_file():
        return override

    localized = logo_path.with_name(f"{logo_path.stem}_{locale}{logo_path.suffix}")
    if localized.is_file():
        return localized

    return logo_path


# file_id Telegram hands back the first time a given (locale-resolved) logo
# file is uploaded, keyed by (path, mtime) so an operator swapping the file
# on disk busts the cache instead of the new image silently never being
# sent. Process-lifetime only - same tradeoff aiogram_dialog's own
# MediaIdStorage makes for "caption" mode (see dialogs/common.py) - a
# redeploy just re-uploads once per locale, then every send after that
# reuses Telegram's cached copy instead of re-uploading the file from disk.
_logo_file_id_cache: dict[Path, tuple[float, str]] = {}

# chat_id -> message_id of the standalone "before"-mode logo message most
# recently sent there. "caption" mode's photo lives inside a dialog Window,
# so a locale switch already makes it swap on its own - branded_logo_getter
# re-resolves the path on every render, and aiogram_dialog's own
# MediaIdStorage edits the message's media in place when that path changes
# (see dialogs/common.py). "before" mode's photo is a plain message sent
# once by handlers/user.py, entirely outside the dialog framework, so
# nothing re-renders it on its own - this lets a locale switch
# (dialogs/user/settings.py) find that exact message again and swap its
# photo via update_before_mode_logo() below.
_before_mode_message_ids: dict[int, int] = {}


def _photo_input(resolved: Path) -> str | FSInputFile:
    mtime = resolved.stat().st_mtime
    cached = _logo_file_id_cache.get(resolved)
    if cached is not None and cached[0] == mtime:
        return cached[1]
    return FSInputFile(resolved)


def _remember_file_id(resolved: Path, sent: Message) -> None:
    if sent.photo:
        _logo_file_id_cache[resolved] = (resolved.stat().st_mtime, sent.photo[-1].file_id)


async def send_before_mode_logo(
    message: Message,
    logo_path: Path | None,
    logo_overrides: dict[str, Path],
    locale: str,
) -> Message | None:
    """Send "before"-mode's standalone logo message and remember it for
    this chat. Returns None (nothing sent) if logo_path is unset or no
    locale-resolved file exists on disk."""
    resolved = resolve_logo_path(logo_path, logo_overrides, locale)
    if resolved is None or not resolved.is_file():
        return None

    photo = _photo_input(resolved)
    sent = await message.answer_photo(photo)
    if isinstance(photo, FSInputFile):
        _remember_file_id(resolved, sent)
    _before_mode_message_ids[sent.chat.id] = sent.message_id
    return sent


async def update_before_mode_logo(
    bot: Bot,
    chat_id: int,
    logo_path: Path | None,
    logo_overrides: dict[str, Path],
    locale: str,
) -> None:
    """Swap "before"-mode's standalone logo message to `locale`'s file, in
    place - called right after a locale switch (see
    dialogs/user/settings.py: on_language_selected). A silent no-op unless
    send_before_mode_logo() already sent one to this chat this process's
    lifetime: nothing to update in "caption" mode (never populates
    _before_mode_message_ids to begin with), before this feature's first
    /start in a chat, or after a redeploy."""
    message_id = _before_mode_message_ids.get(chat_id)
    if message_id is None:
        return
    resolved = resolve_logo_path(logo_path, logo_overrides, locale)
    if resolved is None or not resolved.is_file():
        return

    photo = _photo_input(resolved)
    try:
        result = await bot.edit_message_media(
            chat_id=chat_id, message_id=message_id, media=InputMediaPhoto(media=photo)
        )
    except TelegramBadRequest as exc:
        if "message is not modified" in str(exc).lower():
            # Both locales resolved to the same file (no locale-specific
            # asset configured) - genuinely nothing to change.
            return
        # Anything else - message deleted out from under us, too old to
        # edit (Telegram refuses past 48h), wrong media type, ... - drop
        # the mapping rather than retrying against a dead message_id on
        # every future locale switch, but say so; a silent failure here
        # means the operator has no way to tell "nothing to update" from
        # "update was rejected" when a user reports the logo didn't change.
        logger.warning("Couldn't update the before-mode logo message %s in chat %s: %s", message_id, chat_id, exc)
        _before_mode_message_ids.pop(chat_id, None)
        return

    if isinstance(result, Message) and isinstance(photo, FSInputFile):
        _remember_file_id(resolved, result)
