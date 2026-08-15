from __future__ import annotations

import asyncio
import logging

from proxy_bot.remnawave import RemnawaveAccountCache, RemnawaveClient, RemnawaveError, RemnawaveRegistry, RemnawaveUser
from proxy_bot.remnawave.cache import resolve_account_id
from proxy_bot.storage import Storage, User
from proxy_bot.storage.models import LINK_TYPE_REMNAWAVE
from proxy_bot.utils.audit import actor_id

logger = logging.getLogger(__name__)


async def _create_account(remnawave: RemnawaveClient, db_user: User, squads: list[str]) -> RemnawaveUser:
    """Try `tg_<telegram_username>` first (if the user has one), falling back
    to `tg_<telegram_id>` on a username conflict."""
    candidates = ([f"tg_{db_user.username}"] if db_user.username else []) + [f"tg_{db_user.user_id}"]
    for username in candidates[:-1]:
        try:
            return await remnawave.create_user(username=username, telegram_id=db_user.user_id, squads=squads)
        except RemnawaveError as exc:
            if exc.status_code != 400:
                raise
    return await remnawave.create_user(username=candidates[-1], telegram_id=db_user.user_id, squads=squads)


async def compute_remnawave_grants(storage: Storage, db_user: User) -> dict[str, list[str]]:
    """The internal-squad UUIDs to grant on each Remnawave server, grouped
    by server name - the union of Squad.internal_squad_uuids across every
    `remnawave`-type link in every code `db_user` currently holds, keyed by
    each Squad's own `server`. Empty if the user's own `remnawave_disabled`
    override is set (regardless of what their codes would otherwise grant),
    and a code's contribution is skipped entirely if that code's own
    `remnawave_disabled` is set, as is any individual link with its own
    `disabled` set (see storage.models.Link). A link's `squad_id` pointing
    at a since-deleted Squad is skipped silently - same as any other
    "nothing to point at" dangling reference.
    """
    if db_user.remnawave_disabled:
        return {}

    grants: dict[str, set[str]] = {}
    for code in db_user.codes:
        code_record = await storage.codes.get(code)
        if code_record is None or code_record.remnawave_disabled:
            continue
        for link in code_record.links:
            if link.type != LINK_TYPE_REMNAWAVE or not link.squad_id or link.disabled:
                continue
            squad = await storage.squads.get(link.squad_id)
            if squad is None:
                continue
            grants.setdefault(squad.server, set()).update(squad.internal_squad_uuids)
    return {server: sorted(uuids) for server, uuids in grants.items()}


async def sync_remnawave_access(
    storage: Storage, remnawave: RemnawaveRegistry | None, account_cache: RemnawaveAccountCache, user_id: int
) -> None:
    """Recompute this user's Remnawave squad membership, per server, from
    compute_remnawave_grants(), provisioning (or re-linking) an account on
    first grant for a server. Call after any code grant/revoke, or after
    either remnawave_disabled override changes. No-ops if Remnawave isn't
    configured; swallows API errors per-server so one panel's hiccup never
    blocks a local code grant/revoke or another server's sync.

    An auto-provisioned account whose last grant on a server drops to
    nothing gets disabled ("frozen") rather than just stripped of squads or
    deleted - a later re-grant (the same code again, or a different one)
    re-enables the same account instead of provisioning a new one. A
    manually-linked account (dialogs/admin/link_remnawave.py) is never
    touched on a revoke at all - not frozen, squads left as the admin set
    them - since that account is an admin's explicit pick, not this sync's
    to manage.
    """
    if remnawave is None:
        return

    db_user = await storage.users.get(user_id)
    if db_user is None:
        return

    grants = await compute_remnawave_grants(storage, db_user)
    # The union, not just servers with a grant: a server whose grant just
    # dropped to nothing but still has a live account needs a freeze (or,
    # for a manually-linked one, a no-op - see below) too, or the panel-side
    # membership goes stale instead of following the revoke.
    servers = set(grants) | set(db_user.remnawave_accounts)

    for server in servers:
        client = remnawave.get(server)
        if client is None:
            # Server removed from config since the account was created -
            # nothing to sync against; leave the stored account alone.
            continue

        squad_list = grants.get(server, [])
        account = db_user.remnawave_accounts.get(server)
        if not squad_list and account is None:
            continue

        manual = account.linked_manually if account is not None else False
        # A manually-linked account (dialogs/admin/link_remnawave.py) is an
        # admin's explicit pick, not something this sync should ever
        # freeze/unfreeze or otherwise touch on its own - a revoke here
        # just leaves it exactly as the admin set it up, squads included.
        if not squad_list and manual:
            continue

        try:
            account_id = await account_cache.get(server, user_id)
            just_created = False
            if account_id is None:
                # Cache miss: re-resolve by telegramId. A manually-linked
                # account never gets a panel-side telegramId set, so this
                # always misses for one and falls through to provisioning a
                # fresh "tg_" account below - a known, accepted tradeoff
                # (see remnawave.cache's docstring) rather than this bot
                # writing telegramId onto an account an admin explicitly
                # picked.
                rw_user = await client.get_user_by_telegram_id(user_id)
                if rw_user is None:
                    if not squad_list:
                        continue
                    rw_user = await _create_account(client, db_user, squad_list)
                    manual = False
                    just_created = True
                account_id = rw_user.id
                await account_cache.set(server, user_id, account_id)
                await storage.users.set_remnawave_account(
                    user_id, server, rw_user.subscription_url, rw_user.username, manual=manual
                )

            if just_created:
                # _create_account already set these squads at creation time
                # - nothing more to do.
                continue

            if squad_list:
                if not manual:
                    # Undo a previous freeze (harmless no-op if it wasn't
                    # actually frozen).
                    await client.enable_user(account_id)
                await client.update_user_squads(account_id, squad_list)
            elif not manual:
                # This holder's last grant on this server just dropped to
                # nothing - freeze rather than delete, so re-granting later
                # (another code, or this one again) just re-enables the
                # same account instead of provisioning a new one.
                await client.disable_user(account_id)
        except RemnawaveError:
            # A cached id can be the reason this failed (deleted on the
            # panel since it was resolved) - drop it so the next sync
            # re-resolves instead of retrying the same dead id for the rest
            # of its TTL.
            await account_cache.invalidate(server, user_id)
            logger.warning(
                "Remnawave sync failed for %s on server %r", actor_id(user_id, db_user.username), server, exc_info=True
            )


async def sync_ban_state_from_remnawave(
    storage: Storage, remnawave: RemnawaveRegistry, account_cache: RemnawaveAccountCache, db_user: User
) -> None:
    """The pull direction of ban/unban sync: if any of `db_user`'s linked
    accounts was disabled or re-enabled directly on a Remnawave panel (not
    through this bot), reflect that into the local `banned` flag. The push
    direction - this bot's own ban/unban toggle - takes effect immediately
    at the point of action instead (dialogs.admin.users.on_toggle_ban), so
    this only ever needs to catch a change the bot didn't make itself.

    Only an ACTIVE/DISABLED status is treated as a ban-state signal from a
    given account; every other panel status (expired, traffic-limited, ...)
    is left alone. With accounts on several servers, this mirrors into
    `banned` only when every account with a meaningful status agrees -
    disagreement is logged and left untouched rather than picking a side,
    since "banned" is a single flag with no per-server meaning. Refuses to
    ban a fellow admin through this path, mirroring on_toggle_ban's own
    guard - unlike that handler, there's no admin present to show a popup
    to, so this just logs and leaves the local flag untouched.

    An auto-provisioned account currently holding no grant is also skipped
    (not treated as a ban signal even if DISABLED) - sync_remnawave_access
    freezes exactly that account in exactly that situation on a routine
    revoke, and the panel exposes no way to tell that apart from an actual
    out-of-band ban. A manually-linked account is never auto-frozen, so its
    status stays meaningful regardless of its current grant.
    """
    grants = await compute_remnawave_grants(storage, db_user)
    statuses: set[bool] = set()
    for server, account in db_user.remnawave_accounts.items():
        if not account.linked_manually and not grants.get(server):
            continue
        client = remnawave.get(server)
        if client is None:
            continue
        try:
            account_id = await resolve_account_id(account_cache, remnawave, server, db_user.user_id)
            if account_id is None:
                continue
            rw_user = await client.get_user_by_id(account_id)
        except RemnawaveError:
            # The cached id may itself be why this failed (deleted on the
            # panel since) - drop it so the next sweep re-resolves instead
            # of retrying the same dead id for the rest of its TTL.
            await account_cache.invalidate(server, db_user.user_id)
            logger.warning(
                "Failed to fetch Remnawave status for %s on server %r",
                actor_id(db_user.user_id, db_user.username),
                server,
                exc_info=True,
            )
            continue
        if rw_user is not None and rw_user.status in ("ACTIVE", "DISABLED"):
            statuses.add(rw_user.status == "DISABLED")

    if not statuses:
        return
    if len(statuses) > 1:
        logger.warning(
            "%s has disagreeing ban state across Remnawave servers - leaving local state untouched",
            actor_id(db_user.user_id, db_user.username),
        )
        return

    (remote_banned,) = statuses
    if remote_banned == db_user.banned:
        return
    if remote_banned and await storage.admins.is_admin(db_user.user_id):
        logger.warning(
            "Remnawave shows %s disabled but they're an admin - not mirroring into a local ban",
            actor_id(db_user.user_id, db_user.username),
        )
        return

    await storage.users.set_banned(db_user.user_id, remote_banned)
    logger.info(
        "%s %s locally, mirroring a Remnawave panel status change",
        actor_id(db_user.user_id, db_user.username),
        "banned" if remote_banned else "unbanned",
    )


async def run_remnawave_ban_sync(
    storage: Storage, remnawave: RemnawaveRegistry | None, account_cache: RemnawaveAccountCache, interval: float = 300.0
) -> None:
    """Periodic sweep for the pull direction of ban-state sync (see
    sync_ban_state_from_remnawave): every Remnawave-linked user's panel
    status is checked, and the local `banned` flag updated to match if it
    disagrees. Runs until cancelled - intended to be spawned as a
    background task for the bot's lifetime. No-ops entirely if Remnawave
    isn't configured for this deployment.
    """
    if remnawave is None:
        return
    while True:
        for db_user in await storage.users.all():
            if db_user.remnawave_accounts:
                await sync_ban_state_from_remnawave(storage, remnawave, account_cache, db_user)
        await asyncio.sleep(interval)


async def retire_auto_provisioned_account(
    remnawave: RemnawaveClient | None, db_user: User, keep_id: str
) -> str | None:
    """Clean up the account this user would have gotten from `_create_account`
    (the `tg_<telegram_username>` naming convention) on the same server as
    `remnawave`, once an admin force-links a *different* Remnawave account
    to them on that server - without this, they end up with two live
    accounts and two subscription URLs on that panel, only one of which the
    bot now points at.

    Disables rather than deletes an account that's actually been used
    (`used_traffic_bytes > 0`) - discarding real traffic history isn't this
    bot's call to make, only which account is the active one. Deletes one
    that was provisioned and never connected, since there's nothing there to
    lose. Returns "disabled", "deleted", or None if there was nothing to do
    (no Telegram username to derive the auto account's name from, no such
    account on that server's panel, or it turned out to already be the
    account being kept).
    """
    if remnawave is None or not db_user.username:
        return None

    auto_username = f"tg_{db_user.username}"
    try:
        auto_user = await remnawave.get_user_by_username(auto_username)
        if auto_user is None or str(auto_user.id) == keep_id:
            return None
        if auto_user.used_traffic_bytes > 0:
            await remnawave.disable_user(auto_user.id)
            return "disabled"
        await remnawave.delete_user(auto_user.id)
        return "deleted"
    except RemnawaveError:
        logger.warning(
            "Failed to retire auto-provisioned Remnawave account %r for %s",
            auto_username,
            actor_id(db_user.user_id, db_user.username),
            exc_info=True,
        )
        return None
