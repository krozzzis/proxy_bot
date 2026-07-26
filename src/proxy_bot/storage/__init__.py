from __future__ import annotations

from pathlib import Path

from .admins import AdminRepo
from .codes import CodeRepo
from .models import Admin, Code, User
from .users import UserRepo

__all__ = [
    "Admin",
    "AdminRepo",
    "Code",
    "CodeRepo",
    "Storage",
    "User",
    "UserRepo",
]


class Storage:
    """Bundles the three TOML-backed repositories used by the bot."""

    def __init__(self, data_dir: Path, root_admin_id: int) -> None:
        data_dir.mkdir(parents=True, exist_ok=True)
        self.users = UserRepo(data_dir / "users.toml")
        self.codes = CodeRepo(data_dir / "codes.toml")
        self.admins = AdminRepo(data_dir / "admins.toml", root_admin_id=root_admin_id)
