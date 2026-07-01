"""User-management helpers on top of the Marzban client (FR-6).

Pure helpers (expire parsing, traffic formatting, export/import) are kept
separate from I/O so they can be unit-tested without a live panel.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from pathlib import Path

from .marzban import GB, MarzbanClient, MarzbanUser


def parse_expire(value: str | None, *, now: datetime | None = None) -> int | None:
    """Parse an --expire value into a unix timestamp.

    Accepts: an integer number of days ("30"), a "<N>d" form ("30d"), or an
    ISO date ("2026-12-31"). Empty/None -> no expiry.
    """
    if not value:
        return None
    now = now or datetime.now(UTC)
    v = value.strip().lower()
    if v.endswith("d"):
        v = v[:-1]
    if v.isdigit():
        return int((now + timedelta(days=int(v))).timestamp())
    try:
        dt = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"invalid --expire {value!r}: use days, '<N>d', or ISO date") from exc
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return int(dt.timestamp())


def format_traffic(user: MarzbanUser) -> str:
    """Human-readable 'used / limit' string."""
    used = user.used_traffic / GB
    if not user.data_limit:
        return f"{used:.2f} GB / ∞"
    limit = user.data_limit / GB
    return f"{used:.2f} GB / {limit:.2f} GB"


def format_expire(user: MarzbanUser) -> str:
    if not user.expire:
        return "never"
    return datetime.fromtimestamp(user.expire, tz=UTC).strftime("%Y-%m-%d")


def add_user(
    client: MarzbanClient,
    name: str,
    *,
    inbound_tag: str,
    traffic_gb: float | None = None,
    expire: str | None = None,
) -> MarzbanUser:
    """Create a VLESS+Reality user and return it (with subscription_url)."""
    return client.create_user(
        name,
        inbound_tag=inbound_tag,
        data_limit_gb=traffic_gb,
        expire_ts=parse_expire(expire),
    )


def export_users(users: list[MarzbanUser], path: str | Path) -> None:
    """Dump users to JSON for migration during IP rotation (FR-6.6)."""
    Path(path).write_text(
        json.dumps([asdict(u) for u in users], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def load_export(path: str | Path) -> list[MarzbanUser]:
    """Read an export produced by export_users()."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return [MarzbanUser(**item) for item in data]


def import_users(
    client: MarzbanClient,
    users: list[MarzbanUser],
    *,
    inbound_tag: str,
) -> list[str]:
    """Recreate users on a fresh panel (idempotent: skips existing). Returns skipped."""
    skipped: list[str] = []
    for u in users:
        try:
            client.get_user(u.username)
            skipped.append(u.username)
            continue
        except Exception:  # noqa: BLE001 - any lookup failure means "not present, create"
            pass
        client.create_user(
            u.username,
            inbound_tag=inbound_tag,
            data_limit_gb=(u.data_limit / GB) if u.data_limit else None,
            expire_ts=u.expire,
        )
    return skipped
