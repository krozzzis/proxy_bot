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


@dataclass
class User:
    user_id: int
    username: str | None = None
    full_name: str = ""
    first_seen: str = ""
    banned: bool = False
    codes: list[str] = field(default_factory=list)


@dataclass
class Admin:
    user_id: int
    username: str | None = None
    added_by: int = 0
    added_at: str = ""
