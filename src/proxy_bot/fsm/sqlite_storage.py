from __future__ import annotations

import asyncio
import json
import sqlite3
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from aiogram.exceptions import DataNotDictLikeError
from aiogram.fsm.state import State
from aiogram.fsm.storage.base import BaseStorage, StateType, StorageKey


def _key_str(key: StorageKey) -> str:
    return f"{key.bot_id}:{key.chat_id}:{key.user_id}:{key.thread_id}:{key.business_connection_id}:{key.destiny}"


class SQLiteStorage(BaseStorage):
    """Dev-friendly persistent FSM storage backed by a local SQLite file.

    A dependency-free, single-file stand-in for RedisStorage: dialog/FSM
    state survives process restarts without needing a Redis server. Not
    meant for multi-process deployments - see RedisStorage for that.

    A single sqlite3 connection is reused across calls (check_same_thread
    disabled) and every access is serialized through one asyncio.Lock, so
    the connection is never touched by two threads concurrently even
    though asyncio.to_thread may run on different worker threads.
    """

    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = asyncio.Lock()
        self._conn = sqlite3.connect(str(path), check_same_thread=False)
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS fsm_state ("
            "key TEXT PRIMARY KEY, state TEXT, data TEXT NOT NULL DEFAULT '{}'"
            ")"
        )
        self._conn.commit()

    async def close(self) -> None:
        async with self._lock:
            await asyncio.to_thread(self._conn.close)

    async def set_state(self, key: StorageKey, state: StateType = None) -> None:
        value = state.state if isinstance(state, State) else state
        db_key = _key_str(key)

        def _write() -> None:
            self._conn.execute(
                "INSERT INTO fsm_state (key, state) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET state = excluded.state",
                (db_key, value),
            )
            self._conn.commit()

        async with self._lock:
            await asyncio.to_thread(_write)

    async def get_state(self, key: StorageKey) -> str | None:
        db_key = _key_str(key)

        def _read() -> str | None:
            row = self._conn.execute("SELECT state FROM fsm_state WHERE key = ?", (db_key,)).fetchone()
            return row[0] if row else None

        async with self._lock:
            return await asyncio.to_thread(_read)

    async def set_data(self, key: StorageKey, data: Mapping[str, Any]) -> None:
        if not isinstance(data, dict):
            msg = f"Data must be a dict or dict-like object, got {type(data).__name__}"
            raise DataNotDictLikeError(msg)
        db_key = _key_str(key)
        payload = json.dumps(data)

        def _write() -> None:
            self._conn.execute(
                "INSERT INTO fsm_state (key, data) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET data = excluded.data",
                (db_key, payload),
            )
            self._conn.commit()

        async with self._lock:
            await asyncio.to_thread(_write)

    async def get_data(self, key: StorageKey) -> dict[str, Any]:
        db_key = _key_str(key)

        def _read() -> dict[str, Any]:
            row = self._conn.execute("SELECT data FROM fsm_state WHERE key = ?", (db_key,)).fetchone()
            return json.loads(row[0]) if row else {}

        async with self._lock:
            return await asyncio.to_thread(_read)
