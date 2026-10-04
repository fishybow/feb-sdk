#!/usr/bin/env python3
"""
make_feb.py - Flashiibo Executable Binary (.feb) Generator

WARNING: This tool and the FEB format are in BETA and EXPERIMENTAL status.
Breaking changes might happen without warning.

Packages games and mini apps into downloadable .feb files for Flashiibo external flash storage.
"""

import struct
import argparse
import os
import sys

# '.FEB' in little-endian ASCII: '.'=0x2E, 'F'=0x46, 'E'=0x45, 'B'=0x42
FEB_MAGIC = 0x4245462E
FEB_VERSION = 1

FEB_TYPE_CHIP8 = 0

FEB_FLAG_NONE = 0x0000
FEB_FLAG_HIGH_SCORE = 0x0001
FEB_FLAG_IS_MINI_APP = 0x0002

# Default 16x16 icon for 2048 (4x4 mini-grid)
ICON_2048_16x16 = bytes([
    0xFF, 0xFF,
    0x80, 0x01,
    0xBF, 0xFD,
    0xA1, 0x85,
    0xA1, 0x85,
    0xBF, 0xFD,
    0xA1, 0x05,
    0xA1, 0x05,
    0xBF, 0xFD,
    0x80, 0x01,
    0xBF, 0xFD,
    0xA1, 0x85,
    0xBF, 0xFD,
    0xA1, 0x85,
    0xBF, 0xFD,
    0xFF, 0xFF
])

# Default 16x16 icon for CHIP-8 (Arcade D-pad / Joystick)
ICON_CHIP8_16x16 = bytes([
    0x00, 0x00, 0x7e, 0x7e, 0x81, 0x81, 0x81, 0x81,
    0x99, 0x99, 0xbd, 0xbd, 0x99, 0x99, 0x81, 0x81,
    0x81, 0x81, 0x81, 0x81, 0xbd, 0xbd, 0xa5, 0xa5,
    0xbd, 0xbd, 0x81, 0x81, 0x7e, 0x7e, 0x00, 0x00
])

# Default 16x16 icon for Mini App (App grid / Tools)
ICON_APP_16x16 = bytes([
    0x00, 0x00, 0x3c, 0x3c, 0x24, 0x24, 0x3c, 0x3c,
    0x00, 0x00, 0x3c, 0x3c, 0x24, 0x24, 0x3c, 0x3c,
    0x00, 0x00, 0x3c, 0x3c, 0x24, 0x24, 0x3c, 0x3c,
    0x00, 0x00, 0x3c, 0x3c, 0x24, 0x24, 0x3c, 0x3c
])

def create_feb(app_type, title, author="Flashiibo", version="1.0.0", payload=b"", icon=None, high_score=0, is_mini_app=False):
    if icon is None or len(icon) != 32:
        if is_mini_app:
            icon = ICON_APP_16x16
        elif "2048" in title:
            icon = ICON_2048_16x16
        else:
            icon = ICON_CHIP8_16x16

    magic = FEB_MAGIC
    format_version = FEB_VERSION
    flags = FEB_FLAG_NONE
    if high_score > 0:
        flags |= FEB_FLAG_HIGH_SCORE
    if is_mini_app:
        flags |= FEB_FLAG_IS_MINI_APP

    title_bytes = title.encode('utf-8')[:23].ljust(24, b'\x00')
    author_bytes = author.encode('utf-8')[:15].ljust(16, b'\x00')
    version_bytes = version.encode('utf-8')[:7].ljust(8, b'\x00')

    payload_size = len(payload)
    crc32 = 0

    # Header format:
    # uint32 magic (4B)
    # uint8  format_version (1B)
    # uint8  app_type (1B)
    # uint16 flags (2B)
    # char   title[24] (24B)
    # char   author[16] (16B)
    # char   version[8] (8B)
    # uint8  icon[32] (32B)
    # uint32 payload_size (4B)
    # uint32 high_score (4B)
    # uint32 crc32 (4B)
    # Total: 100 bytes
    header = struct.pack(
        "<IBBH24s16s8s32sIII",
        magic,
        format_version,
        app_type,
        flags,
        title_bytes,
        author_bytes,
        version_bytes,
        icon,
        payload_size,
        high_score,
        crc32
    )

    assert len(header) == 100, f"Header size is {len(header)}, expected 100"
    return header + payload

def main():
    parser = argparse.ArgumentParser(
        description="Flashiibo Executable Binary (.feb) Generator [BETA / EXPERIMENTAL: Breaking changes may occur without warning]"
    )
    parser.add_argument("-o", "--output", required=True, help="Output .feb path")
    parser.add_argument("-t", "--type", choices=["chip8"], default="chip8", help="Executable type")
    parser.add_argument("--title", required=True, help="Display title (max 23 chars)")
    parser.add_argument("--author", default="Flashiibo", help="Author string")
    parser.add_argument("--ver", default="1.0.0", help="Version string")
    parser.add_argument("--payload", default=None, help="Path to binary payload (e.g. .ch8 bytecode)")
    parser.add_argument("--high-score", type=int, default=0, help="Initial high score / state")
    parser.add_argument("--app", action="store_true", help="Mark executable as a mini-app (instead of game)")

    args = parser.parse_args()

    app_type = FEB_TYPE_CHIP8

    payload_bytes = b""
    if args.payload and os.path.exists(args.payload):
        with open(args.payload, "rb") as f:
            payload_bytes = f.read()

    feb_data = create_feb(
        app_type=app_type,
        title=args.title,
        author=args.author,
        version=args.ver,
        payload=payload_bytes,
        high_score=args.high_score,
        is_mini_app=args.app
    )

    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    with open(args.output, "wb") as f:
        f.write(feb_data)

    print(f"Created {args.output} ({len(feb_data)} bytes: 100B header + {len(payload_bytes)}B payload, type: {args.type})")

if __name__ == "__main__":
    main()
