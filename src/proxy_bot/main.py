from __future__ import annotations

import asyncio
import contextlib
import logging
import signal
import ssl
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramAPIError, TelegramForbiddenError
from aiogram.filters import ExceptionTypeFilter
from aiogram.types import FSInputFile
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiogram_dialog import setup_dialogs
from aiogram_dialog.api.exceptions import OutdatedIntent, UnknownIntent, UnknownState
from aiohttp import web

from proxy_bot.commands import setup_bot_commands
from proxy_bot.config import Config, load_config
from proxy_bot.dialogs import router as dialogs_router
from proxy_bot.fsm import build_fsm_storage
from proxy_bot.handlers import get_command_routers, get_fallback_routers, on_unknown_dialog_event
from proxy_bot.heartbeat import run_heartbeat
from proxy_bot.logging_config import setup_logging
from proxy_bot.middlewares import InteractionLoggingMiddleware, RateLimitMiddleware
from proxy_bot.remnawave import RemnawaveClient, RemnawaveRegistry
from proxy_bot.services.remnawave_sync import run_remnawave_ban_sync
from proxy_bot.storage import Storage
from proxy_bot.utils.i18n import build_i18n_middleware, watch_locales
from proxy_bot.utils.webhook_cert import ensure_self_signed_cert, is_self_signed

logger = logging.getLogger(__name__)

# How often the webhook watchdog polls getWebhookInfo, and how fresh a
# reported delivery failure has to be to count as "currently broken" rather
# than a stale error frozen from some past incident that already recovered
# (Telegram never clears last_error_date/last_error_message on success -
# they just stop advancing). A failure timestamped within the last two
# check cycles is treated as ongoing.
_WEBHOOK_CHECK_INTERVAL = 60.0
_WEBHOOK_ERROR_RECENCY = 2 * _WEBHOOK_CHECK_INTERVAL

# Backoff for retrying the admin fallback notice - deliberately unbounded
# (not a fixed attempt count): if outbound connectivity is also down when
# the webhook is first found broken, the notice is only meaningful once it
# can actually get through, however long that takes.
_NOTIFY_RETRY_MIN = 5.0
_NOTIFY_RETRY_MAX = 120.0


def _register_background_task(dp: Dispatcher, factory: Callable[[], Awaitable[None]]) -> None:
    """Run factory() as a task for the lifetime of the bot, cancelled on shutdown."""
    task: asyncio.Task[None] | None = None

    async def start(**_kwargs: object) -> None:
        nonlocal task
        task = asyncio.create_task(factory())

    async def stop(**_kwargs: object) -> None:
        if task is not None:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task

    dp.startup.register(start)
    dp.shutdown.register(stop)


async def run() -> None:
    config = load_config()
    setup_logging(config.logs_dir, level=config.log_level)

    storage = Storage(config.data_dir, root_admin_id=config.root_admin_id)
    remnawave_clients = {
        name: RemnawaveClient(server.url, server.token) for name, server in config.remnawave_servers.items()
    }
    remnawave = RemnawaveRegistry(remnawave_clients) if remnawave_clients else None

    # HTML parse mode is on for every send (plain fluent strings render fine
    # as HTML). Any dynamic value interpolated into a message - names, codes,
    # links, admin-authored text - must go through utils.html.esc() first.
    bot = Bot(token=config.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=build_fsm_storage(config))
    dp["storage"] = storage
    dp["remnawave"] = remnawave
    dp["dispatcher"] = dp
    dp["show_traffic_usage"] = config.show_traffic_usage
    dp["logo_path"] = config.logo_path
    dp["logo_mode"] = config.logo_mode
    dp["logo_path_overrides"] = config.logo_path_overrides

    i18n_middleware = build_i18n_middleware(config.locales_dir, config.default_locale, storage)
    i18n_middleware.setup(dispatcher=dp)

    interaction_logger = InteractionLoggingMiddleware()
    dp.message.outer_middleware(interaction_logger)
    dp.callback_query.outer_middleware(interaction_logger)

    # Registered after the logger, not before - every attempt (including a
    # throttled one) still gets an audit line, but throttled ones never
    # reach a handler.
    rate_limiter = RateLimitMiddleware()
    dp.message.outer_middleware(rate_limiter)
    dp.callback_query.outer_middleware(rate_limiter)

    for router in get_command_routers():
        dp.include_router(router)
    dp.include_router(dialogs_router)
    for router in get_fallback_routers():
        dp.include_router(router)

    setup_dialogs(dp)
    dp.errors.register(on_unknown_dialog_event, ExceptionTypeFilter(UnknownIntent, OutdatedIntent, UnknownState))

    _register_background_task(dp, lambda: watch_locales(i18n_middleware.core, config.locales_dir))
    # Picked up by the Docker HEALTHCHECK (see docker-compose.yml) - the bot
    # has no HTTP server to probe, so liveness is "the event loop is still
    # ticking" via a periodically touched file.
    _register_background_task(dp, lambda: run_heartbeat(config.data_dir / ".heartbeat"))
    # Pull direction of ban-state sync (a panel-side enable/disable flowing
    # back into `banned`) - no-ops on its own if remnawave is None.
    _register_background_task(dp, lambda: run_remnawave_ban_sync(storage, remnawave))

    await setup_bot_commands(bot, storage)

    try:
        if config.use_webhook:
            fell_back = await _run_webhook(bot, dp, config)
            if fell_back:
                await _fall_back_to_polling(bot, dp, storage, i18n_middleware.core, config)
            # else: a clean shutdown signal, not a failure - nothing more to run.
        else:
            # No-op if no webhook was ever set - safe to call unconditionally
            # here since this branch is polling-only (the webhook branch
            # sets one instead of deleting it, and the fallback path above
            # already deletes it itself before calling _start_polling).
            await bot.delete_webhook(drop_pending_updates=True)
            await _start_polling(bot, dp)
    finally:
        # SimpleRequestHandler.close() (webhook branch) already closes the
        # bot session as part of the aiohttp app's own shutdown, but a
        # second close() is a no-op - simpler to always close here than to
        # track which branch already did it.
        await bot.session.close()
        if remnawave is not None:
            await remnawave.close_all()


async def _start_polling(bot: Bot, dp: Dispatcher) -> None:
    logger.info("Starting bot polling")
    await dp.start_polling(bot)


async def _watch_webhook_health(bot: Bot) -> None:
    """Polls getWebhookInfo and returns (doesn't raise) once Telegram
    reports a delivery failure recent enough to treat the webhook as
    currently broken - see `_run_webhook`, which races this against its
    shutdown-signal wait and falls back to polling if this is what won.
    Never returns on its own otherwise - runs until cancelled.

    Requires *both* a recent `last_error_date` *and* a nonzero
    `pending_update_count` - Telegram stamps last_error_date on a single
    failed delivery attempt (a network blip, a momentary 5xx) and then
    routinely retries and recovers on its own, but never clears that
    timestamp once the retry succeeds. Recency alone would treat that
    ordinary blip the same as an actually-broken endpoint and tear down a
    working webhook over it; a pile of undelivered updates is what
    distinguishes "really can't reach us" from "reached us, once, a bit
    slowly".
    """
    while True:
        await asyncio.sleep(_WEBHOOK_CHECK_INTERVAL)
        try:
            info = await bot.get_webhook_info()
        except TelegramAPIError:
            logger.warning("Webhook health check itself failed to reach Telegram", exc_info=True)
            continue
        if info.last_error_date is None or info.pending_update_count == 0:
            continue
        age = (datetime.now(UTC) - info.last_error_date).total_seconds()
        if age <= _WEBHOOK_ERROR_RECENCY:
            logger.error(
                "Webhook delivery is failing (%r, %.0fs ago, %d update(s) pending) - falling back to long polling",
                info.last_error_message,
                age,
                info.pending_update_count,
            )
            return


async def _run_webhook(bot: Bot, dp: Dispatcher, config: Config) -> bool:
    """The webhook counterpart to `dp.start_polling(bot)`: binds an aiohttp
    server directly (no reverse proxy involved - see Config.use_webhook) and
    registers it with Telegram. Runs until cancelled by a shutdown signal or
    until `_watch_webhook_health` decides delivery is currently broken -
    returns True in the latter case (caller should fall back to polling),
    False for a normal shutdown.
    """
    ensure_self_signed_cert(config.webhook_cert_path, config.webhook_privkey_path, config.webhook_host)

    app = web.Application()
    SimpleRequestHandler(dispatcher=dp, bot=bot, secret_token=config.webhook_secret_token).register(
        app, path=config.webhook_path
    )
    # Wires dp's own startup/shutdown (background tasks registered via
    # _register_background_task, above) into the aiohttp app's lifecycle -
    # same role dp.start_polling() plays for the polling branch.
    setup_application(app, dp, bot=bot)

    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ssl_context.load_cert_chain(str(config.webhook_cert_path), str(config.webhook_privkey_path))

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, config.webapp_host, config.webapp_port, ssl_context=ssl_context)
    await site.start()
    logger.info("Webhook server listening on %s:%s%s", config.webapp_host, config.webapp_port, config.webhook_path)

    # Only registered with Telegram once something is actually listening -
    # the other way round would have Telegram start POSTing (and retrying,
    # and logging a delivery error) against a port nothing answers on yet.
    # Telegram only calls back on 443/80/88/8443 and only omits the port
    # from the URL for 443 (the HTTPS default) - every other allowed port
    # must be spelled out explicitly or the callback never arrives.
    port_suffix = "" if config.webapp_port == 443 else f":{config.webapp_port}"
    webhook_url = f"https://{config.webhook_host}{port_suffix}{config.webhook_path}"
    # `certificate=` pins Telegram to this exact file instead of letting it
    # validate the chain normally - required for a self-signed cert (no CA
    # to validate it against otherwise), wrong for a real CA-issued one:
    # pinning would keep working right up until this file expires, then
    # break outright rather than just carrying on across a renewal the way
    # normal CA validation would.
    pin_cert = is_self_signed(config.webhook_cert_path)
    await bot.set_webhook(
        url=webhook_url,
        certificate=FSInputFile(config.webhook_cert_path) if pin_cert else None,
        secret_token=config.webhook_secret_token,
        drop_pending_updates=True,
    )
    logger.info("Webhook registered at %s (cert %s)", webhook_url, "self-signed, pinned" if pin_cert else "CA-issued")

    # dp.start_polling() (the other branch) installs its own SIGINT/SIGTERM
    # handling; this branch needs the same so `docker stop` (SIGTERM) still
    # runs the `finally` below - and, via it, dp.emit_shutdown() - instead
    # of the process just dying mid-request with background tasks and the
    # FSM store never told to close.
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    loop.add_signal_handler(signal.SIGTERM, stop_event.set)
    loop.add_signal_handler(signal.SIGINT, stop_event.set)

    watchdog_task = asyncio.create_task(_watch_webhook_health(bot))
    stop_task = asyncio.create_task(stop_event.wait())
    try:
        done, pending = await asyncio.wait({watchdog_task, stop_task}, return_when=asyncio.FIRST_COMPLETED)
        for task in pending:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
        return watchdog_task in done
    finally:
        # dp.start_polling() installs its own signal handlers on the same
        # loop when the fallback path below calls it next - remove ours
        # first so there's exactly one handler per signal at a time, not a
        # question of which one "wins".
        loop.remove_signal_handler(signal.SIGTERM)
        loop.remove_signal_handler(signal.SIGINT)
        await runner.cleanup()


async def _notify_admin_fallback(bot: Bot, storage: Storage, i18n_core, config: Config, error_message: str | None) -> None:
    """Best-effort admin alert that a webhook->polling fallback happened,
    retried with backoff until it actually gets through - see the
    `_NOTIFY_RETRY_*` constants' docstring for why there's no attempt cap.
    Runs as its own background task (not awaited by the fallback path) so a
    slow/failing outbound connection never delays polling from starting.
    """
    admin = await storage.users.get(config.root_admin_id)
    locale = admin.locale if admin and admin.locale else config.default_locale
    text = i18n_core.get("admin-webhook-fallback-notice", locale, error=error_message or "—")

    delay = _NOTIFY_RETRY_MIN
    while True:
        try:
            await bot.send_message(config.root_admin_id, text)
            return
        except TelegramForbiddenError:
            # Root admin blocked the bot or never started a chat with it -
            # no amount of retrying fixes that; give up rather than spin
            # forever on a condition connectivity can't resolve.
            logger.warning("Couldn't deliver the webhook-fallback notice - root admin is unreachable", exc_info=True)
            return
        except TelegramAPIError:
            logger.warning("Couldn't deliver the webhook-fallback notice yet, retrying in %.0fs", delay, exc_info=True)
            await asyncio.sleep(delay)
            delay = min(delay * 2, _NOTIFY_RETRY_MAX)


async def _fall_back_to_polling(bot: Bot, dp: Dispatcher, storage: Storage, i18n_core, config: Config) -> None:
    last_error = None
    with contextlib.suppress(TelegramAPIError):
        info = await bot.get_webhook_info()
        last_error = info.last_error_message

    # Keep whatever updates piled up while the webhook was broken - unlike
    # a normal polling-mode boot (which deliberately drops a stale backlog),
    # this is specifically about recovering delivery, not starting fresh.
    await bot.delete_webhook(drop_pending_updates=False)
    # Not awaited here - see _notify_admin_fallback's own docstring for why
    # (a slow/failing send must not delay polling from starting). Assigned
    # to a local rather than left as a bare create_task() call: asyncio only
    # holds a weak reference to a task otherwise, so with nothing else
    # keeping it alive it can be garbage-collected mid-retry-loop. This
    # local survives for as long as the coroutine frame does, which is the
    # rest of the process's life - _start_polling below never returns.
    notify_task = asyncio.create_task(_notify_admin_fallback(bot, storage, i18n_core, config, last_error))
    try:
        await _start_polling(bot, dp)
    finally:
        notify_task.cancel()


def main() -> None:
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        logger.info("Bot stopped")


if __name__ == "__main__":
    main()
