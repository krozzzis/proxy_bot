from aiogram.types import Message
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.common import WhenCondition
from aiogram_dialog.widgets.media import StaticMedia
from aiogram_dialog.widgets.style.base import ButtonStyle, Style
from aiogram_dialog.widgets.text import Format

from proxy_bot.config import get_locales_dir
from proxy_bot.utils.branding import resolve_logo_path
from proxy_bot.utils.emoji_config import custom_emoji_id, load_emoji_config


def not_a_command(message: Message) -> bool:
    """TextInput filter: reject slash-commands so they fall through to command handlers."""
    return not (message.text or "").startswith("/")


# Custom-emoji ids for inline-keyboard buttons, derived from
# locales/emoji.toml (the single source of truth also used by Fluent's
# `{ $emoji_x }` variables - see utils/i18n.py). Telegram inline buttons
# carry these via a dedicated icon_custom_emoji_id field, not via text
# entities, so button label text stays a plain string with no :shortcode:
# prefix. A shortcode whose config entry is a literal Unicode override
# (rather than a "[tg_emoji:...]" tag) has no id to give a button -
# custom_emoji_id() returns None for it, which Style/icon_custom_emoji_id
# treats as "no icon" rather than an error.
#
# Read once at import time, like the dict literal this replaced - button
# styles are baked into the Window/Button tree when dialogs are built at
# process startup, so (unlike Fluent text, which re-resolves per message
# through the hot-reloaded core) an emoji.toml edit needs a bot restart to
# reach button icons.
CUSTOM_EMOJI = {name: custom_emoji_id(value) for name, value in load_emoji_config(get_locales_dir() / "emoji.toml").items()}

# The reverse of CUSTOM_EMOJI (id -> shortcode instead of shortcode -> id) -
# every custom-emoji id the bot itself recognizes, for utils.emoji_config's
# collapse_tags() to recognize the bot's own icons inside arbitrary rendered
# HTML (see dialogs/admin/broadcast.py's title preview).
CUSTOM_EMOJI_BY_ID = {emoji_id: name for name, emoji_id in CUSTOM_EMOJI.items() if emoji_id is not None}


def icon(name: str, color: ButtonStyle | None = None, when: WhenCondition = None) -> Style:
    """Button style carrying a pack icon and, for confirm/cancel-type actions
    only, an accent color - plain navigation buttons stay icon-only so color
    reads as a deliberate signal rather than decoration. `icon(a, when=X) |
    icon(b, when=~X)` picks whichever alternative's condition matches."""
    return Style(style=color, emoji_id=CUSTOM_EMOJI[name], when=when)


# Shared "caption" mode (BRANDED_LOGO_MODE) plumbing for every user-facing
# Window one main-menu button away from UserMenu.main - not just the menu
# itself. Telegram's editMessageMedia/editMessageCaption can turn a photo
# message into a different photo message, but there's no API call that
# turns a photo message into a plain text one - so if only UserMenu.main
# carried a StaticMedia widget, navigating anywhere else (Links, EnterCode,
# Help, Settings) forced aiogram_dialog to delete the photo message and
# send a brand new text-only one instead of editing in place, which read as
# the branded message getting silently replaced. Adding this same widget
# (same path, same "when") to every one of those Windows too keeps every
# hop a photo -> photo edit, so the logo stays put across navigation.
#
# One instance, reused by every Window that adds it as a widget - it holds
# only its own init-time config (path text-widget, when-condition), no
# per-render state, so sharing it across unrelated dialogs is safe.
BRANDED_LOGO_MEDIA = StaticMedia(path=Format("{logo_path}"), when="show_logo_caption")


async def branded_logo_getter(dialog_manager: DialogManager, i18n, **kwargs) -> dict:
    logo_path = dialog_manager.middleware_data.get("logo_path")
    logo_mode = dialog_manager.middleware_data.get("logo_mode", "before")
    logo_overrides = dialog_manager.middleware_data.get("logo_path_overrides") or {}
    resolved = resolve_logo_path(logo_path, logo_overrides, i18n.locale) if logo_path else None
    show_logo_caption = bool(resolved is not None and logo_mode == "caption" and resolved.is_file())
    return {
        "logo_path": str(resolved) if resolved is not None else "",
        "show_logo_caption": show_logo_caption,
    }
