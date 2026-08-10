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
    # account for the Squad's server (storage.User.remnawave_accounts) -
    # never stored here.
    url: str = ""
    # Only meaningful for `type == LINK_TYPE_REMNAWAVE`: which bot-level
    # Squad (storage.models.Squad) this link grants and resolves against.
    # Empty (or pointing at a since-deleted Squad) means "nothing to point
    # at" - dropped from rendering and contributes no grant, same as an
    # unlinked account (see services.remnawave_sync).
    squad_id: str = ""


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
    return Link(
        type=raw.get("type", LINK_TYPE_FIX),
        name=raw.get("name", ""),
        url=raw.get("url", ""),
        squad_id=raw.get("squad_id", ""),
    )


def parse_links(raw_links: list) -> list[Link]:
    """Build the `links` list for a Code from its raw TOML value, migrating
    the one remaining pre-migration shape in memory (callers persist the
    result back on their own next write - see storage.codes.CodeRepo): a
    bare-string links list (no type/name/squad_id)."""
    return [parse_link(item) for item in raw_links]


def dump_link(link: Link) -> dict[str, Any]:
    return {"type": link.type, "name": link.name, "url": link.url, "squad_id": link.squad_id}


@dataclass
class Code:
    code: str
    links: list[Link] = field(default_factory=list)
    description: str = ""
    created_by: int = 0
    created_at: str = ""
    active: bool = True
    # Admin override: this code contributes no squads to any holder's
    # account, regardless of what its `remnawave`-type links would otherwise
    # grant - unlike removing those links, the override survives being
    # re-enabled later.
    remnawave_disabled: bool = False

    @classmethod
    def from_raw(cls, code: str, raw: dict) -> Code:
        """Build a Code from its raw `codes.toml` dict, migrating the
        `links` shape in memory (see parse_links)."""
        data = dict(raw)
        raw_links = data.pop("links", [])
        # Pre-Squad codes may still carry a stray `remnawave_squads` key
        # (raw internal-squad UUIDs, no Squad entity to map them onto) -
        # drop it rather than let it land as an unknown kwarg below.
        data.pop("remnawave_squads", None)
        links = parse_links(raw_links)
        return cls(code=code, links=links, **data)


@dataclass
class RemnawaveAccount:
    """One holder's Remnawave account on one configured server - a holder
    can have at most one account per server (storage.User.remnawave_accounts
    is keyed by server name), since Remnawave accounts and their internal
    squads are both scoped to a single panel."""

    uuid: str = ""
    subscription_url: str = ""
    username: str = ""
    # True if an admin force-linked this account via the "Link Remnawave"
    # flow (dialogs/admin/link_remnawave.py); False if it was provisioned or
    # matched automatically (services/remnawave_sync.py).
    linked_manually: bool = False


@dataclass
class Squad:
    """A bot-admin-managed bundle of internal squads on one configured
    Remnawave server, referenced by id from a Code's `remnawave`-type
    Link.squad_id. Global to the bot (storage.squads.SquadRepo), not
    per-code - the same Squad can be attached to links in several codes."""

    id: str
    name: str
    server: str
    internal_squad_uuids: list[str] = field(default_factory=list)


@dataclass
class User:
    user_id: int
    username: str | None = None
    full_name: str = ""
    first_seen: str = ""
    banned: bool = False
    codes: list[str] = field(default_factory=list)
    # This holder's Remnawave accounts, keyed by server name - at most one
    # per configured server (see RemnawaveAccount). Empty means no account
    # anywhere yet.
    remnawave_accounts: dict[str, RemnawaveAccount] = field(default_factory=dict)
    # Admin override: never provision or grant this user Remnawave squads on
    # any server, regardless of what their codes would otherwise entitle
    # them to. Existing accounts (if any) and their uuids are left alone -
    # only the active grant stops, so re-enabling doesn't need to
    # re-provision or re-match anything.
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
