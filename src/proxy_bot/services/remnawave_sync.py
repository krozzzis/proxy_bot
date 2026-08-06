from __future__ import annotations

import asyncio
import logging

from proxy_bot.remnawave import RemnawaveClient, RemnawaveError, RemnawaveUser
from proxy_bot.storage import Storage, User
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


async def compute_remnawave_squads(storage: Storage, db_user: User) -> list[str]:
    """The union of `remnawave_squads` across every code `db_user` currently
    holds - empty if the user's own `remnawave_disabled` override is set
    (regardless of what their codes would otherwise grant), and a code's
    contribution is skipped entirely if that code's own `remnawave_disabled`
    is set."""
    if db_user.remnawave_disabled:
        return []

    squads: set[str] = set()
    for code in db_user.codes:
        code_record = await storage.codes.get(code)
        if code_record is not None and not code_record.remnawave_disabled:
            squads.update(code_record.remnawave_squads)
    return sorted(squads)


async def sync_remnawave_access(storage: Storage, remnawave: RemnawaveClient | None, user_id: int) -> None:
    """Recompute this user's Remnawave squad membership from
    compute_remnawave_squads(), provisioning (or re-linking) their account
    on first grant. Call after any code grant/revoke, or after either
    remnawave_disabled override changes. No-ops if Remnawave isn't
    configured; swallows API errors so a panel hiccup never blocks a local
    code grant/revoke.
    """
    if remnawave is None:
        return

    db_user = await storage.users.get(user_id)
    if db_user is None:
        return

    squad_list = await compute_remnawave_squads(storage, db_user)

    if not squad_list and not db_user.remnawave_uuid:
        return

    try:
        if db_user.remnawave_uuid:
            await remnawave.update_user_squads(db_user.remnawave_uuid, squad_list)
            return

        rw_user = await remnawave.get_user_by_telegram_id(user_id)
        if rw_user is None:
            rw_user = await _create_account(remnawave, db_user, squad_list)
        else:
            await remnawave.update_user_squads(rw_user.uuid, squad_list)
        await storage.users.set_remnawave_account(user_id, rw_user.uuid, rw_user.subscription_url, rw_user.username, manual=False)
    except RemnawaveError:
        logger.warning(
            "Remnawave sync failed for %s", actor_id(user_id, db_user.username), exc_info=True
        )


async def sync_ban_state_from_remnawave(storage: Storage, remnawave: RemnawaveClient, db_user: User) -> None:
    """The pull direction of ban/unban sync: if `db_user`'s linked account
    was disabled or re-enabled directly on the Remnawave panel (not through
    this bot), reflect that into the local `banned` flag. The push
    direction - this bot's own ban/unban toggle - takes effect immediately
    at the point of action instead (dialogs.admin.users.on_toggle_ban), so
    this only ever needs to catch a change the bot didn't make itself.

    Only an ACTIVE/DISABLED status is treated as a ban-state signal; every
    other panel status (expired, traffic-limited, ...) is left alone rather
    than misread as an admin's decision. Refuses to ban a fellow admin
    through this path, mirroring on_toggle_ban's own guard - unlike that
    handler, there's no admin present to show a popup to, so this just logs
    and leaves the local flag untouched.
    """
    if not db_user.remnawave_uuid:
        return
    try:
        rw_user = await remnawave.get_user_by_uuid(db_user.remnawave_uuid)
    except RemnawaveError:
        logger.warning(
            "Failed to fetch Remnawave status for %s", actor_id(db_user.user_id, db_user.username), exc_info=True
        )
        return
    if rw_user is None or rw_user.status not in ("ACTIVE", "DISABLED"):
        return

    remote_banned = rw_user.status == "DISABLED"
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


async def run_remnawave_ban_sync(storage: Storage, remnawave: RemnawaveClient | None, interval: float = 300.0) -> None:
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
            if db_user.remnawave_uuid:
                await sync_ban_state_from_remnawave(storage, remnawave, db_user)
        await asyncio.sleep(interval)


async def retire_auto_provisioned_account(
    remnawave: RemnawaveClient | None, db_user: User, keep_uuid: str
) -> str | None:
    """Clean up the account this user would have gotten from `_create_account`
    (the `tg_<telegram_username>` naming convention) once an admin force-links
    a *different* Remnawave account to them - without this, they end up with
    two live accounts and two subscription URLs, only one of which the bot
    now points at.

    Disables rather than deletes an account that's actually been used
    (`used_traffic_bytes > 0`) - discarding real traffic history isn't this
    bot's call to make, only which account is the active one. Deletes one
    that was provisioned and never connected, since there's nothing there to
    lose. Returns "disabled", "deleted", or None if there was nothing to do
    (no Telegram username to derive the auto account's name from, no such
    account on the panel, or it turned out to already be the account being
    kept).
    """
    if remnawave is None or not db_user.username:
        return None

    auto_username = f"tg_{db_user.username}"
    try:
        auto_user = await remnawave.get_user_by_username(auto_username)
        if auto_user is None or auto_user.uuid == keep_uuid:
            return None
        if auto_user.used_traffic_bytes > 0:
            await remnawave.disable_user(auto_user.uuid)
            return "disabled"
        await remnawave.delete_user(auto_user.uuid)
        return "deleted"
    except RemnawaveError:
        logger.warning(
            "Failed to retire auto-provisioned Remnawave account %r for %s",
            auto_username,
            actor_id(db_user.user_id, db_user.username),
            exc_info=True,
        )
        return None
