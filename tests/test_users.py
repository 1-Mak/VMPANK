from datetime import UTC, datetime

import pytest

from vpnctl import users
from vpnctl.marzban import GB, MarzbanUser


def _user(**kw):
    base = dict(
        username="alice",
        status="active",
        data_limit=None,
        used_traffic=0,
        expire=None,
        subscription_url="https://x/sub/alice",
        online_at=None,
    )
    base.update(kw)
    return MarzbanUser(**base)


def test_parse_expire_days_and_suffix():
    now = datetime(2026, 1, 1, tzinfo=UTC)
    ts = users.parse_expire("30", now=now)
    assert ts == int(datetime(2026, 1, 31, tzinfo=UTC).timestamp())
    assert users.parse_expire("30d", now=now) == ts


def test_parse_expire_iso_and_none():
    assert users.parse_expire(None) is None
    ts = users.parse_expire("2026-12-31")
    assert datetime.fromtimestamp(ts, tz=UTC).year == 2026


def test_parse_expire_invalid():
    with pytest.raises(ValueError):
        users.parse_expire("not-a-date")


def test_format_traffic_unlimited_and_limited():
    assert "∞" in users.format_traffic(_user())
    u = _user(data_limit=10 * GB, used_traffic=2 * GB)
    assert users.format_traffic(u) == "2.00 GB / 10.00 GB"


def test_export_import_roundtrip(tmp_path):
    path = tmp_path / "export.json"
    users.export_users([_user(), _user(username="bob")], path)
    loaded = users.load_export(path)
    assert [u.username for u in loaded] == ["alice", "bob"]
