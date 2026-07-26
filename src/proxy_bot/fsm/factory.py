from __future__ import annotations

import logging

from aiogram.fsm.storage.base import BaseStorage

from proxy_bot.config import Config

from .sqlite_storage import SQLiteStorage

logger = logging.getLogger(__name__)


def build_fsm_storage(config: Config) -> BaseStorage:
    """Dialog/FSM state storage: SQLite for dev, Redis for prod (FSM_BACKEND)."""
    if config.fsm_backend == "redis":
        if not config.redis_url:
            raise RuntimeError("REDIS_URL is required when FSM_BACKEND=redis")
        from aiogram.fsm.storage.redis import RedisStorage

        logger.info("Using Redis FSM storage")
        return RedisStorage.from_url(config.redis_url)

    if config.fsm_backend != "sqlite":
        raise RuntimeError(f"Unknown FSM_BACKEND {config.fsm_backend!r}, expected 'sqlite' or 'redis'")

    logger.info("Using SQLite FSM storage at %s", config.fsm_sqlite_path)
    return SQLiteStorage(config.fsm_sqlite_path)
