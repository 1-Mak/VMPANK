import json

import pytest

from vpnctl import reality


def test_keygen_roundtrip():
    keys = reality.generate_keys()
    assert reality.public_from_private(keys.private_key) == keys.public_key


def test_short_id_length():
    assert len(reality.generate_short_id(8)) == 16
    with pytest.raises(ValueError):
        reality.generate_short_id(9)


def test_inbound_enforces_o2_invariants():
    keys = reality.generate_keys()
    inbound = reality.RealityInbound(
        sni="www.example.com",
        private_key=keys.private_key,
        public_key=keys.public_key,
        short_ids=["ab12"],
    )
    obj = inbound.to_xray_inbound()
    assert obj["port"] == 443
    assert obj["protocol"] == "vless"
    rs = obj["streamSettings"]["realitySettings"]
    assert obj["streamSettings"]["security"] == "reality"
    assert rs["serverNames"] == ["www.example.com"]
    assert rs["fingerprint"] == "chrome"
    reality.validate_inbound(inbound)  # must not raise


def test_validate_rejects_wrong_flow_and_port():
    keys = reality.generate_keys()
    base = dict(sni="x.com", private_key=keys.private_key, public_key=keys.public_key)
    with pytest.raises(ValueError):
        reality.validate_inbound(reality.RealityInbound(flow="none", **base))
    with pytest.raises(ValueError):
        reality.validate_inbound(reality.RealityInbound(port=8443, **base))


def test_validate_rejects_mismatched_public_key():
    a = reality.generate_keys()
    b = reality.generate_keys()
    with pytest.raises(ValueError):
        reality.validate_inbound(
            reality.RealityInbound(sni="x.com", private_key=a.private_key, public_key=b.public_key)
        )


def test_build_xray_config_is_json_serialisable():
    keys = reality.generate_keys()
    inbound = reality.RealityInbound(
        sni="x.com", private_key=keys.private_key, public_key=keys.public_key
    )
    cfg = reality.build_xray_config(inbound)
    parsed = json.loads(reality.dumps(cfg))
    assert parsed["inbounds"][0]["port"] == 443
    # О-4: no PQ-TLS / seed defaults leaked into realitySettings
    rs = parsed["inbounds"][0]["streamSettings"]["realitySettings"]
    assert "mldsa65Seed" not in rs and "pqv" not in rs
