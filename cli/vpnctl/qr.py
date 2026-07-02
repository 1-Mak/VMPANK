"""QR-хелперы для subscription-ссылок / конфигов AWG (FR-5.2, FR-6.1)."""

from __future__ import annotations

from pathlib import Path

import qrcode


def to_ascii(data: str) -> str:
    """Отрендерить QR-код как ASCII для печати в терминале."""
    qr = qrcode.QRCode(border=1)
    qr.add_data(data)
    qr.make(fit=True)
    lines: list[str] = []
    matrix = qr.get_matrix()
    for row in matrix:
        lines.append("".join("██" if cell else "  " for cell in row))
    return "\n".join(lines)


def to_png(data: str, path: str | Path) -> Path:
    """Записать QR-код в PNG и вернуть путь."""
    img = qrcode.make(data)
    out = Path(path)
    img.save(out)
    return out
