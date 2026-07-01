"""Terraform provisioning wrapper (FR-1).

Each provider is a self-contained Terraform module under infra/providers/<name>
exposing a uniform interface (vars: region, plan, image, ssh_public_key;
output: ipv4). This wrapper selects the module, writes a gitignored tfvars from
settings, and runs init/apply/destroy. Idempotency comes from Terraform state
(NFR-1); `destroy` enables IP rotation (FR-1.5, FR-8.3).
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from .settings import Settings

SUPPORTED_PROVIDERS = ("upcloud", "scaleway")


def provider_dir(provider: str, infra_root: Path) -> Path:
    if provider not in SUPPORTED_PROVIDERS:
        raise ValueError(
            f"unknown VPS_PROVIDER {provider!r}; supported: {', '.join(SUPPORTED_PROVIDERS)}"
        )
    return infra_root / "providers" / provider


def build_tfvars(settings: Settings) -> dict[str, str]:
    """Map operator settings to the module's uniform variable interface."""
    pubkey = Path(settings.ssh_public_key_path).expanduser().read_text(encoding="utf-8").strip()
    return {
        "region": settings.vps_region,
        "plan": settings.vps_plan,
        "image": settings.vps_image,
        "ssh_public_key": pubkey,
        "hostname": "vpn-selfhost",
    }


def write_tfvars(vars_: dict[str, str], path: Path) -> None:
    path.write_text(json.dumps(vars_, indent=2), encoding="utf-8")


def _run(cmd: list[str], cwd: Path) -> None:
    subprocess.run(cmd, cwd=cwd, check=True)


def terraform_apply(settings: Settings, infra_root: Path) -> str:
    """Init + apply the selected provider module; return the VPS IPv4."""
    wd = provider_dir(settings.vps_provider, infra_root)
    write_tfvars(build_tfvars(settings), wd / "terraform.tfvars.json")
    _pass_provider_credentials(settings)
    _run(["terraform", "init", "-input=false"], wd)
    _run(["terraform", "apply", "-auto-approve", "-input=false"], wd)
    out = subprocess.run(
        ["terraform", "output", "-json", "ipv4"],
        cwd=wd,
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(out.stdout)


def terraform_destroy(settings: Settings, infra_root: Path) -> None:
    wd = provider_dir(settings.vps_provider, infra_root)
    _pass_provider_credentials(settings)
    _run(["terraform", "destroy", "-auto-approve", "-input=false"], wd)


def _pass_provider_credentials(settings: Settings) -> None:
    """Export provider creds as env vars Terraform expects (never written to disk)."""
    import os

    if settings.vps_provider == "upcloud":
        os.environ.setdefault("UPCLOUD_USERNAME", settings.vps_api_user)
        os.environ.setdefault("UPCLOUD_PASSWORD", settings.vps_api_password)
    elif settings.vps_provider == "scaleway":
        os.environ.setdefault("SCW_ACCESS_KEY", settings.vps_api_user)
        os.environ.setdefault("SCW_SECRET_KEY", settings.vps_api_token)
