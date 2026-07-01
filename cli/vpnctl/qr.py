"""QR helpers for subscription links / AWG configs (FR-5.2, FR-6.1)."""

from __future__ import annotations

from pathlib import Path

import qrcode


def to_ascii(data: str) -> str:
    """Render a QR code as terminal-printable ASCII."""
    qr = qrcode.QRCode(border=1)
    qr.add_data(data)
    qr.make(fit=True)
    lines: list[str] = []
    matrix = qr.get_matrix()
    for row in matrix:
        lines.append("".join("██" if cell else "  " for cell in row))
    return "\n".join(lines)


def to_png(data: str, path: str | Path) -> Path:
    """Write a PNG QR code and return the path."""
    img = qrcode.make(data)
    out = Path(path)
    img.save(out)
    return out
