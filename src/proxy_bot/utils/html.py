from __future__ import annotations

from html import escape as _escape


def esc(value: object) -> str:
    """Escape a dynamic value for Telegram HTML parse mode.

    Only "&", "<", ">" need escaping in Telegram's HTML dialect; quotes are
    left alone (quote=False) since we never put values inside tag attributes.
    """
    return _escape(str(value), quote=False)
