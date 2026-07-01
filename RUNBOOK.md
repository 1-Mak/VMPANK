# Runbook

Operational procedures and incident playbooks (NFR-7).

## Access the panel

```bash
ssh -L 8000:127.0.0.1:8000 vpnadmin@<vps-ip>   # keep open in a terminal
# browser -> http://127.0.0.1:8000 ; or vpnctl talks to it directly
```
The panel is bound to localhost on the server and is **not** reachable from the
internet by design (О-3). If `curl http://<vps-ip>:8000` connects, that's a
misconfiguration — stop and investigate.

## Add / manage users

```bash
vpnctl users add bob --traffic 100 --expire 2026-12-31   # link + QR
vpnctl users list
vpnctl users disable bob        # enable / delete / reset-traffic likewise
```

---

## Incident: IP unreachable from Russia

**Symptom:** `vpnctl monitor ru` reports 0/N RU nodes reachable, or clients in RU
stop connecting while the server is otherwise healthy.

1. Confirm the server itself is up: `vpnctl status`, `vpnctl monitor health`.
2. Confirm it's an RU-side block, not an outage: reach `443` from a non-RU host.
3. If RU-blocked → **rotate the IP:**
   ```bash
   vpnctl users export .build/users-export.json   # via the current tunnel
   vpnctl rotate-ip
   ```
   Open a tunnel to the new panel when prompted so users import. If
   `MARZBAN_PANEL_DOMAIN` is set and its DNS is repointed to the new IP, clients
   auto-pull the new server; otherwise resend subscription links.
4. If rotation on the same provider keeps getting banned, switch `VPS_PROVIDER`
   (UpCloud ⇄ Scaleway) in `.env` and rotate again.

## Incident: TLS "freeze" (connect OK, data stalls at ~15–20 KB)

**Symptom:** `vpnctl monitor freeze` shows `connected=True frozen=True`; clients
handshake but pages hang.

1. This is the ТСПУ shaping symptom — the IP/route is suspect. Treat as an IP-ban
   event: rotate the IP (above).
2. If it recurs quickly on fresh IPs, enable the WS+CDN masquerade mode (COULD, see
   ARCHITECTURE) or move the primary to `separate-host` AWG while investigating.

## Incident: service down

**Symptom:** `vpnctl status` → "Marzban unreachable" (tunnel is open).

1. On the server: `cd /opt/marzban && docker compose ps` and `... logs --tail=100`.
2. `docker compose up -d` to bring it back; the container has `restart: always`,
   so a reboot alone shouldn't drop it — check disk (`vpnctl monitor health`).
3. Xray config broken after a change? Validate before restart:
   `docker compose exec marzban xray -test -c /var/lib/marzban/xray_config.json`.

## Incident: Reality burned in a region

**Symptom:** Reality connections fail region-wide though the IP is reachable and
the service is up.

1. Rotate Reality material and SNI without rebuilding the server:
   ```bash
   vpnctl sni check                     # pick a fresh masquerade domain
   $EDITOR .env                         # update REALITY_SNI; clear REALITY_* keys to regen
   vpnctl configure && vpnctl deploy    # pushes new xray_config.json
   ```
2. Meanwhile, hand affected users the AmneziaWG backup config.

## Client can't connect

1. Subscription link current? Re-issue: `vpnctl users list` then resend.
2. User over quota / expired? `vpnctl users reset-traffic <name>` or re-add with a
   new `--expire`.
3. Time skew on the client breaks Reality — check the device clock.
4. Try the AWG backup profile to isolate Reality-specific issues.

## Backups & restore

```bash
vpnctl backup                          # encrypted archive in BACKUP_DIR
vpnctl restore backups/vpn-backup-<ts>.tar.gz
```
Test restores periodically (NFR-3): restore into a scratch dir and diff the
recovered `xray_config.json` / user export against production.

## Routine

- Timers (see `monitoring/`) run healthcheck (5 min), RU-check (10 min), backup
  (daily). Alerts go to Telegram when configured.
- Keep Xray/Marzban versions current but pinned — bump `XRAY_VERSION` /
  `MARZBAN_VERSION` in `.env`, then `vpnctl deploy`. Do **not** enable PQ-TLS /
  new Vision seed defaults (О-4).
