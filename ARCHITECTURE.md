# Architecture

## Layers

```
Operator machine (vpnctl / Makefile)
   │  terraform            │  ansible over SSH        │  Marzban REST (via SSH tunnel)
   ▼                       ▼                          ▼
┌──────────────────────────── VPS (Ubuntu 22.04/24.04) ────────────────────────────┐
│ L1 OS+security  : vpnadmin user, key-only SSH, UFW(SSH,443/tcp,AWG/udp),          │
│                   fail2ban, unattended-upgrades                                    │
│ L2 Marzban      : Docker Compose; Xray inbound VLESS+Reality :443 vision;          │
│                   panel + REST bound to 127.0.0.1 only                             │
│ L3 AmneziaWG    : awg0 on a UDP port, obfuscated (Jc/Jmin/Jmax/S1/S2/H1..H4)       │
│ L4 Ops          : systemd timers (healthcheck, RU-check, backup)                   │
└────────────────────────────────────────────────────────────────────────────────────┘
```

## Key decisions

**Terraform for provisioning, Ansible for config.** Terraform's state gives
idempotency (NFR-1) and a clean `destroy`/recreate for IP rotation (FR-1.5,
FR-8.3). Ansible is agentless and idempotent for hardening + Docker + Marzban +
AWG. `vpnctl` is the single entrypoint that drives both and talks to the Marzban
API directly.

**Provider adapters (NFR-6).** Each provider is a self-contained Terraform module
under `infra/providers/<name>` with an identical variable/output interface, so
`vpnctl` can drive any of them and new ones drop in without touching the core.
Bundled: **UpCloud** (Finland) and **Scaleway** (NL/FR) — deliberately *not* the
"засвеченные" big clouds (Hetzner/DO/OVH/Vultr/AWS/GCP) whose ranges hit RU
block-lists fast (ТЗ §3.3, FR-1.2).

**Reality is generated, not templated by hand (FR-4).** `reality.py` produces the
x25519 keypair + shortId and asserts the ТЗ invariants on every build:
port `443`, `flow=xtls-rprx-vision`, `fingerprint=chrome` (О-2), and **no** PQ-TLS
or new Vision "seed" defaults in the inbound (О-4). The SNI is validated
(`sni.py`: reachable + TLS 1.3 + HTTP/2, overused-domain denylist) before use.

**AmneziaWG params are generated once and shared.** Server and every client embed
the same Jc/Jmin/Jmax/S1/S2/H1..H4 (`awg.py`), because a mismatch breaks the
handshake. The server config includes NAT masquerade so traffic actually routes.

**Panel is never on the public internet (О-3 / NFR-2).** Marzban binds
`127.0.0.1`; the operator reaches it over an SSH tunnel. UFW never opens the panel
port. An optional domain + TLS mode exists for teams that want a stable
subscription host (also what makes IP rotation transparent to clients).

## Backup / rotation model

- **Backup (FR-8.1):** tar.gz of the Marzban DB + `xray_config.json` + AWG config +
  user export. Secret files (`.env`, keys) are encrypted with a passphrase-derived
  Fernet key *before* entering the archive — the archive never holds plaintext
  secrets.
- **Rotation (FR-8.3):** export users → provision fresh VPS → deploy+configure →
  import users → switch subscription → drop the old box. **Subscription
  continuity** (no client reinstall) needs a stable subscription host: set
  `MARZBAN_PANEL_DOMAIN` and repoint its DNS to the new IP. Without a domain,
  subscription links are IP-bound and clients must reimport.

## AWG placement (FR-5.3)

`AWG_DEPLOY_MODE=same-host` runs the backup on the Reality box (one IP; simplest).
`separate-host` puts it on a second VPS/IP so a ban of the Reality IP leaves the
backup reachable — recommended when availability matters (ТЗ §4 key decision).

## Threat model → mitigations (ТЗ §3.3, §14)

| Threat | Mitigation in this system |
|---|---|
| IP banned in RU | RU availability monitor (FR-7.1) + fast `rotate-ip` (FR-8.3) + 2nd provider (FR-1.2) |
| TLS "freeze" >15–20 KB | freeze-symptom probe (FR-7.2) → alert → rotate; WS+CDN is a COULD |
| Reality burned in a region | rotate keys/SNI (`vpnctl configure`) + fail over to AWG |
| Panel compromise | localhost-only panel, secrets out of git, fail2ban |
| Server loss | encrypted backups + one-command restore |
