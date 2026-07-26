from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

import emoji
import watchfiles
from aiogram_i18n import I18nMiddleware
from aiogram_i18n.cores import FluentCompileCore
from aiogram_i18n.managers.memory import MemoryManager

logger = logging.getLogger(__name__)

# [tg_emoji:<custom_emoji_id>:<fallback_shortcode>] -> a Telegram Premium/custom
# emoji. <custom_emoji_id> is the numeric id of a real custom emoji document
# (e.g. obtained via the Bot API's getCustomEmojiStickers, or copied from a
# client); <fallback_shortcode> is a regular :shortcode:-style alias (no
# colons) used as the character shown to clients that can't render custom
# emoji. Expands to Telegram's own <tg-emoji emoji-id="..."> HTML tag, which
# the Bot API turns into a proper custom_emoji message entity - no manual
# offset/length bookkeeping needed since we're already sending as HTML.
_PREMIUM_EMOJI_RE = re.compile(r"\[tg_emoji:(\d+):([a-z0-9_+\-]+)\]")


def _expand_premium_emoji(text: str) -> str:
    def _sub(match: re.Match[str]) -> str:
        emoji_id, fallback_name = match.group(1), match.group(2)
        fallback = emoji.emojize(f":{fallback_name}:", language="alias")
        return f'<tg-emoji emoji-id="{emoji_id}">{fallback}</tg-emoji>'

    return _PREMIUM_EMOJI_RE.sub(_sub, text)


class EmojiFluentCompileCore(FluentCompileCore):
    """FluentCompileCore that expands emoji shortcodes in rendered messages.

    Two forms are supported so .ftl files never need raw Unicode pasted in:
    - ":wave:" - GitHub/Slack-style alias for a regular Unicode emoji.
    - "[tg_emoji:5368324170671202286:wave]" - a Telegram Premium/custom emoji
      by id, with a shortcode fallback for clients that can't render it.
    """

    def get(self, message: str, locale: str | None = None, /, **kwargs: Any) -> str:
        text = super().get(message, locale, **kwargs)
        text = _expand_premium_emoji(text)
        return emoji.emojize(text, language="alias")


def build_i18n_middleware(locales_dir: Path, default_locale: str) -> I18nMiddleware:
    core = EmojiFluentCompileCore(
        path=locales_dir / "{locale}",
        default_locale=default_locale,
    )
    manager = MemoryManager(default_locale=default_locale)
    return I18nMiddleware(core=core, manager=manager, default_locale=default_locale)


async def watch_locales(core: EmojiFluentCompileCore, locales_dir: Path) -> None:
    """Hot-reload .ftl files on change, so translation edits don't need a bot restart.

    Runs until cancelled - intended to be spawned as a background task for
    the lifetime of the bot process.
    """
    async for changes in watchfiles.awatch(locales_dir):
        logger.info("Locale files changed (%d), reloading translations", len(changes))
        await core.startup()
