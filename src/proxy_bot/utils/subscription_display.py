from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from proxy_bot.config import get_locales_dir
from proxy_bot.remnawave import RemnawaveClient, RemnawaveError
from proxy_bot.utils.emoji_config import load_emoji_config

logger = logging.getLogger(__name__)

# Threshold, not an exact match against RemnawaveClient.DEFAULT_EXPIRE_AT:
# this app never sets a real expiry (every account it provisions carries
# that exact placeholder), but a manually force-linked account
# (dialogs/admin/link_remnawave.py) could carry a different far-future date
# set by whoever created it outside the bot - anything this far out still
# reads as "no real expiry" to a user looking at it.
_ETERNAL_YEAR = 2090

_EMOJI = load_emoji_config(get_locales_dir() / "emoji.toml")


def _tag(name: str) -> str:
    return _EMOJI.get(name, "")


def _parse(expire_at: str) -> datetime:
    return datetime.fromisoformat(expire_at)


def is_eternal(expire_at: str | None) -> bool:
    if not expire_at:
        return True
    try:
        return _parse(expire_at).year >= _ETERNAL_YEAR
    except ValueError:
        return False


def is_unlimited(traffic_limit_bytes: int) -> bool:
    return traffic_limit_bytes <= 0


def format_gb(num_bytes: int) -> str:
    return f"{num_bytes / (1024**3):.1f}"


def expiry_line(expire_at: str | None) -> str:
    """One HTML-ready line for "when does this account expire" - a
    <tg-time> entity (Bot API 9.5+, aiogram: HtmlDecoration.DATE_TIME_TAG)
    with no explicit format, so the client's own built-in date/time
    rendering picks the display, or the "infinity" icon alone if the
    account has no real expiry."""
    if is_eternal(expire_at):
        return _tag("infinity")
    dt = _parse(expire_at)
    unix = int(dt.timestamp())
    fallback = dt.strftime("%d.%m.%Y")
    return f'{_tag("calendar")} <tg-time unix="{unix}">{fallback}</tg-time>'


def traffic_line(used_bytes: int, limit_bytes: int, unit_label: str) -> str:
    """One HTML-ready line for traffic used (and, unless unlimited, the
    cap). `unit_label` is the caller's already-localized "GB"/"ГБ" word -
    the literal "infinity" text isn't translated, matching how the icon
    that goes with it doesn't change per locale either."""
    used = format_gb(used_bytes)
    if is_unlimited(limit_bytes):
        return f'{_tag("infinity")} {used} {unit_label} / infinity'
    limit = format_gb(limit_bytes)
    return f'{_tag("bar_chart")} {used} / {limit} {unit_label}'


async def fetch_subscription_lines(remnawave: RemnawaveClient | None, uuid: str | None, i18n: Any) -> dict[str, str] | None:
    """expiry_line() + traffic_line() for a linked account, fetched live
    (traffic/expiry aren't cached locally - storage.User only keeps the
    uuid). Shared by the user-facing "my subscriptions" screen
    (dialogs/user/links.py) and the admin user-detail page
    (dialogs/admin/users.py) so the two can't drift apart. None if there's
    nothing to show: no Remnawave configured, no account linked, or the
    account turned out not to exist (usually a stale link - deleted on the
    panel since, or by retire_auto_provisioned_account) or a panel error.
    """
    if remnawave is None or not uuid:
        return None
    try:
        rw_user = await remnawave.get_user_by_uuid(uuid)
    except RemnawaveError:
        logger.warning("Failed to fetch Remnawave account %r for subscription info", uuid, exc_info=True)
        return None
    if rw_user is None:
        return None
    unit = i18n.get("sub-unit-gb")
    return {
        "expiry": expiry_line(rw_user.expire_at),
        "traffic": traffic_line(rw_user.used_traffic_bytes, rw_user.traffic_limit_bytes, unit),
    }
