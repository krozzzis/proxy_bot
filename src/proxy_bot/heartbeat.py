from __future__ import annotations

import asyncio
from pathlib import Path


async def run_heartbeat(path: Path, interval: float = 30.0) -> None:
    """Touch a file periodically so a Docker HEALTHCHECK can detect a hung event loop.

    Runs until cancelled - intended to be spawned as a background task for
    the lifetime of the bot process.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    while True:
        path.touch()
        await asyncio.sleep(interval)
