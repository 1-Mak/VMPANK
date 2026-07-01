import tarfile

import pytest
from cryptography.fernet import InvalidToken

from vpnctl import backup


def test_encrypt_decrypt_roundtrip():
    blob = backup.encrypt_bytes(b"super secret token", "passphrase")
    assert b"super secret token" not in blob  # ciphertext, not plaintext
    assert backup.decrypt_bytes(blob, "passphrase") == b"super secret token"


def test_decrypt_wrong_passphrase_fails():
    blob = backup.encrypt_bytes(b"x", "right")
    with pytest.raises(InvalidToken):
        backup.decrypt_bytes(blob, "wrong")


def test_backup_restore_roundtrip(tmp_path):
    plain = tmp_path / "xray_config.json"
    plain.write_text('{"ok": true}', encoding="utf-8")
    secret = tmp_path / ".env"
    secret.write_text("VPS_API_TOKEN=abc123", encoding="utf-8")

    archive = backup.create_backup(
        tmp_path / "out",
        plain_items=[plain],
        secret_items=[secret],
        passphrase="pw",
    )

    # The secret must NOT appear in plaintext anywhere in the archive.
    with tarfile.open(archive, "r:gz") as tar:
        for m in tar.getmembers():
            f = tar.extractfile(m)
            if f is not None:
                assert b"abc123" not in f.read()

    restored = backup.restore_backup(archive, tmp_path / "restored", passphrase="pw")
    names = {p.name: p for p in restored}
    assert names[".env"].read_text(encoding="utf-8") == "VPS_API_TOKEN=abc123"
    assert names["xray_config.json"].read_text(encoding="utf-8") == '{"ok": true}'


def test_restore_secret_requires_passphrase(tmp_path):
    secret = tmp_path / ".env"
    secret.write_text("x=1", encoding="utf-8")
    archive = backup.create_backup(
        tmp_path / "out", plain_items=[], secret_items=[secret], passphrase="pw"
    )
    with pytest.raises(ValueError):
        backup.restore_backup(archive, tmp_path / "r", passphrase="")
