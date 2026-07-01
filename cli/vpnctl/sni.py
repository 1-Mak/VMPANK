"""Reality SNI/dest candidate validation (FR-4.3).

A good Reality masquerade domain must (technical, machine-checkable here):
  * be reachable on :443,
  * negotiate TLS 1.3,
  * advertise HTTP/2 (ALPN h2),
  * be hosted abroad.

Reputational criteria ("not blocked in RU", "not overused") cannot be fully
verified offline; we flag popular/overused domains from a denylist and leave a
final regional check to the operator + the check-host probe in monitoring.py.
"""

from __future__ import annotations

import socket
import ssl
from dataclasses import dataclass

# Sane defaults: large foreign sites that terminate TLS 1.3 + HTTP/2 themselves.
# Treat as a starting point — validate per-region before use (Д-3).
DEFAULT_CANDIDATES: tuple[str, ...] = (
    "www.samsung.com",
    "www.nvidia.com",
    "cdn.jsdelivr.net",
    "www.lovelive-anime.jp",
    "www.tesla.com",
    "dl.google.com",
    "www.asus.com",
)

# Domains that are famously overused as Reality SNIs — higher fingerprinting risk.
OVERUSED_DENYLIST: frozenset[str] = frozenset(
    {
        "www.microsoft.com",
        "www.apple.com",
        "www.cloudflare.com",
        "www.google.com",
        "yahoo.com",
        "www.amazon.com",
    }
)


@dataclass
class SniCheck:
    domain: str
    reachable: bool = False
    tls13: bool = False
    http2: bool = False
    overused: bool = False
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.reachable and self.tls13 and self.http2 and not self.overused

    def reasons(self) -> list[str]:
        r: list[str] = []
        if not self.reachable:
            r.append("unreachable on :443")
        if self.reachable and not self.tls13:
            r.append("no TLS 1.3")
        if self.reachable and not self.http2:
            r.append("no HTTP/2 (ALPN h2)")
        if self.overused:
            r.append("overused SNI (fingerprinting risk)")
        if self.error:
            r.append(self.error)
        return r


def _probe(domain: str, port: int = 443, timeout: float = 6.0) -> tuple[str | None, str | None]:
    """Return (tls_version, alpn_protocol). Raises OSError/ssl.SSLError on failure."""
    ctx = ssl.create_default_context()
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    ctx.set_alpn_protocols(["h2", "http/1.1"])
    with (
        socket.create_connection((domain, port), timeout=timeout) as sock,
        ctx.wrap_socket(sock, server_hostname=domain) as tls,
    ):
        return tls.version(), tls.selected_alpn_protocol()


def check_candidate(domain: str, timeout: float = 6.0) -> SniCheck:
    """Run the full technical + reputational check for one domain."""
    result = SniCheck(domain=domain, overused=domain.lower() in OVERUSED_DENYLIST)
    try:
        version, alpn = _probe(domain, timeout=timeout)
        result.reachable = True
        result.tls13 = version == "TLSv1.3"
        result.http2 = alpn == "h2"
    except (OSError, ssl.SSLError) as exc:
        result.error = f"{type(exc).__name__}: {exc}"
    return result


def pick_first_valid(candidates: list[str] | None = None, timeout: float = 6.0) -> SniCheck | None:
    """Return the first candidate that passes all checks, or None."""
    for domain in candidates or list(DEFAULT_CANDIDATES):
        check = check_candidate(domain, timeout=timeout)
        if check.ok:
            return check
    return None
