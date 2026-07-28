from __future__ import annotations

from collections.abc import Sequence

from .html import esc


# The pack's "link" icon (scripts/generate_emoji_pack.py: ICONS["link"]),
# kept as a literal here since that's how every other [tg_emoji:...] marker
# in this codebase is embedded (each ftl string repeats its own ids rather
# than sharing a constant). EmojiFluentCompileCore.get() expands these
# markers in the fully-assembled message text regardless of whether they
# came from the .ftl file or, as here, from a value substituted into one of
# its placeholders.
_BULLET = "[tg_emoji:5425048503829179049:link]"


def format_links(links: Sequence[str]) -> str:
    """Render a monospaced (tap-to-copy) list of links for HTML parse mode.

    Every link gets the same bullet regardless of how many there are -
    omitting it for a lone link made single- and multi-link codes look
    inconsistent with each other in a "my links" screen listing several
    codes side by side.
    """
    return "\n".join(f"{_BULLET} <code>{esc(link)}</code>" for link in links)
