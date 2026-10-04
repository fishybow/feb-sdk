#!/usr/bin/env python3
"""
make_icon.py - Flashiibo Executable Binary (.feb) 16x16 App Icon Tool

Create, convert, inspect, preview, and export 16x16 monochrome (1-bit) app icons
for Flashiibo Pro Gen3 devices running FEB Runner (firmware >= 26.10.4).

FEB Container Specification:
  Icon offset: 56..87 (32 bytes, 1-bit per pixel, 16 rows of 16 pixels, row-major).
  Bit 7 of byte 0 is (x=0, y=0), Bit 0 of byte 1 is (x=15, y=0).

Features:
  - Convert standard images (.png, .jpg, .bmp, .gif, .webp) to 32-byte FEB icons
  - Image preprocessing: aspect-fit, center-crop, stretch, thresholding, dithering
  - Parse / generate ASCII art text grids (.txt) for quick editing in code editors
  - Generate C header definitions (#include "icon.h" / static const uint8_t APP_ICON[32])
  - Procedural text / letter icon generator (--text "20" / --text "GO" with optional border)
  - Extract embedded icons directly from compiled .feb executable binaries
  - Visual terminal preview using Unicode blocks (██)
  - Export icons as upscaled preview images (.png / .bmp with --scale 8 / 16)
  - Generates ready-to-use ASCII templates (--template)

Usage Examples:
  # 1. Convert PNG image to raw 32-byte icon binary:
  python3 tools/make_icon.py icon.png -o icon.bin

  # 2. Convert PNG image to C header snippet:
  python3 tools/make_icon.py icon.png -o icon.h --c-var ICON_PLAYER

  # 3. Create an editable ASCII template:
  python3 tools/make_icon.py --template icon.txt

  # 4. Convert ASCII art grid to binary icon:
  python3 tools/make_icon.py icon.txt -o icon.bin

  # 5. Generate a procedural letter/number icon with a border:
  python3 tools/make_icon.py --text "20" --border -o icon.bin

  # 6. Preview an existing icon (or .feb binary) in the terminal:
  python3 tools/make_icon.py my_app.feb --preview

  # 7. Export an icon binary to an upscaled 128x128 preview PNG:
  python3 tools/make_icon.py icon.bin -o preview.png --scale 8
"""

import sys
import os
import re
import struct
import argparse

# Try importing PIL (Pillow) for advanced image formats
try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

# FEB Container constants
FEB_MAGIC = 0x4245462E  # '.FEB' in little-endian ASCII
ICON_BYTE_SIZE = 32
ICON_WIDTH = 16
ICON_HEIGHT = 16

# ----------------------------------------------------------------------------
# Built-in Fonts for Procedural Glyph & Text Generation
# ----------------------------------------------------------------------------

# 5x7 Font: 7 rows of 5-bit integers (bits 4..0)
FONT_5X7 = {
    '0': (0x0E, 0x11, 0x13, 0x15, 0x19, 0x11, 0x0E),
    '1': (0x04, 0x0C, 0x04, 0x04, 0x04, 0x04, 0x0E),
    '2': (0x0E, 0x11, 0x01, 0x02, 0x04, 0x08, 0x1F),
    '3': (0x1F, 0x02, 0x04, 0x02, 0x01, 0x11, 0x0E),
    '4': (0x02, 0x06, 0x0A, 0x12, 0x1F, 0x02, 0x02),
    '5': (0x1F, 0x10, 0x1E, 0x01, 0x01, 0x11, 0x0E),
    '6': (0x06, 0x08, 0x10, 0x1E, 0x11, 0x11, 0x0E),
    '7': (0x1F, 0x01, 0x02, 0x04, 0x08, 0x08, 0x08),
    '8': (0x0E, 0x11, 0x11, 0x0E, 0x11, 0x11, 0x0E),
    '9': (0x0E, 0x11, 0x11, 0x0F, 0x01, 0x02, 0x0C),
    'A': (0x0E, 0x11, 0x11, 0x1F, 0x11, 0x11, 0x11),
    'B': (0x1E, 0x11, 0x11, 0x1E, 0x11, 0x11, 0x1E),
    'C': (0x0E, 0x11, 0x10, 0x10, 0x10, 0x11, 0x0E),
    'D': (0x1C, 0x12, 0x11, 0x11, 0x11, 0x12, 0x1C),
    'E': (0x1F, 0x10, 0x10, 0x1E, 0x10, 0x10, 0x1F),
    'F': (0x1F, 0x10, 0x10, 0x1E, 0x10, 0x10, 0x10),
    'G': (0x0E, 0x11, 0x10, 0x17, 0x11, 0x11, 0x0F),
    'H': (0x11, 0x11, 0x11, 0x1F, 0x11, 0x11, 0x11),
    'I': (0x0E, 0x04, 0x04, 0x04, 0x04, 0x04, 0x0E),
    'J': (0x07, 0x02, 0x02, 0x02, 0x02, 0x12, 0x0C),
    'K': (0x11, 0x12, 0x14, 0x18, 0x14, 0x12, 0x11),
    'L': (0x10, 0x10, 0x10, 0x10, 0x10, 0x10, 0x1F),
    'M': (0x11, 0x1B, 0x15, 0x15, 0x11, 0x11, 0x11),
    'N': (0x11, 0x19, 0x15, 0x13, 0x11, 0x11, 0x11),
    'O': (0x0E, 0x11, 0x11, 0x11, 0x11, 0x11, 0x0E),
    'P': (0x1E, 0x11, 0x11, 0x1E, 0x10, 0x10, 0x10),
    'Q': (0x0E, 0x11, 0x11, 0x11, 0x15, 0x12, 0x0D),
    'R': (0x1E, 0x11, 0x11, 0x1E, 0x14, 0x12, 0x11),
    'S': (0x0E, 0x11, 0x10, 0x0E, 0x01, 0x11, 0x0E),
    'T': (0x1F, 0x04, 0x04, 0x04, 0x04, 0x04, 0x04),
    'U': (0x11, 0x11, 0x11, 0x11, 0x11, 0x11, 0x0E),
    'V': (0x11, 0x11, 0x11, 0x11, 0x11, 0x0A, 0x04),
    'W': (0x11, 0x11, 0x11, 0x15, 0x15, 0x1B, 0x11),
    'X': (0x11, 0x11, 0x0A, 0x04, 0x0A, 0x11, 0x11),
    'Y': (0x11, 0x11, 0x0A, 0x04, 0x04, 0x04, 0x04),
    'Z': (0x1F, 0x01, 0x02, 0x04, 0x08, 0x10, 0x1F),
    ' ': (0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00),
    '!': (0x04, 0x04, 0x04, 0x04, 0x04, 0x00, 0x04),
    '?': (0x0E, 0x11, 0x01, 0x02, 0x04, 0x00, 0x04),
    '+': (0x00, 0x04, 0x04, 0x1F, 0x04, 0x04, 0x00),
    '-': (0x00, 0x00, 0x00, 0x1F, 0x00, 0x00, 0x00),
    '*': (0x00, 0x04, 0x15, 0x0E, 0x15, 0x04, 0x00),
    '#': (0x0A, 0x0A, 0x1F, 0x0A, 0x1F, 0x0A, 0x0A),
    ':': (0x00, 0x04, 0x00, 0x00, 0x04, 0x00, 0x00),
    '.': (0x00, 0x00, 0x00, 0x00, 0x00, 0x04, 0x04),
    '_': (0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x1F),
}

# 3x5 Font: 5 rows of 3-bit integers (bits 2..0) for 3-4 character strings
FONT_3X5 = {
    '0': (0x7, 0x5, 0x5, 0x5, 0x7),
    '1': (0x2, 0x6, 0x2, 0x2, 0x7),
    '2': (0x7, 0x1, 0x7, 0x4, 0x7),
    '3': (0x7, 0x1, 0x7, 0x1, 0x7),
    '4': (0x5, 0x5, 0x7, 0x1, 0x1),
    '5': (0x7, 0x4, 0x7, 0x1, 0x7),
    '6': (0x7, 0x4, 0x7, 0x5, 0x7),
    '7': (0x7, 0x1, 0x2, 0x2, 0x2),
    '8': (0x7, 0x5, 0x7, 0x5, 0x7),
    '9': (0x7, 0x5, 0x7, 0x1, 0x7),
    'A': (0x7, 0x5, 0x7, 0x5, 0x5),
    'B': (0x6, 0x5, 0x6, 0x5, 0x6),
    'C': (0x7, 0x4, 0x4, 0x4, 0x7),
    'D': (0x6, 0x5, 0x5, 0x5, 0x6),
    'E': (0x7, 0x4, 0x6, 0x4, 0x7),
    'F': (0x7, 0x4, 0x6, 0x4, 0x4),
    'G': (0x7, 0x4, 0x5, 0x5, 0x7),
    'H': (0x5, 0x5, 0x7, 0x5, 0x5),
    'I': (0x7, 0x2, 0x2, 0x2, 0x7),
    'J': (0x1, 0x1, 0x1, 0x5, 0x2),
    'K': (0x5, 0x5, 0x6, 0x5, 0x5),
    'L': (0x4, 0x4, 0x4, 0x4, 0x7),
    'M': (0x5, 0x7, 0x5, 0x5, 0x5),
    'N': (0x6, 0x5, 0x5, 0x5, 0x5),
    'O': (0x7, 0x5, 0x5, 0x5, 0x7),
    'P': (0x7, 0x5, 0x7, 0x4, 0x4),
    'Q': (0x7, 0x5, 0x5, 0x7, 0x1),
    'R': (0x6, 0x5, 0x6, 0x5, 0x5),
    'S': (0x3, 0x4, 0x7, 0x1, 0x6),
    'T': (0x7, 0x2, 0x2, 0x2, 0x2),
    'U': (0x5, 0x5, 0x5, 0x5, 0x7),
    'V': (0x5, 0x5, 0x5, 0x5, 0x2),
    'W': (0x5, 0x5, 0x5, 0x7, 0x5),
    'X': (0x5, 0x5, 0x2, 0x5, 0x5),
    'Y': (0x5, 0x5, 0x2, 0x2, 0x2),
    'Z': (0x7, 0x1, 0x2, 0x4, 0x7),
    ' ': (0x0, 0x0, 0x0, 0x0, 0x0),
    '!': (0x2, 0x2, 0x2, 0x0, 0x2),
    '-': (0x0, 0x0, 0x7, 0x0, 0x0),
    '+': (0x0, 0x2, 0x7, 0x2, 0x0),
    '.': (0x0, 0x0, 0x0, 0x0, 0x2),
    '#': (0x5, 0x7, 0x5, 0x7, 0x5),
}

# ----------------------------------------------------------------------------
# Core Bitmap Grid & Binary Conversions
# ----------------------------------------------------------------------------

def bytes_to_grid(icon_bytes):
    """
    Converts 32 bytes of packed bitmap data into a 16x16 2D grid of 0s and 1s.
    """
    if len(icon_bytes) != ICON_BYTE_SIZE:
        raise ValueError(f"Icon binary must be exactly {ICON_BYTE_SIZE} bytes (got {len(icon_bytes)})")

    grid = []
    for y in range(ICON_HEIGHT):
        row = []
        b0 = icon_bytes[y * 2]
        b1 = icon_bytes[y * 2 + 1]
        for bit in range(7, -1, -1):
            row.append((b0 >> bit) & 1)
        for bit in range(7, -1, -1):
            row.append((b1 >> bit) & 1)
        grid.append(row)
    return grid

def grid_to_bytes(grid):
    """
    Converts a 16x16 2D grid of 0s and 1s into 32 packed bitmap bytes.
    """
    if len(grid) != ICON_HEIGHT:
        raise ValueError(f"Grid must have exactly {ICON_HEIGHT} rows (got {len(grid)})")

    result = bytearray()
    for y in range(ICON_HEIGHT):
        row = grid[y]
        if len(row) != ICON_WIDTH:
            raise ValueError(f"Row {y} must have exactly {ICON_WIDTH} columns (got {len(row)})")
        b0 = 0
        b1 = 0
        for x in range(8):
            if row[x]:
                b0 |= (1 << (7 - x))
        for x in range(8):
            if row[8 + x]:
                b1 |= (1 << (7 - x))
        result.append(b0)
        result.append(b1)
    return bytes(result)

def invert_grid(grid):
    """Inverts 0s and 1s in a 16x16 grid."""
    return [[1 - p for p in row] for row in grid]

def add_border(grid):
    """Draws a 1-pixel outer frame around the 16x16 grid."""
    new_grid = [list(row) for row in grid]
    for x in range(ICON_WIDTH):
        new_grid[0][x] = 1
        new_grid[ICON_HEIGHT - 1][x] = 1
    for y in range(ICON_HEIGHT):
        new_grid[y][0] = 1
        new_grid[y][ICON_WIDTH - 1] = 1
    return new_grid

# ----------------------------------------------------------------------------
# Rendering & Export Formatters
# ----------------------------------------------------------------------------

def render_ascii(grid_or_bytes, lit_char="#", unlit_char="."):
    """
    Renders 16x16 icon as 16 lines of ASCII text.
    """
    if isinstance(grid_or_bytes, (bytes, bytearray)):
        grid = bytes_to_grid(grid_or_bytes)
    else:
        grid = grid_or_bytes

    return "\n".join("".join(lit_char if p else unlit_char for p in row) for row in grid)

def render_terminal(grid_or_bytes):
    """
    Renders a formatted visual ANSI preview of the icon in the terminal.
    Uses double Unicode full blocks (██) for a square 1:1 pixel aspect ratio.
    """
    if isinstance(grid_or_bytes, (bytes, bytearray)):
        grid = bytes_to_grid(grid_or_bytes)
        icon_bytes = bytes(grid_or_bytes)
    else:
        grid = grid_or_bytes
        icon_bytes = grid_to_bytes(grid)

    lit_count = sum(sum(row) for row in grid)
    total_pixels = ICON_WIDTH * ICON_HEIGHT
    pct = (lit_count / total_pixels) * 100.0

    lines = []
    lines.append("     0 1 2 3 4 5 6 7 8 9 A B C D E F")
    lines.append("   ┌" + "──" * ICON_WIDTH + "┐")

    for y in range(ICON_HEIGHT):
        row_str = "".join("██" if p else "  " for p in grid[y])
        lines.append(f"{y:2X} │{row_str}│")

    lines.append("   └" + "──" * ICON_WIDTH + "┘")
    lines.append(f"   Icon: 16x16 px | Size: 32 bytes | Lit: {lit_count}/{total_pixels} ({pct:.1f}%)")
    return "\n".join(lines)

def render_c_header(grid_or_bytes, var_name="APP_ICON"):
    """
    Generates a clean C header defining the 32-byte icon array with row-by-row ASCII comments.
    """
    if isinstance(grid_or_bytes, (bytes, bytearray)):
        grid = bytes_to_grid(grid_or_bytes)
        icon_bytes = bytes(grid_or_bytes)
    else:
        grid = grid_or_bytes
        icon_bytes = grid_to_bytes(grid)

    header_guard = f"{var_name.upper()}_H"
    lines = [
        f"#ifndef {header_guard}",
        f"#define {header_guard}",
        "",
        "#include <stdint.h>",
        "",
        "/**",
        " * Flashiibo FEB 16x16 App Icon (32 bytes)",
        " * Display Target: Super-CHIP 16x16 sprite / FEB header offset 56..87",
        " */",
        f"static const uint8_t {var_name}[32] = {{"
    ]

    for y in range(ICON_HEIGHT):
        b0 = icon_bytes[y * 2]
        b1 = icon_bytes[y * 2 + 1]
        ascii_row = "".join("#" if p else "." for p in grid[y])
        comma = "," if y < ICON_HEIGHT - 1 else " "
        lines.append(f"    0x{b0:02x}, 0x{b1:02x}{comma} /* Row {y:2d}: {ascii_row} */")

    lines.append("};")
    lines.append("")
    lines.append(f"#endif /* {header_guard} */")
    return "\n".join(lines)

def generate_template():
    """
    Generates an editable 16x16 ASCII text template file with documentation.
    """
    return """; ----------------------------------------------------------------------------
; Flashiibo 16x16 FEB App Icon Template
;
; Instructions:
;   - Edit this 16x16 pixel grid directly in any text editor.
;   - Use '#' or 'X' for lit pixels (OLED pixel ON).
;   - Use '.' or ' ' for unlit pixels (OLED pixel OFF).
;   - Lines starting with ';' or '//' are comments.
;
; Compile into your app:
;   python3 tools/make_icon.py icon.txt -o icon.bin
;   python3 tools/feb_build.py main.c -o app.feb --icon icon.txt
; ----------------------------------------------------------------------------
................
.##############.
.#............#.
.#............#.
.#...######...#.
.#...#....#...#.
.#...######...#.
.#...#....#...#.
.#...#....#...#.
.#...######...#.
.#............#.
.#............#.
.#............#.
.#............#.
.##############.
................
"""

# ----------------------------------------------------------------------------
# Procedural Glyph & Text Generation
# ----------------------------------------------------------------------------

def render_text_glyph(text, border=False, invert=False):
    """
    Generates a 16x16 icon rendering 1 to 4 characters (letters, numbers, or symbols).
    """
    clean_text = text.strip()
    if not clean_text:
        clean_text = "?"

    grid = [[0] * ICON_WIDTH for _ in range(ICON_HEIGHT)]

    if len(clean_text) == 1:
        # Single character: 2x scaled 5x7 font -> 10x14 pixels centered
        ch = clean_text[0].upper()
        glyph = FONT_5X7.get(ch, FONT_5X7.get('?', (0, 0, 0, 0, 0, 0, 0)))
        sx = 3
        sy = 1
        for r, row_val in enumerate(glyph):
            for c in range(5):
                if (row_val >> (4 - c)) & 1:
                    for dr in (0, 1):
                        for dc in (0, 1):
                            grid[sy + r * 2 + dr][sx + c * 2 + dc] = 1

    elif len(clean_text) == 2:
        # Two characters: 5x7 font -> 11 pixels wide, centered at x=2, y=4
        sx = 2
        sy = 4
        for idx, ch_raw in enumerate(clean_text[:2]):
            ch = ch_raw.upper()
            glyph = FONT_5X7.get(ch, FONT_5X7.get('?', (0, 0, 0, 0, 0, 0, 0)))
            ox = sx + idx * 6
            for r, row_val in enumerate(glyph):
                for c in range(5):
                    if (row_val >> (4 - c)) & 1:
                        grid[sy + r][ox + c] = 1

    elif len(clean_text) == 3:
        # Three characters: 3x5 font -> 11 pixels wide, centered at x=2, y=5
        sx = 2
        sy = 5
        for idx, ch_raw in enumerate(clean_text[:3]):
            ch = ch_raw.upper()
            glyph = FONT_3X5.get(ch, FONT_3X5.get('?', (0, 0, 0, 0, 0)))
            ox = sx + idx * 4
            for r, row_val in enumerate(glyph):
                for c in range(3):
                    if (row_val >> (2 - c)) & 1:
                        grid[sy + r][ox + c] = 1

    else:
        # Four characters: 3x5 font -> 15 pixels wide, centered at x=0, y=5
        sx = 0
        sy = 5
        for idx, ch_raw in enumerate(clean_text[:4]):
            ch = ch_raw.upper()
            glyph = FONT_3X5.get(ch, FONT_3X5.get('?', (0, 0, 0, 0, 0)))
            ox = sx + idx * 4
            for r, row_val in enumerate(glyph):
                for c in range(3):
                    if (row_val >> (2 - c)) & 1:
                        if ox + c < ICON_WIDTH:
                            grid[sy + r][ox + c] = 1

    if border:
        grid = add_border(grid)

    if invert:
        grid = invert_grid(grid)

    return grid_to_bytes(grid)

# ----------------------------------------------------------------------------
# Input Parsers: ASCII, C Header, FEB Binary, Image Files
# ----------------------------------------------------------------------------

def load_from_ascii(text_or_lines):
    """
    Parses a 16x16 ASCII text grid into 32 icon bytes.
    Permissive with comments (;, //, #) and surrounding borders (| or []).
    """
    if isinstance(text_or_lines, str):
        lines = text_or_lines.splitlines()
    else:
        lines = list(text_or_lines)

    LIT_CHARS = set("#*Xx1@%Oo+$█■")
    UNLIT_CHARS = set(". 0-_")

    valid_rows = []
    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue
        # Check for comments
        if line.startswith(";") or line.startswith("//"):
            continue
        # Comment lines starting with '#' followed by space or text
        if line.startswith("#") and (len(line) == 1 or line[1] in " \tABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"):
            continue

        row_bits = []
        for ch in line:
            if ch in LIT_CHARS:
                row_bits.append(1)
            elif ch in UNLIT_CHARS:
                row_bits.append(0)
            elif ch in "|[]:!":
                continue  # ignore frame borders
            else:
                continue

        if len(row_bits) >= ICON_WIDTH:
            valid_rows.append(row_bits[:ICON_WIDTH])

    if len(valid_rows) != ICON_HEIGHT:
        raise ValueError(
            f"ASCII icon must contain exactly {ICON_HEIGHT} rows of {ICON_WIDTH} pixels (found {len(valid_rows)} valid rows)."
        )

    return grid_to_bytes(valid_rows)

def load_from_c_header(text):
    """
    Extracts 32 hex byte literals from C source code or headers.
    """
    hex_matches = re.findall(r"0x([0-9a-fA-F]{1,2})\b", text)
    if len(hex_matches) >= ICON_BYTE_SIZE:
        return bytes(int(h, 16) for h in hex_matches[:ICON_BYTE_SIZE])
    raise ValueError(f"Could not find 32 hex bytes in C source / header (found {len(hex_matches)})")

def load_from_feb(data_or_path):
    """
    Extracts the embedded 16x16 icon from a Flashiibo Executable Binary (.feb).
    """
    if isinstance(data_or_path, (bytes, bytearray)):
        data = data_or_path
    else:
        with open(data_or_path, "rb") as f:
            data = f.read()

    if len(data) < 96:
        raise ValueError(f"File too small for FEB container ({len(data)} bytes, expected at least 96)")

    magic, = struct.unpack_from("<I", data, 0)
    if magic != FEB_MAGIC:
        raise ValueError(f"Invalid FEB magic: 0x{magic:08X} (expected 0x{FEB_MAGIC:08X})")

    icon = data[56:88]
    assert len(icon) == ICON_BYTE_SIZE
    return icon

def load_from_image(path_or_file, mode="fit", threshold=128, dither=False, invert=False):
    """
    Loads an image file, downscales/fits to 16x16, applies binarization/dithering,
    and returns 32 icon bytes.
    """
    if HAS_PIL:
        img = Image.open(path_or_file)

        # Handle alpha transparency: composite over black background
        if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
            rgba = img.convert("RGBA")
            bg = Image.new("RGBA", rgba.size, (0, 0, 0, 255))
            bg.paste(rgba, (0, 0), mask=rgba.split()[3])
            img = bg.convert("RGB")
        else:
            img = img.convert("RGB")

        orig_w, orig_h = img.size
        if (orig_w, orig_h) == (ICON_WIDTH, ICON_HEIGHT):
            resized = img
        elif mode == "stretch":
            resized = img.resize((ICON_WIDTH, ICON_HEIGHT), resample=Image.Resampling.LANCZOS)
        elif mode == "crop":
            min_dim = min(orig_w, orig_h)
            left = (orig_w - min_dim) // 2
            top = (orig_h - min_dim) // 2
            cropped = img.crop((left, top, left + min_dim, top + min_dim))
            resized = cropped.resize((ICON_WIDTH, ICON_HEIGHT), resample=Image.Resampling.LANCZOS)
        else:  # "fit" (default)
            scale = min(float(ICON_WIDTH) / orig_w, float(ICON_HEIGHT) / orig_h)
            new_w = max(1, int(round(orig_w * scale)))
            new_h = max(1, int(round(orig_h * scale)))
            scaled = img.resize((new_w, new_h), resample=Image.Resampling.LANCZOS)
            resized = Image.new("RGB", (ICON_WIDTH, ICON_HEIGHT), color=(0, 0, 0))
            ox = (ICON_WIDTH - new_w) // 2
            oy = (ICON_HEIGHT - new_h) // 2
            resized.paste(scaled, (ox, oy))

        grid = [[0] * ICON_WIDTH for _ in range(ICON_HEIGHT)]
        if dither:
            bw = resized.convert("1", dither=Image.Dither.FLOYDSTEINBERG)
            bw_pixels = bw.load()
            for y in range(ICON_HEIGHT):
                for x in range(ICON_WIDTH):
                    val = 1 if bw_pixels[x, y] > 0 else 0
                    if invert:
                        val ^= 1
                    grid[y][x] = val
        else:
            gray = resized.convert("L")
            gray_pixels = gray.load()
            for y in range(ICON_HEIGHT):
                for x in range(ICON_WIDTH):
                    val = 1 if gray_pixels[x, y] >= threshold else 0
                    if invert:
                        val ^= 1
                    grid[y][x] = val

        return grid_to_bytes(grid)

    else:
        # Pure Python fallback: reads uncompressed BMP
        try:
            return load_from_bmp_file(path_or_file, threshold=threshold, invert=invert)
        except Exception:
            raise ImportError(
                "Pillow is required for PNG/JPEG image conversion. Install via: pip install pillow\n"
                "Alternatively, you can provide an ASCII art .txt file, C header .h, or uncompressed .bmp."
            )

def load_from_bmp_file(path, threshold=128, invert=False):
    """Pure-Python standard library reader for uncompressed 16x16 24-bit/32-bit BMP."""
    with open(path, "rb") as f:
        data = f.read()
    if data[:2] != b"BM":
        raise ValueError("Not a valid BMP file")

    offset, = struct.unpack_from("<I", data, 10)
    dib_size, width, height, planes, bpp, compression = struct.unpack_from("<IIIHHI", data, 14)
    if width != ICON_WIDTH or abs(height) != ICON_HEIGHT or compression != 0:
        raise ValueError(f"Pure-Python BMP reader only supports uncompressed 16x16 BMPs (got {width}x{height})")

    row_bytes = width * (bpp // 8)
    padding = (4 - (row_bytes % 4)) % 4
    bytes_per_pixel = bpp // 8

    grid = [[0] * ICON_WIDTH for _ in range(ICON_HEIGHT)]
    pos = offset
    top_down = (height < 0)
    y_range = range(ICON_HEIGHT) if top_down else reversed(range(ICON_HEIGHT))

    for y in y_range:
        for x in range(ICON_WIDTH):
            b = data[pos]
            g = data[pos + 1]
            r = data[pos + 2]
            pos += bytes_per_pixel
            gray = int(0.299 * r + 0.587 * g + 0.114 * b)
            val = 1 if gray >= threshold else 0
            if invert:
                val ^= 1
            grid[y][x] = val
        pos += padding

    return grid_to_bytes(grid)

def load_icon(source, **kwargs):
    """
    Universal icon loader: accepts raw bytes, .bin, .feb, .png, .jpg, .bmp, .txt, or .h.
    Returns exactly 32 bytes of packed bitmap data.
    """
    if isinstance(source, (bytes, bytearray)):
        if len(source) == ICON_BYTE_SIZE:
            return bytes(source)
        if len(source) >= 96 and struct.unpack_from("<I", source, 0)[0] == FEB_MAGIC:
            return load_from_feb(source)
        try:
            return load_from_ascii(source.decode("utf-8"))
        except Exception:
            pass
        raise ValueError(f"Raw byte input must be {ICON_BYTE_SIZE} bytes (got {len(source)})")

    if not isinstance(source, str):
        raise TypeError(f"Unsupported icon source type: {type(source)}")

    if not os.path.exists(source):
        # Check if caller passed a multiline ASCII string directly
        if "\n" in source or len(source) >= ICON_WIDTH:
            return load_from_ascii(source)
        raise FileNotFoundError(f"Icon file not found: {source}")

    ext = os.path.splitext(source)[1].lower()

    if ext == ".feb":
        return load_from_feb(source)

    if ext in (".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp"):
        return load_from_image(source, **kwargs)

    if ext in (".h", ".c"):
        with open(source, "r", encoding="utf-8") as f:
            return load_from_c_header(f.read())

    if ext in (".bin", ".raw", ".icon"):
        with open(source, "rb") as f:
            data = f.read()
        if len(data) == ICON_BYTE_SIZE:
            return data
        raise ValueError(f"Icon binary '{source}' must be exactly {ICON_BYTE_SIZE} bytes (got {len(data)})")

    # For .txt or unknown extension: try ASCII first, then image, then binary
    try:
        with open(source, "r", encoding="utf-8") as f:
            content = f.read()
        return load_from_ascii(content)
    except Exception:
        pass

    try:
        return load_from_image(source, **kwargs)
    except Exception:
        pass

    with open(source, "rb") as f:
        data = f.read()
    if len(data) == ICON_BYTE_SIZE:
        return data

    raise ValueError(f"Unable to parse icon from '{source}'. Expected .png, .txt, .h, or 32-byte .bin.")

# ----------------------------------------------------------------------------
# Output Savers: Binary, PNG, BMP, C Header, ASCII
# ----------------------------------------------------------------------------

def save_to_png(icon_bytes, output_path, scale=1):
    """Saves icon as a PNG image, optionally upscaled."""
    if not HAS_PIL:
        raise ImportError("Pillow is required for PNG output. Install via: pip install pillow")

    grid = bytes_to_grid(icon_bytes)
    img = Image.new("RGB", (ICON_WIDTH, ICON_HEIGHT), color=(0, 0, 0))
    pixels = img.load()
    for y in range(ICON_HEIGHT):
        for x in range(ICON_WIDTH):
            if grid[y][x]:
                pixels[x, y] = (255, 255, 255)

    if scale > 1:
        img = img.resize((ICON_WIDTH * scale, ICON_HEIGHT * scale), resample=Image.Resampling.NEAREST)

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    img.save(output_path)

def save_to_bmp(icon_bytes, output_path, scale=1):
    """Pure-Python standard library saver for 24-bit uncompressed BMP."""
    grid = bytes_to_grid(icon_bytes)
    width = ICON_WIDTH * scale
    height = ICON_HEIGHT * scale

    row_bytes = width * 3
    padding = (4 - (row_bytes % 4)) % 4
    image_size = (row_bytes + padding) * height
    file_size = 54 + image_size

    header = struct.pack("<2sIHHI", b"BM", file_size, 0, 0, 54)
    dib = struct.pack("<IIIHHIIIIII", 40, width, height, 1, 24, 0, image_size, 2835, 2835, 0, 0)

    pixel_data = bytearray()
    for y in reversed(range(height)):
        orig_y = y // scale
        for x in range(width):
            orig_x = x // scale
            c = 255 if grid[orig_y][orig_x] else 0
            pixel_data.extend([c, c, c])
        pixel_data.extend([0] * padding)

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(header + dib + pixel_data)

def save_icon(icon_bytes, output_path, scale=1, c_var="APP_ICON"):
    """
    Saves icon bytes to the destination file based on its extension.
    """
    out_dir = os.path.dirname(os.path.abspath(output_path))
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    ext = os.path.splitext(output_path)[1].lower()

    if ext in (".h", ".c"):
        header_text = render_c_header(icon_bytes, var_name=c_var)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(header_text)
    elif ext == ".txt":
        ascii_text = render_ascii(icon_bytes)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(ascii_text + "\n")
    elif ext == ".png":
        save_to_png(icon_bytes, output_path, scale=max(1, scale))
    elif ext == ".bmp":
        save_to_bmp(icon_bytes, output_path, scale=max(1, scale))
    else:  # .bin, .raw, .icon, or default binary
        with open(output_path, "wb") as f:
            f.write(icon_bytes)

# ----------------------------------------------------------------------------
# Command-Line Interface
# ----------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Flashiibo FEB 16x16 App Icon Tool: Create, convert, inspect, preview, and export app icons."
    )
    parser.add_argument("input", nargs="?", default=None, help="Input file (.png, .jpg, .bmp, .txt, .h, .bin, .feb)")
    parser.add_argument("-i", "--input", dest="input_flag", default=None, help="Input file (alternative to positional argument)")
    parser.add_argument("-o", "--output", default=None, help="Output file (.bin, .h, .txt, .png, .bmp)")
    parser.add_argument("--text", default=None, help="Generate icon from 1-4 letters or numbers (e.g. '20', 'GO', 'A')")
    parser.add_argument("--border", "--box", action="store_true", help="Draw a 1-pixel frame around the icon")
    parser.add_argument("--mode", choices=["fit", "crop", "stretch"], default="fit", help="Image resize mode (default: fit)")
    parser.add_argument("--threshold", type=int, default=128, help="Monochrome threshold 0..255 (default: 128)")
    parser.add_argument("--dither", action="store_true", help="Apply Floyd-Steinberg dithering for images")
    parser.add_argument("--invert", action="store_true", help="Invert monochrome bits (swap lit and unlit pixels)")
    parser.add_argument("--scale", type=int, default=1, help="Scale multiplier for PNG/BMP export (default: 1, or 8 for previews)")
    parser.add_argument("--c-var", default="APP_ICON", help="C variable name when exporting .h (default: APP_ICON)")
    parser.add_argument("--preview", action="store_true", help="Print visual ANSI block preview in terminal")
    parser.add_argument("--preview-png", default=None, help="Path to save an upscaled preview PNG (scaled 8x)")
    parser.add_argument("--template", nargs="?", const="icon.txt", default=None, help="Generate editable ASCII template (default: icon.txt)")
    parser.add_argument("-q", "--quiet", action="store_true", help="Suppress terminal preview when writing output file")

    args = parser.parse_args()

    # Mode 1: Generate template
    if args.template is not None:
        template_path = args.template
        template_content = generate_template()
        with open(template_path, "w", encoding="utf-8") as f:
            f.write(template_content)
        print(f"Generated editable ASCII icon template: {template_path}")
        print("Edit this 16x16 grid with '#' and '.', then build with make_icon.py or feb_build.py.")
        return

    # Determine input source
    input_source = args.input_flag or args.input

    # Mode 2: Generate from text glyphs
    if args.text is not None:
        icon_bytes = render_text_glyph(args.text, border=args.border, invert=args.invert)
        source_desc = f"Text glyph '{args.text}'" + (" (with border)" if args.border else "")
    elif input_source:
        source_desc = input_source
        icon_bytes = load_icon(
            input_source,
            mode=args.mode,
            threshold=args.threshold,
            dither=args.dither,
            invert=args.invert
        )
        if args.border:
            grid = bytes_to_grid(icon_bytes)
            grid = add_border(grid)
            icon_bytes = grid_to_bytes(grid)
    else:
        parser.print_help()
        sys.exit(1)

    # Save output file if requested
    if args.output:
        save_scale = args.scale
        # Default upscaled scale if exporting PNG/BMP without explicit scale
        if args.output.endswith((".png", ".bmp")) and args.scale == 1:
            save_scale = 8
        save_icon(icon_bytes, args.output, scale=save_scale, c_var=args.c_var)
        print(f"Wrote icon ({len(icon_bytes)}B) -> {args.output}")

    # Save PNG preview if requested
    if args.preview_png:
        save_to_png(icon_bytes, args.preview_png, scale=8)
        print(f"Wrote preview PNG (128x128) -> {args.preview_png}")

    # Display terminal preview if requested, or if no output was specified, or unless quiet
    if not args.quiet:
        if args.preview or not args.output or args.text is not None:
            print(f"\n--- Preview: {source_desc} ---")
            print(render_terminal(icon_bytes))

        # If no output file was specified, also print the C header snippet
        if not args.output:
            print("\n--- C Header Snippet ---")
            print(render_c_header(icon_bytes, var_name=args.c_var))

if __name__ == "__main__":
    main()
