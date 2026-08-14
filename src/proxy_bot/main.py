from __future__ import annotations

import asyncio
import contextlib
import logging
import signal
import ssl
from collections.abc import Awaitable, Callable

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
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
from proxy_bot.middlewares import InteractionLoggingMiddleware
from proxy_bot.remnawave import RemnawaveClient, RemnawaveRegistry
from proxy_bot.services.remnawave_sync import run_remnawave_ban_sync
from proxy_bot.storage import Storage
from proxy_bot.utils.i18n import build_i18n_middleware, watch_locales
from proxy_bot.utils.webhook_cert import ensure_self_signed_cert

logger = logging.getLogger(__name__)


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
            await _run_webhook(bot, dp, config)
        else:
            logger.info("Starting bot polling")
            # No-op if no webhook was ever set - safe to call unconditionally
            # here since this branch is polling-only (the webhook branch
            # below sets one instead of deleting it).
            await bot.delete_webhook(drop_pending_updates=True)
            await dp.start_polling(bot)
    finally:
        # SimpleRequestHandler.close() (webhook branch) already closes the
        # bot session as part of the aiohttp app's own shutdown, but a
        # second close() is a no-op - simpler to always close here than to
        # track which branch already did it.
        await bot.session.close()
        if remnawave is not None:
            await remnawave.close_all()


async def _run_webhook(bot: Bot, dp: Dispatcher, config: Config) -> None:
    """The webhook counterpart to `dp.start_polling(bot)`: binds an aiohttp
    server directly (no reverse proxy involved - see Config.use_webhook) and
    registers it with Telegram. Runs until cancelled, same contract as
    start_polling.
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
    await bot.set_webhook(
        url=webhook_url,
        certificate=FSInputFile(config.webhook_cert_path),
        secret_token=config.webhook_secret_token,
        drop_pending_updates=True,
    )
    logger.info("Webhook registered at %s", webhook_url)

    # dp.start_polling() (the other branch) installs its own SIGINT/SIGTERM
    # handling; this branch needs the same so `docker stop` (SIGTERM) still
    # runs the `finally` below - and, via it, dp.emit_shutdown() - instead
    # of the process just dying mid-request with background tasks and the
    # FSM store never told to close.
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    loop.add_signal_handler(signal.SIGTERM, stop_event.set)
    loop.add_signal_handler(signal.SIGINT, stop_event.set)
    try:
        await stop_event.wait()
    finally:
        await runner.cleanup()


def main() -> None:
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        logger.info("Bot stopped")


if __name__ == "__main__":
    main()
