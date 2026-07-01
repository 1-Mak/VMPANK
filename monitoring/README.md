# monitoring/ (FR-7)

The detection logic lives in `cli/vpnctl/monitoring.py`; these units just
schedule it.

| unit                     | where it runs        | what it does                              |
|--------------------------|----------------------|-------------------------------------------|
| `vpn-healthcheck.*`      | the VPS              | containers/port/disk (`monitor health`)   |
| `vpn-ru-check.*`         | operator/off-RU host | `monitor ru` + `monitor freeze`, alerts   |
| `vpn-backup.*`           | the VPS or operator  | daily `vpnctl backup`                     |

Install:

```bash
sudo cp systemd/*.service systemd/*.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now vpn-healthcheck.timer vpn-ru-check.timer vpn-backup.timer
```

**Why the RU check runs off-RU:** check-host.net dispatches the probe *from*
Russian nodes for you (FR-7.1), so the timer itself just needs reliable outbound
internet and the Telegram token — it does not need to be inside Russia.

Alerts go to Telegram when `TELEGRAM_BOT_TOKEN`/`TELEGRAM_CHAT_ID` are set
(FR-7.4); otherwise failures are logged and the timer exits non-zero (visible in
`journalctl -u <unit>`).
