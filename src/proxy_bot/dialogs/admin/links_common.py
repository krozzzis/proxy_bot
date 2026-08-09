from __future__ import annotations

from proxy_bot.storage.models import LINK_TYPE_REMNAWAVE, Link
from proxy_bot.utils.html import esc


def has_remnawave_link(links: list[Link]) -> bool:
    """A code's Remnawave subscription URL is a single per-user value (see
    storage.models.Link), so only one `remnawave`-type entry in a code's
    `links` ever makes sense - callers use this to hide "add a Remnawave
    link" once one exists, same as how only one Remnawave squads selection
    exists per code."""
    return any(link.type == LINK_TYPE_REMNAWAVE for link in links)


def link_row(link: Link, i18n) -> str:
    """One admin-facing line for a link entry - equal treatment for both
    types (position, type label, value), but a `remnawave` entry never
    shows a URL: it doesn't have one to show (its subscription URL is
    resolved live per holder, see storage.models.Link) - just a fixed
    placeholder, with the type label telling the admin what it actually is.
    """
    if link.type == LINK_TYPE_REMNAWAVE:
        type_label = i18n.get("admin-code-link-type-remnawave")
        value = i18n.get("admin-code-link-remnawave-value")
    else:
        type_label = i18n.get("admin-code-link-type-fix")
        value = f"<code>{esc(link.url)}</code>"
    if link.name:
        return i18n.get("admin-code-link-row-named", name=esc(link.name), type=type_label, value=value)
    return i18n.get("admin-code-link-row", type=type_label, value=value)
