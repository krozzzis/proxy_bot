from __future__ import annotations

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


async def sync_remnawave_access(storage: Storage, remnawave: RemnawaveClient | None, user_id: int) -> None:
    """Recompute this user's Remnawave squad membership from the union of
    `remnawave_squads` across every code they currently hold, provisioning
    (or re-linking) their account on first grant. Call after any code
    grant/revoke. No-ops if Remnawave isn't configured; swallows API errors
    so a panel hiccup never blocks a local code grant/revoke.
    """
    if remnawave is None:
        return

    db_user = await storage.users.get(user_id)
    if db_user is None:
        return

    squads: set[str] = set()
    for code in db_user.codes:
        code_record = await storage.codes.get(code)
        if code_record is not None:
            squads.update(code_record.remnawave_squads)
    squad_list = sorted(squads)

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
        await storage.users.set_remnawave_account(user_id, rw_user.uuid, rw_user.subscription_url)
    except RemnawaveError:
        logger.warning(
            "Remnawave sync failed for %s", actor_id(user_id, db_user.username), exc_info=True
        )
