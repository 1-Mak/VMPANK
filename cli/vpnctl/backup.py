"""Бэкап / восстановление с шифрованием секретов (FR-8.1, FR-8.2).

Бэкап — это .tar.gz с меткой времени. Несекретные артефакты (БД Marzban, конфиг
xray, конфиги AWG, экспорт пользователей) кладутся как есть; секретные файлы
(.env, ключи) шифруются Fernet-ключом, выведенным из парольной фразы, до
добавления — так сам архив никогда не содержит секретов в открытом виде (FR-8.1, NFR-2).
"""

from __future__ import annotations

import base64
import os
import tarfile
from datetime import UTC, datetime
from pathlib import Path

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

_SALT_LEN = 16
_MAGIC = b"VPNSELFHOST1"  # заголовок шифрованных блобов: MAGIC || salt || token


def _derive_key(passphrase: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=390_000)
    return base64.urlsafe_b64encode(kdf.derive(passphrase.encode("utf-8")))


def encrypt_bytes(data: bytes, passphrase: str) -> bytes:
    salt = os.urandom(_SALT_LEN)
    token = Fernet(_derive_key(passphrase, salt)).encrypt(data)
    return _MAGIC + salt + token


def decrypt_bytes(blob: bytes, passphrase: str) -> bytes:
    if not blob.startswith(_MAGIC):
        raise ValueError("not a vpn-selfhost encrypted blob")
    body = blob[len(_MAGIC) :]
    salt, token = body[:_SALT_LEN], body[_SALT_LEN:]
    return Fernet(_derive_key(passphrase, salt)).decrypt(token)


def create_backup(
    out_dir: str | Path,
    *,
    plain_items: list[Path],
    secret_items: list[Path],
    passphrase: str,
    now: datetime | None = None,
) -> Path:
    """Создать tar.gz-бэкап с шифрованием секретов и вернуть его путь."""
    if secret_items and not passphrase:
        raise ValueError("BACKUP_PASSPHRASE required to back up secret files")
    stamp = (now or datetime.now(UTC)).strftime("%Y%m%dT%H%M%SZ")
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    archive = out_dir / f"vpn-backup-{stamp}.tar.gz"

    with tarfile.open(archive, "w:gz") as tar:
        for item in plain_items:
            p = Path(item)
            if p.exists():
                tar.add(p, arcname=f"plain/{p.name}")
        for item in secret_items:
            p = Path(item)
            if not p.exists():
                continue
            enc = encrypt_bytes(p.read_bytes(), passphrase)
            tmp = out_dir / f".{p.name}.enc"
            tmp.write_bytes(enc)
            try:
                tar.add(tmp, arcname=f"secrets/{p.name}.enc")
            finally:
                tmp.unlink(missing_ok=True)
    return archive


def restore_backup(
    archive: str | Path,
    dest: str | Path,
    *,
    passphrase: str = "",
) -> list[Path]:
    """Распаковать бэкап, расшифровав секреты. Возвращает пути восстановленных файлов."""
    archive = Path(archive)
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    restored: list[Path] = []
    with tarfile.open(archive, "r:gz") as tar:
        for member in tar.getmembers():
            if not member.isfile():
                continue
            name = Path(member.name).name
            data = tar.extractfile(member)
            if data is None:
                continue
            raw = data.read()
            if member.name.startswith("secrets/"):
                if not passphrase:
                    raise ValueError("passphrase required to restore encrypted secrets")
                raw = decrypt_bytes(raw, passphrase)
                name = name.removesuffix(".enc")
            target = dest / name
            target.write_bytes(raw)
            if member.name.startswith("secrets/"):
                target.chmod(0o600)  # FR-9.3
            restored.append(target)
    return restored
