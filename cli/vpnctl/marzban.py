"""Тонкий клиент REST API Marzban (FR-6.5).

Все операции с пользователями идут через API — никаких прямых правок БД. Панель
доступна на 127.0.0.1 через SSH-туннель (О-3), поэтому base URL локальный.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

GB = 1024**3


class MarzbanError(RuntimeError):
    pass


@dataclass
class MarzbanUser:
    username: str
    status: str
    data_limit: int | None
    used_traffic: int
    expire: int | None
    subscription_url: str
    online_at: str | None

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> MarzbanUser:
        return cls(
            username=data["username"],
            status=data.get("status", "unknown"),
            data_limit=data.get("data_limit"),
            used_traffic=data.get("used_traffic", 0),
            expire=data.get("expire"),
            subscription_url=data.get("subscription_url", ""),
            online_at=data.get("online_at"),
        )

    @property
    def is_online(self) -> bool:
        return self.online_at is not None


class MarzbanClient:
    """Аутентифицированный клиент. Использовать как контекст-менеджер или вызвать close()."""

    def __init__(
        self,
        base_url: str,
        username: str,
        password: str,
        timeout: float = 15.0,
        transport: httpx.BaseTransport | None = None,
    ):
        self._base_url = base_url.rstrip("/")
        self._username = username
        self._password = password
        self._client = httpx.Client(base_url=self._base_url, timeout=timeout, transport=transport)
        self._token: str | None = None

    def __enter__(self) -> MarzbanClient:
        self.login()
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def close(self) -> None:
        self._client.close()

    # -- аутентификация -------------------------------------------------------
    def login(self) -> None:
        resp = self._client.post(
            "/api/admin/token",
            data={"username": self._username, "password": self._password},
        )
        if resp.status_code != 200:
            raise MarzbanError(f"Marzban login failed: {resp.status_code} {resp.text}")
        self._token = resp.json()["access_token"]
        self._client.headers["Authorization"] = f"Bearer {self._token}"

    def _ensure_auth(self) -> None:
        if self._token is None:
            self.login()

    def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        self._ensure_auth()
        resp = self._client.request(method, path, **kwargs)
        if resp.status_code == 401:  # токен истёк -> один релогин
            self.login()
            resp = self._client.request(method, path, **kwargs)
        if resp.status_code >= 400:
            raise MarzbanError(f"{method} {path} -> {resp.status_code} {resp.text}")
        return resp

    # -- пользователи ---------------------------------------------------------
    def create_user(
        self,
        username: str,
        *,
        inbound_tag: str,
        flow: str = "xtls-rprx-vision",
        data_limit_gb: float | None = None,
        expire_ts: int | None = None,
    ) -> MarzbanUser:
        body = {
            "username": username,
            "proxies": {"vless": {"flow": flow}},
            "inbounds": {"vless": [inbound_tag]},
            "data_limit": int(data_limit_gb * GB) if data_limit_gb else 0,
            "expire": expire_ts or 0,
            "data_limit_reset_strategy": "no_reset",
            "status": "active",
        }
        resp = self._request("POST", "/api/user", json=body)
        return MarzbanUser.from_api(resp.json())

    def get_user(self, username: str) -> MarzbanUser:
        resp = self._request("GET", f"/api/user/{username}")
        return MarzbanUser.from_api(resp.json())

    def list_users(self) -> list[MarzbanUser]:
        resp = self._request("GET", "/api/users")
        return [MarzbanUser.from_api(u) for u in resp.json().get("users", [])]

    def set_status(self, username: str, status: str) -> MarzbanUser:
        if status not in {"active", "disabled"}:
            raise ValueError("status must be 'active' or 'disabled'")
        resp = self._request("PUT", f"/api/user/{username}", json={"status": status})
        return MarzbanUser.from_api(resp.json())

    def delete_user(self, username: str) -> None:
        self._request("DELETE", f"/api/user/{username}")

    def reset_traffic(self, username: str) -> MarzbanUser:
        resp = self._request("POST", f"/api/user/{username}/reset")
        return MarzbanUser.from_api(resp.json())

    # -- система --------------------------------------------------------------
    def system_stats(self) -> dict[str, Any]:
        return self._request("GET", "/api/system").json()

    def inbounds(self) -> dict[str, Any]:
        return self._request("GET", "/api/inbounds").json()
