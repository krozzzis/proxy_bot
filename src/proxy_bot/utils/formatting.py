from __future__ import annotations

from collections.abc import Sequence

from proxy_bot.config import get_locales_dir
from proxy_bot.utils.emoji_config import expand_tags, load_emoji_config

from .html import esc

# The pack's "link" icon, read from locales/emoji.toml like everything else
# that needs one - NOT hardcoded, unlike an earlier version of this file
# that pinned the tag's id as a literal. That id went stale the first time
# the pack was regenerated (every id rotates on --recreate) since nothing
# here would pick up the new one, and broke every "my subscriptions" render
# for any user with a link until caught in production - read once at import
# time, same as dialogs/common.py's CUSTOM_EMOJI (a process restart is
# needed to pick up a regenerated pack either way).
#
# Expanded to real HTML *here*, via expand_tags(), rather than left as a raw
# "[tg_emoji:...]" marker for EmojiFluentCompileCore to expand later: that
# only happens for text that passes through Fluent's own get()/get_plain(),
# and this string is handed straight to a Format() widget (see
# dialogs/user/links.py), which never touches Fluent at all - a marker left
# unexpanded here would reach the client as literal bracket text instead of
# an icon (as happened the first time this bypassed Fluent entirely).
_BULLET = expand_tags(load_emoji_config(get_locales_dir() / "emoji.toml").get("link", "🔗"))


def format_links(entries: Sequence[tuple[str, str, str]]) -> str:
    """Render a monospaced (tap-to-copy) list of links for HTML parse mode,
    one `(name, url, suffix)` triple per entry - fixed and Remnawave links
    alike, in whatever order the caller already resolved them in (see
    dialogs/user/links.py._resolve_link_entries).

    `suffix` is an already-rendered trailing bit of text for the header
    line - used for a remnawave link's own expiry when a code's links
    resolve to more than one distinct Remnawave account (see
    dialogs/user/links.py._build_detail); empty for every other link.
    Passed through as-is, NOT esc()'d - it may itself carry real HTML (a
    `<tg-time>` tag from utils.subscription_display), unlike `name` which is
    admin-authored plain text.

    A link with a name and/or suffix renders as
    "((bullet)) ((name)) — ((suffix)):\\n ((url))" (either half optional);
    one with neither (every link that predates naming, or one an admin left
    blank) degrades to the original single-line "((bullet)) ((url))" -
    every link gets the same bullet regardless of how many there are, so a
    lone link doesn't look inconsistent with a multi-link code shown right
    next to it.
    """
    lines = []
    for name, url, suffix in entries:
        header = " — ".join(part for part in (esc(name) if name else "", suffix) if part)
        if header:
            lines.append(f"{_BULLET} {header}:\n <code>{esc(url)}</code>")
        else:
            lines.append(f"{_BULLET} <code>{esc(url)}</code>")
    return "\n".join(lines)


def display_name(username: str | None, full_name: str, user_id: int) -> str:
    """"@username" if set, else the Telegram display name, else a bare id -
    shared by every admin-panel list that names a Telegram user (users,
    admins) so they can't drift into showing different things for the same
    person."""
    if username:
        return f"@{username}"
    return full_name or str(user_id)
