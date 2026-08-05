from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, cast

import emoji
import watchfiles
from aiogram.types import User as TelegramUser
from aiogram_i18n import I18nContext, I18nMiddleware
from aiogram_i18n.cores import FluentCompileCore
from aiogram_i18n.managers.base import BaseManager

from proxy_bot.storage import Storage
from proxy_bot.utils.emoji_config import expand_tags, load_emoji_config, plain_emoji

logger = logging.getLogger(__name__)


class EmojiFluentCompileCore(FluentCompileCore):
    """FluentCompileCore that expands emoji shortcodes in rendered messages.

    Three forms reach a rendered message, and only the first needs raw
    Unicode pasted into a .ftl file directly:
    - ":wave:" - GitHub/Slack-style alias for a regular Unicode emoji.
    - "[tg_emoji:5368324170671202286:wave]" - a Telegram Premium/custom emoji
      by id, with a shortcode fallback for clients that can't render it.
    - "{ $emoji_wave }" - a Fluent variable resolving to whatever
      locales/emoji.toml's `wave` entry holds (a tag as above, or a literal
      Unicode override) - see utils/emoji_config.py. Injected into every
      `get()` call automatically, so message authors don't pass it
      per-call, and every shortcode in emoji.toml is available even to
      messages that don't otherwise take arguments.
    """

    def __init__(self, *args: Any, emoji_config_path: Path, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._emoji_config_path = emoji_config_path
        self._emoji_vars: dict[str, str] = {}
        self._emoji_vars_plain: dict[str, str] = {}
        self._reload_emoji_vars()

    def _reload_emoji_vars(self) -> None:
        config = load_emoji_config(self._emoji_config_path)
        self._emoji_vars = {f"emoji_{name}": value for name, value in config.items()}
        self._emoji_vars_plain = {f"emoji_{name}": plain_emoji(value) for name, value in config.items()}

    async def startup(self) -> None:
        # Picked up by watch_locales' hot-reload same as the .ftl files
        # themselves, since emoji.toml lives inside locales_dir too.
        self._reload_emoji_vars()
        await super().startup()

    def get(self, message: str, locale: str | None = None, /, **kwargs: Any) -> str:
        text = super().get(message, locale, **{**self._emoji_vars, **kwargs})
        text = expand_tags(text)
        return emoji.emojize(text, language="alias")

    def get_plain(self, message: str, locale: str | None = None, /, **kwargs: Any) -> str:
        """Like get(), but every `{ $emoji_x }` resolves to its plain
        fallback character instead of a <tg-emoji> tag - for contexts that
        can't render HTML/custom emoji at all, unlike a message body.
        Telegram callback-query popups (`answerCallbackQuery`'s `text`) are
        the one in this bot: it's plain, unparsed text, so a `<tg-emoji>`
        tag would show up as literal angle-bracket text instead of an icon.
        See popup_text() below for the call-site-facing wrapper.

        No expand_tags() pass here: emoji vars are already plain,
        and a literal "[tg_emoji:...]" pasted directly into a popup-only
        .ftl value (rather than reached through a variable) would be a
        message-author mistake - left unexpanded so it's visibly wrong
        instead of silently working differently than get_plain promises.
        """
        text = super().get(message, locale, **{**self._emoji_vars_plain, **kwargs})
        return emoji.emojize(text, language="alias")


class PersistentLocaleManager(BaseManager):
    """Reads/writes the user's language choice from the same users.toml
    row everything else about them lives in (see storage.users.User.locale),
    instead of aiogram_i18n's own MemoryManager - which forgets every
    choice on process restart since it only ever lives in a dict."""

    def __init__(self, storage: Storage, default_locale: str | None = None) -> None:
        super().__init__(default_locale=default_locale)
        self._storage = storage

    async def get_locale(self, event_from_user: TelegramUser | None = None, **kwargs: object) -> str:
        if event_from_user is None:
            return self.default_locale
        user = await self._storage.users.get(event_from_user.id)
        if user and user.locale:
            return user.locale
        return self.default_locale

    async def set_locale(self, locale: str, event_from_user: TelegramUser | None = None, **kwargs: object) -> None:
        if event_from_user is not None:
            await self._storage.users.set_locale(event_from_user.id, locale)


def popup_text(i18n: I18nContext, message: str, **kwargs: Any) -> str:
    """Render a message for a Telegram callback-query popup
    (`callback.answer(popup_text(...), show_alert=...)`) instead of a
    message body - routes through EmojiFluentCompileCore.get_plain() so any
    `{ $emoji_x }` in the message renders as a plain character rather than
    a <tg-emoji> tag popups can't display. Use this instead of `i18n.get()`
    at every `callback.answer(...)` call site, even ones whose message
    doesn't currently reference an emoji - a later edit to that .ftl key
    that adds one should render correctly for free, not require noticing
    which call sites feed a popup."""
    core = cast(EmojiFluentCompileCore, i18n.core)
    return core.get_plain(message, i18n.locale, **kwargs)


def build_i18n_middleware(locales_dir: Path, default_locale: str, storage: Storage) -> I18nMiddleware:
    core = EmojiFluentCompileCore(
        path=locales_dir / "{locale}",
        default_locale=default_locale,
        emoji_config_path=locales_dir / "emoji.toml",
    )
    manager = PersistentLocaleManager(storage, default_locale=default_locale)
    return I18nMiddleware(core=core, manager=manager, default_locale=default_locale)


async def watch_locales(core: EmojiFluentCompileCore, locales_dir: Path) -> None:
    """Hot-reload .ftl files on change, so translation edits don't need a bot restart.

    Runs until cancelled - intended to be spawned as a background task for
    the lifetime of the bot process.
    """
    async for changes in watchfiles.awatch(locales_dir):
        logger.info("Locale files changed (%d), reloading translations", len(changes))
        await core.startup()
