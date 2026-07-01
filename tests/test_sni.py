from vpnctl import sni


def test_overused_domain_is_flagged(monkeypatch):
    monkeypatch.setattr(sni, "_probe", lambda d, timeout=6.0: ("TLSv1.3", "h2"))
    result = sni.check_candidate("www.microsoft.com")
    assert result.overused
    assert not result.ok
    assert "overused SNI (fingerprinting risk)" in result.reasons()


def test_good_domain_passes(monkeypatch):
    monkeypatch.setattr(sni, "_probe", lambda d, timeout=6.0: ("TLSv1.3", "h2"))
    result = sni.check_candidate("www.samsung.com")
    assert result.ok
    assert result.reasons() == []


def test_no_tls13_or_http2_fails(monkeypatch):
    monkeypatch.setattr(sni, "_probe", lambda d, timeout=6.0: ("TLSv1.2", "http/1.1"))
    result = sni.check_candidate("some.host")
    assert not result.ok
    assert "no TLS 1.3" in result.reasons()
    assert "no HTTP/2 (ALPN h2)" in result.reasons()


def test_unreachable_records_error(monkeypatch):
    def boom(domain, timeout=6.0):
        raise OSError("connection refused")

    monkeypatch.setattr(sni, "_probe", boom)
    result = sni.check_candidate("dead.host")
    assert not result.reachable
    assert not result.ok


def test_pick_first_valid(monkeypatch):
    def probe(domain, timeout=6.0):
        return ("TLSv1.3", "h2") if domain == "cdn.jsdelivr.net" else ("TLSv1.2", None)

    monkeypatch.setattr(sni, "_probe", probe)
    pick = sni.pick_first_valid(["bad.one", "cdn.jsdelivr.net"])
    assert pick is not None and pick.domain == "cdn.jsdelivr.net"
