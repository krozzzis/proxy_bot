from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent

_LOGO_MODES = ("before", "caption")


@dataclass(frozen=True, slots=True)
class RemnawaveServerConfig:
    url: str
    token: str


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
    # Zero or more independently-configured Remnawave panels, keyed by
    # lowercased server name from the REMNAWAVE_API_URL_<NAME>/
    # REMNAWAVE_API_TOKEN_<NAME> env pair (see _remnawave_servers_env) -
    # empty dict means the integration is off entirely for this deployment.
    remnawave_servers: dict[str, RemnawaveServerConfig]
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
    # Off by default (long polling, see main.run()). When on, the bot binds
    # its own HTTPS listener directly (no reverse proxy involved) and
    # registers it with Telegram via setWebhook, per the "self-signed
    # certificate" pattern the Bot API supports for exactly this - no CA-
    # issued cert or Caddy/Nginx in front required, just a DNS record for
    # webhook_host pointing at this host and the matching port reachable
    # from the internet (443/80/88/8443 are the only ports Telegram will
    # call back on).
    use_webhook: bool
    webhook_host: str
    webhook_path: str
    webhook_secret_token: str
    webhook_cert_path: Path
    webhook_privkey_path: Path
    webapp_host: str
    webapp_port: int


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
        remnawave_servers=_remnawave_servers_env(),
        show_traffic_usage=_bool_env("SHOW_TRAFFIC_USAGE"),
        logo_path=(Path(os.environ["BRANDED_LOGO_PATH"]) if os.environ.get("BRANDED_LOGO_PATH") else None),
        logo_mode=_logo_mode_env(),
        logo_path_overrides=_logo_path_overrides_env(),
        **_webhook_env(),
    )


def _webhook_env() -> dict[str, object]:
    use_webhook = _bool_env("USE_WEBHOOK")
    data_dir = Path(os.environ.get("DATA_DIR", BASE_DIR / "data"))
    # WEBHOOK_HOST/WEBHOOK_SECRET are only required once webhook mode is
    # actually turned on - _require_env here (rather than at Config
    # construction time unconditionally) keeps every polling-mode deployment
    # (the default, including local dev and the test bot) working without
    # ever having to set them.
    webhook_host = _require_env("WEBHOOK_HOST") if use_webhook else ""
    webhook_secret_token = _require_env("WEBHOOK_SECRET") if use_webhook else ""
    return {
        "use_webhook": use_webhook,
        "webhook_host": webhook_host,
        # Secret-bearing path component, not just a fixed "/webhook" - an
        # unauthenticated POST to a guessed path could otherwise feed
        # forged Update objects into the dispatcher. Doubles as the
        # X-Telegram-Bot-Api-Secret-Token value Telegram echoes back on
        # every real callback (see SimpleRequestHandler in main.py), so a
        # request needs to know both to be accepted.
        "webhook_path": f"/webhook/{webhook_secret_token}" if use_webhook else "",
        "webhook_secret_token": webhook_secret_token,
        "webhook_cert_path": Path(os.environ.get("WEBHOOK_CERT_PATH", data_dir / "webhook_cert.pem")),
        "webhook_privkey_path": Path(os.environ.get("WEBHOOK_PRIVKEY_PATH", data_dir / "webhook_privkey.pem")),
        "webapp_host": os.environ.get("WEBAPP_HOST", "0.0.0.0"),
        "webapp_port": int(os.environ.get("WEBAPP_PORT", "8443")),
    }


def _logo_mode_env() -> str:
    value = os.environ.get("BRANDED_LOGO_MODE", "before").strip().lower()
    if value not in _LOGO_MODES:
        # A typo here (e.g. "captoin") would otherwise silently fall back to
        # "before" - wrong mode, no error, nothing in the logs to explain why
        # the logo isn't showing where the operator configured it to.
        raise RuntimeError(f"BRANDED_LOGO_MODE must be one of {_LOGO_MODES}, got {value!r}")
    return value


_REMNAWAVE_URL_PREFIX = "REMNAWAVE_API_URL_"
_REMNAWAVE_TOKEN_PREFIX = "REMNAWAVE_API_TOKEN_"


def _remnawave_servers_env() -> dict[str, RemnawaveServerConfig]:
    """Every REMNAWAVE_API_URL_<NAME> paired with its REMNAWAVE_API_TOKEN_<NAME>,
    keyed by lowercased <NAME>. Each URL requires a matching token (and vice
    versa) - a lone half of the pair is almost certainly a typo'd name on one
    of the two variables, not an intentionally partial server, so it's
    raised on rather than silently dropped (same philosophy as
    _logo_mode_env() refusing a typo'd mode)."""
    urls = {
        key[len(_REMNAWAVE_URL_PREFIX) :].lower(): value
        for key, value in os.environ.items()
        if key.startswith(_REMNAWAVE_URL_PREFIX) and value
    }
    tokens = {
        key[len(_REMNAWAVE_TOKEN_PREFIX) :].lower(): value
        for key, value in os.environ.items()
        if key.startswith(_REMNAWAVE_TOKEN_PREFIX) and value
    }
    missing_tokens = urls.keys() - tokens.keys()
    if missing_tokens:
        raise RuntimeError(
            f"REMNAWAVE_API_URL_<NAME> set without a matching REMNAWAVE_API_TOKEN_<NAME> for: {sorted(missing_tokens)}"
        )
    missing_urls = tokens.keys() - urls.keys()
    if missing_urls:
        raise RuntimeError(
            f"REMNAWAVE_API_TOKEN_<NAME> set without a matching REMNAWAVE_API_URL_<NAME> for: {sorted(missing_urls)}"
        )
    return {name: RemnawaveServerConfig(url=url, token=tokens[name]) for name, url in urls.items()}


_LOGO_OVERRIDE_PREFIX = "BRANDED_LOGO_PATH_"


def _logo_path_overrides_env() -> dict[str, Path]:
    return {
        key[len(_LOGO_OVERRIDE_PREFIX) :].lower(): Path(value)
        for key, value in os.environ.items()
        if key.startswith(_LOGO_OVERRIDE_PREFIX) and value
    }
