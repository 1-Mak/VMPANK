# monitoring/ (FR-7)

Логика детекции живёт в `cli/vpnctl/monitoring.py`; эти юниты только её планируют.

| юнит                     | где запускается      | что делает                                |
|--------------------------|----------------------|-------------------------------------------|
| `vpn-healthcheck.*`      | на VPS               | контейнеры/порт/диск (`monitor health`)   |
| `vpn-ru-check.*`         | оператор/хост вне РФ | `monitor ru` + `monitor freeze`, алерты   |
| `vpn-backup.*`           | VPS или оператор     | ежедневный `vpnctl backup`                |

Установка:

```bash
sudo cp systemd/*.service systemd/*.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now vpn-healthcheck.timer vpn-ru-check.timer vpn-backup.timer
```

**Почему RU-check запускается вне РФ:** check-host.net сам отправляет пробу *с*
российских нод за тебя (FR-7.1), поэтому самому таймеру нужен лишь надёжный
исходящий интернет и токен Telegram — быть внутри России не требуется.

Алерты уходят в Telegram, когда заданы `TELEGRAM_BOT_TOKEN`/`TELEGRAM_CHAT_ID`
(FR-7.4); иначе сбои логируются, а таймер завершается ненулевым кодом (видно в
`journalctl -u <unit>`).
