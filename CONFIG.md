# Справочник по конфигурации

Все настройки берутся из переменных окружения, обычно через `.env` (скопировать из
`.env.example`, `chmod 600`). Загружается модулем `cli/vpnctl/settings.py`. Секретам
не место в git (FR-9).

## Провайдер (§10)

| Переменная | Обязательна | По умолчанию | Заметки |
|---|---|---|---|
| `VPS_PROVIDER` | да | `upcloud` | адаптер: `upcloud` \| `scaleway` |
| `VPS_API_TOKEN` | Scaleway | — | секретный ключ Scaleway |
| `VPS_API_USER` | да | — | логин UpCloud / access key Scaleway |
| `VPS_API_PASSWORD` | UpCloud | — | пароль UpCloud |
| `VPS_REGION` | да | — | напр. `fi-hel1`, `nl-ams-1` (предпочтительно FI/NL/DE/SE) |
| `VPS_PLAN` | да | — | напр. `1xCPU-2GB`, `DEV1-S` |
| `VPS_IMAGE` | нет | Ubuntu 24.04 | образ ОС |
| `SSH_PUBLIC_KEY_PATH` | да | `~/.ssh/id_ed25519.pub` | авторизуется на VPS |
| `SSH_PRIVATE_KEY_PATH` | да | `~/.ssh/id_ed25519` | используется Ansible |
| `SSH_PORT` | нет | `22` | порт подключения |
| `SSH_HARDENED_PORT` | нет | `22` | напр. `2222`, чтобы увести SSH с 22 (FR-2.2) |

## Marzban

| Переменная | Обязательна | По умолчанию | Заметки |
|---|---|---|---|
| `MARZBAN_ADMIN_USER` / `MARZBAN_ADMIN_PASS` | да | — | sudo-админ панели |
| `MARZBAN_PANEL_DOMAIN` | нет | — | задать для HTTPS + стабильного хоста subscription (ротация!) |
| `MARZBAN_PORT` | нет | `8000` | bind только на localhost (О-3) |
| `MARZBAN_VERSION` | нет | `v0.8.4` | запиненный тег образа |
| `XRAY_VERSION` | нет | `26.3.27` | запиненный Xray-core |

## VLESS / Reality (FR-4)

| Переменная | Обязательна | По умолчанию | Заметки |
|---|---|---|---|
| `REALITY_SNI` | да | — | маскировочный домен; проверить `vpnctl sni check` |
| `REALITY_SHORT_ID` | нет | генерируется | hex, 1–8 байт |
| `REALITY_PRIVATE_KEY` | нет | генерируется | сохрани значение, которое печатает `vpnctl configure` |
| `REALITY_PUBLIC_KEY` | нет | выводится | |
| `REALITY_FINGERPRINT` | нет | `chrome` | О-2 |

## AmneziaWG (FR-5)

| Переменная | Обязательна | По умолчанию | Заметки |
|---|---|---|---|
| `AWG_PORT` | нет | `51820` | UDP |
| `AWG_DEPLOY_MODE` | нет | `same-host` | `same-host` \| `separate-host` |
| `AWG_SEPARATE_HOST` | separate-host | — | IP/хост второго VPS |
| `AWG_SEPARATE_SSH_PORT` | нет | `22` | |

## Мониторинг / алерты (FR-7)

| Переменная | Обязательна | По умолчанию | Заметки |
|---|---|---|---|
| `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` | нет | — | алерты; при отсутствии — только лог |
| `CHECKHOST_ENABLED` | нет | `true` | доступность из РФ через check-host.net |
| `CHECKHOST_RU_NODES` | нет | авто | слаги нод через запятую |
| `MONITOR_FREEZE_THRESHOLD_KB` | нет | `18` | порог симптома заморозки (~15–20 КБ) |

## Бэкапы (FR-8)

| Переменная | Обязательна | По умолчанию | Заметки |
|---|---|---|---|
| `BACKUP_DIR` | нет | `./backups` | локальная папка архивов |
| `BACKUP_REMOTE` | нет | — | опциональный rclone-remote |
| `BACKUP_PASSPHRASE` | для бэкапа секретов | — | шифрует `.env`/ключи внутри архива |
