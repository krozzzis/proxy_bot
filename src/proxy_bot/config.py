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
    remnawave_api_url: str | None
    remnawave_api_token: str | None


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Environment variable {name} is required but not set")
    return value


def get_locales_dir() -> Path:
    """Same resolution `load_config()` uses for `Config.locales_dir`, exposed
    standalone for import-time consumers (dialogs/common.py's CUSTOM_EMOJI)
    that need it before a full Config is loaded - and without load_config's
    hard requirement on BOT_TOKEN/ROOT_ADMIN_ID being set. Loads .env itself
    (idempotent) since dialogs is imported before main.py's own
    load_config() call would otherwise do it."""
    load_dotenv()
    return Path(os.environ.get("LOCALES_DIR", BASE_DIR / "locales"))


def load_config() -> Config:
    load_dotenv()
    return Config(
        bot_token=_require_env("BOT_TOKEN"),
        root_admin_id=int(_require_env("ROOT_ADMIN_ID")),
        data_dir=Path(os.environ.get("DATA_DIR", BASE_DIR / "data")),
        logs_dir=Path(os.environ.get("LOGS_DIR", BASE_DIR / "logs")),
        locales_dir=get_locales_dir(),
        default_locale=os.environ.get("DEFAULT_LOCALE", "ru"),
        log_level=os.environ.get("LOG_LEVEL", "INFO"),
        fsm_backend=os.environ.get("FSM_BACKEND", "sqlite").lower(),
        fsm_sqlite_path=Path(os.environ.get("FSM_SQLITE_PATH", BASE_DIR / "data" / "fsm.sqlite3")),
        redis_url=os.environ.get("REDIS_URL"),
        remnawave_api_url=os.environ.get("REMNAWAVE_API_URL"),
        remnawave_api_token=os.environ.get("REMNAWAVE_API_TOKEN"),
    )
