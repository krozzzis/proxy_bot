from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from proxy_bot.remnawave import RemnawaveAccountCache, RemnawaveError, RemnawaveRegistry, resolve_account_id

logger = logging.getLogger(__name__)

# Threshold, not an exact match against RemnawaveClient.DEFAULT_EXPIRE_AT:
# this app never sets a real expiry (every account it provisions carries
# that exact placeholder), but a manually force-linked account
# (dialogs/admin/link_remnawave.py) could carry a different far-future date
# set by whoever created it outside the bot - anything this far out still
# reads as "no real expiry" to a user looking at it.
_ETERNAL_YEAR = 2090


def is_eternal(expire_at: str | None) -> bool:
    if not expire_at:
        return True
    try:
        return datetime.fromisoformat(expire_at).year >= _ETERNAL_YEAR
    except ValueError:
        return False


def is_unlimited(traffic_limit_bytes: int) -> bool:
    return traffic_limit_bytes <= 0


def format_gb(num_bytes: int) -> str:
    return f"{num_bytes / (1024**3):.2f}"


# Locale-aware month names for the <tg-time> fallback text (shown only to
# clients too old to render the entity itself, which then picks its own
# display via each user's own client locale/settings) - not delegated to
# datetime.strftime("%B") since that depends on the process's system
# locale being installed and set, which nothing else in this project
# relies on (every other piece of translated text is a literal string in
# locales/*/bot.ftl, not derived from the OS).
_MONTHS = {
    "ru": [
        "января", "февраля", "марта", "апреля", "мая", "июня",
        "июля", "августа", "сентября", "октября", "ноября", "декабря",
    ],
    "en": [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December",
    ],
}


def format_date_fallback(dt: datetime, locale: str) -> str:
    months = _MONTHS.get(locale, _MONTHS["en"])
    return f"{dt.day} {months[dt.month - 1]} {dt.year}"


async def fetch_subscription_lines(
    remnawave: RemnawaveRegistry | None,
    account_cache: RemnawaveAccountCache,
    server: str,
    user_id: int,
    i18n: Any,
    *,
    show_traffic: bool = False,
) -> dict[str, str] | None:
    """Fully-rendered lines for a linked account, fetched live
    (expiry/traffic aren't cached locally - only the resolved account id is,
    via `account_cache`; see remnawave.cache). Shared by the user-facing
    "my subscriptions" screen (dialogs/user/links.py) and the admin
    user-detail page (dialogs/admin/users.py) so the two can't drift apart,
    and rendered here (not left as raw values for the caller's own Fluent
    template) so both label wording and the eternal/unlimited branching
    live in exactly one place: locales/*/bot.ftl's sub-expiry-* and
    sub-traffic-* keys.

    `show_traffic` gates the "traffic" line specifically (Config.
    show_traffic_usage, off by default - see config.py) - traffic usage is
    a coarser, more sensitive number than "does this account still have
    access", so it's opt-in per deployment rather than always shown
    alongside expiry. `traffic` comes back as "" when disabled, same as
    when there's genuinely nothing to show.

    None if there's nothing to show at all: no Remnawave configured, the
    account can't be resolved (see remnawave.cache.resolve_account_id - a
    manually-linked account whose cache entry has expired reads as "no
    account" here until the next sync_remnawave_access re-provisions one),
    or a panel error.
    """
    if remnawave is None:
        return None
    client = remnawave.get(server)
    if client is None:
        return None
    try:
        account_id = await resolve_account_id(account_cache, remnawave, server, user_id)
        if account_id is None:
            return None
        rw_user = await client.get_user_by_id(account_id)
    except RemnawaveError:
        # The cached id may itself be why this failed (deleted on the panel
        # since) - drop it so the next view re-resolves instead of retrying
        # the same dead id for the rest of its TTL.
        await account_cache.invalidate(server, user_id)
        logger.warning(
            "Failed to fetch Remnawave account for %s on server %r for subscription info", user_id, server, exc_info=True
        )
        return None
    if rw_user is None:
        return None

    if is_eternal(rw_user.expire_at):
        expiry = i18n.get("sub-expiry-eternal")
    else:
        dt = datetime.fromisoformat(rw_user.expire_at)
        # Bot API 9.5+ <tg-time> entity (aiogram: HtmlDecoration.DATE_TIME_TAG)
        # with no explicit format, so the client's own built-in date/time
        # display picks how it looks; the tag's content is only the
        # fallback shown to clients that predate it.
        fallback = format_date_fallback(dt, i18n.locale)
        date_tag = f'<tg-time unix="{int(dt.timestamp())}">{fallback}</tg-time>'
        expiry = i18n.get("sub-expiry-normal", date=date_tag)

    traffic = ""
    if show_traffic:
        used = format_gb(rw_user.used_traffic_bytes)
        if is_unlimited(rw_user.traffic_limit_bytes):
            traffic = i18n.get("sub-traffic-unlimited", used=used)
        else:
            traffic = i18n.get("sub-traffic-normal", used=used, limit=format_gb(rw_user.traffic_limit_bytes))

    return {"expiry": expiry, "traffic": traffic}
