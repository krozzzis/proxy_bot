from __future__ import annotations

import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path


def setup_logging(logs_dir: Path, level: str = "INFO") -> None:
    logs_dir.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = TimedRotatingFileHandler(
        filename=logs_dir / "bot.log",
        when="midnight",
        backupCount=14,
        encoding="utf-8",
        utc=True,
    )
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()
    root.addHandler(file_handler)
    root.addHandler(console_handler)

    # aiohttp/aiogram internals are noisy at DEBUG; keep them at INFO minimum.
    logging.getLogger("aiogram.event").setLevel(max(logging.INFO, root.level))
