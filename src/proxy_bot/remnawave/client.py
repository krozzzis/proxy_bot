from __future__ import annotations

from dataclasses import dataclass, field

import httpx

# Existing manually-created accounts on the reference panel use these values
# to mean "no limit" - Code itself has no expiry/quota concept in this app,
# so auto-provisioned accounts mirror that convention.
DEFAULT_TRAFFIC_LIMIT_BYTES = 0
DEFAULT_TRAFFIC_LIMIT_STRATEGY = "NO_RESET"
DEFAULT_EXPIRE_AT = "2099-12-31T00:00:00.000Z"


class RemnawaveError(RuntimeError):
    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


@dataclass
class Squad:
    uuid: str
    name: str


@dataclass
class RemnawaveUser:
    uuid: str
    username: str
    telegram_id: int | None
    subscription_url: str | None
    active_internal_squads: list[str] = field(default_factory=list)


def _parse_user(raw: dict) -> RemnawaveUser:
    return RemnawaveUser(
        uuid=raw["uuid"],
        username=raw["username"],
        telegram_id=raw.get("telegramId"),
        subscription_url=raw.get("subscriptionUrl"),
        active_internal_squads=[s["uuid"] for s in raw.get("activeInternalSquads", [])],
    )


class RemnawaveClient:
    def __init__(self, base_url: str, token: str) -> None:
        self._client = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            headers={"Authorization": f"Bearer {token}"},
            timeout=15.0,
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def _request(self, method: str, path: str, *, json: dict | None = None) -> dict:
        try:
            response = await self._client.request(method, path, json=json)
        except httpx.HTTPError as exc:
            raise RemnawaveError(f"{method} {path} failed: {exc}") from exc
        if response.status_code >= 400:
            raise RemnawaveError(
                f"{method} {path} returned {response.status_code}: {response.text}",
                status_code=response.status_code,
            )
        return response.json()

    async def list_internal_squads(self) -> list[Squad]:
        data = await self._request("GET", "/api/internal-squads")
        return [Squad(uuid=s["uuid"], name=s["name"]) for s in data["response"]["internalSquads"]]

    async def get_user_by_telegram_id(self, telegram_id: int) -> RemnawaveUser | None:
        data = await self._request("GET", f"/api/users/by-telegram-id/{telegram_id}")
        users = data["response"]
        return _parse_user(users[0]) if users else None

    async def get_user_by_username(self, username: str) -> RemnawaveUser | None:
        try:
            data = await self._request("GET", f"/api/users/by-username/{username}")
        except RemnawaveError as exc:
            if exc.status_code == 404:
                return None
            raise
        return _parse_user(data["response"])

    async def create_user(
        self,
        *,
        username: str,
        telegram_id: int,
        squads: list[str],
        traffic_limit_bytes: int = DEFAULT_TRAFFIC_LIMIT_BYTES,
        traffic_limit_strategy: str = DEFAULT_TRAFFIC_LIMIT_STRATEGY,
        expire_at: str = DEFAULT_EXPIRE_AT,
    ) -> RemnawaveUser:
        data = await self._request(
            "POST",
            "/api/users",
            json={
                "username": username,
                "telegramId": telegram_id,
                "expireAt": expire_at,
                "trafficLimitBytes": traffic_limit_bytes,
                "trafficLimitStrategy": traffic_limit_strategy,
                "activeInternalSquads": squads,
            },
        )
        return _parse_user(data["response"])

    async def update_user_squads(self, uuid: str, squads: list[str]) -> RemnawaveUser:
        data = await self._request("PATCH", "/api/users", json={"uuid": uuid, "activeInternalSquads": squads})
        return _parse_user(data["response"])
