from __future__ import annotations

from collections.abc import Sequence

from .html import esc


def format_links(links: Sequence[str]) -> str:
    """Render a numbered, monospaced (tap-to-copy) list of links for HTML parse mode."""
    return "\n".join(f"{idx}. <code>{esc(link)}</code>" for idx, link in enumerate(links, start=1))
