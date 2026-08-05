from aiogram.types import Message
from aiogram_dialog.widgets.common import WhenCondition
from aiogram_dialog.widgets.style.base import ButtonStyle, Style

from proxy_bot.config import get_locales_dir
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
