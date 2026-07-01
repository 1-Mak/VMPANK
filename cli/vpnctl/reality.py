"""VLESS + Reality key material and Xray inbound/config generation (FR-4).

Enforces the ТЗ constraints:
  О-2 : port 443/tcp, flow = xtls-rprx-vision, fingerprint chrome
  О-4 : do NOT enable post-quantum TLS / new Vision "seed" defaults in the inbound
"""

from __future__ import annotations

import base64
import json
import secrets
from dataclasses import dataclass, field
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey

# ТЗ-mandated invariants — asserted by validate_inbound() and the test suite.
REALITY_PORT = 443
REALITY_FLOW = "xtls-rprx-vision"
DEFAULT_FINGERPRINT = "chrome"


def _b64url_nopad(raw: bytes) -> str:
    """Base64url without padding — the encoding `xray x25519` emits."""
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


@dataclass(frozen=True)
class RealityKeys:
    """An x25519 keypair in the same encoding as `xray x25519` (FR-4.1)."""

    private_key: str
    public_key: str


def generate_keys() -> RealityKeys:
    """Generate an x25519 keypair for Reality (equivalent to `xray x25519`)."""
    priv = X25519PrivateKey.generate()
    priv_raw = priv.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )
    pub_raw = priv.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return RealityKeys(private_key=_b64url_nopad(priv_raw), public_key=_b64url_nopad(pub_raw))


def public_from_private(private_key: str) -> str:
    """Derive the Reality public key from a base64url private key."""
    padded = private_key + "=" * (-len(private_key) % 4)
    raw = base64.urlsafe_b64decode(padded)
    if len(raw) != 32:
        raise ValueError("Reality private key must decode to 32 bytes")
    priv = X25519PrivateKey.from_private_bytes(raw)
    pub_raw = priv.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return _b64url_nopad(pub_raw)


def generate_short_id(length_bytes: int = 8) -> str:
    """Random hex shortId (FR-4.1). Reality allows 1..8 bytes (2..16 hex chars)."""
    if not 1 <= length_bytes <= 8:
        raise ValueError("shortId length must be 1..8 bytes")
    return secrets.token_hex(length_bytes)


@dataclass
class RealityInbound:
    """Parameters for a single VLESS+Reality inbound."""

    sni: str
    private_key: str
    public_key: str
    short_ids: list[str] = field(default_factory=list)
    port: int = REALITY_PORT
    flow: str = REALITY_FLOW
    fingerprint: str = DEFAULT_FINGERPRINT
    dest: str | None = None  # defaults to sni:443
    tag: str = "vless-reality-in"

    def dest_addr(self) -> str:
        return self.dest or f"{self.sni}:443"

    def to_xray_inbound(self) -> dict[str, Any]:
        """Render the Xray inbound object (О-2/О-4 compliant)."""
        return {
            "tag": self.tag,
            "listen": "0.0.0.0",
            "port": self.port,
            "protocol": "vless",
            "settings": {
                "clients": [],  # populated by Marzban per-user
                "decryption": "none",
            },
            "streamSettings": {
                "network": "tcp",
                "security": "reality",
                "realitySettings": {
                    "show": False,
                    "dest": self.dest_addr(),
                    "xver": 0,
                    "serverNames": [self.sni],
                    "privateKey": self.private_key,
                    "shortIds": self.short_ids or [""],
                    "fingerprint": self.fingerprint,
                    # О-4: PQ-TLS and new Vision "seed" defaults intentionally OFF.
                },
            },
            "sniffing": {"enabled": True, "destOverride": ["http", "tls", "quic"]},
        }


def build_xray_config(inbound: RealityInbound, log_level: str = "warning") -> dict[str, Any]:
    """Assemble a full, minimal xray_config.json around the Reality inbound."""
    return {
        "log": {"loglevel": log_level},
        "inbounds": [inbound.to_xray_inbound()],
        "outbounds": [
            {"tag": "direct", "protocol": "freedom"},
            {"tag": "block", "protocol": "blackhole"},
        ],
        "routing": {
            "rules": [
                # Drop BitTorrent to reduce abuse/attention on a shared server (Д-4).
                {"type": "field", "protocol": ["bittorrent"], "outboundTag": "block"},
            ]
        },
    }


def validate_inbound(inbound: RealityInbound) -> None:
    """Assert ТЗ hard constraints (О-2). Raises ValueError on violation."""
    if inbound.port != REALITY_PORT:
        raise ValueError(f"О-2 violation: Reality port must be {REALITY_PORT}, got {inbound.port}")
    if inbound.flow != REALITY_FLOW:
        raise ValueError(f"О-2 violation: flow must be {REALITY_FLOW!r}, got {inbound.flow!r}")
    if not inbound.sni:
        raise ValueError("Reality requires an SNI/dest domain")
    if public_from_private(inbound.private_key) != inbound.public_key:
        raise ValueError("Reality public key does not match the private key")


def dumps(config: dict[str, Any]) -> str:
    return json.dumps(config, indent=2, ensure_ascii=False)
