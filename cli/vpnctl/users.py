"""Хелперы управления пользователями поверх клиента Marzban (FR-6).

Чистые хелперы (парсинг expire, форматирование трафика, экспорт/импорт) отделены
от I/O, чтобы их можно было юнит-тестировать без живой панели.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from pathlib import Path

from .marzban import GB, MarzbanClient, MarzbanUser


def parse_expire(value: str | None, *, now: datetime | None = None) -> int | None:
    """Разобрать значение --expire в unix-таймстамп.

    Принимает: число дней ("30"), форму "<N>d" ("30d") или ISO-дату
    ("2026-12-31"). Пусто/None -> без срока.
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
    """Человекочитаемая строка 'использовано / лимит'."""
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
    """Создать пользователя VLESS+Reality и вернуть его (с subscription_url)."""
    return client.create_user(
        name,
        inbound_tag=inbound_tag,
        data_limit_gb=traffic_gb,
        expire_ts=parse_expire(expire),
    )


def export_users(users: list[MarzbanUser], path: str | Path) -> None:
    """Выгрузить пользователей в JSON для миграции при ротации IP (FR-6.6)."""
    Path(path).write_text(
        json.dumps([asdict(u) for u in users], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def load_export(path: str | Path) -> list[MarzbanUser]:
    """Прочитать экспорт, созданный export_users()."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return [MarzbanUser(**item) for item in data]


def import_users(
    client: MarzbanClient,
    users: list[MarzbanUser],
    *,
    inbound_tag: str,
) -> list[str]:
    """Пересоздать пользователей на свежей панели (идемпотентно: пропуск существующих).

    Возвращает список пропущенных имён.
    """
    skipped: list[str] = []
    for u in users:
        try:
            client.get_user(u.username)
            skipped.append(u.username)
            continue
        except Exception:  # noqa: BLE001 - любая ошибка поиска означает «нет, создаём»
            pass
        client.create_user(
            u.username,
            inbound_tag=inbound_tag,
            data_limit_gb=(u.data_limit / GB) if u.data_limit else None,
            expire_ts=u.expire,
        )
    return skipped
