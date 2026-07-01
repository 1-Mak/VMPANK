# vpn-selfhost

Self-hosted, DPI/ТСПУ-resistant VPN for the 2026 RU blocking landscape:
**VLESS + Reality (XTLS-Vision)** as the primary protocol and **AmneziaWG** as
the backup, managed by [Marzban](https://github.com/Gozargah/Marzban) and a
Python operator CLI (`vpnctl`). Provisioning is Terraform; server config is
Ansible; everything is driven from one CLI / `Makefile`.

Built to the ТЗ in `TZ-vpn-samohost-2026.md`. See [ARCHITECTURE.md](ARCHITECTURE.md)
for the design and [RUNBOOK.md](RUNBOOK.md) for operations.

> **Why this shape:** the main risk is *IP reputation*, not the protocol. So the
> design leans on clean-IP EU providers, availability monitoring from Russia, and
> fast IP rotation — not just a good Reality config. (ТЗ §3.3)

## Requirements (operator machine, Linux/macOS — Д-2)

- Python 3.11+
- Terraform ≥ 1.5, Ansible (+ `ansible-galaxy collection install -r ansible/requirements.yml`)
- Docker CLI (for local checks), an SSH keypair
- A VPS provider account: **UpCloud** or **Scaleway** (see [infra/README.md](infra/README.md))

## Quick start

```bash
# 1. Install the CLI
make install                    # pip install -e ".[dev]"

# 2. Configure
cp .env.example .env && chmod 600 .env
$EDITOR .env                    # provider creds, Marzban admin, etc.

# 3. Pick a Reality masquerade domain (validates TLS1.3 + HTTP/2 + reputation)
vpnctl sni check                # scan defaults, or: vpnctl sni check www.samsung.com
#   -> put the winner in REALITY_SNI

# 4. Bootstrap end-to-end (Ц-1): provision -> configure -> deploy
make bootstrap

# 5. Open the panel tunnel and add your first user
ssh -L 8000:127.0.0.1:8000 vpnadmin@<vps-ip>     # keep this open
vpnctl users add alice --traffic 200 --expire 30d
#   -> prints a subscription link + QR; import into v2rayTun / Hiddify
```

## Everyday commands

| Command | What |
|---|---|
| `vpnctl users add/list/disable/delete/reset-traffic` | user lifecycle (FR-6) |
| `vpnctl users export / import` | migrate users during rotation (FR-6.6) |
| `vpnctl status` | health across layers (NFR-5) |
| `vpnctl monitor ru / freeze / health` | RU availability, freeze symptom, local health (FR-7) |
| `vpnctl backup` / `vpnctl restore <archive>` | encrypted backups (FR-8) |
| `vpnctl rotate-ip` | fresh IP + user migration (FR-8.3) |
| `vpnctl destroy` | tear down the VPS (FR-1.5) |

`make help` lists the Makefile wrappers.

## Security defaults (harden-by-default, NFR-2)

- Panel binds `127.0.0.1` only — **never** exposed over HTTP; reach it via SSH tunnel (О-3).
- Root login + password auth disabled; UFW opens only SSH, `443/tcp`, AWG UDP (FR-2).
- fail2ban + unattended-upgrades on.
- Secrets live in `.env` (mode 600) / environment, never in git (FR-9).

## Tests & lint

```bash
make test      # pytest
make lint      # ruff + mypy
```

## Scope & status

See [STATUS.md](STATUS.md) for exactly what is implemented vs. what requires a
live VPS to exercise. This repository fully implements the operator CLI, config
generation, monitoring/backup logic, Terraform provider modules, and the Ansible
deploy — validated by unit tests and local runs. The end-to-end path (provision a
real VPS → deploy → connect a client) requires your provider credentials and has
not been run against live infrastructure here.
