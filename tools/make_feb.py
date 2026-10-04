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

# Sidecar Save Specification (.sav)
FEB_SAVE_MAGIC = 0x56415346 # 'FSAV' (little-endian ASCII)
FEB_SAVE_VERSION = 1
FEB_SAVE_FLAG_NONE = 0x0000
FEB_SAVE_FLAG_HIGH_SCORE = 0x0001

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

def create_feb(app_type, title, author="Flashiibo", version="1.0.0", payload=b"", icon=None):
    if icon is None or len(icon) != 32:
        icon = ICON_CHIP8_16x16

    magic = FEB_MAGIC
    format_version = FEB_VERSION
    flags = FEB_FLAG_NONE

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
    # uint32 crc32 (4B)
    # Total: 96 bytes
    header = struct.pack(
        "<IBBH24s16s8s32sII",
        magic,
        format_version,
        app_type,
        flags,
        title_bytes,
        author_bytes,
        version_bytes,
        icon,
        payload_size,
        crc32
    )

    assert len(header) == 96, f"Header size is {len(header)}, expected 96"
    return header + payload

def create_save(high_score=0, rpl_flags=None, extra_data=b""):
    if rpl_flags is None:
        rpl_flags = b"\x00" * 16
    elif len(rpl_flags) < 16:
        rpl_flags = bytes(rpl_flags).ljust(16, b"\x00")
    else:
        rpl_flags = bytes(rpl_flags[:16])

    flags = FEB_SAVE_FLAG_NONE
    if high_score > 0:
        flags |= FEB_SAVE_FLAG_HIGH_SCORE

    header = struct.pack(
        "<IHHI16sHH",
        FEB_SAVE_MAGIC,
        FEB_SAVE_VERSION,
        flags,
        high_score,
        rpl_flags,
        len(extra_data),
        0
    )
    assert len(header) == 32, f"Save header size is {len(header)}, expected 32"
    return header + extra_data

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
    parser.add_argument("--icon", default=None, help="Path to 16x16 1-bit icon bitmap (32 bytes)")

    args = parser.parse_args()

    app_type = FEB_TYPE_CHIP8

    payload_bytes = b""
    if args.payload and os.path.exists(args.payload):
        with open(args.payload, "rb") as f:
            payload_bytes = f.read()

    icon_bytes = None
    if args.icon and os.path.exists(args.icon):
        with open(args.icon, "rb") as f:
            icon_bytes = f.read()

    feb_data = create_feb(
        app_type=app_type,
        title=args.title,
        author=args.author,
        version=args.ver,
        payload=payload_bytes,
        icon=icon_bytes
    )

    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    with open(args.output, "wb") as f:
        f.write(feb_data)

    print(f"Created {args.output} ({len(feb_data)} bytes: 96B header + {len(payload_bytes)}B payload, type: {args.type})")

if __name__ == "__main__":
    main()
