"""Repo-relative paths and tiny operator-state persistence."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
INFRA_ROOT = REPO_ROOT / "infra"
ANSIBLE_ROOT = REPO_ROOT / "ansible"
BUILD_DIR = REPO_ROOT / ".build"  # generated configs (gitignored)
STATE_DIR = REPO_ROOT / ".state"  # current IP etc. (gitignored)


def save_ip(ip: str) -> None:
    STATE_DIR.mkdir(exist_ok=True)
    (STATE_DIR / "ip").write_text(ip.strip() + "\n", encoding="utf-8")


def load_ip() -> str | None:
    f = STATE_DIR / "ip"
    return f.read_text(encoding="utf-8").strip() if f.exists() else None
