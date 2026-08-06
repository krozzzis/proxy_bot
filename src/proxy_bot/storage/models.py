from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Code:
    code: str
    links: list[str] = field(default_factory=list)
    description: str = ""
    created_by: int = 0
    created_at: str = ""
    active: bool = True
    # Internal squad UUIDs granted on activation. Empty means fixed `links`
    # only - no per-user Remnawave account is provisioned for this code.
    remnawave_squads: list[str] = field(default_factory=list)
    # Admin override: this code contributes no squads to any holder's
    # account, regardless of `remnawave_squads` - unlike clearing the squad
    # list itself, the selection survives being re-enabled later.
    remnawave_disabled: bool = False


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
