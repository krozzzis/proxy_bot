from __future__ import annotations

import asyncio
import os
import tomllib
from collections.abc import Callable
from pathlib import Path
from typing import Any, TypeVar

import tomli_w

T = TypeVar("T")


class TomlFile:
    """Async-safe TOML-backed store with atomic (write-tmp + replace) writes.

    A single asyncio.Lock serializes all reads and read-modify-write cycles
    for this file within the process, which is what actually prevents
    concurrent handlers from corrupting or losing data.
    """

    def __init__(self, path: Path, default: dict[str, Any]) -> None:
        self.path = path
        self._default = default
        self._lock = asyncio.Lock()

    def _read_sync(self) -> dict[str, Any]:
        if not self.path.exists():
            return {k: (v.copy() if isinstance(v, dict) else v) for k, v in self._default.items()}
        with self.path.open("rb") as fp:
            return tomllib.load(fp)

    def _write_sync(self, data: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self.path.with_name(self.path.name + ".tmp")
        with tmp_path.open("wb") as fp:
            tomli_w.dump(data, fp)
        os.replace(tmp_path, self.path)

    async def read(self) -> dict[str, Any]:
        async with self._lock:
            return await asyncio.to_thread(self._read_sync)

    async def update(self, mutator: Callable[[dict[str, Any]], T]) -> T:
        """Read the file, run `mutator` on the parsed dict in place, persist it.

        Returns whatever `mutator` returns.
        """
        async with self._lock:
            data = await asyncio.to_thread(self._read_sync)
            result = mutator(data)
            await asyncio.to_thread(self._write_sync, data)
            return result
