from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent


@dataclass(frozen=True, slots=True)
class Config:
    bot_token: str
    root_admin_id: int
    data_dir: Path
    logs_dir: Path
    locales_dir: Path
    default_locale: str
    log_level: str
    fsm_backend: str
    fsm_sqlite_path: Path
    redis_url: str | None


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Environment variable {name} is required but not set")
    return value


def load_config() -> Config:
    load_dotenv()
    return Config(
        bot_token=_require_env("BOT_TOKEN"),
        root_admin_id=int(_require_env("ROOT_ADMIN_ID")),
        data_dir=Path(os.environ.get("DATA_DIR", BASE_DIR / "data")),
        logs_dir=Path(os.environ.get("LOGS_DIR", BASE_DIR / "logs")),
        locales_dir=Path(os.environ.get("LOCALES_DIR", BASE_DIR / "locales")),
        default_locale=os.environ.get("DEFAULT_LOCALE", "ru"),
        log_level=os.environ.get("LOG_LEVEL", "INFO"),
        fsm_backend=os.environ.get("FSM_BACKEND", "sqlite").lower(),
        fsm_sqlite_path=Path(os.environ.get("FSM_SQLITE_PATH", BASE_DIR / "data" / "fsm.sqlite3")),
        redis_url=os.environ.get("REDIS_URL"),
    )
