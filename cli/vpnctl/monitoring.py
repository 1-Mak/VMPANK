"""Доступность + детекция «заморозки» + локальный healthcheck (FR-7).

Три независимые проверки:
  * check_ru_availability  — доступен ли IP:443 с российских нод? (FR-7.1)
  * detect_freeze          — TCP коннектится, но передача встаёт на >~15-20 КБ (FR-7.2)
  * local_healthcheck      — контейнеры / порт / AWG / ресурсы на машине (FR-7.3)

Сетевая обвязка тонкая, а парсинг вынесен отдельно, чтобы логику можно было
тестировать без обращения к сети.
"""

from __future__ import annotations

import shutil
import socket
import ssl
import time
from dataclasses import dataclass, field
from typing import Any

import httpx

CHECKHOST_BASE = "https://check-host.net"
# Несколько стабильных RU-нод check-host; переопределяется через CHECKHOST_RU_NODES.
DEFAULT_RU_NODES = ("ru1.node.check-host.net", "ru2.node.check-host.net", "ru3.node.check-host.net")


# --- FR-7.1: доступность из России ------------------------------------------
@dataclass
class NodeResult:
    node: str
    ok: bool
    time_ms: float | None
    error: str | None = None


@dataclass
class AvailabilityReport:
    ip: str
    port: int
    nodes: list[NodeResult] = field(default_factory=list)

    @property
    def reachable_from_ru(self) -> bool:
        return any(n.ok for n in self.nodes)

    @property
    def summary(self) -> str:
        good = sum(1 for n in self.nodes if n.ok)
        return f"{good}/{len(self.nodes)} RU nodes reachable"


def parse_checkhost_results(data: dict[str, Any]) -> list[NodeResult]:
    """Разобрать payload /check-result/<id> в список NodeResult.

    TCP-результат check-host по каждой ноде — один из:
      [{"time": 0.12, "address": "1.2.3.4"}]  -> ok
      [{"error": "..."}]                        -> сбой
      null                                       -> ещё в ожидании (здесь как сбой)
    """
    results: list[NodeResult] = []
    for node, payload in data.items():
        if not payload or not isinstance(payload, list) or payload[0] is None:
            results.append(NodeResult(node=node, ok=False, time_ms=None, error="pending/no-data"))
            continue
        entry = payload[0]
        if "error" in entry:
            results.append(NodeResult(node=node, ok=False, time_ms=None, error=str(entry["error"])))
        else:
            t = entry.get("time")
            ms = round(t * 1000, 1) if t else None
            results.append(NodeResult(node=node, ok=True, time_ms=ms))
    return results


def check_ru_availability(
    ip: str,
    port: int = 443,
    nodes: list[str] | None = None,
    *,
    poll_timeout: float = 20.0,
    client: httpx.Client | None = None,
) -> AvailabilityReport:
    """Попросить check-host.net пробить IP:port с RU-нод (FR-7.1)."""
    node_list = nodes or list(DEFAULT_RU_NODES)
    owns_client = client is None
    client = client or httpx.Client(timeout=15.0, headers={"Accept": "application/json"})
    try:
        params = httpx.QueryParams(
            [("host", f"{ip}:{port}"), *(("node", n) for n in node_list)]
        )
        started = client.get(f"{CHECKHOST_BASE}/check-tcp", params=params)
        started.raise_for_status()
        request_id = started.json()["request_id"]

        deadline = time.monotonic() + poll_timeout
        data: dict[str, Any] = {}
        while time.monotonic() < deadline:
            time.sleep(2)
            res = client.get(f"{CHECKHOST_BASE}/check-result/{request_id}")
            res.raise_for_status()
            data = res.json()
            if all(v is not None for v in data.values()):
                break
        return AvailabilityReport(ip=ip, port=port, nodes=parse_checkhost_results(data))
    finally:
        if owns_client:
            client.close()


# --- FR-7.2: детекция «заморозки» / шейпинга --------------------------------
@dataclass
class FreezeResult:
    connected: bool
    bytes_transferred: int
    frozen: bool
    detail: str


def detect_freeze(
    host: str,
    port: int = 443,
    threshold_kb: int = 18,
    timeout: float = 10.0,
) -> FreezeResult:
    """Эвристика симптома «заморозки» ТСПУ (FR-7.2).

    Устанавливает TCP+TLS и пытается вытянуть > threshold_kb байт. Если соединение
    открывается, но передача встаёт ниже порога — это соответствует симптому
    «коннект есть, данные не идут», и мы помечаем это как frozen.

    ЗАМЕЧАНИЕ: это проба симптома против эндпоинта; окончательная проверка —
    реальная массовая закачка через установленный клиентский туннель.
    """
    threshold = threshold_kb * 1024
    try:
        raw = socket.create_connection((host, port), timeout=timeout)
    except OSError as exc:
        return FreezeResult(False, 0, False, f"tcp connect failed: {exc}")

    transferred = 0
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        with ctx.wrap_socket(raw, server_hostname=host) as tls:
            tls.sendall(
                f"GET / HTTP/1.1\r\nHost: {host}\r\nConnection: close\r\n\r\n".encode()
            )
            tls.settimeout(timeout)
            deadline = time.monotonic() + timeout
            while transferred < threshold and time.monotonic() < deadline:
                try:
                    chunk = tls.recv(4096)
                except TimeoutError:
                    break
                if not chunk:
                    break
                transferred += len(chunk)
    except (OSError, ssl.SSLError) as exc:
        frozen = transferred < threshold
        return FreezeResult(True, transferred, frozen, f"tls/transfer error: {exc}")

    frozen = transferred < threshold
    detail = "transfer stalled below threshold" if frozen else "transfer ok"
    return FreezeResult(True, transferred, frozen, detail)


# --- FR-7.3: локальный healthcheck ------------------------------------------
@dataclass
class HealthReport:
    checks: dict[str, bool] = field(default_factory=dict)
    details: dict[str, str] = field(default_factory=dict)

    @property
    def healthy(self) -> bool:
        return all(self.checks.values())

    def add(self, name: str, ok: bool, detail: str = "") -> None:
        self.checks[name] = ok
        if detail:
            self.details[name] = detail


def port_listening(host: str, port: int, timeout: float = 3.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def disk_free_ok(path: str = "/", min_free_gb: float = 1.0) -> tuple[bool, str]:
    usage = shutil.disk_usage(path)
    free_gb = usage.free / (1024**3)
    return free_gb >= min_free_gb, f"{free_gb:.1f} GB free"
