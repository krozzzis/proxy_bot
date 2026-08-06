from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from .models import Code
from .toml_file import TomlFile


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


class CodeRepo:
    def __init__(self, path: Path) -> None:
        self._file = TomlFile(path, default={"codes": {}})

    async def get(self, code: str) -> Code | None:
        data = await self._file.read()
        raw = data.get("codes", {}).get(code)
        if raw is None:
            return None
        return Code(code=code, **raw)

    async def exists(self, code: str) -> bool:
        return await self.get(code) is not None

    async def all(self) -> list[Code]:
        data = await self._file.read()
        return [Code(code=key, **raw) for key, raw in data.get("codes", {}).items()]

    async def create(
        self,
        code: str,
        links: list[str],
        description: str,
        created_by: int,
        remnawave_squads: list[str] | None = None,
    ) -> Code | None:
        """Create a new code. Returns None if the code already exists."""

        def mutate(data: dict) -> Code | None:
            codes = data.setdefault("codes", {})
            if code in codes:
                return None
            codes[code] = {
                "links": list(links),
                "description": description,
                "created_by": created_by,
                "created_at": _now(),
                "active": True,
                "remnawave_squads": list(remnawave_squads or []),
            }
            return Code(code=code, **codes[code])

        return await self._file.update(mutate)

    async def rename(self, old_code: str, new_code: str) -> bool:
        """Rename a code, keyed by its code string. Returns False if
        `old_code` doesn't exist or `new_code` is already taken."""

        def mutate(data: dict) -> bool:
            codes = data.get("codes", {})
            if old_code not in codes or new_code in codes:
                return False
            codes[new_code] = codes.pop(old_code)
            return True

        return await self._file.update(mutate)

    async def delete(self, code: str) -> bool:
        def mutate(data: dict) -> bool:
            codes = data.get("codes", {})
            if code not in codes:
                return False
            del codes[code]
            return True

        return await self._file.update(mutate)

    async def add_link(self, code: str, link: str) -> bool:
        def mutate(data: dict) -> bool:
            codes = data.get("codes", {})
            if code not in codes:
                return False
            codes[code].setdefault("links", []).append(link)
            return True

        return await self._file.update(mutate)

    async def remove_link(self, code: str, link: str) -> bool:
        def mutate(data: dict) -> bool:
            codes = data.get("codes", {})
            if code not in codes:
                return False
            links = codes[code].get("links", [])
            if link not in links:
                return False
            links.remove(link)
            return True

        return await self._file.update(mutate)

    async def set_description(self, code: str, description: str) -> bool:
        def mutate(data: dict) -> bool:
            codes = data.get("codes", {})
            if code not in codes:
                return False
            codes[code]["description"] = description
            return True

        return await self._file.update(mutate)

    async def set_remnawave_squads(self, code: str, squads: list[str]) -> bool:
        def mutate(data: dict) -> bool:
            codes = data.get("codes", {})
            if code not in codes:
                return False
            codes[code]["remnawave_squads"] = list(squads)
            return True

        return await self._file.update(mutate)

    async def set_remnawave_disabled(self, code: str, disabled: bool) -> bool:
        def mutate(data: dict) -> bool:
            codes = data.get("codes", {})
            if code not in codes:
                return False
            codes[code]["remnawave_disabled"] = disabled
            return True

        return await self._file.update(mutate)
