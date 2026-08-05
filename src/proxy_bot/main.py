from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import Awaitable, Callable

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import ExceptionTypeFilter
from aiogram_dialog import setup_dialogs
from aiogram_dialog.api.exceptions import OutdatedIntent, UnknownIntent, UnknownState

from proxy_bot.commands import setup_bot_commands
from proxy_bot.config import load_config
from proxy_bot.dialogs import router as dialogs_router
from proxy_bot.fsm import build_fsm_storage
from proxy_bot.handlers import get_command_routers, get_fallback_routers, on_unknown_dialog_event
from proxy_bot.heartbeat import run_heartbeat
from proxy_bot.logging_config import setup_logging
from proxy_bot.middlewares import InteractionLoggingMiddleware
from proxy_bot.remnawave import RemnawaveClient
from proxy_bot.storage import Storage
from proxy_bot.utils.i18n import build_i18n_middleware, watch_locales

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
    remnawave = (
        RemnawaveClient(config.remnawave_api_url, config.remnawave_api_token)
        if config.remnawave_api_url and config.remnawave_api_token
        else None
    )

    # HTML parse mode is on for every send (plain fluent strings render fine
    # as HTML). Any dynamic value interpolated into a message - names, codes,
    # links, admin-authored text - must go through utils.html.esc() first.
    bot = Bot(token=config.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=build_fsm_storage(config))
    dp["storage"] = storage
    dp["remnawave"] = remnawave
    dp["dispatcher"] = dp

    i18n_middleware = build_i18n_middleware(config.locales_dir, config.default_locale)
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

    await setup_bot_commands(bot, storage)

    logger.info("Starting bot polling")
    await bot.delete_webhook(drop_pending_updates=True)
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        if remnawave is not None:
            await remnawave.close()


def main() -> None:
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        logger.info("Bot stopped")


if __name__ == "__main__":
    main()
