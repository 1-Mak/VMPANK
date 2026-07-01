import json

import pytest

from vpnctl import configure, reality
from vpnctl import settings as settings_mod


@pytest.fixture
def base_env(monkeypatch, tmp_path):
    pub = tmp_path / "id.pub"
    pub.write_text("ssh-ed25519 AAAA k", encoding="utf-8")
    monkeypatch.setenv("SSH_PUBLIC_KEY_PATH", str(pub))
    monkeypatch.setenv("REALITY_SNI", "www.samsung.com")


def test_resolve_reality_generates_key_when_missing(base_env):
    s = settings_mod.load(env_file=None)
    inbound, generated = configure.resolve_reality(s)
    assert generated is not None  # a private key was generated
    reality.validate_inbound(inbound)
    assert inbound.public_key == reality.public_from_private(inbound.private_key)


def test_resolve_reality_requires_sni(monkeypatch):
    monkeypatch.delenv("REALITY_SNI", raising=False)
    s = settings_mod.load(env_file=None)
    with pytest.raises(ValueError):
        configure.resolve_reality(s)


def test_generate_reality_config_writes_valid_json(base_env, tmp_path):
    s = settings_mod.load(env_file=None)
    gen = configure.generate_reality_config(s, tmp_path / "build")
    data = json.loads(gen.config_path.read_text(encoding="utf-8"))
    assert data["inbounds"][0]["port"] == 443
    assert data["inbounds"][0]["streamSettings"]["security"] == "reality"


def test_generate_awg_config_matches_params(base_env, tmp_path):
    s = settings_mod.load(env_file=None)
    server = configure.generate_awg_config(s, "203.0.113.9", tmp_path / "build")
    conf = (tmp_path / "build" / "awg0.conf").read_text(encoding="utf-8")
    assert f"ListenPort = {server.listen_port}" in conf
    assert "MASQUERADE" in conf
