from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from .models import Code, Link, dump_link, parse_links
from .toml_file import TomlFile


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _normalize_entry_links(entry: dict) -> list[dict]:
    """Rewrite `entry["links"]` in place to the canonical list-of-dict shape
    (migrating legacy bare-string links and synthesizing a `remnawave`-type
    entry per models.parse_links, if `remnawave_squads` calls for one) and
    return it.

    Every mutator below that indexes into `links` calls this first, so it
    operates on - and persists - the exact same shape `CodeRepo.get`/`all`
    would produce in memory from this entry (see models.Code.from_raw). That
    keeps positions in sync: without this, a link synthesized only in
    memory on read would shift every later index that
    remove_link_at/move_link addresses by position.
    """
    links = parse_links(entry.get("links", []), entry.get("remnawave_squads", []))
    entry["links"] = [dump_link(link) for link in links]
    return entry["links"]


class CodeRepo:
    def __init__(self, path: Path) -> None:
        self._file = TomlFile(path, default={"codes": {}})

    async def get(self, code: str) -> Code | None:
        data = await self._file.read()
        raw = data.get("codes", {}).get(code)
        if raw is None:
            return None
        return Code.from_raw(code, raw)

    async def exists(self, code: str) -> bool:
        return await self.get(code) is not None

    async def all(self) -> list[Code]:
        data = await self._file.read()
        return [Code.from_raw(key, raw) for key, raw in data.get("codes", {}).items()]

    async def create(
        self,
        code: str,
        links: list[Link],
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
                "links": [dump_link(link) for link in links],
                "description": description,
                "created_by": created_by,
                "created_at": _now(),
                "active": True,
                "remnawave_squads": list(remnawave_squads or []),
            }
            _normalize_entry_links(codes[code])
            return Code.from_raw(code, codes[code])

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

    async def add_link(self, code: str, link: Link) -> bool:
        def mutate(data: dict) -> bool:
            codes = data.get("codes", {})
            if code not in codes:
                return False
            links = _normalize_entry_links(codes[code])
            links.append(dump_link(link))
            return True

        return await self._file.update(mutate)

    async def remove_link_at(self, code: str, index: int) -> bool:
        def mutate(data: dict) -> bool:
            codes = data.get("codes", {})
            if code not in codes:
                return False
            links = _normalize_entry_links(codes[code])
            if not (0 <= index < len(links)):
                return False
            links.pop(index)
            return True

        return await self._file.update(mutate)

    async def set_link_url(self, code: str, index: int, url: str) -> bool:
        """Replace the URL of the `type == LINK_TYPE_FIX` link at `index`.
        Callers are responsible for not calling this on a `remnawave`-type
        entry - its URL is resolved live per holder and isn't stored here
        (see models.Link)."""

        def mutate(data: dict) -> bool:
            codes = data.get("codes", {})
            if code not in codes:
                return False
            links = _normalize_entry_links(codes[code])
            if not (0 <= index < len(links)):
                return False
            links[index]["url"] = url
            return True

        return await self._file.update(mutate)

    async def set_link_name(self, code: str, index: int, name: str) -> bool:
        def mutate(data: dict) -> bool:
            codes = data.get("codes", {})
            if code not in codes:
                return False
            links = _normalize_entry_links(codes[code])
            if not (0 <= index < len(links)):
                return False
            links[index]["name"] = name
            return True

        return await self._file.update(mutate)

    async def move_link(self, code: str, index: int, offset: int) -> bool:
        """Swap the link at `index` with the one `offset` positions away
        (-1 = up/earlier, +1 = down/later). Returns False if either
        position is out of range - including at either end of the list, so
        callers don't need to special-case the boundary themselves."""

        def mutate(data: dict) -> bool:
            codes = data.get("codes", {})
            if code not in codes:
                return False
            links = _normalize_entry_links(codes[code])
            target = index + offset
            if not (0 <= index < len(links) and 0 <= target < len(links)):
                return False
            links[index], links[target] = links[target], links[index]
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
            # A code that just gained squads but has no `remnawave`-type
            # link entry yet would otherwise grant access with nothing in
            # "my subscriptions" pointing at it - see models.parse_links.
            _normalize_entry_links(codes[code])
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
