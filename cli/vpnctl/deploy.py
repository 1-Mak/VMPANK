"""Ansible deploy wrapper (FR-2, FR-3, FR-5).

Generates an inventory from the provisioned IP + operator settings and runs the
hardening/deploy playbook. Extra vars carry ports, versions and the generated
Reality/AWG material so playbooks stay declarative.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from .settings import Settings


def build_inventory(ip: str, settings: Settings) -> str:
    """Render an Ansible INI inventory for the target host."""
    key = Path(settings.ssh_private_key_path).expanduser()
    return (
        "[vpn]\n"
        f"{ip} ansible_user=root ansible_port={settings.ssh_port} "
        f"ansible_ssh_private_key_file={key}\n"
    )


def write_inventory(ip: str, settings: Settings, ansible_root: Path) -> Path:
    inv = ansible_root / "inventory" / "hosts.generated"
    inv.parent.mkdir(parents=True, exist_ok=True)
    inv.write_text(build_inventory(ip, settings), encoding="utf-8")
    return inv


def build_extra_vars(settings: Settings, reality_config_path: str, awg_config_path: str) -> dict:
    """Non-secret deploy knobs handed to the playbook via --extra-vars."""
    pubkey = Path(settings.ssh_public_key_path).expanduser().read_text(encoding="utf-8").strip()
    return {
        "operator_ssh_key": pubkey,
        "ssh_hardened_port": settings.ssh_hardened_port,
        "awg_port": settings.awg_port,
        "awg_deploy_mode": settings.awg_deploy_mode,
        "marzban_port": settings.marzban_port,
        "marzban_version": settings.marzban_version,
        "xray_version": settings.xray_version,
        "marzban_panel_domain": settings.marzban_panel_domain,
        "reality_config_path": reality_config_path,
        "awg_config_path": awg_config_path,
    }


def run_playbook(
    inventory: Path,
    playbook: Path,
    extra_vars: dict,
    *,
    vault_env: dict[str, str] | None = None,
) -> None:
    cmd = [
        "ansible-playbook",
        "-i",
        str(inventory),
        str(playbook),
        "--extra-vars",
        json.dumps(extra_vars),
    ]
    subprocess.run(cmd, check=True, env=vault_env)
