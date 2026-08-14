from __future__ import annotations

import json
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
class InternalSquad:
    uuid: str
    name: str


@dataclass
class RemnawaveUser:
    # Panel-internal numeric primary key (Remnawave 3.x+) - required by every
    # write endpoint (PATCH/DELETE/actions). Panels below 3.0 identified
    # users by a `uuid` instead; this app only ever talks to 3.x+ panels.
    id: int
    # Stable public identifier used in subscription URLs and the
    # by-short-uuid lookup - the closest 3.x equivalent of the old `uuid`.
    short_uuid: str
    username: str
    telegram_id: int | None
    subscription_url: str | None
    active_internal_squads: list[str] = field(default_factory=list)
    # Lifetime traffic, from the panel's own counter - the simplest signal
    # for "has this account ever actually been used" (vs. just provisioned
    # and never connected), used to decide disable-vs-delete when an admin
    # force-links a different account over an auto-provisioned one. Distinct
    # from userTraffic.usedTrafficBytes, which can reset on a
    # trafficLimitStrategy period.
    used_traffic_bytes: int = 0
    # 0 means unlimited (DEFAULT_TRAFFIC_LIMIT_BYTES) - shown to users/admins
    # as the account's traffic cap.
    traffic_limit_bytes: int = 0
    # ISO 8601 string, or None if the panel didn't send one. DEFAULT_EXPIRE_AT
    # is this app's own "no real expiry" placeholder, but a manually linked
    # account (dialogs/admin/link_remnawave.py) could carry a genuinely
    # different value from whoever set it up outside the bot.
    expire_at: str | None = None
    # "ACTIVE", "DISABLED", or a handful of other panel-driven states
    # (expired, limited, ...) this app never sets itself - only ACTIVE vs
    # DISABLED is meaningful to services.remnawave_sync's ban-state
    # reconciliation; anything else is left alone rather than guessed at.
    status: str = "ACTIVE"


def _parse_user(raw: dict) -> RemnawaveUser:
    return RemnawaveUser(
        id=raw["id"],
        short_uuid=raw.get("shortUuid", ""),
        username=raw["username"],
        telegram_id=raw.get("telegramId"),
        subscription_url=raw.get("subscriptionUrl"),
        active_internal_squads=[s["uuid"] for s in raw.get("activeInternalSquads", [])],
        used_traffic_bytes=(raw.get("userTraffic") or {}).get("lifetimeUsedTrafficBytes", 0),
        traffic_limit_bytes=raw.get("trafficLimitBytes", 0),
        expire_at=raw.get("expireAt"),
        status=raw.get("status", "ACTIVE"),
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

    async def _request(
        self, method: str, path: str, *, json_body: dict | None = None, params: dict | None = None
    ) -> dict:
        try:
            response = await self._client.request(method, path, json=json_body, params=params)
        except httpx.HTTPError as exc:
            raise RemnawaveError(f"{method} {path} failed: {exc}") from exc
        if response.status_code >= 400:
            raise RemnawaveError(
                f"{method} {path} returned {response.status_code}: {response.text}",
                status_code=response.status_code,
            )
        # A number of 3.x write endpoints (DELETE, enable/disable actions on
        # some panel versions) answer 204/202 with an empty body - nothing to
        # decode, and callers of those methods don't use the return value.
        if not response.content:
            return {}
        try:
            return response.json()
        except ValueError as exc:
            raise RemnawaveError(f"{method} {path} returned a non-JSON body: {exc}") from exc

    async def list_internal_squads(self) -> list[InternalSquad]:
        data = await self._request("GET", "/api/internal-squads")
        return [InternalSquad(uuid=s["uuid"], name=s["name"]) for s in data["response"]["internalSquads"]]

    async def get_user_by_id(self, user_id: int) -> RemnawaveUser | None:
        try:
            data = await self._request("GET", f"/api/users/{user_id}")
        except RemnawaveError as exc:
            if exc.status_code == 404:
                return None
            raise
        return _parse_user(data["response"])

    async def get_user_by_username(self, username: str) -> RemnawaveUser | None:
        try:
            data = await self._request("GET", f"/api/users/by-username/{username}")
        except RemnawaveError as exc:
            if exc.status_code == 404:
                return None
            raise
        return _parse_user(data["response"])

    async def get_user_by_telegram_id(self, telegram_id: int) -> RemnawaveUser | None:
        """3.x dropped the dedicated by-telegram-id lookup endpoint - the
        panel's own frontend does this same telegramId-filtered listing
        query for its user search, so it's the supported (if less direct)
        replacement rather than a workaround."""
        data = await self._request(
            "GET",
            "/api/users",
            params={
                "start": 0,
                "size": 1,
                "filters": json.dumps([{"id": "telegramId", "value": telegram_id}]),
                "filterModes": json.dumps({"telegramId": "equals"}),
            },
        )
        users = data["response"]["users"]
        return _parse_user(users[0]) if users else None

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
            json_body={
                "username": username,
                "telegramId": telegram_id,
                "expireAt": expire_at,
                "trafficLimitBytes": traffic_limit_bytes,
                "trafficLimitStrategy": traffic_limit_strategy,
                "activeInternalSquads": squads,
            },
        )
        return _parse_user(data["response"])

    async def update_user_squads(self, user_id: int, squads: list[str]) -> RemnawaveUser:
        data = await self._request("PATCH", "/api/users", json_body={"id": user_id, "activeInternalSquads": squads})
        return _parse_user(data["response"])

    async def disable_user(self, user_id: int) -> RemnawaveUser:
        data = await self._request("POST", f"/api/users/{user_id}/actions/disable")
        return _parse_user(data["response"])

    async def enable_user(self, user_id: int) -> RemnawaveUser:
        data = await self._request("POST", f"/api/users/{user_id}/actions/enable")
        return _parse_user(data["response"])

    async def delete_user(self, user_id: int) -> None:
        await self._request("DELETE", f"/api/users/{user_id}")


class RemnawaveRegistry:
    """One RemnawaveClient per configured panel, keyed by (lowercased)
    server name - see config.Config.remnawave_servers. Callers that already
    know which server they're dealing with (a Squad's `server`, or a key in
    User.remnawave_accounts) go through .get(); .names() lists what's
    configured, for UI that needs to offer a server choice or fall back to
    the sole one."""

    def __init__(self, clients: dict[str, RemnawaveClient]) -> None:
        self._clients = clients

    def get(self, server: str) -> RemnawaveClient | None:
        return self._clients.get(server)

    def names(self) -> list[str]:
        return list(self._clients)

    async def close_all(self) -> None:
        for client in self._clients.values():
            await client.close()
