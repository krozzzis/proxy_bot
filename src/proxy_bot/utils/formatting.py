from __future__ import annotations

from collections.abc import Sequence

from proxy_bot.config import get_locales_dir
from proxy_bot.utils.emoji_config import load_emoji_config

from .html import esc

# The pack's "link" icon, read from locales/emoji.toml like everything else
# that needs one - NOT hardcoded, unlike an earlier version of this file
# that pinned the tag's id as a literal. That id went stale the first time
# the pack was regenerated (every id rotates on --recreate) since nothing
# here would pick up the new one, and broke every "my subscriptions" render
# for any user with a link until caught in production. EmojiFluentCompileCore
# .get() expands this marker in the fully-assembled message text regardless
# of whether it came from the .ftl file or, as here, from a value
# substituted into one of its placeholders - read once at import time, same
# as dialogs/common.py's CUSTOM_EMOJI (a process restart is needed to pick
# up a regenerated pack either way).
_BULLET = load_emoji_config(get_locales_dir() / "emoji.toml").get("link", "🔗")


def format_links(links: Sequence[str]) -> str:
    """Render a monospaced (tap-to-copy) list of links for HTML parse mode.

    Every link gets the same bullet regardless of how many there are -
    omitting it for a lone link made single- and multi-link codes look
    inconsistent with each other in a "my links" screen listing several
    codes side by side.
    """
    return "\n".join(f"{_BULLET} <code>{esc(link)}</code>" for link in links)


def display_name(username: str | None, full_name: str, user_id: int) -> str:
    """"@username" if set, else the Telegram display name, else a bare id -
    shared by every admin-panel list that names a Telegram user (users,
    admins) so they can't drift into showing different things for the same
    person."""
    if username:
        return f"@{username}"
    return full_name or str(user_id)
