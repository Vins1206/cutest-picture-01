#!/usr/bin/env python3
"""cutest-picture-01 entry: copy art.png to /output/entry.png.

The picture beside this file (art.png, a baby panda cub hugging a pink
heart) is the entry. This program validates it against the competition
gate -- a whole PNG or JPEG, at most 1 MiB and at most 1024 x 1024
pixels -- and then writes it byte for byte to the output path.

Outside the grader's container, MAKEFUN_OUTPUT_DIR stands in for
/output:

    mkdir -p out && MAKEFUN_OUTPUT_DIR=out python3 main.py

Python 3.13, standard library only. No network, deterministic: two
runs write exactly the same bytes, well under the 60 second limit.
"""

import os
import struct
import sys
from pathlib import Path

MAX_BYTES = 1_048_576  # 1 MiB
MAX_WIDTH = 1024
MAX_HEIGHT = 1024
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
JPEG_MAGIC = b"\xff\xd8\xff"


def png_dimensions(data: bytes) -> tuple[int, int]:
    """Read width and height from a PNG's IHDR chunk."""
    if len(data) < 24 or data[12:16] != b"IHDR":
        raise ValueError("PNG is missing its IHDR chunk")
    width, height = struct.unpack(">II", data[16:24])
    return width, height


def jpeg_dimensions(data: bytes) -> tuple[int, int]:
    """Scan JPEG segments for a Start Of Frame marker holding the size."""
    pos = 2  # skip the SOI marker (FF D8)
    while pos + 4 <= len(data):
        if data[pos] != 0xFF:
            raise ValueError("JPEG segment does not start with 0xFF")
        marker = data[pos + 1]
        if marker in (0xD9, 0xDA):  # EOI / SOS before any SOF
            break
        length = struct.unpack(">H", data[pos + 2 : pos + 4])[0]
        if length < 2 or pos + 2 + length > len(data):
            raise ValueError("JPEG segment length is out of range")
        # SOF0-SOF15, except DHT (C4), JPG (C8) and DAC (CC).
        if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
            if length < 7:
                raise ValueError("JPEG SOF segment is too short")
            height, width = struct.unpack(">HH", data[pos + 5 : pos + 9])
            return width, height
        pos += 2 + length
    raise ValueError("JPEG has no Start Of Frame segment")


def validate(data: bytes) -> None:
    """Raise ValueError unless data passes the cutest-picture gate."""
    if not data:
        raise ValueError("image file is empty")
    if len(data) > MAX_BYTES:
        raise ValueError(f"image is {len(data)} bytes, over the 1 MiB cap")
    if data.startswith(PNG_MAGIC):
        width, height = png_dimensions(data)
        if not data.endswith(b"IEND\xaeB`\x82"):
            raise ValueError("PNG does not end with a complete IEND chunk")
    elif data.startswith(JPEG_MAGIC):
        width, height = jpeg_dimensions(data)
        if not data.endswith(b"\xff\xd9"):
            raise ValueError("JPEG does not end with its EOI marker")
    else:
        raise ValueError("image is neither a PNG nor a JPEG")
    if width < 1 or height < 1:
        raise ValueError("image has a zero dimension")
    if width > MAX_WIDTH or height > MAX_HEIGHT:
        raise ValueError(
            f"image is {width}x{height}, over the {MAX_WIDTH}x{MAX_HEIGHT} cap"
        )


def main() -> int:
    here = Path(__file__).resolve().parent
    data = (here / "art.png").read_bytes()
    validate(data)
    out_dir = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "entry.png"
    out_path.write_bytes(data)
    # Verify the copy on disk: a short or corrupted write must fail the
    # run loudly here, not reach the judge as a broken picture.
    if out_path.read_bytes() != data:
        raise IOError("written entry.png does not match art.png byte for byte")
    return 0


if __name__ == "__main__":
    sys.exit(main())
