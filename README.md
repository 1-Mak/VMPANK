# vpn-selfhost

Самостоятельно размещаемый VPN, устойчивый к DPI/ТСПУ по ландшафту блокировок РФ
2026 года: **VLESS + Reality (XTLS-Vision)** как основной протокол и
**AmneziaWG** как резерв, под управлением [Marzban](https://github.com/Gozargah/Marzban)
и Python-CLI оператора (`vpnctl`). Провижининг — Terraform; конфигурация сервера —
Ansible; всё управляется из одного CLI / `Makefile`.

Реализовано по ТЗ `TZ-vpn-samohost-2026.md`. Дизайн — в [ARCHITECTURE.md](ARCHITECTURE.md),
эксплуатация — в [RUNBOOK.md](RUNBOOK.md).

> **Почему именно так:** главный риск — *репутация IP*, а не протокол. Поэтому
> дизайн опирается на провайдеров с «чистыми» IP в ЕС, мониторинг доступности из
> России и быструю ротацию IP — а не только на хорошую конфигурацию Reality. (ТЗ §3.3)

## Требования (машина оператора, Linux/macOS — Д-2)

- Python 3.11+
- Terraform ≥ 1.5, Ansible (+ `ansible-galaxy collection install -r ansible/requirements.yml`)
- Docker CLI (для локальных проверок), SSH-ключ
- Аккаунт у VPS-провайдера: **UpCloud** или **Scaleway** (см. [infra/README.md](infra/README.md))

## Быстрый старт

```bash
# 1. Установить CLI
make install                    # pip install -e ".[dev]"

# 2. Настроить
cp .env.example .env && chmod 600 .env
$EDITOR .env                    # креды провайдера, админ Marzban и т.д.

# 3. Выбрать маскировочный домен для Reality (проверяет TLS1.3 + HTTP/2 + репутацию)
vpnctl sni check                # прогнать дефолты, либо: vpnctl sni check www.samsung.com
#   -> победителя вписать в REALITY_SNI

# 4. Развернуть всё одной командой (Ц-1): provision -> configure -> deploy
make bootstrap

# 5. Открыть туннель к панели и создать первого пользователя
ssh -L 8000:127.0.0.1:8000 vpnadmin@<vps-ip>     # держать открытым
vpnctl users add alice --traffic 200 --expire 30d
#   -> выведет subscription-ссылку + QR; импортировать в v2rayTun / Hiddify
```

## Повседневные команды

| Команда | Что делает |
|---|---|
| `vpnctl users add/list/disable/delete/reset-traffic` | жизненный цикл пользователей (FR-6) |
| `vpnctl users export / import` | миграция пользователей при ротации (FR-6.6) |
| `vpnctl status` | здоровье всех слоёв (NFR-5) |
| `vpnctl monitor ru / freeze / health` | доступность из РФ, симптом заморозки, локальное здоровье (FR-7) |
| `vpnctl backup` / `vpnctl restore <archive>` | зашифрованные бэкапы (FR-8) |
| `vpnctl rotate-ip` | новый IP + миграция пользователей (FR-8.3) |
| `vpnctl destroy` | снести VPS (FR-1.5) |

`make help` покажет обёртки Makefile.

## Безопасные дефолты (harden-by-default, NFR-2)

- Панель слушает только `127.0.0.1` — **никогда** не торчит в интернет по HTTP; доступ через SSH-туннель (О-3).
- Вход под root и по паролю отключён; UFW открывает только SSH, `443/tcp`, UDP AWG (FR-2).
- fail2ban + unattended-upgrades включены.
- Секреты живут в `.env` (права 600) / переменных окружения, никогда в git (FR-9).

## Тесты и линт

```bash
make test      # pytest
make lint      # ruff + mypy
```

## Область и статус

В [STATUS.md](STATUS.md) — что именно реализовано и что требует живого VPS для
проверки. Этот репозиторий полностью реализует CLI оператора, генерацию конфигов,
логику мониторинга/бэкапов, Terraform-модули провайдеров и Ansible-деплой — всё
проверено юнит-тестами и локальными запусками. Сквозной путь (поднять реальный
VPS → развернуть → подключить клиента) требует твоих кредов провайдера и здесь
против живой инфраструктуры не прогонялся.
