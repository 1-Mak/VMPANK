import json

import pytest

from vpnctl import deploy, provision
from vpnctl import settings as settings_mod


@pytest.fixture
def settings(monkeypatch, tmp_path):
    pub = tmp_path / "id.pub"
    pub.write_text("ssh-ed25519 AAAA operator@host", encoding="utf-8")
    monkeypatch.setenv("SSH_PUBLIC_KEY_PATH", str(pub))
    monkeypatch.setenv("SSH_PRIVATE_KEY_PATH", str(tmp_path / "id"))
    monkeypatch.setenv("VPS_REGION", "fi-hel1")
    monkeypatch.setenv("VPS_PLAN", "1xCPU-2GB")
    monkeypatch.setenv("SSH_PORT", "22")
    return settings_mod.load(env_file=None)


def test_provider_dir_validates(tmp_path):
    with pytest.raises(ValueError):
        provision.provider_dir("hetzner", tmp_path)  # засвечен + не поддерживается
    assert provision.provider_dir("upcloud", tmp_path).name == "upcloud"


def test_build_and_write_tfvars(settings, tmp_path):
    vars_ = provision.build_tfvars(settings)
    assert vars_["region"] == "fi-hel1"
    assert vars_["ssh_public_key"].startswith("ssh-ed25519")
    out = tmp_path / "terraform.tfvars.json"
    provision.write_tfvars(vars_, out)
    assert json.loads(out.read_text())["plan"] == "1xCPU-2GB"


def test_build_inventory_format(settings):
    inv = deploy.build_inventory("203.0.113.5", settings)
    assert "203.0.113.5 ansible_user=root ansible_port=22" in inv


def test_extra_vars_carries_ports_and_key(settings, tmp_path):
    extra = deploy.build_extra_vars(settings, "/x/xray.json", "/x/awg.conf")
    assert extra["operator_ssh_key"].startswith("ssh-ed25519")
    assert extra["reality_config_path"] == "/x/xray.json"
    assert "marzban_port" in extra
