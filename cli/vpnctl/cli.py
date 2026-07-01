"""vpnctl command-line interface (FR-6, FR-10).

Layers that need a live server (provision/deploy) shell out to Terraform/Ansible
and are honest when those tools or a target IP are missing. Local operations
(key/config generation, SNI checks, backups, Marzban-over-tunnel user ops) run
without any special privileges.
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

app = typer.Typer(add_completion=False, help="Self-hosted DPI-resistant VPN operator CLI")
users_app = typer.Typer(help="User management via the Marzban API (FR-6)")
reality_app = typer.Typer(help="Reality key material (FR-4)")
sni_app = typer.Typer(help="Reality SNI validation (FR-4.3)")
monitor_app = typer.Typer(help="Availability / freeze / health checks (FR-7)")
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
        console.print(f"[red]Missing settings:[/red] {', '.join(missing)}")
        raise typer.Exit(1)
    return MarzbanClient(s.marzban_base_url, s.marzban_admin_user, s.marzban_admin_pass)


# --- reality ----------------------------------------------------------------
@reality_app.command("keygen")
def reality_keygen() -> None:
    """Generate an x25519 keypair + shortId for Reality (FR-4.1)."""
    keys = reality.generate_keys()
    console.print(f"REALITY_PRIVATE_KEY={keys.private_key}")
    console.print(f"REALITY_PUBLIC_KEY={keys.public_key}")
    console.print(f"REALITY_SHORT_ID={reality.generate_short_id()}")


# --- sni --------------------------------------------------------------------
@sni_app.command("list")
def sni_list() -> None:
    """List the default SNI candidates."""
    for d in sni.DEFAULT_CANDIDATES:
        console.print(d)


@sni_app.command("check")
def sni_check(
    domain: str = typer.Argument(None, help="Domain to check; omit to scan defaults"),
) -> None:
    """Validate a Reality SNI candidate (TLS1.3 + HTTP/2 + reputation) (FR-4.3)."""
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
    traffic: float = typer.Option(None, "--traffic", help="Data limit in GB"),
    expire: str = typer.Option(None, "--expire", help="Days, '<N>d', or ISO date"),
    show_qr: bool = typer.Option(True, "--qr/--no-qr", help="Print subscription QR"),
) -> None:
    """Create a user, print subscription link + QR (FR-6.1)."""
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
    console.print(f"[green]created[/green] {user.username}")
    console.print(f"subscription: {user.subscription_url}")
    if show_qr and user.subscription_url:
        console.print(qr.to_ascii(user.subscription_url))


@users_app.command("list")
def users_list() -> None:
    """List users with traffic, status and expiry (FR-6.2)."""
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
    console.print(f"[green]enabled[/green] {name}")


@users_app.command("disable")
def users_disable(name: str) -> None:
    with _marzban(_settings()) as client:
        client.set_status(name, "disabled")
    console.print(f"[yellow]disabled[/yellow] {name}")


@users_app.command("delete")
def users_delete(name: str) -> None:
    with _marzban(_settings()) as client:
        client.delete_user(name)
    console.print(f"[red]deleted[/red] {name}")


@users_app.command("reset-traffic")
def users_reset_traffic(name: str) -> None:
    with _marzban(_settings()) as client:
        client.reset_traffic(name)
    console.print(f"[green]traffic reset[/green] {name}")


@users_app.command("export")
def users_export(path: str = typer.Argument("users-export.json")) -> None:
    """Export users for migration during rotation (FR-6.6)."""
    with _marzban(_settings()) as client:
        rows = client.list_users()
    users.export_users(rows, path)
    console.print(f"[green]exported[/green] {len(rows)} users -> {path}")


@users_app.command("import")
def users_import(path: str) -> None:
    """Recreate users from an export on the current panel (FR-6.6)."""
    rows = users.load_export(path)
    with _marzban(_settings()) as client:
        skipped = users.import_users(client, rows, inbound_tag=configure.REALITY_INBOUND_TAG)
    console.print(f"[green]imported[/green] {len(rows) - len(skipped)}, skipped {len(skipped)}")


# --- monitor ----------------------------------------------------------------
def _alert(s: settings_mod.Settings, text: str) -> None:
    TelegramNotifier(s.telegram_bot_token, s.telegram_chat_id).send(text)


@monitor_app.command("ru")
def monitor_ru(ip: str = typer.Argument(None, help="Target IP (defaults to current)")) -> None:
    """Check IP:443 availability from RU nodes via check-host.net (FR-7.1)."""
    s = _settings()
    target = ip or paths.load_ip()
    if not target:
        console.print("[red]no IP known; provision first or pass one[/red]")
        raise typer.Exit(1)
    nodes = [n for n in s.checkhost_ru_nodes.split(",") if n.strip()] or None
    report = monitoring.check_ru_availability(target, nodes=nodes)
    console.print(report.summary)
    for n in report.nodes:
        console.print(f"  {n.node}: {'ok ' + str(n.time_ms) + 'ms' if n.ok else n.error}")
    if not report.reachable_from_ru:
        _alert(s, f"⚠️ {target}:443 unreachable from RU ({report.summary})")


@monitor_app.command("freeze")
def monitor_freeze(host: str = typer.Argument(None)) -> None:
    """Probe the ТСПУ freeze symptom (FR-7.2)."""
    s = _settings()
    target = host or paths.load_ip()
    if not target:
        console.print("[red]no host known[/red]")
        raise typer.Exit(1)
    res = monitoring.detect_freeze(target, threshold_kb=s.monitor_freeze_threshold_kb)
    console.print(f"connected={res.connected} bytes={res.bytes_transferred} frozen={res.frozen}")
    console.print(res.detail)
    if res.frozen:
        _alert(s, f"⚠️ possible freeze/shaping on {target}: {res.detail}")


@monitor_app.command("health")
def monitor_health() -> None:
    """Local healthcheck: port 443 + disk (run on the server) (FR-7.3)."""
    report = monitoring.HealthReport()
    report.add("port_443", monitoring.port_listening("127.0.0.1", 443))
    ok, detail = monitoring.disk_free_ok("/")
    report.add("disk", ok, detail)
    for name, passed in report.checks.items():
        console.print(f"  {name}: {'[green]ok[/green]' if passed else '[red]FAIL[/red]'}")
    raise typer.Exit(0 if report.healthy else 1)


# --- infra orchestration ----------------------------------------------------
def configure_cmd() -> None:  # registered below as `configure`
    """Generate validated Reality + AWG configs into .build (FR-4, FR-5)."""
    s = _settings()
    gen = configure.generate_reality_config(s, paths.BUILD_DIR)
    console.print(f"[green]xray_config.json[/green] -> {gen.config_path}")
    reality.validate_inbound(gen.inbound)
    console.print(f"  public key: {gen.inbound.public_key}")
    if gen.generated_private_key:
        console.print("[yellow]Generated a Reality private key — persist it in .env:[/yellow]")
        console.print(f"  REALITY_PRIVATE_KEY={gen.generated_private_key}")
    endpoint = paths.load_ip() or "SERVER_IP"
    server = configure.generate_awg_config(s, endpoint, paths.BUILD_DIR)
    awg_path = paths.BUILD_DIR / "awg0.conf"
    console.print(f"[green]awg0.conf[/green] -> {awg_path} (port {server.listen_port})")


app.command(name="configure")(configure_cmd)


def _need_tool(name: str) -> None:
    import shutil

    if shutil.which(name) is None:
        console.print(f"[red]{name} not found on PATH[/red] — install it (Д-2) and retry")
        raise typer.Exit(1)


@app.command()
def provision() -> None:
    """Create/converge the VPS via Terraform (FR-1)."""
    _need_tool("terraform")
    from . import provision as prov

    s = _settings()
    ip = prov.terraform_apply(s, paths.INFRA_ROOT)
    paths.save_ip(ip)
    console.print(f"[green]VPS ready[/green] ip={ip}")


@app.command()
def deploy() -> None:
    """Harden OS + deploy Marzban + AWG via Ansible (FR-2,3,5)."""
    _need_tool("ansible-playbook")
    from . import deploy as dep

    s = _settings()
    ip = paths.load_ip()
    if not ip:
        console.print("[red]no IP; run `provision` first[/red]")
        raise typer.Exit(1)
    inv = dep.write_inventory(ip, s, paths.ANSIBLE_ROOT)
    extra = dep.build_extra_vars(
        s,
        str(paths.BUILD_DIR / "xray_config.json"),
        str(paths.BUILD_DIR / "awg0.conf"),
    )
    dep.run_playbook(inv, paths.ANSIBLE_ROOT / "site.yml", extra)
    console.print("[green]deploy complete[/green]")


@app.command()
def up() -> None:
    """provision + configure + deploy."""
    provision()
    configure_cmd()
    deploy()


@app.command()
def destroy() -> None:
    """Destroy the VPS and its resources (FR-1.5)."""
    _need_tool("terraform")
    from . import provision as prov

    prov.terraform_destroy(_settings(), paths.INFRA_ROOT)
    console.print("[yellow]destroyed[/yellow]")


@app.command()
def status() -> None:
    """Health across layers (NFR-5)."""
    s = _settings()
    ip = paths.load_ip()
    console.print(f"server IP: {ip or '[dim]unknown[/dim]'}")
    try:
        with _marzban(s) as client:
            stats = client.system_stats()
        console.print(f"[green]Marzban up[/green] users={stats.get('total_user', '?')}")
    except Exception as exc:  # noqa: BLE001
        console.print(f"[red]Marzban unreachable[/red] ({exc}) — is the SSH tunnel open?")


@app.command()
def backup() -> None:
    """Backup DB + configs + encrypted secrets (FR-8.1)."""
    from . import backup as bk

    s = _settings()
    archive = bk.create_backup(
        s.backup_dir,
        plain_items=[paths.BUILD_DIR / "xray_config.json", paths.BUILD_DIR / "awg0.conf"],
        secret_items=[paths.REPO_ROOT / ".env"],
        passphrase=s.backup_passphrase,
    )
    console.print(f"[green]backup[/green] -> {archive}")


@app.command()
def restore(archive: str) -> None:
    """Restore from a backup archive (FR-8.2)."""
    from . import backup as bk

    s = _settings()
    restored = bk.restore_backup(archive, paths.BUILD_DIR, passphrase=s.backup_passphrase)
    console.print(f"[green]restored[/green] {len(restored)} files")


@app.command(name="rotate-ip")
def rotate_ip() -> None:
    """Rotate to a fresh IP, migrate users, switch subscription (FR-8.3).

    Requires an SSH tunnel to the CURRENT panel (to export users) and, after the
    new box is up, a tunnel to the NEW panel (to import them). Subscription links
    survive the move only if MARZBAN_PANEL_DOMAIN is set and its DNS is repointed
    to the new IP — otherwise clients must reimport (see RUNBOOK.md).
    """
    from . import provision as prov
    from . import rotate as rot

    s = _settings()
    old_ip = paths.load_ip()
    if not old_ip:
        console.print("[red]no current IP; nothing to rotate[/red]")
        raise typer.Exit(1)
    export_path = paths.BUILD_DIR / "users-export.json"

    def export_current() -> list:
        with _marzban(s) as client:
            rows = client.list_users()
        users.export_users(rows, export_path)
        console.print(f"exported {len(rows)} users -> {export_path}")
        return rows

    def provision_new() -> str:
        _need_tool("terraform")
        ip = prov.terraform_apply(s, paths.INFRA_ROOT)  # single-state: recreates -> new IP
        paths.save_ip(ip)
        return ip

    def deploy_and_configure(_ip: str) -> None:
        configure_cmd()
        deploy()

    def do_import(_ip: str, rows: list) -> None:
        console.print("[yellow]open an SSH tunnel to the NEW panel, then press Enter[/yellow]")
        typer.confirm("tunnel open?", default=True)
        with _marzban(s) as client:
            users.import_users(client, rows, inbound_tag=configure.REALITY_INBOUND_TAG)

    def switch_subscription(_ip: str) -> bool:
        return bool(s.marzban_panel_domain)  # DNS repoint is the operator's step

    plan = rot.rotate(
        provision_new=provision_new,
        export_current_users=export_current,
        deploy_and_configure=deploy_and_configure,
        import_users=do_import,
        switch_subscription=switch_subscription,
        destroy_old=lambda _ip: None,  # old box already replaced by Terraform
        old_ip=old_ip,
    )
    console.print(
        f"[green]rotated[/green] {plan.old_ip} -> {plan.new_ip}, {plan.users_migrated} users"
    )
    if not plan.subscription_switched:
        console.print(
            "[yellow]set MARZBAN_PANEL_DOMAIN + repoint DNS to avoid client reimport[/yellow]"
        )


@app.command()
def bootstrap() -> None:
    """End-to-end: API key -> first working user (Ц-1, FR-10.2)."""
    console.print("[bold]bootstrap[/bold]: provision -> configure -> deploy -> first user")
    up()
    console.print("Open the SSH tunnel, then: [cyan]vpnctl users add first-user[/cyan]")


if __name__ == "__main__":
    sys.exit(app())
