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
    # Explicit language choice from the settings menu. Empty means "not
    # chosen yet" - falls back to the bot's default_locale.
    locale: str = ""


@dataclass
class Admin:
    user_id: int
    username: str | None = None
    added_by: int = 0
    added_at: str = ""
