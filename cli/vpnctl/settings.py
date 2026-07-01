"""Operator settings loaded from environment / .env (FR-9, §10).

Secrets live only in the environment or the .env file (mode 600), never in the
repo. This module is the single place that reads them.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


def _get(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def _get_int(name: str, default: int) -> int:
    raw = _get(name)
    return int(raw) if raw else default


def _get_bool(name: str, default: bool = False) -> bool:
    raw = _get(name).lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "on"}


@dataclass
class Settings:
    # provider
    vps_provider: str
    vps_api_token: str
    vps_api_user: str
    vps_api_password: str
    vps_region: str
    vps_plan: str
    vps_image: str
    ssh_public_key_path: str
    ssh_private_key_path: str
    ssh_port: int
    ssh_hardened_port: int
    # marzban
    marzban_admin_user: str
    marzban_admin_pass: str
    marzban_panel_domain: str
    marzban_port: int
    marzban_version: str
    xray_version: str
    # reality
    reality_sni: str
    reality_short_id: str
    reality_private_key: str
    reality_public_key: str
    reality_fingerprint: str
    # awg
    awg_port: int
    awg_deploy_mode: str
    awg_separate_host: str
    awg_separate_ssh_port: int
    # monitoring
    telegram_bot_token: str
    telegram_chat_id: str
    checkhost_enabled: bool
    checkhost_ru_nodes: str
    monitor_freeze_threshold_kb: int
    # backups
    backup_dir: str
    backup_remote: str
    backup_passphrase: str

    @property
    def marzban_base_url(self) -> str:
        """Local base URL for the Marzban API (reached via SSH tunnel, О-3)."""
        return f"http://127.0.0.1:{self.marzban_port}"

    def missing(self, keys: list[str]) -> list[str]:
        """Return the subset of attribute names whose value is falsy."""
        return [k for k in keys if not getattr(self, k)]


def load(env_file: str | os.PathLike[str] | None = ".env") -> Settings:
    """Load settings from the given .env file (if present) and the environment."""
    if env_file and Path(env_file).exists():
        load_dotenv(env_file, override=False)
    return Settings(
        vps_provider=_get("VPS_PROVIDER", "upcloud"),
        vps_api_token=_get("VPS_API_TOKEN"),
        vps_api_user=_get("VPS_API_USER"),
        vps_api_password=_get("VPS_API_PASSWORD"),
        vps_region=_get("VPS_REGION"),
        vps_plan=_get("VPS_PLAN"),
        vps_image=_get("VPS_IMAGE", "Ubuntu Server 24.04 LTS"),
        ssh_public_key_path=_get("SSH_PUBLIC_KEY_PATH", "~/.ssh/id_ed25519.pub"),
        ssh_private_key_path=_get("SSH_PRIVATE_KEY_PATH", "~/.ssh/id_ed25519"),
        ssh_port=_get_int("SSH_PORT", 22),
        ssh_hardened_port=_get_int("SSH_HARDENED_PORT", 22),
        marzban_admin_user=_get("MARZBAN_ADMIN_USER"),
        marzban_admin_pass=_get("MARZBAN_ADMIN_PASS"),
        marzban_panel_domain=_get("MARZBAN_PANEL_DOMAIN"),
        marzban_port=_get_int("MARZBAN_PORT", 8000),
        marzban_version=_get("MARZBAN_VERSION", "v0.8.4"),
        xray_version=_get("XRAY_VERSION", "25.6.8"),
        reality_sni=_get("REALITY_SNI"),
        reality_short_id=_get("REALITY_SHORT_ID"),
        reality_private_key=_get("REALITY_PRIVATE_KEY"),
        reality_public_key=_get("REALITY_PUBLIC_KEY"),
        reality_fingerprint=_get("REALITY_FINGERPRINT", "chrome"),
        awg_port=_get_int("AWG_PORT", 51820),
        awg_deploy_mode=_get("AWG_DEPLOY_MODE", "same-host"),
        awg_separate_host=_get("AWG_SEPARATE_HOST"),
        awg_separate_ssh_port=_get_int("AWG_SEPARATE_SSH_PORT", 22),
        telegram_bot_token=_get("TELEGRAM_BOT_TOKEN"),
        telegram_chat_id=_get("TELEGRAM_CHAT_ID"),
        checkhost_enabled=_get_bool("CHECKHOST_ENABLED", True),
        checkhost_ru_nodes=_get("CHECKHOST_RU_NODES"),
        monitor_freeze_threshold_kb=_get_int("MONITOR_FREEZE_THRESHOLD_KB", 18),
        backup_dir=_get("BACKUP_DIR", "./backups"),
        backup_remote=_get("BACKUP_REMOTE"),
        backup_passphrase=_get("BACKUP_PASSPHRASE"),
    )
