from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent

_LOGO_MODES = ("before", "caption")


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
    # Off by default: traffic usage is a coarser, more sensitive number than
    # "does this account still have access" - operators who don't want it
    # shown (to users or admins) can leave this unset rather than the bot
    # deciding for them.
    show_traffic_usage: bool
    # Optional branded logo - unset (default) disables the feature entirely,
    # same opt-in shape as the Remnawave integration below.
    logo_path: Path | None
    # How logo_path is shown, when set:
    # "before"  - its own plain photo message right before the main menu on
    #             every /start (mirrors the Liberty VPN bot; default).
    # "caption" - attached directly to the main menu message itself (photo
    #             with the menu text as its caption, buttons underneath).
    logo_mode: str
    # Per-locale overrides, keyed by lowercased locale code (e.g. "ru"),
    # from any BRANDED_LOGO_PATH_<LOCALE> env var. Optional on top of an
    # already-optional feature: without an override, utils/branding.py's
    # resolve_logo_path() still auto-picks a `<logo_path stem>_<locale>
    # <suffix>` sibling file (logo.png -> logo_ru.png) if one exists, before
    # falling back to logo_path itself.
    logo_path_overrides: dict[str, Path]


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Environment variable {name} is required but not set")
    return value


def _bool_env(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


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
        show_traffic_usage=_bool_env("SHOW_TRAFFIC_USAGE"),
        logo_path=(Path(os.environ["BRANDED_LOGO_PATH"]) if os.environ.get("BRANDED_LOGO_PATH") else None),
        logo_mode=_logo_mode_env(),
        logo_path_overrides=_logo_path_overrides_env(),
    )


def _logo_mode_env() -> str:
    value = os.environ.get("BRANDED_LOGO_MODE", "before").strip().lower()
    if value not in _LOGO_MODES:
        # A typo here (e.g. "captoin") would otherwise silently fall back to
        # "before" - wrong mode, no error, nothing in the logs to explain why
        # the logo isn't showing where the operator configured it to.
        raise RuntimeError(f"BRANDED_LOGO_MODE must be one of {_LOGO_MODES}, got {value!r}")
    return value


_LOGO_OVERRIDE_PREFIX = "BRANDED_LOGO_PATH_"


def _logo_path_overrides_env() -> dict[str, Path]:
    return {
        key[len(_LOGO_OVERRIDE_PREFIX) :].lower(): Path(value)
        for key, value in os.environ.items()
        if key.startswith(_LOGO_OVERRIDE_PREFIX) and value
    }
