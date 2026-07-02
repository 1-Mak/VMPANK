"""Валидация кандидатов SNI/dest для Reality (FR-4.3).

Хороший маскировочный домен для Reality должен (технически, проверяемо здесь):
  * быть доступен на :443,
  * согласовывать TLS 1.3,
  * анонсировать HTTP/2 (ALPN h2),
  * хоститься за рубежом.

Репутационные критерии («не заблокирован в РФ», «не заезжен») офлайн полностью не
проверить; популярные/заезженные домены помечаем по чёрному списку, а финальную
региональную проверку оставляем оператору + пробе check-host в monitoring.py.
"""

from __future__ import annotations

import socket
import ssl
from dataclasses import dataclass

# Разумные дефолты: крупные зарубежные сайты, сами терминирующие TLS 1.3 + HTTP/2.
# Считать отправной точкой — проверять по региону перед использованием (Д-3).
DEFAULT_CANDIDATES: tuple[str, ...] = (
    "www.samsung.com",
    "www.nvidia.com",
    "cdn.jsdelivr.net",
    "www.lovelive-anime.jp",
    "www.tesla.com",
    "dl.google.com",
    "www.asus.com",
)

# Домены, известные как заезженные SNI для Reality — выше риск фингерпринтинга.
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
    """Вернуть (tls_version, alpn_protocol). Бросает OSError/ssl.SSLError при сбое."""
    ctx = ssl.create_default_context()
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    ctx.set_alpn_protocols(["h2", "http/1.1"])
    with (
        socket.create_connection((domain, port), timeout=timeout) as sock,
        ctx.wrap_socket(sock, server_hostname=domain) as tls,
    ):
        return tls.version(), tls.selected_alpn_protocol()


def check_candidate(domain: str, timeout: float = 6.0) -> SniCheck:
    """Полная техническая + репутационная проверка одного домена."""
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
    """Вернуть первого кандидата, прошедшего все проверки, или None."""
    for domain in candidates or list(DEFAULT_CANDIDATES):
        check = check_candidate(domain, timeout=timeout)
        if check.ok:
            return check
    return None
