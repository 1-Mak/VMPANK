# Configuration reference

All settings come from environment variables, normally via `.env` (copy from
`.env.example`, `chmod 600`). Loaded by `cli/vpnctl/settings.py`. Secrets never
belong in git (FR-9).

## Provider (§10)

| Variable | Required | Default | Notes |
|---|---|---|---|
| `VPS_PROVIDER` | yes | `upcloud` | adapter: `upcloud` \| `scaleway` |
| `VPS_API_TOKEN` | Scaleway | — | Scaleway secret key |
| `VPS_API_USER` | yes | — | UpCloud username / Scaleway access key |
| `VPS_API_PASSWORD` | UpCloud | — | UpCloud password |
| `VPS_REGION` | yes | — | e.g. `fi-hel1`, `nl-ams-1` (FI/NL/DE/SE preferred) |
| `VPS_PLAN` | yes | — | e.g. `1xCPU-2GB`, `DEV1-S` |
| `VPS_IMAGE` | no | Ubuntu 24.04 | OS template |
| `SSH_PUBLIC_KEY_PATH` | yes | `~/.ssh/id_ed25519.pub` | authorized on the VPS |
| `SSH_PRIVATE_KEY_PATH` | yes | `~/.ssh/id_ed25519` | used by Ansible |
| `SSH_PORT` | no | `22` | connect port |
| `SSH_HARDENED_PORT` | no | `22` | set e.g. `2222` to move SSH off 22 (FR-2.2) |

## Marzban

| Variable | Required | Default | Notes |
|---|---|---|---|
| `MARZBAN_ADMIN_USER` / `MARZBAN_ADMIN_PASS` | yes | — | panel sudo admin |
| `MARZBAN_PANEL_DOMAIN` | no | — | set to enable HTTPS + stable subscription host (rotation!) |
| `MARZBAN_PORT` | no | `8000` | localhost bind only (О-3) |
| `MARZBAN_VERSION` | no | `v0.8.4` | pinned image tag |
| `XRAY_VERSION` | no | `25.6.8` | pinned Xray-core |

## VLESS / Reality (FR-4)

| Variable | Required | Default | Notes |
|---|---|---|---|
| `REALITY_SNI` | yes | — | masquerade domain; validate with `vpnctl sni check` |
| `REALITY_SHORT_ID` | no | generated | hex, 1–8 bytes |
| `REALITY_PRIVATE_KEY` | no | generated | persist the value `vpnctl configure` prints |
| `REALITY_PUBLIC_KEY` | no | derived | |
| `REALITY_FINGERPRINT` | no | `chrome` | О-2 |

## AmneziaWG (FR-5)

| Variable | Required | Default | Notes |
|---|---|---|---|
| `AWG_PORT` | no | `51820` | UDP |
| `AWG_DEPLOY_MODE` | no | `same-host` | `same-host` \| `separate-host` |
| `AWG_SEPARATE_HOST` | separate-host | — | 2nd VPS IP/host |
| `AWG_SEPARATE_SSH_PORT` | no | `22` | |

## Monitoring / alerts (FR-7)

| Variable | Required | Default | Notes |
|---|---|---|---|
| `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` | no | — | alerts; absent = log only |
| `CHECKHOST_ENABLED` | no | `true` | RU availability via check-host.net |
| `CHECKHOST_RU_NODES` | no | auto | comma-separated node slugs |
| `MONITOR_FREEZE_THRESHOLD_KB` | no | `18` | freeze-symptom threshold (~15–20 KB) |

## Backups (FR-8)

| Variable | Required | Default | Notes |
|---|---|---|---|
| `BACKUP_DIR` | no | `./backups` | local archive dir |
| `BACKUP_REMOTE` | no | — | optional rclone remote |
| `BACKUP_PASSPHRASE` | for secret backups | — | encrypts `.env`/keys inside the archive |
