"""Интерфейс командной строки vpnctl (FR-6, FR-10).

Слои, которым нужен живой сервер (provision/deploy), вызывают Terraform/Ansible и
честно сообщают, если этих инструментов или целевого IP нет. Локальные операции
(генерация ключей/конфигов, проверки SNI, бэкапы, операции с юзерами через туннель
к Marzban) работают без каких-либо особых привилегий.
"""

from __future__ import annotations

import logging
import sys

import typer
from rich.console import Console
from rich.table import Table

from . import configure, monitoring, paths, qr, reality, sni, users
from . import settings as settings_mod
from .alerts import TelegramNotifier
from .marzban import MarzbanClient, MarzbanError

app = typer.Typer(add_completion=False, help="CLI оператора self-hosted VPN, устойчивого к DPI")
users_app = typer.Typer(help="Управление пользователями через API Marzban (FR-6)")
reality_app = typer.Typer(help="Ключевой материал Reality (FR-4)")
sni_app = typer.Typer(help="Валидация SNI для Reality (FR-4.3)")
monitor_app = typer.Typer(help="Проверки доступности / заморозки / здоровья (FR-7)")
app.add_typer(users_app, name="users")
app.add_typer(reality_app, name="reality")
app.add_typer(sni_app, name="sni")
app.add_typer(monitor_app, name="monitor")

console = Console()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def _settings() -> settings_mod.Settings:
    return settings_mod.load()


def _marzban(s: settings_mod.Settings) -> MarzbanClient:
    missing = s.missing(["marzban_admin_user", "marzban_admin_pass"])
    if missing:
        console.print(f"[red]Не заданы настройки:[/red] {', '.join(missing)}")
        raise typer.Exit(1)
    return MarzbanClient(s.marzban_base_url, s.marzban_admin_user, s.marzban_admin_pass)


# --- reality ----------------------------------------------------------------
@reality_app.command("keygen")
def reality_keygen() -> None:
    """Сгенерировать пару ключей x25519 + shortId для Reality (FR-4.1)."""
    keys = reality.generate_keys()
    console.print(f"REALITY_PRIVATE_KEY={keys.private_key}")
    console.print(f"REALITY_PUBLIC_KEY={keys.public_key}")
    console.print(f"REALITY_SHORT_ID={reality.generate_short_id()}")


# --- sni --------------------------------------------------------------------
@sni_app.command("list")
def sni_list() -> None:
    """Показать список дефолтных кандидатов SNI."""
    for d in sni.DEFAULT_CANDIDATES:
        console.print(d)


@sni_app.command("check")
def sni_check(
    domain: str = typer.Argument(None, help="Домен для проверки; без него — прогнать дефолты"),
) -> None:
    """Проверить кандидата SNI для Reality (TLS1.3 + HTTP/2 + репутация) (FR-4.3)."""
    candidates = [domain] if domain else list(sni.DEFAULT_CANDIDATES)
    table = Table("domain", "reachable", "TLS1.3", "HTTP/2", "verdict")
    for d in candidates:
        c = sni.check_candidate(d)
        verdict = "[green]OK[/green]" if c.ok else "[red]" + "; ".join(c.reasons()) + "[/red]"
        table.add_row(d, str(c.reachable), str(c.tls13), str(c.http2), verdict)
    console.print(table)


# --- users ------------------------------------------------------------------
@users_app.command("add")
def users_add(
    name: str,
    traffic: float = typer.Option(None, "--traffic", help="Лимит трафика в ГБ"),
    expire: str = typer.Option(None, "--expire", help="Дни, '<N>d' или ISO-дата"),
    show_qr: bool = typer.Option(True, "--qr/--no-qr", help="Печатать QR subscription"),
) -> None:
    """Создать пользователя, напечатать subscription-ссылку + QR (FR-6.1)."""
    s = _settings()
    try:
        with _marzban(s) as client:
            user = users.add_user(
                client,
                name,
                inbound_tag=configure.REALITY_INBOUND_TAG,
                traffic_gb=traffic,
                expire=expire,
            )
    except MarzbanError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from exc
    console.print(f"[green]создан[/green] {user.username}")
    console.print(f"subscription: {user.subscription_url}")
    if show_qr and user.subscription_url:
        console.print(qr.to_ascii(user.subscription_url))


@users_app.command("list")
def users_list() -> None:
    """Показать пользователей с трафиком, статусом и сроком (FR-6.2)."""
    s = _settings()
    with _marzban(s) as client:
        rows = client.list_users()
    table = Table("user", "status", "online", "traffic", "expires")
    for u in rows:
        table.add_row(
            u.username,
            u.status,
            "●" if u.is_online else "○",
            users.format_traffic(u),
            users.format_expire(u),
        )
    console.print(table)


@users_app.command("enable")
def users_enable(name: str) -> None:
    with _marzban(_settings()) as client:
        client.set_status(name, "active")
    console.print(f"[green]включён[/green] {name}")


@users_app.command("disable")
def users_disable(name: str) -> None:
    with _marzban(_settings()) as client:
        client.set_status(name, "disabled")
    console.print(f"[yellow]отключён[/yellow] {name}")


@users_app.command("delete")
def users_delete(name: str) -> None:
    with _marzban(_settings()) as client:
        client.delete_user(name)
    console.print(f"[red]удалён[/red] {name}")


@users_app.command("reset-traffic")
def users_reset_traffic(name: str) -> None:
    with _marzban(_settings()) as client:
        client.reset_traffic(name)
    console.print(f"[green]трафик сброшен[/green] {name}")


@users_app.command("export")
def users_export(path: str = typer.Argument("users-export.json")) -> None:
    """Экспортировать пользователей для миграции при ротации (FR-6.6)."""
    with _marzban(_settings()) as client:
        rows = client.list_users()
    users.export_users(rows, path)
    console.print(f"[green]экспортировано[/green] {len(rows)} юзеров -> {path}")


@users_app.command("import")
def users_import(path: str) -> None:
    """Пересоздать пользователей из экспорта на текущей панели (FR-6.6)."""
    rows = users.load_export(path)
    with _marzban(_settings()) as client:
        skipped = users.import_users(client, rows, inbound_tag=configure.REALITY_INBOUND_TAG)
    imported = len(rows) - len(skipped)
    console.print(f"[green]импортировано[/green] {imported}, пропущено {len(skipped)}")


# --- monitor ----------------------------------------------------------------
def _alert(s: settings_mod.Settings, text: str) -> None:
    TelegramNotifier(s.telegram_bot_token, s.telegram_chat_id).send(text)


@monitor_app.command("ru")
def monitor_ru(ip: str = typer.Argument(None, help="Целевой IP (по умолчанию текущий)")) -> None:
    """Проверить доступность IP:443 с RU-нод через check-host.net (FR-7.1)."""
    s = _settings()
    target = ip or paths.load_ip()
    if not target:
        console.print("[red]IP неизвестен; сначала provision или передай его[/red]")
        raise typer.Exit(1)
    nodes = [n for n in s.checkhost_ru_nodes.split(",") if n.strip()] or None
    report = monitoring.check_ru_availability(target, nodes=nodes)
    console.print(report.summary)
    for n in report.nodes:
        console.print(f"  {n.node}: {'ok ' + str(n.time_ms) + 'ms' if n.ok else n.error}")
    if not report.reachable_from_ru:
        _alert(s, f"⚠️ {target}:443 недоступен из РФ ({report.summary})")


@monitor_app.command("freeze")
def monitor_freeze(host: str = typer.Argument(None)) -> None:
    """Проба симптома «заморозки» ТСПУ (FR-7.2)."""
    s = _settings()
    target = host or paths.load_ip()
    if not target:
        console.print("[red]хост неизвестен[/red]")
        raise typer.Exit(1)
    res = monitoring.detect_freeze(target, threshold_kb=s.monitor_freeze_threshold_kb)
    console.print(f"connected={res.connected} bytes={res.bytes_transferred} frozen={res.frozen}")
    console.print(res.detail)
    if res.frozen:
        _alert(s, f"⚠️ возможна заморозка/шейпинг на {target}: {res.detail}")


@monitor_app.command("health")
def monitor_health() -> None:
    """Локальный healthcheck: порт 443 + диск (запускать на сервере) (FR-7.3)."""
    report = monitoring.HealthReport()
    report.add("port_443", monitoring.port_listening("127.0.0.1", 443))
    ok, detail = monitoring.disk_free_ok("/")
    report.add("disk", ok, detail)
    for name, passed in report.checks.items():
        console.print(f"  {name}: {'[green]ok[/green]' if passed else '[red]FAIL[/red]'}")
    raise typer.Exit(0 if report.healthy else 1)


# --- оркестрация инфраструктуры ---------------------------------------------
def configure_cmd() -> None:  # регистрируется ниже как `configure`
    """Сгенерировать валидированные конфиги Reality + AWG в .build (FR-4, FR-5)."""
    s = _settings()
    gen = configure.generate_reality_config(s, paths.BUILD_DIR)
    console.print(f"[green]xray_config.json[/green] -> {gen.config_path}")
    reality.validate_inbound(gen.inbound)
    console.print(f"  публичный ключ: {gen.inbound.public_key}")
    if gen.generated_private_key:
        console.print("[yellow]Сгенерирован приватный ключ Reality — сохрани его в .env:[/yellow]")
        console.print(f"  REALITY_PRIVATE_KEY={gen.generated_private_key}")
    endpoint = paths.load_ip() or "SERVER_IP"
    server = configure.generate_awg_config(s, endpoint, paths.BUILD_DIR)
    awg_path = paths.BUILD_DIR / "awg0.conf"
    console.print(f"[green]awg0.conf[/green] -> {awg_path} (порт {server.listen_port})")


app.command(name="configure")(configure_cmd)


def _need_tool(name: str) -> None:
    import shutil

    if shutil.which(name) is None:
        console.print(f"[red]{name} не найден в PATH[/red] — установи его (Д-2) и повтори")
        raise typer.Exit(1)


@app.command()
def provision() -> None:
    """Создать/привести VPS в нужное состояние через Terraform (FR-1)."""
    _need_tool("terraform")
    from . import provision as prov

    s = _settings()
    ip = prov.terraform_apply(s, paths.INFRA_ROOT)
    paths.save_ip(ip)
    console.print(f"[green]VPS готов[/green] ip={ip}")


@app.command()
def deploy() -> None:
    """Харденинг ОС + деплой Marzban + AWG через Ansible (FR-2,3,5)."""
    _need_tool("ansible-playbook")
    from . import deploy as dep

    s = _settings()
    ip = paths.load_ip()
    if not ip:
        console.print("[red]нет IP; сначала запусти `provision`[/red]")
        raise typer.Exit(1)
    inv = dep.write_inventory(ip, s, paths.ANSIBLE_ROOT)
    extra = dep.build_extra_vars(
        s,
        str(paths.BUILD_DIR / "xray_config.json"),
        str(paths.BUILD_DIR / "awg0.conf"),
    )
    dep.run_playbook(inv, paths.ANSIBLE_ROOT / "site.yml", extra)
    console.print("[green]деплой завершён[/green]")


@app.command()
def up() -> None:
    """provision + configure + deploy."""
    provision()
    configure_cmd()
    deploy()


@app.command()
def destroy() -> None:
    """Снести VPS и его ресурсы (FR-1.5)."""
    _need_tool("terraform")
    from . import provision as prov

    prov.terraform_destroy(_settings(), paths.INFRA_ROOT)
    console.print("[yellow]снесено[/yellow]")


@app.command()
def status() -> None:
    """Здоровье всех слоёв (NFR-5)."""
    s = _settings()
    ip = paths.load_ip()
    console.print(f"IP сервера: {ip or '[dim]неизвестен[/dim]'}")
    try:
        with _marzban(s) as client:
            stats = client.system_stats()
        console.print(f"[green]Marzban поднят[/green] users={stats.get('total_user', '?')}")
    except Exception as exc:  # noqa: BLE001
        console.print(f"[red]Marzban недоступен[/red] ({exc}) — открыт ли SSH-туннель?")


@app.command()
def backup() -> None:
    """Бэкап БД + конфигов + зашифрованных секретов (FR-8.1)."""
    from . import backup as bk

    s = _settings()
    archive = bk.create_backup(
        s.backup_dir,
        plain_items=[paths.BUILD_DIR / "xray_config.json", paths.BUILD_DIR / "awg0.conf"],
        secret_items=[paths.REPO_ROOT / ".env"],
        passphrase=s.backup_passphrase,
    )
    console.print(f"[green]бэкап[/green] -> {archive}")


@app.command()
def restore(archive: str) -> None:
    """Восстановить из архива бэкапа (FR-8.2)."""
    from . import backup as bk

    s = _settings()
    restored = bk.restore_backup(archive, paths.BUILD_DIR, passphrase=s.backup_passphrase)
    console.print(f"[green]восстановлено[/green] файлов: {len(restored)}")


@app.command(name="rotate-ip")
def rotate_ip() -> None:
    """Ротация на свежий IP, миграция юзеров, переключение subscription (FR-8.3).

    Требует SSH-туннель к ТЕКУЩЕЙ панели (для экспорта юзеров) и, после подъёма
    новой машины, туннель к НОВОЙ панели (для их импорта). Subscription-ссылки
    переживут переезд, только если задан MARZBAN_PANEL_DOMAIN и его DNS
    перенаправлен на новый IP — иначе клиентам придётся переимпортировать (см. RUNBOOK.md).
    """
    from . import provision as prov
    from . import rotate as rot

    s = _settings()
    old_ip = paths.load_ip()
    if not old_ip:
        console.print("[red]текущего IP нет; ротировать нечего[/red]")
        raise typer.Exit(1)
    export_path = paths.BUILD_DIR / "users-export.json"

    def export_current() -> list:
        with _marzban(s) as client:
            rows = client.list_users()
        users.export_users(rows, export_path)
        console.print(f"экспортировано {len(rows)} юзеров -> {export_path}")
        return rows

    def provision_new() -> str:
        _need_tool("terraform")
        ip = prov.terraform_apply(s, paths.INFRA_ROOT)  # единый стейт: пересоздаёт -> новый IP
        paths.save_ip(ip)
        return ip

    def deploy_and_configure(_ip: str) -> None:
        configure_cmd()
        deploy()

    def do_import(_ip: str, rows: list) -> None:
        console.print("[yellow]открой SSH-туннель к НОВОЙ панели, затем нажми Enter[/yellow]")
        typer.confirm("туннель открыт?", default=True)
        with _marzban(s) as client:
            users.import_users(client, rows, inbound_tag=configure.REALITY_INBOUND_TAG)

    def switch_subscription(_ip: str) -> bool:
        return bool(s.marzban_panel_domain)  # перенаправление DNS — шаг оператора

    plan = rot.rotate(
        provision_new=provision_new,
        export_current_users=export_current,
        deploy_and_configure=deploy_and_configure,
        import_users=do_import,
        switch_subscription=switch_subscription,
        destroy_old=lambda _ip: None,  # старая машина уже заменена Terraform
        old_ip=old_ip,
    )
    console.print(
        f"[green]ротация[/green] {plan.old_ip} -> {plan.new_ip}, юзеров: {plan.users_migrated}"
    )
    if not plan.subscription_switched:
        console.print(
            "[yellow]задай MARZBAN_PANEL_DOMAIN + перенаправь DNS, "
            "иначе клиентам придётся переимпортировать[/yellow]"
        )


@app.command()
def bootstrap() -> None:
    """Сквозной сценарий: API-ключ -> первый рабочий юзер (Ц-1, FR-10.2)."""
    console.print("[bold]bootstrap[/bold]: provision -> configure -> deploy -> первый юзер")
    up()
    console.print("Открой SSH-туннель, затем: [cyan]vpnctl users add first-user[/cyan]")


if __name__ == "__main__":
    sys.exit(app())
