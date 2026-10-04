#!/usr/bin/env python3
"""
test_tooling.py - Automated Verification Suite for FEB Tooling & SDK
"""

import unittest
import os
import sys
import tempfile
import struct

# Add repo tools and include to path
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS_DIR = os.path.join(REPO_ROOT, "tools")
sys.path.insert(0, TOOLS_DIR)

import assemble_chip8
import make_feb
import feb_build
import make_icon

class TestAssembleChip8(unittest.TestCase):
    def test_assemble_simple_instruction(self):
        asm = """
        START:
            cls
            ret
        """
        code = assemble_chip8.assemble(asm)
        self.assertEqual(code, bytes([0x00, 0xE0, 0x00, 0xEE]))

    def test_assemble_template_demo(self):
        asm = feb_build.generate_template_asm()
        code = assemble_chip8.assemble(asm)
        self.assertGreater(len(code), 50)
        self.assertEqual(len(code), 78)

    def test_assemble_schip_instructions(self):
        asm = """
        START:
            high
            low
            bighex v5
            saveflags v3
            loadflags v7
        """
        code = assemble_chip8.assemble(asm)
        self.assertEqual(code, bytes([0x00, 0xFF, 0x00, 0xFE, 0xF5, 0x30, 0xF3, 0x75, 0xF7, 0x85]))

class TestMakeFeb(unittest.TestCase):
    def test_header_structure_and_magic(self):
        payload = bytes([0x00, 0xE0, 0x00, 0xEE])
        feb_data = make_feb.create_feb(
            app_type=make_feb.FEB_TYPE_CHIP8,
            title="Test App",
            author="Dev",
            version="1.0.0",
            payload=payload
        )
        self.assertEqual(len(feb_data), 96 + len(payload))

        # Check magic (.FEB in LE: 0x4245462E)
        magic, ver, app_type, flags = struct.unpack_from("<IBBH", feb_data, 0)
        self.assertEqual(magic, make_feb.FEB_MAGIC)
        self.assertEqual(ver, 1)
        self.assertEqual(app_type, make_feb.FEB_TYPE_CHIP8)
        self.assertEqual(flags, make_feb.FEB_FLAG_NONE)

        # Check title and payload size
        title = feb_data[8:32].split(b'\x00')[0].decode('utf-8')
        self.assertEqual(title, "Test App")

        payload_size, crc32 = struct.unpack_from("<II", feb_data, 88)
        self.assertEqual(payload_size, len(payload))
        self.assertEqual(crc32, 0)

    def test_create_save_container(self):
        save_data = make_feb.create_save(
            high_score=2048,
            rpl_flags=bytes([1, 2, 3, 4]),
            extra_data=b"EXTRA"
        )
        self.assertEqual(len(save_data), 32 + 5)
        magic, ver, flags, score, rpl, extra_len, res = struct.unpack_from("<IHHI16sHH", save_data, 0)
        self.assertEqual(magic, make_feb.FEB_SAVE_MAGIC)
        self.assertEqual(ver, 1)
        self.assertEqual(score, 2048)
        self.assertTrue(flags & make_feb.FEB_SAVE_FLAG_HIGH_SCORE)
        self.assertEqual(rpl[:4], bytes([1, 2, 3, 4]))
        self.assertEqual(extra_len, 5)

class TestFebBuild(unittest.TestCase):
    def test_build_2048_c(self):
        c_path = os.path.join(REPO_ROOT, "examples", "2048", "main.c")
        with tempfile.NamedTemporaryFile(suffix=".feb", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            asm_code = feb_build.compile_c_to_asm(c_path)
            bytecode = assemble_chip8.assemble(asm_code)
            feb_data = make_feb.create_feb(
                app_type=make_feb.FEB_TYPE_CHIP8,
                title="2048",
                author="Flashiibo",
                version="1.0.0",
                payload=bytecode
            )
            self.assertEqual(len(feb_data), 96 + 540)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_build_template_c(self):
        c_path = os.path.join(REPO_ROOT, "examples", "template", "main.c")
        asm_code = feb_build.compile_c_to_asm(c_path)
        bytecode = assemble_chip8.assemble(asm_code)
        self.assertEqual(len(bytecode), 78)

    def test_build_button_test_c(self):
        c_path = os.path.join(REPO_ROOT, "examples", "button_test", "main.c")
        asm_code = feb_build.compile_c_to_asm(c_path)
        bytecode = assemble_chip8.assemble(asm_code)
        self.assertEqual(len(bytecode), 112)

    def test_build_auto_detected_icon(self):
        # Verify feb_build automatically discovers icon.txt in examples/2048/
        c_path = os.path.join(REPO_ROOT, "examples", "2048", "main.c")
        with tempfile.NamedTemporaryFile(suffix=".feb", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            cmd = [
                sys.executable,
                os.path.join(TOOLS_DIR, "feb_build.py"),
                c_path,
                "-o", tmp_path,
                "--title", "2048",
                "--author", "Test",
                "--ver", "1.0.0"
            ]
            import subprocess
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            self.assertEqual(res.returncode, 0)
            self.assertIn("Auto-detected app icon", res.stdout)
            self.assertIn("custom icon: 32B", res.stdout)

            # Check that the icon in the container matches icon.txt
            with open(tmp_path, "rb") as f:
                feb_bytes = f.read()
            icon_in_feb = feb_bytes[56:88]
            expected_icon = make_icon.load_icon(os.path.join(REPO_ROOT, "examples", "2048", "icon.txt"))
            self.assertEqual(icon_in_feb, expected_icon)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)


class TestMakeIcon(unittest.TestCase):
    def test_bytes_to_grid_and_back(self):
        original = make_feb.ICON_2048_16x16
        grid = make_icon.bytes_to_grid(original)
        self.assertEqual(len(grid), 16)
        for row in grid:
            self.assertEqual(len(row), 16)
        repacked = make_icon.grid_to_bytes(grid)
        self.assertEqual(repacked, original)

    def test_ascii_parse_and_render(self):
        ascii_text = make_icon.render_ascii(make_feb.ICON_2048_16x16)
        self.assertEqual(len(ascii_text.splitlines()), 16)
        parsed_bytes = make_icon.load_from_ascii(ascii_text)
        self.assertEqual(parsed_bytes, make_feb.ICON_2048_16x16)

    def test_text_glyph_generation(self):
        # 1 letter: 2x scaled
        icon_f = make_icon.render_text_glyph("F")
        self.assertEqual(len(icon_f), 32)

        # 2 characters with border
        icon_20 = make_icon.render_text_glyph("20", border=True)
        self.assertEqual(len(icon_20), 32)
        grid_20 = make_icon.bytes_to_grid(icon_20)
        # Check border
        self.assertEqual(grid_20[0], [1] * 16)
        self.assertEqual(grid_20[15], [1] * 16)

        # 3 characters: 3x5 font
        icon_feb = make_icon.render_text_glyph("FEB", border=False)
        self.assertEqual(len(icon_feb), 32)

        # Invert option
        icon_inv = make_icon.render_text_glyph("A", invert=True)
        self.assertEqual(len(icon_inv), 32)
        grid_inv = make_icon.bytes_to_grid(icon_inv)
        # Corner at (0,0) in normal text is 0, so inverted is 1
        self.assertEqual(grid_inv[0][0], 1)

    def test_c_header_generation_and_load(self):
        c_code = make_icon.render_c_header(make_feb.ICON_CHIP8_16x16, var_name="MY_CUSTOM_ICON")
        self.assertIn("MY_CUSTOM_ICON[32]", c_code)
        parsed_bytes = make_icon.load_from_c_header(c_code)
        self.assertEqual(parsed_bytes, make_feb.ICON_CHIP8_16x16)

    def test_template_generation(self):
        template = make_icon.generate_template()
        self.assertIn("16x16 FEB App Icon Template", template)
        parsed_bytes = make_icon.load_from_ascii(template)
        self.assertEqual(len(parsed_bytes), 32)

    def test_feb_icon_extraction(self):
        custom_icon = make_icon.render_text_glyph("GO", border=True)
        feb_data = make_feb.create_feb(
            app_type=make_feb.FEB_TYPE_CHIP8,
            title="GoGame",
            payload=b"\x00\xe0\x00\xee",
            icon=custom_icon
        )
        extracted = make_icon.load_from_feb(feb_data)
        self.assertEqual(extracted, custom_icon)

    def test_save_and_load_roundtrip_png_and_bmp(self):
        original = make_feb.ICON_2048_16x16
        with tempfile.TemporaryDirectory() as tmpdir:
            # 1. Test BMP roundtrip
            bmp_path = os.path.join(tmpdir, "test.bmp")
            make_icon.save_icon(original, bmp_path)
            loaded_bmp = make_icon.load_icon(bmp_path)
            self.assertEqual(loaded_bmp, original)

            # 2. Test PNG roundtrip (if PIL available)
            if make_icon.HAS_PIL:
                png_path = os.path.join(tmpdir, "test.png")
                make_icon.save_icon(original, png_path, scale=8)
                loaded_png = make_icon.load_icon(png_path)
                self.assertEqual(loaded_png, original)

            # 3. Test C header roundtrip
            h_path = os.path.join(tmpdir, "test.h")
            make_icon.save_icon(original, h_path, c_var="TEST_ICON")
            loaded_h = make_icon.load_icon(h_path)
            self.assertEqual(loaded_h, original)

            # 4. Test ASCII txt roundtrip
            txt_path = os.path.join(tmpdir, "test.txt")
            make_icon.save_icon(original, txt_path)
            loaded_txt = make_icon.load_icon(txt_path)
            self.assertEqual(loaded_txt, original)


if __name__ == "__main__":
    unittest.main()
