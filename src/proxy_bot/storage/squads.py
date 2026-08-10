from __future__ import annotations

from pathlib import Path

from .models import Squad
from .toml_file import TomlFile


class SquadRepo:
    """Bot-admin-managed Squad registry (see storage.models.Squad), backed
    by squads.toml. Ids are short sequential strings from a counter in the
    file root, not UUIDs - they end up in aiogram_dialog Select/Multiselect
    callback_data, which this codebase already keeps well under Telegram's
    64-byte cap elsewhere (see dialogs/admin/codes.py addressing links by
    position for the same reason)."""

    def __init__(self, path: Path) -> None:
        self._file = TomlFile(path, default={"squads": {}, "next_id": 1})

    async def get(self, squad_id: str) -> Squad | None:
        data = await self._file.read()
        raw = data.get("squads", {}).get(squad_id)
        if raw is None:
            return None
        return Squad(id=squad_id, **raw)

    async def all(self) -> list[Squad]:
        data = await self._file.read()
        return [Squad(id=key, **raw) for key, raw in data.get("squads", {}).items()]

    async def create(self, name: str, server: str, internal_squad_uuids: list[str]) -> Squad:
        def mutate(data: dict) -> Squad:
            squads = data.setdefault("squads", {})
            squad_id = str(data.get("next_id", 1))
            data["next_id"] = int(squad_id) + 1
            squads[squad_id] = {
                "name": name,
                "server": server,
                "internal_squad_uuids": list(internal_squad_uuids),
            }
            return Squad(id=squad_id, **squads[squad_id])

        return await self._file.update(mutate)

    async def set_name(self, squad_id: str, name: str) -> bool:
        def mutate(data: dict) -> bool:
            squads = data.get("squads", {})
            if squad_id not in squads:
                return False
            squads[squad_id]["name"] = name
            return True

        return await self._file.update(mutate)

    async def set_internal_squad_uuids(self, squad_id: str, internal_squad_uuids: list[str]) -> bool:
        def mutate(data: dict) -> bool:
            squads = data.get("squads", {})
            if squad_id not in squads:
                return False
            squads[squad_id]["internal_squad_uuids"] = list(internal_squad_uuids)
            return True

        return await self._file.update(mutate)

    async def delete(self, squad_id: str) -> bool:
        def mutate(data: dict) -> bool:
            squads = data.get("squads", {})
            if squad_id not in squads:
                return False
            del squads[squad_id]
            return True

        return await self._file.update(mutate)
