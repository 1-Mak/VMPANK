"""AmneziaWG (obfuscated WireGuard) key/peer/config generation (FR-5).

Server and every peer MUST share identical obfuscation parameters (Jc/Jmin/Jmax/
S1/S2/H1..H4), otherwise the handshake fails. Generate them once per deployment
and reuse for all peers.
"""

from __future__ import annotations

import base64
import secrets
from dataclasses import dataclass, field

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey


@dataclass(frozen=True)
class WgKeys:
    private_key: str  # standard WireGuard base64 (44 chars)
    public_key: str


def generate_keys() -> WgKeys:
    """Generate a WireGuard/AmneziaWG Curve25519 keypair."""
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
    return WgKeys(
        private_key=base64.b64encode(priv_raw).decode("ascii"),
        public_key=base64.b64encode(pub_raw).decode("ascii"),
    )


@dataclass(frozen=True)
class Obfuscation:
    """AmneziaWG junk/header parameters. Must match on both ends."""

    jc: int
    jmin: int
    jmax: int
    s1: int
    s2: int
    h1: int
    h2: int
    h3: int
    h4: int

    def validate(self) -> None:
        if not 1 <= self.jc <= 128:
            raise ValueError("Jc must be 1..128")
        if not self.jmin < self.jmax:
            raise ValueError("Jmin must be < Jmax")
        if self.s1 + 56 == self.s2:
            raise ValueError("S1+56 must not equal S2 (detectable)")
        headers = {self.h1, self.h2, self.h3, self.h4}
        if len(headers) != 4:
            raise ValueError("H1..H4 must be distinct")
        if any(h <= 4 for h in headers):
            raise ValueError("H1..H4 must be > 4")


def generate_obfuscation() -> Obfuscation:
    """Randomize obfuscation params within safe, mutually-consistent ranges."""
    s1 = secrets.randbelow(100) + 15  # 15..114
    while True:
        s2 = secrets.randbelow(100) + 15
        if s1 + 56 != s2:
            break
    headers: set[int] = set()
    while len(headers) < 4:
        headers.add(secrets.randbelow(0x7FFFFFF0) + 5)
    h1, h2, h3, h4 = sorted(headers)
    obf = Obfuscation(
        jc=secrets.randbelow(6) + 4,  # 4..9
        jmin=40,
        jmax=70,
        s1=s1,
        s2=s2,
        h1=h1,
        h2=h2,
        h3=h3,
        h4=h4,
    )
    obf.validate()
    return obf


@dataclass
class Peer:
    name: str
    private_key: str
    public_key: str
    address: str  # e.g. 10.8.0.2/32


@dataclass
class ServerConfig:
    private_key: str
    public_key: str
    address: str  # e.g. 10.8.0.1/24
    listen_port: int
    endpoint_host: str
    obf: Obfuscation
    dns: str = "1.1.1.1"
    wan_iface: str = "eth0"
    peers: list[Peer] = field(default_factory=list)

    def _obf_lines(self) -> str:
        o = self.obf
        return (
            f"Jc = {o.jc}\nJmin = {o.jmin}\nJmax = {o.jmax}\n"
            f"S1 = {o.s1}\nS2 = {o.s2}\n"
            f"H1 = {o.h1}\nH2 = {o.h2}\nH3 = {o.h3}\nH4 = {o.h4}"
        )

    def render_server(self) -> str:
        """Render the server-side awg0.conf."""
        wan = self.wan_iface
        post_up = (
            f"iptables -A FORWARD -i %i -j ACCEPT; "
            f"iptables -t nat -A POSTROUTING -o {wan} -j MASQUERADE"
        )
        post_down = (
            f"iptables -D FORWARD -i %i -j ACCEPT; "
            f"iptables -t nat -D POSTROUTING -o {wan} -j MASQUERADE"
        )
        lines = [
            "[Interface]",
            f"Address = {self.address}",
            f"ListenPort = {self.listen_port}",
            f"PrivateKey = {self.private_key}",
            f"PostUp = {post_up}",
            f"PostDown = {post_down}",
            self._obf_lines(),
        ]
        for p in self.peers:
            lines += [
                "",
                f"# {p.name}",
                "[Peer]",
                f"PublicKey = {p.public_key}",
                f"AllowedIPs = {p.address}",
            ]
        return "\n".join(lines) + "\n"

    def render_client(self, peer: Peer) -> str:
        """Render a client config for `peer` (Amnezia/AWG compatible, FR-5.4)."""
        host = self.endpoint_host
        lines = [
            "[Interface]",
            f"PrivateKey = {peer.private_key}",
            f"Address = {peer.address}",
            f"DNS = {self.dns}",
            self._obf_lines(),
            "",
            "[Peer]",
            f"PublicKey = {self.public_key}",
            f"Endpoint = {host}:{self.listen_port}",
            "AllowedIPs = 0.0.0.0/0, ::/0",
            "PersistentKeepalive = 25",
        ]
        return "\n".join(lines) + "\n"


def add_peer(server: ServerConfig, name: str, index: int) -> Peer:
    """Create and attach a peer; index maps to 10.x.x.(index+1)."""
    keys = generate_keys()
    base = server.address.split("/")[0].rsplit(".", 1)[0]
    peer = Peer(
        name=name,
        private_key=keys.private_key,
        public_key=keys.public_key,
        address=f"{base}.{index + 1}/32",
    )
    server.peers.append(peer)
    return peer
