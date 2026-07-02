import base64

import pytest

from vpnctl import awg


def test_keygen_is_standard_wg_base64():
    keys = awg.generate_keys()
    for k in (keys.private_key, keys.public_key):
        raw = base64.b64decode(k)
        assert len(raw) == 32
        assert len(k) == 44  # 32 байта -> base64 из 44 символов с паддингом


def test_obfuscation_generation_is_valid():
    for _ in range(20):
        obf = awg.generate_obfuscation()
        obf.validate()  # не должно бросить исключение
        assert obf.jmin < obf.jmax
        assert obf.s1 + 56 != obf.s2
        assert len({obf.h1, obf.h2, obf.h3, obf.h4}) == 4


def test_obfuscation_validate_catches_bad_headers():
    with pytest.raises(ValueError):
        awg.Obfuscation(jc=4, jmin=1, jmax=2, s1=20, s2=30, h1=5, h2=5, h3=6, h4=7).validate()


def test_render_server_and_client_share_obfuscation():
    server = awg.ServerConfig(
        private_key=awg.generate_keys().private_key,
        public_key=awg.generate_keys().public_key,
        address="10.8.0.1/24",
        listen_port=51820,
        endpoint_host="203.0.113.10",
        obf=awg.generate_obfuscation(),
    )
    peer = awg.add_peer(server, "alice", index=1)
    assert peer.address == "10.8.0.2/32"

    server_conf = server.render_server()
    client_conf = server.render_client(peer)
    for line in (f"Jc = {server.obf.jc}", f"H1 = {server.obf.h1}"):
        assert line in server_conf
        assert line in client_conf
    assert "MASQUERADE" in server_conf  # NAT, чтобы трафик реально маршрутизировался
    assert f"Endpoint = 203.0.113.10:{server.listen_port}" in client_conf
    assert "AllowedIPs = 0.0.0.0/0, ::/0" in client_conf
