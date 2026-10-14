"""Read (width, height) from a JPEG/PNG/GIF file header using only the stdlib."""
from __future__ import annotations

import struct
from pathlib import Path

_SOF = {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}


def image_size(path: str | Path) -> tuple[int, int] | None:
    """Return (width, height) in pixels, or None if the file is missing or unreadable."""
    try:
        with open(path, "rb") as f:
            head = f.read(26)
            if head[:8] == b"\x89PNG\r\n\x1a\n":
                w, h = struct.unpack(">II", head[16:24])
            elif head[:6] in (b"GIF87a", b"GIF89a"):
                w, h = struct.unpack("<HH", head[6:10])
            elif head[:2] == b"\xff\xd8":
                f.seek(2)
                while True:
                    b = f.read(1)
                    while b and b != b"\xff":
                        b = f.read(1)
                    while b == b"\xff":
                        b = f.read(1)
                    if not b:
                        return None
                    marker = b[0]
                    if marker in (0x01, *range(0xD0, 0xDA)):
                        continue
                    seg = f.read(2)
                    if len(seg) < 2:
                        return None
                    (length,) = struct.unpack(">H", seg)
                    if marker in _SOF:
                        data = f.read(5)
                        if len(data) < 5:
                            return None
                        h, w = struct.unpack(">xHH", data)
                        break
                    f.seek(length - 2, 1)
            else:
                return None
    except (OSError, struct.error):
        return None
    return (w, h) if w > 0 and h > 0 else None
