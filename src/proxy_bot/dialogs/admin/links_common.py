from __future__ import annotations

from proxy_bot.storage.models import LINK_TYPE_REMNAWAVE, Link, Squad
from proxy_bot.utils.html import esc


def available_squads(all_squads: list[Squad], links: list[Link]) -> list[Squad]:
    """Bot Squads not yet attached to a `remnawave`-type link in `links` -
    a Squad can only be attached to one link per code ("each with its own
    Squad"), so this is what "add a remnawave link" offers to pick from.
    Empty means either no Squads exist yet (create one in the Squads admin
    screen first) or every existing Squad is already attached here."""
    used = {link.squad_id for link in links if link.type == LINK_TYPE_REMNAWAVE and link.squad_id}
    return [squad for squad in all_squads if squad.id not in used]


def link_row(link: Link, i18n, squad_name: str | None = None) -> str:
    """One admin-facing line for a link entry - equal treatment for both
    types (position, type label, value). A `remnawave` entry shows its
    attached Squad's name (resolved by the caller, since that's a storage
    lookup) rather than a URL - it doesn't have one to show, its
    subscription URL is resolved live per holder (see storage.models.Link) -
    or a "squad missing" placeholder if `squad_id` is empty or dangling.
    """
    if link.type == LINK_TYPE_REMNAWAVE:
        type_label = i18n.get("admin-code-link-type-remnawave")
        value = esc(squad_name) if squad_name else i18n.get("admin-code-link-squad-missing")
    else:
        type_label = i18n.get("admin-code-link-type-fix")
        value = f"<code>{esc(link.url)}</code>"
    if link.name:
        row = i18n.get("admin-code-link-row-named", name=esc(link.name), type=type_label, value=value)
    else:
        row = i18n.get("admin-code-link-row", type=type_label, value=value)
    if link.disabled:
        return i18n.get("admin-code-link-row-disabled", row=row)
    return row


# Telegram button text has no markup, so a value this long would just spill
# across the keyboard - long enough to still recognize a URL by, short
# enough to keep the row readable.
_LINK_BUTTON_URL_MAX = 40


def link_button_label(link: Link, i18n, squad_name: str | None = None) -> str:
    """Plain-text (no HTML) label for the inline button that opens a link's
    edit submenu - same fields as link_row, but Telegram button text can't
    render markup, so no <code> tags and no esc()."""
    type_label = i18n.get(
        "admin-code-link-type-remnawave" if link.type == LINK_TYPE_REMNAWAVE else "admin-code-link-type-fix"
    )
    if link.name:
        label = f"{link.name} ({type_label})"
    elif link.type == LINK_TYPE_REMNAWAVE:
        label = f"{type_label}: {squad_name}" if squad_name else type_label
    else:
        url = link.url
        if len(url) > _LINK_BUTTON_URL_MAX:
            url = url[: _LINK_BUTTON_URL_MAX - 1] + "…"
        label = f"{type_label}: {url}"
    if link.disabled:
        return f"🚫 {label}"
    return label
