#!/usr/bin/env python3
"""
feb_vm.py - Flashiibo FEB / CHIP-8 / Super-CHIP Virtual Machine Engine

High-fidelity Python implementation of the Flashiibo FEB runtime matching
the firmware-52832 architecture (chip8.c and feb_runner_view.c):
  - 128x64 default Super-CHIP (or 64x32 legacy) display modes
  - Standard CHIP-8 + Super-CHIP instructions (00Cn, 00FB, 00FC, 00FD, 00FE, 00FF)
  - Custom Flashiibo VM extensions (firmware >= 26.10.4):
      * FX90-FX99: Hardware vector geometry (pixel, line, hline, vline, rect, fillrect, circle, disc, drawmode, testpixel)
      * FXA0-FXA3: Typography & string/number formatting (u8g2 fonts 4x6, 6x10, 8x8)
      * FXB0: Instantaneous 4-button hardware polling bitmask (getkeys)
      * FX75/FX85: Persistent RPL user flags (.sav sidecar storage)
  - Flashiibo 4-button navigation contract & UP+DOWN system exit chord
  - 60 Hz delay/sound timer countdown and delay-loop detection (is_in_delay_wait)
"""

import os
import struct
import random
import sys

# Ensure tools directory is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import feb_fonts

# Format Constants
FEB_MAGIC = 0x4245462E       # '.FEB' in little-endian ASCII
FEB_SAVE_MAGIC = 0x56415346  # 'FSAV' in little-endian ASCII
FEB_VERSION = 1
FEB_SAVE_VERSION = 1
FEB_TYPE_CHIP8 = 0

# Flashiibo 4-Button Virtual Key Codes
FEB_KEY_UP = 0x2
FEB_KEY_DOWN = 0x8
FEB_KEY_LEFT = 0x4    # BACK button
FEB_KEY_RIGHT = 0x6   # OK / CONFIRM button
FEB_KEY_BACK = FEB_KEY_LEFT
FEB_KEY_OK = FEB_KEY_RIGHT

# Hardware Polling Bitmask (FXB0 GETKEYS)
FEB_BTN_UP = (1 << 0)     # 0x01
FEB_BTN_DOWN = (1 << 1)   # 0x02
FEB_BTN_LEFT = (1 << 2)   # 0x04 (BACK)
FEB_BTN_RIGHT = (1 << 3)  # 0x08 (OK)
FEB_BTN_BACK = FEB_BTN_LEFT
FEB_BTN_OK = FEB_BTN_RIGHT

# Drawing Modes (FX98 DRAWMODE)
FEB_DRAW_MODE_XOR = 0
FEB_DRAW_MODE_SET = 1
FEB_DRAW_MODE_CLEAR = 2
FEB_DRAW_MODE_OPAQUE = 3
FEB_DRAW_MODE_INVERTED_OPAQUE = 4

# Standard CHIP-8 Font (16 characters, 5 bytes each, loaded at 0x0000)
CHIP8_FONT_5X8 = bytes([
    0xF0, 0x90, 0x90, 0x90, 0xF0,  # 0
    0x20, 0x60, 0x20, 0x20, 0x70,  # 1
    0xF0, 0x10, 0xF0, 0x80, 0xF0,  # 2
    0xF0, 0x10, 0xF0, 0x10, 0xF0,  # 3
    0x90, 0x90, 0xF0, 0x10, 0x10,  # 4
    0xF0, 0x80, 0xF0, 0x10, 0xF0,  # 5
    0xF0, 0x80, 0xF0, 0x90, 0xF0,  # 6
    0xF0, 0x10, 0x20, 0x40, 0x40,  # 7
    0xF0, 0x90, 0xF0, 0x90, 0xF0,  # 8
    0xF0, 0x90, 0xF0, 0x10, 0xF0,  # 9
    0xF0, 0x90, 0xF0, 0x90, 0x90,  # A
    0xE0, 0x90, 0xE0, 0x90, 0xE0,  # B
    0xF0, 0x80, 0x80, 0x80, 0xF0,  # C
    0xE0, 0x90, 0x90, 0x90, 0xE0,  # D
    0xF0, 0x80, 0xF0, 0x80, 0xF0,  # E
    0xF0, 0x80, 0xF0, 0x80, 0x80   # F
])

# Super-CHIP 16x10 Large Font (10 characters, 10 bytes each, loaded at 0x0050)
SCHIP_FONT_10X10 = bytes([
    0x3C, 0x7E, 0xE7, 0xC3, 0xC3, 0xC3, 0xC3, 0xE7, 0x7E, 0x3C,  # 0
    0x18, 0x38, 0x78, 0x18, 0x18, 0x18, 0x18, 0x18, 0x7E, 0x7E,  # 1
    0x7E, 0xFF, 0x83, 0x06, 0x0C, 0x18, 0x30, 0x60, 0xFF, 0xFF,  # 2
    0x7E, 0xFF, 0x83, 0x03, 0x3E, 0x03, 0x03, 0x83, 0xFF, 0x7E,  # 3
    0xC3, 0xC3, 0xC3, 0xC3, 0xFF, 0xFF, 0x03, 0x03, 0x03, 0x03,  # 4
    0xFF, 0xFF, 0xC0, 0xC0, 0xFE, 0x03, 0x03, 0x83, 0xFF, 0x7E,  # 5
    0x7E, 0xFF, 0xC0, 0xC0, 0xFE, 0xC3, 0xC3, 0xC3, 0xFF, 0x7E,  # 6
    0xFF, 0xFF, 0x03, 0x06, 0x0C, 0x18, 0x30, 0x60, 0x60, 0x60,  # 7
    0x7E, 0xFF, 0xC3, 0xC3, 0x7E, 0xC3, 0xC3, 0xC3, 0xFF, 0x7E,  # 8
    0x7E, 0xFF, 0xC3, 0xC3, 0x7F, 0x03, 0x03, 0x03, 0xFF, 0x7E   # 9
])


class FebVM:
    """Flashiibo Executable Binary (.feb) Virtual Machine."""

    def __init__(self):
        self.memory = bytearray(4096)
        self.v = bytearray(16)
        self.i = 0
        self.pc = 0x200
        self.stack = [0] * 16
        self.sp = 0
        self.delay_timer = 0
        self.sound_timer = 0
        self.display = bytearray(1024)  # 128x64 1-bit packed (16 bytes/row x 64 rows)
        self.keys = 0                   # CHIP-8 key bitmask (bits 0..15)
        self.schip_mode = False         # False = 64x32, True = 128x64
        self.draw_mode = 0              # 0=XOR, 1=SET, 2=CLEAR, 3=OPAQUE, 4=INV_OPAQUE
        self.rotation = 0               # 0=0 deg (128x64), 1=90 deg (64x128), 2=180 deg, 3=270 deg
        self.draw_flag = True
        self.waiting_for_key = False
        self.key_reg = 0
        self.exited = False
        self.rpl_flags = bytearray(16)
        self.flags_dirty = False

        # Input & timing tracking
        self.key_hold_frames = [0] * 16
        self.physical_buttons_down = 0
        self.fast_forward_until_key = False
        self.instructions_executed = 0

        # Application container metadata
        self.filepath = ""
        self.title = ""
        self.author = ""
        self.version = ""
        self.icon = None

        self.reset()

    def reset(self):
        """Resets the VM state while keeping loaded ROM in memory."""
        self.v = bytearray(16)
        self.i = 0
        self.pc = 0x200
        self.stack = [0] * 16
        self.sp = 0
        self.delay_timer = 0
        self.sound_timer = 0
        self.display = bytearray(1024)
        self.keys = 0
        self.schip_mode = False
        self.draw_mode = 0
        self.rotation = 0
        self.draw_flag = True
        self.waiting_for_key = False
        self.key_reg = 0
        self.exited = False
        self.key_hold_frames = [0] * 16
        self.physical_buttons_down = 0
        self.fast_forward_until_key = False

        # Load interpreter fonts
        self.memory[0x0000:0x0000 + len(CHIP8_FONT_5X8)] = CHIP8_FONT_5X8
        self.memory[0x0050:0x0050 + len(SCHIP_FONT_10X10)] = SCHIP_FONT_10X10

    def load_rom(self, rom_data):
        """Loads raw CHIP-8 bytecode starting at address 0x200."""
        self.reset()
        if len(rom_data) > (4096 - 0x200):
            raise ValueError(f"ROM payload size ({len(rom_data)}) exceeds available memory ({4096 - 0x200})")
        self.memory[0x200:0x200 + len(rom_data)] = rom_data
        return True

    def load_feb(self, filepath_or_data):
        """Loads a Flashiibo Executable Binary (.feb) file or bytes."""
        if isinstance(filepath_or_data, str):
            self.filepath = os.path.abspath(filepath_or_data)
            with open(self.filepath, "rb") as f:
                data = f.read()
        else:
            self.filepath = ""
            data = bytes(filepath_or_data)

        if len(data) < 96:
            raise ValueError("File too short to be a valid .feb binary (minimum 96 bytes)")

        magic, format_ver, app_type, flags, title_b, author_b, ver_b, icon, payload_sz, crc32 = struct.unpack(
            "<IBBH24s16s8s32sII", data[:96]
        )

        if magic != FEB_MAGIC:
            raise ValueError(f"Invalid FEB magic: 0x{magic:08X} (expected 0x{FEB_MAGIC:08X} '.FEB')")

        if app_type != FEB_TYPE_CHIP8:
            raise ValueError(f"Unsupported FEB app_type: {app_type} (expected {FEB_TYPE_CHIP8} CHIP-8)")

        self.title = title_b.split(b"\x00")[0].decode("utf-8", errors="replace")
        self.author = author_b.split(b"\x00")[0].decode("utf-8", errors="replace")
        self.version = ver_b.split(b"\x00")[0].decode("utf-8", errors="replace")
        self.icon = icon

        payload = data[96:96 + payload_sz] if payload_sz > 0 else data[96:]
        self.load_rom(payload)

        # Attempt to load companion .sav file
        if self.filepath:
            self.load_save_sidecar()

        return True

    def load_save_sidecar(self):
        """Loads RPL persistent flags from companion .sav file if present."""
        if not self.filepath:
            return False

        # Look in same directory or in /saves/ directory
        base_dir = os.path.dirname(self.filepath)
        stem = os.path.splitext(os.path.basename(self.filepath))[0]
        candidates = [
            os.path.join(base_dir, f"{stem}.sav"),
            os.path.join(base_dir, "saves", f"{stem}.sav"),
        ]

        for sav_path in candidates:
            if os.path.exists(sav_path):
                try:
                    with open(sav_path, "rb") as f:
                        sav_data = f.read()
                    if len(sav_data) >= 32:
                        magic, ver, flags, high_score, rpl, extra_len, _ = struct.unpack("<IHHI16sHH", sav_data[:32])
                        if magic == FEB_SAVE_MAGIC:
                            self.rpl_flags[:] = rpl
                            self.flags_dirty = False
                            return True
                except Exception:
                    pass
        return False

    def flush_save_sidecar(self):
        """Flushes modified RPL persistent flags to companion .sav file."""
        if not self.filepath or not self.flags_dirty:
            return False

        base_dir = os.path.dirname(self.filepath)
        stem = os.path.splitext(os.path.basename(self.filepath))[0]
        sav_path = os.path.join(base_dir, f"{stem}.sav")

        header = struct.pack(
            "<IHHI16sHH",
            FEB_SAVE_MAGIC,
            FEB_SAVE_VERSION,
            0,
            0,
            bytes(self.rpl_flags),
            0,
            0
        )
        try:
            with open(sav_path, "wb") as f:
                f.write(header)
            self.flags_dirty = False
            return True
        except Exception:
            return False

    def get_pixel(self, x, y):
        """Returns True if pixel at (x, y) is ON, False otherwise."""
        w = 128 if self.schip_mode else 64
        h = 64 if self.schip_mode else 32
        px, py = x, y

        if self.rotation == 1:
            if x < 0 or x >= h or y < 0 or y >= w:
                return False
            px = (w - 1) - y
            py = x
        elif self.rotation == 2:
            if x < 0 or x >= w or y < 0 or y >= h:
                return False
            px = (w - 1) - x
            py = (h - 1) - y
        elif self.rotation == 3:
            if x < 0 or x >= h or y < 0 or y >= w:
                return False
            px = y
            py = (h - 1) - x
        else:
            if x < 0 or x >= w or y < 0 or y >= h:
                return False

        row_bytes = 16 if self.schip_mode else 8
        byte_idx = py * row_bytes + (px // 8)
        bit_mask = 0x80 >> (px % 8)
        return (self.display[byte_idx] & bit_mask) != 0

    def draw_point(self, x, y, col_ref=None):
        """Plots a single pixel respecting the active draw mode and rotation."""
        w = 128 if self.schip_mode else 64
        h = 64 if self.schip_mode else 32
        px, py = x, y

        if self.rotation == 1:
            if x < 0 or x >= h or y < 0 or y >= w:
                return
            px = (w - 1) - y
            py = x
        elif self.rotation == 2:
            if x < 0 or x >= w or y < 0 or y >= h:
                return
            px = (w - 1) - x
            py = (h - 1) - y
        elif self.rotation == 3:
            if x < 0 or x >= h or y < 0 or y >= w:
                return
            px = y
            py = (h - 1) - x
        else:
            if x < 0 or x >= w or y < 0 or y >= h:
                return

        row_bytes = 16 if self.schip_mode else 8
        byte_idx = py * row_bytes + (px // 8)
        bit_mask = 0x80 >> (px % 8)
        current = (self.display[byte_idx] & bit_mask) != 0

        if self.draw_mode == 0:  # XOR
            if current and col_ref is not None:
                col_ref[0] = True
            self.display[byte_idx] ^= bit_mask
        elif self.draw_mode in (1, 3):  # SET / OPAQUE fg
            self.display[byte_idx] |= bit_mask
        elif self.draw_mode in (2, 4):  # CLEAR / INVERTED_OPAQUE fg
            self.display[byte_idx] &= ~bit_mask

    def draw_line(self, x1, y1, x2, y2, col_ref=None):
        """Bresenham line algorithm matching chip8.c draw_line."""
        dx = abs(x2 - x1)
        sx = 1 if x1 < x2 else -1
        dy = -abs(y2 - y1)
        sy = 1 if y1 < y2 else -1
        err = dx + dy

        while True:
            self.draw_point(x1, y1, col_ref)
            if x1 == x2 and y1 == y2:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x1 += sx
            if e2 <= dx:
                err += dx
                y1 += sy

    def draw_hline(self, x, y, length, col_ref=None):
        """Fast horizontal line."""
        if length <= 0:
            return
        for i in range(length):
            self.draw_point(x + i, y, col_ref)

    def draw_vline(self, x, y, length, col_ref=None):
        """Fast vertical line."""
        if length <= 0:
            return
        for i in range(length):
            self.draw_point(x, y + i, col_ref)

    def draw_rect(self, x, y, w, h, filled=False, col_ref=None):
        """Hollow or filled rectangle."""
        if w <= 0 or h <= 0:
            return
        if filled:
            for row in range(h):
                self.draw_hline(x, y + row, w, col_ref)
        else:
            self.draw_hline(x, y, w, col_ref)
            if h > 1:
                self.draw_hline(x, y + h - 1, w, col_ref)
            if h > 2:
                self.draw_vline(x, y + 1, h - 2, col_ref)
                if w > 1:
                    self.draw_vline(x + w - 1, y + 1, h - 2, col_ref)

    def draw_circle(self, cx, cy, r, filled=False, col_ref=None):
        """Midpoint circle algorithm matching chip8.c draw_circle."""
        if r < 0:
            return
        if r == 0:
            self.draw_point(cx, cy, col_ref)
            return

        x = 0
        y = r
        d = 3 - 2 * r

        while y >= x:
            if filled:
                self.draw_hline(cx - x, cy - y, 2 * x + 1, col_ref)
                self.draw_hline(cx - x, cy + y, 2 * x + 1, col_ref)
                self.draw_hline(cx - y, cy - x, 2 * y + 1, col_ref)
                self.draw_hline(cx - y, cy + x, 2 * y + 1, col_ref)
            else:
                self.draw_point(cx + x, cy + y, col_ref)
                self.draw_point(cx - x, cy + y, col_ref)
                self.draw_point(cx + x, cy - y, col_ref)
                self.draw_point(cx - x, cy - y, col_ref)
                self.draw_point(cx + y, cy + x, col_ref)
                self.draw_point(cx - y, cy + x, col_ref)
                self.draw_point(cx + y, cy - x, col_ref)
                self.draw_point(cx - y, cy - x, col_ref)
            x += 1
            if d > 0:
                y -= 1
                d = d + 4 * (x - y) + 10
            else:
                d = d + 4 * x + 6

    def draw_triangle(self, x0, y0, x1, y1, x2, y2, col_ref=None):
        """Draws hollow outline triangle connecting three vertices."""
        self.draw_line(x0, y0, x1, y1, col_ref)
        self.draw_line(x1, y1, x2, y2, col_ref)
        self.draw_line(x2, y2, x0, y0, col_ref)

    def draw_rrect(self, x, y, w, h, col_ref=None):
        """Draws unfilled outline rounded rectangle with 1px corner radius."""
        if w <= 0 or h <= 0:
            return
        if w <= 2 or h <= 2:
            self.draw_rect(x, y, w, h, filled=False, col_ref=col_ref)
            return
        self.draw_hline(x + 1, y, w - 2, col_ref)
        self.draw_hline(x + 1, y + h - 1, w - 2, col_ref)
        self.draw_vline(x, y + 1, h - 2, col_ref)
        self.draw_vline(x + w - 1, y + 1, h - 2, col_ref)

    def draw_fill_rrect(self, x, y, w, h, col_ref=None):
        """Draws solid filled rounded rectangle with 1px corner radius."""
        if w <= 0 or h <= 0:
            return
        if w <= 2 or h <= 2:
            self.draw_rect(x, y, w, h, filled=True, col_ref=col_ref)
            return
        self.draw_hline(x + 1, y, w - 2, col_ref)
        for row in range(1, h - 1):
            self.draw_hline(x, y + row, w, col_ref)
        self.draw_hline(x + 1, y + h - 1, w - 2, col_ref)

    def draw_single_char(self, x, y, ch, font_id, col_ref=None):
        """Renders single ASCII character using built-in u8g2 font matching chip8.c."""
        font, fh, fw = feb_fonts.get_font(font_id)
        enc = ord(ch) if isinstance(ch, str) else int(ch)
        gw = font.get_glyph_width(enc)
        w = gw if gw > 0 else fw

        if self.draw_mode == 3:  # OPAQUE: Clear background box
            orig_mode = self.draw_mode
            self.draw_mode = 2  # CLEAR
            self.draw_rect(x, y, w, fh, filled=True)
            self.draw_mode = orig_mode
        elif self.draw_mode == 4:  # INVERTED_OPAQUE: Fill background box
            orig_mode = self.draw_mode
            self.draw_mode = 1  # SET
            self.draw_rect(x, y, w, fh, filled=True)
            self.draw_mode = orig_mode

        adv, pixels = font.render_glyph(enc, x, y)
        if adv == 0:
            adv = w

        for px, py in pixels:
            self.draw_point(px, py, col_ref)

        return adv

    def draw_string(self, x, y, font_id, col_ref=None):
        """Renders null-terminated ASCII string at address I."""
        font, fh, fw = feb_fonts.get_font(font_id)
        cur_x = x
        cur_y = y
        ptr = self.i

        while ptr < 4096 and self.memory[ptr] != 0:
            ch = chr(self.memory[ptr])
            ptr += 1
            if ch == "\n":
                cur_x = x
                cur_y += fh
            else:
                adv = self.draw_single_char(cur_x, cur_y, ch, font_id, col_ref)
                cur_x += adv

        return max(0, min(255, cur_x))

    def measure_string(self, font_id):
        """Measures pixel advance width of null-terminated string at address I."""
        font, fh, fw = feb_fonts.get_font(font_id)
        ptr = self.i
        total_w = 0

        while ptr < 4096 and self.memory[ptr] != 0:
            ch = chr(self.memory[ptr])
            ptr += 1
            if ch == "\n":
                break
            gw = font.get_glyph_width(ord(ch))
            total_w += gw if gw > 0 else fw

        return min(255, total_w)

    def draw_number(self, x, y, font_id, col_ref=None):
        """Renders 16-bit unsigned integer in register I in decimal format."""
        num_str = str(self.i)
        cur_x = x
        for ch in num_str:
            adv = self.draw_single_char(cur_x, y, ch, font_id, col_ref)
            cur_x += adv
        return max(0, min(255, cur_x))

    def is_in_delay_wait(self):
        """
        Detects if VM is in a tight polling loop waiting for delay_timer == 0.
        Matches feb_runner_view.c is_in_delay_wait for authentic 60 Hz yield.
        """
        if self.delay_timer == 0:
            return False
        if self.pc >= 4096 - 5:
            return False

        op1 = (self.memory[self.pc] << 8) | self.memory[self.pc + 1]
        # Fx07 (LD Vx, DT)
        if (op1 & 0xF0FF) == 0xF007:
            x = (op1 >> 8) & 0x0F
            op2 = (self.memory[self.pc + 2] << 8) | self.memory[self.pc + 3]
            # Pattern 1: SE Vx, 0 (3x00) followed by JP loop (1nnn with nnn <= pc)
            if op2 == (0x3000 | (x << 8)):
                op3 = (self.memory[self.pc + 4] << 8) | self.memory[self.pc + 5]
                if (op3 & 0xF000) == 0x1000 and (op3 & 0x0FFF) <= self.pc:
                    return True
            # Pattern 2: SNE Vx, 0 (4x00) followed by JP exit, JP loop
            if op2 == (0x4000 | (x << 8)):
                op4 = (self.memory[self.pc + 6] << 8) | self.memory[self.pc + 7]
                if (op4 & 0xF000) == 0x1000 and (op4 & 0x0FFF) <= self.pc:
                    return True
        return False

    def timer_tick(self):
        """Ticks delay and sound timers at 60 Hz."""
        if self.delay_timer > 0:
            self.delay_timer -= 1
        if self.sound_timer > 0:
            self.sound_timer -= 1

    def press_key(self, key_code):
        """
        Registers a button press.
        Synchronously satisfies waiting_for_key and checks exit chord.
        """
        if key_code > 15:
            return

        if key_code == FEB_KEY_UP:
            self.physical_buttons_down |= FEB_BTN_UP
        elif key_code == FEB_KEY_DOWN:
            self.physical_buttons_down |= FEB_BTN_DOWN
        elif key_code == FEB_KEY_LEFT:
            self.physical_buttons_down |= FEB_BTN_LEFT
        elif key_code == FEB_KEY_RIGHT:
            self.physical_buttons_down |= FEB_BTN_RIGHT

        # Flashiibo Hardware Exit Chord: UP + DOWN
        if (self.physical_buttons_down & (FEB_BTN_UP | FEB_BTN_DOWN)) == (FEB_BTN_UP | FEB_BTN_DOWN):
            self.exited = True
            self.waiting_for_key = False
            return

        self.keys |= (1 << key_code)
        self.key_hold_frames[key_code] = 4  # Keep pressed for ~4 frames (~66ms)

        if self.waiting_for_key:
            self.v[self.key_reg] = key_code
            self.waiting_for_key = False
            self.keys = 0
            self.key_hold_frames = [0] * 16

            # Execute turn burst synchronously up to 10,000 instructions
            for _ in range(10000):
                if self.waiting_for_key or self.exited or self.is_in_delay_wait():
                    break
                self.step()

            self.fast_forward_until_key = (
                not self.waiting_for_key and not self.exited and self.delay_timer == 0
            )

    def release_key(self, key_code):
        """Registers button release."""
        if key_code > 15:
            return

        if key_code == FEB_KEY_UP:
            self.physical_buttons_down &= ~FEB_BTN_UP
        elif key_code == FEB_KEY_DOWN:
            self.physical_buttons_down &= ~FEB_BTN_DOWN
        elif key_code == FEB_KEY_LEFT:
            self.physical_buttons_down &= ~FEB_BTN_LEFT
        elif key_code == FEB_KEY_RIGHT:
            self.physical_buttons_down &= ~FEB_BTN_RIGHT

        if self.key_hold_frames[key_code] == 0:
            self.keys &= ~(1 << key_code)

    def step(self):
        """Executes a single CHIP-8 instruction."""
        if self.exited or self.waiting_for_key:
            return

        # Check UP + DOWN exit chord
        exit_chord = (1 << FEB_KEY_UP) | (1 << FEB_KEY_DOWN)
        if (self.keys & exit_chord) == exit_chord:
            self.exited = True
            return

        if self.pc >= 4095:
            self.exited = True
            return

        opcode = (self.memory[self.pc] << 8) | self.memory[self.pc + 1]
        self.pc += 2
        self.instructions_executed += 1

        op_prefix = opcode & 0xF000
        x = (opcode >> 8) & 0x0F
        y = (opcode >> 4) & 0x0F
        n = opcode & 0x0F
        kk = opcode & 0xFF
        nnn = opcode & 0xFFF

        if op_prefix == 0x0000:
            if opcode == 0x00E0:  # CLS
                self.display[:] = b"\x00" * 1024
                self.draw_flag = True
            elif opcode == 0x00EE:  # RET
                if self.sp > 0:
                    self.sp -= 1
                    self.pc = self.stack[self.sp]
            elif (opcode & 0xFFF0) == 0x00C0:  # SCHIP 00Cn: Scroll down n lines
                lines = n
                row_bytes = 16 if self.schip_mode else 8
                max_h = 64 if self.schip_mode else 32
                if lines > max_h:
                    lines = max_h
                shift_bytes = lines * row_bytes
                total_bytes = max_h * row_bytes
                self.display[shift_bytes:total_bytes] = self.display[0:total_bytes - shift_bytes]
                self.display[0:shift_bytes] = b"\x00" * shift_bytes
                self.draw_flag = True
            elif opcode == 0x00FB:  # SCHIP 00FB: Scroll right 4 pixels
                row_bytes = 16 if self.schip_mode else 8
                max_h = 64 if self.schip_mode else 32
                for r in range(max_h):
                    start = r * row_bytes
                    row_data = bytearray(self.display[start:start + row_bytes])
                    # Shift entire byte array right by 4 bits
                    carry = 0
                    for b in range(row_bytes):
                        new_carry = (row_data[b] & 0x0F) << 4
                        row_data[b] = (row_data[b] >> 4) | carry
                        carry = new_carry
                    self.display[start:start + row_bytes] = row_data
                self.draw_flag = True
            elif opcode == 0x00FC:  # SCHIP 00FC: Scroll left 4 pixels
                row_bytes = 16 if self.schip_mode else 8
                max_h = 64 if self.schip_mode else 32
                for r in range(max_h):
                    start = r * row_bytes
                    row_data = bytearray(self.display[start:start + row_bytes])
                    # Shift entire byte array left by 4 bits
                    carry = 0
                    for b in range(row_bytes - 1, -1, -1):
                        new_carry = (row_data[b] & 0xF0) >> 4
                        row_data[b] = ((row_data[b] << 4) & 0xFF) | carry
                        carry = new_carry
                    self.display[start:start + row_bytes] = row_data
                self.draw_flag = True
            elif opcode == 0x00FD:  # SCHIP 00FD: EXIT
                self.exited = True
            elif opcode == 0x00FE:  # SCHIP 00FE: Low resolution (64x32)
                self.schip_mode = False
                self.display[:] = b"\x00" * 1024
                self.draw_flag = True
            elif opcode == 0x00FF:  # SCHIP 00FF: High resolution (128x64)
                self.schip_mode = True
                self.display[:] = b"\x00" * 1024
                self.draw_flag = True

        elif op_prefix == 0x1000:  # JP addr
            self.pc = nnn

        elif op_prefix == 0x2000:  # CALL addr
            if self.sp < 16:
                self.stack[self.sp] = self.pc
                self.sp += 1
                self.pc = nnn

        elif op_prefix == 0x3000:  # SE Vx, byte
            if self.v[x] == kk:
                self.pc += 2

        elif op_prefix == 0x4000:  # SNE Vx, byte
            if self.v[x] != kk:
                self.pc += 2

        elif op_prefix == 0x5000:  # SE Vx, Vy
            if n == 0 and self.v[x] == self.v[y]:
                self.pc += 2

        elif op_prefix == 0x6000:  # LD Vx, byte
            self.v[x] = kk

        elif op_prefix == 0x7000:  # ADD Vx, byte
            self.v[x] = (self.v[x] + kk) & 0xFF

        elif op_prefix == 0x8000:
            if n == 0x0:
                self.v[x] = self.v[y]
            elif n == 0x1:
                self.v[x] |= self.v[y]
                self.v[0xF] = 0
            elif n == 0x2:
                self.v[x] &= self.v[y]
                self.v[0xF] = 0
            elif n == 0x3:
                self.v[x] ^= self.v[y]
                self.v[0xF] = 0
            elif n == 0x4:
                s = self.v[x] + self.v[y]
                self.v[x] = s & 0xFF
                self.v[0xF] = 1 if s > 255 else 0
            elif n == 0x5:
                flag = 1 if self.v[x] >= self.v[y] else 0
                self.v[x] = (self.v[x] - self.v[y]) & 0xFF
                self.v[0xF] = flag
            elif n == 0x6:
                val = self.v[x] if self.schip_mode else self.v[y]
                flag = val & 0x01
                self.v[x] = (val >> 1) & 0xFF
                self.v[0xF] = flag
            elif n == 0x7:
                flag = 1 if self.v[y] >= self.v[x] else 0
                self.v[x] = (self.v[y] - self.v[x]) & 0xFF
                self.v[0xF] = flag
            elif n == 0xE:
                val = self.v[x] if self.schip_mode else self.v[y]
                flag = (val >> 7) & 0x01
                self.v[x] = (val << 1) & 0xFF
                self.v[0xF] = flag

        elif op_prefix == 0x9000:  # SNE Vx, Vy
            if n == 0 and self.v[x] != self.v[y]:
                self.pc += 2

        elif op_prefix == 0xA000:  # LD I, addr
            self.i = nnn

        elif op_prefix == 0xB000:  # JP V0, addr
            self.pc = (nnn + self.v[0]) & 0xFFF

        elif op_prefix == 0xC000:  # RND Vx, byte
            self.v[x] = random.randint(0, 255) & kk

        elif op_prefix == 0xD000:  # DRW Vx, Vy, nibble
            vx = self.v[x]
            vy = self.v[y]
            width = 128 if self.schip_mode else 64
            height = 64 if self.schip_mode else 32
            collision = False

            if n == 0:  # 16x16 sprite in SCHIP / modern mode
                for row in range(16):
                    if self.i + row * 2 + 1 >= 4096:
                        break
                    sprite_word = (self.memory[self.i + row * 2] << 8) | self.memory[self.i + row * 2 + 1]
                    for col in range(16):
                        if sprite_word & (0x8000 >> col):
                            px = (vx + col) % width
                            py = (vy + row) % height
                            row_bytes = 16 if self.schip_mode else 8
                            byte_idx = py * row_bytes + (px // 8)
                            bit_mask = 0x80 >> (px % 8)
                            if self.display[byte_idx] & bit_mask:
                                collision = True
                            self.display[byte_idx] ^= bit_mask
            else:  # Standard 8xN sprite
                for row in range(n):
                    if self.i + row >= 4096:
                        break
                    sprite_byte = self.memory[self.i + row]
                    for col in range(8):
                        if sprite_byte & (0x80 >> col):
                            px = (vx + col) % width
                            py = (vy + row) % height
                            row_bytes = 16 if self.schip_mode else 8
                            byte_idx = py * row_bytes + (px // 8)
                            bit_mask = 0x80 >> (px % 8)
                            if self.display[byte_idx] & bit_mask:
                                collision = True
                            self.display[byte_idx] ^= bit_mask

            self.v[0xF] = 1 if collision else 0
            self.draw_flag = True

        elif op_prefix == 0xE000:
            if kk == 0x9E:  # SKP Vx
                if self.keys & (1 << (self.v[x] & 0x0F)):
                    self.pc += 2
            elif kk == 0xA1:  # SKNP Vx
                if not (self.keys & (1 << (self.v[x] & 0x0F))):
                    self.pc += 2

        elif op_prefix == 0xF000:
            if kk == 0x07:  # LD Vx, DT
                self.v[x] = self.delay_timer
            elif kk == 0x0A:  # LD Vx, K
                self.waiting_for_key = True
                self.key_reg = x
            elif kk == 0x15:  # LD DT, Vx
                self.delay_timer = self.v[x]
            elif kk == 0x18:  # LD ST, Vx
                self.sound_timer = self.v[x]
            elif kk == 0x1E:  # ADD I, Vx
                self.i = (self.i + self.v[x]) & 0xFFF
            elif kk == 0x29:  # LD F, Vx
                self.i = (self.v[x] & 0x0F) * 5
            elif kk == 0x30:  # LD HF, Vx
                self.i = 0x050 + (self.v[x] & 0x0F) * 10
            elif kk == 0x33:  # LD B, Vx (BCD)
                self.memory[self.i] = self.v[x] // 100
                self.memory[self.i + 1] = (self.v[x] // 10) % 10
                self.memory[self.i + 2] = self.v[x] % 10
            elif kk == 0x55:  # LD [I], Vx
                for j in range(x + 1):
                    self.memory[self.i + j] = self.v[j]
                self.i += x + 1
            elif kk == 0x65:  # LD Vx, [I]
                for j in range(x + 1):
                    self.v[j] = self.memory[self.i + j]
                self.i += x + 1
            elif kk == 0x75:  # FX75: LD R, Vx (Store into RPL flags)
                for j in range(min(x + 1, 16)):
                    self.rpl_flags[j] = self.v[j]
                self.flags_dirty = True
            elif kk == 0x85:  # FX85: LD Vx, R (Read RPL flags)
                for j in range(min(x + 1, 16)):
                    self.v[j] = self.rpl_flags[j]

            # Custom Flashiibo Vector Geometry Extensions (FX90..FX99)
            elif kk == 0x90:  # PIXEL Vx
                col = [False]
                self.draw_point(self.v[x], self.v[(x + 1) & 0xF], col)
                self.v[0xF] = 1 if col[0] else 0
                self.draw_flag = True
            elif kk == 0x91:  # LINE Vx
                col = [False]
                self.draw_line(
                    self.v[x], self.v[(x + 1) & 0xF],
                    self.v[(x + 2) & 0xF], self.v[(x + 3) & 0xF],
                    col
                )
                self.v[0xF] = 1 if col[0] else 0
                self.draw_flag = True
            elif kk == 0x92:  # HLINE Vx
                col = [False]
                self.draw_hline(self.v[x], self.v[(x + 1) & 0xF], self.v[(x + 2) & 0xF], col)
                self.v[0xF] = 1 if col[0] else 0
                self.draw_flag = True
            elif kk == 0x93:  # VLINE Vx
                col = [False]
                self.draw_vline(self.v[x], self.v[(x + 1) & 0xF], self.v[(x + 2) & 0xF], col)
                self.v[0xF] = 1 if col[0] else 0
                self.draw_flag = True
            elif kk == 0x94:  # RECT Vx
                col = [False]
                self.draw_rect(
                    self.v[x], self.v[(x + 1) & 0xF],
                    self.v[(x + 2) & 0xF], self.v[(x + 3) & 0xF],
                    filled=False, col_ref=col
                )
                self.v[0xF] = 1 if col[0] else 0
                self.draw_flag = True
            elif kk == 0x95:  # FILLRECT Vx
                col = [False]
                self.draw_rect(
                    self.v[x], self.v[(x + 1) & 0xF],
                    self.v[(x + 2) & 0xF], self.v[(x + 3) & 0xF],
                    filled=True, col_ref=col
                )
                self.v[0xF] = 1 if col[0] else 0
                self.draw_flag = True
            elif kk == 0x96:  # CIRCLE Vx
                col = [False]
                self.draw_circle(self.v[x], self.v[(x + 1) & 0xF], self.v[(x + 2) & 0xF], filled=False, col_ref=col)
                self.v[0xF] = 1 if col[0] else 0
                self.draw_flag = True
            elif kk == 0x97:  # DISC Vx
                col = [False]
                self.draw_circle(self.v[x], self.v[(x + 1) & 0xF], self.v[(x + 2) & 0xF], filled=True, col_ref=col)
                self.v[0xF] = 1 if col[0] else 0
                self.draw_flag = True
            elif kk == 0x98:  # DRAWMODE Vx
                self.draw_mode = self.v[x] % 5
            elif kk == 0x99:  # TESTPIXEL Vx
                self.v[0xF] = 1 if self.get_pixel(self.v[x], self.v[(x + 1) & 0xF]) else 0
            elif kk == 0x9A:  # ROTATE Vx
                self.rotation = self.v[x] & 0x03
            elif kk == 0x9B:  # TRIANGLE Vx (Vx..V(x+5))
                col = [False]
                self.draw_triangle(
                    self.v[x], self.v[(x + 1) & 0xF],
                    self.v[(x + 2) & 0xF], self.v[(x + 3) & 0xF],
                    self.v[(x + 4) & 0xF], self.v[(x + 5) & 0xF],
                    col
                )
                self.v[0xF] = 1 if col[0] else 0
                self.draw_flag = True
            elif kk == 0x9C:  # RRECT Vx (Vx..V(x+3))
                col = [False]
                self.draw_rrect(
                    self.v[x], self.v[(x + 1) & 0xF],
                    self.v[(x + 2) & 0xF], self.v[(x + 3) & 0xF],
                    col
                )
                self.v[0xF] = 1 if col[0] else 0
                self.draw_flag = True
            elif kk == 0x9D:  # FILLRRECT Vx (Vx..V(x+3))
                col = [False]
                self.draw_fill_rrect(
                    self.v[x], self.v[(x + 1) & 0xF],
                    self.v[(x + 2) & 0xF], self.v[(x + 3) & 0xF],
                    col
                )
                self.v[0xF] = 1 if col[0] else 0
                self.draw_flag = True

            # Custom Flashiibo Typography Extensions (FXA0..FXA3)
            elif kk == 0xA0:  # TEXT Vx
                col = [False]
                final_x = self.draw_string(self.v[x], self.v[(x + 1) & 0xF], self.v[(x + 2) & 0xF], col)
                self.v[x] = final_x
                if x != 0xF:
                    self.v[0xF] = 1 if col[0] else 0
                self.draw_flag = True
            elif kk == 0xA1:  # CHAR Vx
                col = [False]
                adv = self.draw_single_char(
                    self.v[x], self.v[(x + 1) & 0xF],
                    self.v[(x + 3) & 0xF], self.v[(x + 2) & 0xF],
                    col
                )
                self.v[0xF] = 1 if col[0] else 0
                self.draw_flag = True
            elif kk == 0xA2:  # TEXTLEN Vx
                self.v[x] = self.measure_string(self.v[x])
            elif kk == 0xA3:  # NUM Vx
                col = [False]
                final_x = self.draw_number(self.v[x], self.v[(x + 1) & 0xF], self.v[(x + 2) & 0xF], col)
                self.v[x] = final_x
                if x != 0xF:
                    self.v[0xF] = 1 if col[0] else 0
                self.draw_flag = True

            # Custom Flashiibo Deterministic Button Polling (FXB0)
            elif kk == 0xB0:  # GETKEYS Vx
                btn_mask = 0
                if self.keys & (1 << FEB_KEY_UP):
                    btn_mask |= FEB_BTN_UP
                if self.keys & (1 << FEB_KEY_DOWN):
                    btn_mask |= FEB_BTN_DOWN
                if self.keys & (1 << FEB_KEY_LEFT):
                    btn_mask |= FEB_BTN_LEFT
                if self.keys & (1 << FEB_KEY_RIGHT):
                    btn_mask |= FEB_BTN_RIGHT
                self.v[x] = btn_mask

    def step_frame(self, max_steps=10000):
        """
        Executes one 60 Hz frame matching feb_runner_view.c timer handler.
        Ticks timers, decrements key hold frames, and executes CPU step budget.
        """
        if self.exited:
            return

        # 1. 60 Hz timer ticks
        self.timer_tick()

        # 2. Key hold frames decay
        for k in range(16):
            if self.key_hold_frames[k] > 0:
                self.key_hold_frames[k] -= 1
                if self.key_hold_frames[k] == 0:
                    phys_mask = 0
                    if k == FEB_KEY_UP:
                        phys_mask = FEB_BTN_UP
                    elif k == FEB_KEY_DOWN:
                        phys_mask = FEB_BTN_DOWN
                    elif k == FEB_KEY_LEFT:
                        phys_mask = FEB_BTN_LEFT
                    elif k == FEB_KEY_RIGHT:
                        phys_mask = FEB_BTN_RIGHT
                    if not (self.physical_buttons_down & phys_mask):
                        self.keys &= ~(1 << k)

        # 3. CPU step budget
        if not self.waiting_for_key:
            steps = 5000 if self.fast_forward_until_key else max_steps
            for _ in range(steps):
                if self.waiting_for_key or self.exited:
                    break
                if self.is_in_delay_wait():
                    break
                self.step()

            if self.waiting_for_key or self.exited or self.delay_timer > 0:
                self.fast_forward_until_key = False
