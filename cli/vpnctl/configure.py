"""Turn settings into on-disk protocol configs (FR-4, FR-5).

Generates a validated xray_config.json (Reality) and an AmneziaWG server config
into the build dir. Key material is generated when absent so `configure` is
runnable end-to-end; generated secrets are surfaced to the operator to persist
in .env.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from . import awg, reality
from .settings import Settings

REALITY_INBOUND_TAG = "vless-reality-in"


@dataclass
class GeneratedReality:
    inbound: reality.RealityInbound
    config_path: Path
    generated_private_key: str | None  # set if we had to generate one


def resolve_reality(settings: Settings) -> tuple[reality.RealityInbound, str | None]:
    """Build a validated Reality inbound, generating key/shortId if missing."""
    if not settings.reality_sni:
        raise ValueError("REALITY_SNI is required (run `vpnctl sni check` to pick one)")

    generated_priv: str | None = None
    priv = settings.reality_private_key
    if not priv:
        keys = reality.generate_keys()
        priv, pub = keys.private_key, keys.public_key
        generated_priv = priv
    else:
        pub = settings.reality_public_key or reality.public_from_private(priv)

    short_id = settings.reality_short_id or reality.generate_short_id()
    inbound = reality.RealityInbound(
        sni=settings.reality_sni,
        private_key=priv,
        public_key=pub,
        short_ids=[short_id],
        fingerprint=settings.reality_fingerprint or "chrome",
        tag=REALITY_INBOUND_TAG,
    )
    reality.validate_inbound(inbound)
    return inbound, generated_priv


def generate_reality_config(settings: Settings, build_dir: Path) -> GeneratedReality:
    inbound, generated_priv = resolve_reality(settings)
    config = reality.build_xray_config(inbound)
    build_dir.mkdir(parents=True, exist_ok=True)
    path = build_dir / "xray_config.json"
    path.write_text(reality.dumps(config), encoding="utf-8")
    return GeneratedReality(inbound=inbound, config_path=path, generated_private_key=generated_priv)


def generate_awg_config(
    settings: Settings, endpoint_host: str, build_dir: Path
) -> awg.ServerConfig:
    keys = awg.generate_keys()
    server = awg.ServerConfig(
        private_key=keys.private_key,
        public_key=keys.public_key,
        address="10.8.0.1/24",
        listen_port=settings.awg_port,
        endpoint_host=endpoint_host,
        obf=awg.generate_obfuscation(),
    )
    build_dir.mkdir(parents=True, exist_ok=True)
    (build_dir / "awg0.conf").write_text(server.render_server(), encoding="utf-8")
    return server
