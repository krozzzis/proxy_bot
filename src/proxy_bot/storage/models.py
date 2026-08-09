from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

LINK_TYPE_FIX = "fix"
LINK_TYPE_REMNAWAVE = "remnawave"


@dataclass
class Link:
    """One entry in a Code's ordered `links` list - a fixed URL or a
    Remnawave subscription placeholder, shown to holders as equal citizens
    (see dialogs/user/links.py). List order is display order.
    """

    type: str = LINK_TYPE_FIX
    # Admin-supplied title shown alongside the link (see the
    # "((link_emoji)) ((Description)):\n((link_url))" format in
    # utils/formatting.py). Empty falls back to just the bullet + url/
    # placeholder, matching pre-naming output.
    name: str = ""
    # Only meaningful for `type == LINK_TYPE_FIX`. A `remnawave`-type
    # entry's actual URL is resolved live per holder from their linked
    # account (storage.User.remnawave_subscription_url) - never stored here.
    url: str = ""


def parse_link(raw: str | dict) -> Link:
    """A single Link from its raw shape - a bare URL string (pre-migration
    `codes.toml` rows: no type/name, always a fixed link back then, since
    Remnawave access wasn't representable as a `links` entry yet) or a
    `dump_link()`-shaped dict. Also used to round-trip a link through
    aiogram_dialog's `dialog_data` (see dialogs/admin/create_code.py) - that
    gets JSON-serialized by this project's FSM storage, which a raw `Link`
    dataclass instance can't survive, so it's kept there as a plain dict via
    dump_link() and converted back with this on read.
    """
    if isinstance(raw, str):
        return Link(type=LINK_TYPE_FIX, name="", url=raw)
    return Link(type=raw.get("type", LINK_TYPE_FIX), name=raw.get("name", ""), url=raw.get("url", ""))


def parse_links(raw_links: list, remnawave_squads: list[str]) -> list[Link]:
    """Build the `links` list for a Code from its raw TOML value, migrating
    two pre-migration shapes in memory (callers persist the result back on
    their own next write - see storage.codes.CodeRepo):

    - a bare-string links list (no type/name), and
    - a code with `remnawave_squads` set but no `remnawave`-type link entry
      yet, i.e. one created before Remnawave links became explicit list
      entries. Back then any non-empty `remnawave_squads` alone made the
      subscription link show up in "my subscriptions" (see the old
      dialogs/user/links.py); synthesizing the entry here (unnamed, appended
      last - the same position it used to render in) preserves that
      behavior for existing codes without an admin having to redo it by hand.
    """
    links = [parse_link(item) for item in raw_links]
    if remnawave_squads and not any(link.type == LINK_TYPE_REMNAWAVE for link in links):
        links.append(Link(type=LINK_TYPE_REMNAWAVE))
    return links


def dump_link(link: Link) -> dict[str, Any]:
    return {"type": link.type, "name": link.name, "url": link.url}


@dataclass
class Code:
    code: str
    links: list[Link] = field(default_factory=list)
    description: str = ""
    created_by: int = 0
    created_at: str = ""
    active: bool = True
    # Internal squad UUIDs granted on activation. Empty means no per-user
    # Remnawave account is provisioned for this code - independent of
    # whether `links` includes a `remnawave`-type entry (that's a display
    # concern; this is the access grant).
    remnawave_squads: list[str] = field(default_factory=list)
    # Admin override: this code contributes no squads to any holder's
    # account, regardless of `remnawave_squads` - unlike clearing the squad
    # list itself, the selection survives being re-enabled later.
    remnawave_disabled: bool = False

    @classmethod
    def from_raw(cls, code: str, raw: dict) -> Code:
        """Build a Code from its raw `codes.toml` dict, migrating the
        `links` shape in memory (see parse_links)."""
        data = dict(raw)
        raw_links = data.pop("links", [])
        links = parse_links(raw_links, data.get("remnawave_squads", []))
        return cls(code=code, links=links, **data)


@dataclass
class User:
    user_id: int
    username: str | None = None
    full_name: str = ""
    first_seen: str = ""
    banned: bool = False
    codes: list[str] = field(default_factory=list)
    # Set once a Remnawave account is provisioned or manually linked for
    # this user; shared across all remnawave-enabled codes they hold.
    remnawave_uuid: str | None = None
    remnawave_subscription_url: str | None = None
    remnawave_username: str | None = None
    # True if an admin force-linked this account via the "Link Remnawave"
    # flow (dialogs/admin/link_remnawave.py); False if it was provisioned or
    # matched automatically (services/remnawave_sync.py). Absent/False for
    # anyone linked before this field existed - their account was in fact
    # auto-provisioned back then, so the default isn't a guess.
    remnawave_linked_manually: bool = False
    # Admin override: never provision or grant this user Remnawave squads,
    # regardless of what their codes would otherwise entitle them to. The
    # existing account (if any) and its uuid are left alone - only the
    # active grant stops, so re-enabling doesn't need to re-provision or
    # re-match anything.
    remnawave_disabled: bool = False
    # Explicit language choice from the settings menu. Empty means "not
    # chosen yet" - falls back to the bot's default_locale.
    locale: str = ""


@dataclass
class Admin:
    user_id: int
    username: str | None = None
    added_by: int = 0
    added_at: str = ""
