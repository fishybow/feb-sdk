#!/usr/bin/env python3
"""
feb_fonts.py - U8G2 Font Decoder for Flashiibo FEB Simulator

Decodes built-in u8g2 bitmap fonts matching firmware-52832:
  - Font 0: u8g2_font_4x6_tr (4x6 compact numeric & ASCII)
  - Font 1: u8g2_font_siji_t_6x10 (6x10 standard UI)
  - Font 2: u8g2_font_likeminecraft_te (8x8 retro arcade)
"""

import base64

FONT_4X6_B64 = "XwACAgMDAgQEBAYA/wX/Bf8A6QHTArYgBYDNACEG6cisACIGk8skFSMKrMikNFQaKgEkCbPHpaFHSgAlCKvIZNRGASYJrMjFFKuYAicF0csIKAfyx6lmACkIssfEVCkAKgeryKRqNSsIq8jFtGICLAaSxykALQWLygwuBcnIBC8Hq8hWZQQwCKvIVUNVADEHq8glWQ0yB6vINVMaMwiryMyUFwA0CKvIJDViATUIq8iMqBcANgeryE3VAjcIq8jMVEYAOAeryK3WAjkHq8i15AI6BuHIxAA7B6rHZagAPAeryKa6AD0Gm8nsAT4Hq8jkqgQ/CKvI6JRhAkAGq8gtW0EIq8hVQ6kAQgiryKi00gJDCKvIVTJVAEQIq8ioZC0ARQiryIyo4gBGCKvIjKhiBEcIq8jNpJIASAiryCQ1lApJB6vIrFgNSgeryJaqAksIq8gktZIKTAeryMTmAE0Iq8ikMZQKTgiryKqhJABPB6vIVVYFUAiryKi0YgRRB7PHVVYdUgiryKi0kgpTB6vI7bwAVAeryKzYAlUHq8gk1whWCKvIJGukBFcIq8gkNYYKWAiryCTVUgFZCKvIJFVWAFoHq8jMVA5bBurIrEpcB6vIxFwGXQaqyKhqXgWTyzVfBYvHDGAG0svEAGEHo8gtlQRiCKvIRJXUAmMGo8jNLGQIq8impZIAZQajyFVTZgiryKa0YgJnCKvHrSQXAGgIq8hElawAaQiryGUk0wBqCLPHZlguAGsIq8jEtJIKbAeryMjWAG0Io8ikoVQAbgejyKhkBW8Ho8hVqgJwCKvHqLRiBHEIq8ctlWQAcgijyKQVIwBzB6PIjbwAdAiryKUVcwB1B6PIJCsJdgejyCSrAncIo8gkNVQAeAejyKQyFXkIq8ckleQCegejyMyUBnsIs8emJOsAfAbpyAwBfQmzx+SoYooAfgeUyyWVAAAAAAT//wAA"
FONT_SIJI_B64 = "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"
FONT_MINECRAFT_B64 = "agADAgMEAQQFBwkA/gf+BwABNAJrA+ogBYA4ASEHuSgxKAEiB5NNkSgBIxG/iJWESTQMURINQ5SESQQkDL1olQ1KtiWDFgElC71oIS1hVkwmASYMvnijRW1alGjREicFkS0hKAm8WKVEWTEUKQm8WCHWSokEKgabTJF0KwqtaRVGgxRGACwGkjejAC0GjWsxCC4FiSgRLwq9aJmFWTELATAMvWizZNKSTFqyADEJvWiViZ0GATILvWizZGEkZeEgMwu9aLNkYaRqyQI0Cr1oJyUlbRgLNQu9aHEMh1RLFgA2DL1os2TikGRasgA3Cb1ocQuzYgk4DL1os2RasmRasgA5DL1os2RaMoRasgA6BqkpkQU7CLo3k0MKADwHq0mV1Ao9CJ1qMaiDAD4Iq0mRVUoAPwu9aLNkYVaHIgBADr+IMyippCgVadAHBUENv4iXJmGSlQYlVQNCDb1oMSSZNiiZNigAQwq9aLNkYluyAEQKvWgxJJm3QQFFC71ocQyHJAwHAUYKvWhxDIckLAJHC71os2RitGnJAkgKvWiR2YYhswVJCLtIsURdBkoJvWg1NmrJAksMvWiRSUlJS6JKFkwIvWgR9jgITQq9aJEtS6K5BU4LvWiRTUoibbYATwm9aLNk3pIFUAu9aDEkmTYoYRFRCb1os2SeIiVSC71oMSSZNiiZLVMLvWizZOqqJQsAVAm9aDFIYU8AVQm9aJH5liwAVgy9aJHZklISJVkEVwm9aJF5SW4BWAu9aJFpSa1S0wJZCr1okSW1sBMAWgm9aDGIWcdBWwi7SDFEnQZcCb1okYZpMQ1dCLtIMXUaAl4InWyVJbUAXwaNaDEIYAaSPREFYQqtaLMmg5YMAWILvWgRFock0wYFYwqtaLNkYpYsAGQKvWjZMmhaMgRlCq1os2TDkA4BZgm8WKVEU9YEZwy9ZjNoWjKEWrIAaAm8WJHVlsgUaQe5KJEMAmoKxFeXZzUpUQBrC7xYkZWUREpKAWwHujiR9BRtCq1oobQoiaYFbgmtaDEkmVsAbwmtaLNktmQBcAu1ZzEkmTYoYQhxCrVnM2haMoQFcgmtaJGYxCIAcwmsWDOE4pAAdAm7SJMsUVsAdQmtaJG5JUMAdgutaJFpSSnJIgB3Ca1okVkSpUV4Ca1okSW1Si15C7VnkdmSIRwUAHoJrWgxaG2DAHsJvFizZJFWG3wGuShxCH0KvFix1aQsWQB+CJ+KI0ZFBaAFgDgBoQe5J5EMAqILvFiVDEovQ5QAowu+eKVFyZjWhgWkC61pkSVTEi1ZAKUNvWiRJbVokKJBigCmBrkosQynDb1os2RDlmRDliwAqAaLTpEEqQ+/iDMoqaQomaSoyaAAAAAABP//IKwNvng1ZYMWDllpAQAA"

class BitStream:
    """Reads bit-packed u8g2 glyph data streams."""
    def __init__(self, data, ptr):
        self.data = data
        self.ptr = ptr
        self.bit_pos = 0

    def get_unsigned_bits(self, cnt):
        if cnt == 0:
            return 0
        val = self.data[self.ptr] >> self.bit_pos
        bit_pos_plus_cnt = self.bit_pos + cnt
        if bit_pos_plus_cnt >= 8:
            s = 8 - self.bit_pos
            self.ptr += 1
            if self.ptr < len(self.data):
                val |= (self.data[self.ptr] << s)
            bit_pos_plus_cnt -= 8
        val &= (1 << cnt) - 1
        self.bit_pos = bit_pos_plus_cnt
        return val

    def get_signed_bits(self, cnt):
        v = self.get_unsigned_bits(cnt)
        return v - (1 << (cnt - 1))

class U8G2Font:
    """Parser and decoder for a single U8G2 font structure."""
    def __init__(self, raw_bytes, default_h, default_w):
        self.data = raw_bytes
        self.default_h = default_h
        self.default_w = default_w

        # Header fields
        self.glyph_cnt = self.data[0]
        self.bbx_mode = self.data[1]
        self.bits_per_0 = self.data[2]
        self.bits_per_1 = self.data[3]
        self.bits_per_char_width = self.data[4]
        self.bits_per_char_height = self.data[5]
        self.bits_per_char_x = self.data[6]
        self.bits_per_char_y = self.data[7]
        self.bits_per_delta_x = self.data[8]
        self.max_char_width = self.data[9]
        self.max_char_height = self.data[10]
        self.x_offset = self.data[11]
        self.y_offset = self.data[12]
        self.ascent_A = self.data[13]
        self.descent_g = self.data[14]
        self.start_pos_upper_A = (self.data[17] << 8) | self.data[18]
        self.start_pos_lower_a = (self.data[19] << 8) | self.data[20]

        # Cache glyph pointers and widths for fast lookup
        self._glyph_cache = {}
        self._build_cache()

    def _build_cache(self):
        ptr = 23
        while ptr < len(self.data):
            size = self.data[ptr + 1]
            if size == 0:
                break
            enc = self.data[ptr]
            glyph_ptr = ptr + 2

            # Decode glyph header info
            bs = BitStream(self.data, glyph_ptr)
            gw = bs.get_unsigned_bits(self.bits_per_char_width)
            gh = bs.get_unsigned_bits(self.bits_per_char_height)
            cx = bs.get_signed_bits(self.bits_per_char_x)
            cy = bs.get_signed_bits(self.bits_per_char_y)
            dx = bs.get_signed_bits(self.bits_per_delta_x)

            self._glyph_cache[enc] = (glyph_ptr, gw, gh, cx, cy, dx)
            ptr += size

    def get_glyph_width(self, encoding):
        if encoding in self._glyph_cache:
            return self._glyph_cache[encoding][5]
        return 0

    def render_glyph(self, encoding, target_x=0, target_y=0):
        """
        Decodes and renders glyph to a list of (x, y) relative pixel coordinates.
        Returns (advance_x, pixel_list).
        """
        if encoding not in self._glyph_cache:
            return 0, []

        glyph_ptr, gw, gh, cx, cy, dx = self._glyph_cache[encoding]
        if gw == 0:
            return dx, []

        # U8G2 Top Position vertical reference: vref = ascent_A + 1
        vref = self.ascent_A + 1
        gx = target_x + cx
        gy = target_y + vref - (gh + cy)

        # Read bit stream starting after the 5 header values
        stream = BitStream(self.data, glyph_ptr)
        stream.get_unsigned_bits(self.bits_per_char_width)
        stream.get_unsigned_bits(self.bits_per_char_height)
        stream.get_signed_bits(self.bits_per_char_x)
        stream.get_signed_bits(self.bits_per_char_y)
        stream.get_signed_bits(self.bits_per_delta_x)

        pixels = []
        lx = 0
        ly = 0

        def decode_len(length, is_fg):
            nonlocal lx, ly
            cnt = length
            while True:
                rem = gw - lx
                current = cnt if cnt < rem else rem
                if is_fg:
                    for i in range(current):
                        pixels.append((gx + lx + i, gy + ly))
                if cnt < rem:
                    break
                cnt -= rem
                lx = 0
                ly += 1
            lx += cnt

        while True:
            a = stream.get_unsigned_bits(self.bits_per_0)
            b = stream.get_unsigned_bits(self.bits_per_1)
            while True:
                decode_len(a, False)
                decode_len(b, True)
                if stream.get_unsigned_bits(1) == 0:
                    break
            if ly >= gh:
                break

        return dx, pixels

# Singleton font instances
FONT_4X6 = U8G2Font(base64.b64decode(FONT_4X6_B64), 6, 4)
FONT_SIJI = U8G2Font(base64.b64decode(FONT_SIJI_B64), 10, 6)
FONT_MINECRAFT = U8G2Font(base64.b64decode(FONT_MINECRAFT_B64), 8, 8)

def get_font(font_id):
    """Returns (font_instance, font_height, font_width) for font_id (0..2)."""
    if font_id == 0:
        return FONT_4X6, 6, 4
    elif font_id == 1:
        return FONT_SIJI, 10, 6
    else:
        return FONT_MINECRAFT, 8, 8
