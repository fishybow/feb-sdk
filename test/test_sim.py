#!/usr/bin/env python3
"""
test_sim.py - Automated Unit & Integration Tests for Pygame FEB Simulator
"""

import unittest
import os
import sys
import tempfile
import struct

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS_DIR = os.path.join(REPO_ROOT, "tools")
BUILD_DIR = os.path.join(REPO_ROOT, "build")
sys.path.insert(0, TOOLS_DIR)

import feb_vm
import feb_fonts
import feb_sim


class TestFebFonts(unittest.TestCase):
    """Verifies u8g2 font decoding and rendering."""

    def test_fonts_available(self):
        for fid in range(3):
            font, fh, fw = feb_fonts.get_font(fid)
            self.assertIsNotNone(font)
            self.assertGreater(fh, 0)
            self.assertGreater(fw, 0)
            self.assertGreater(len(font._glyph_cache), 50)

    def test_glyph_rendering_and_width(self):
        font, _, _ = feb_fonts.get_font(0)  # 4x6 font
        dx, pixels = font.render_glyph(ord("A"), 0, 0)
        self.assertEqual(dx, 4)
        self.assertGreater(len(pixels), 0)

        # Space has 0 drawn pixels but positive advance width
        dx_sp, pixels_sp = font.render_glyph(ord(" "), 0, 0)
        self.assertEqual(dx_sp, 4)
        self.assertEqual(len(pixels_sp), 0)


class TestFebVM(unittest.TestCase):
    """Verifies core FebVM execution and opcode semantics."""

    def setUp(self):
        self.vm = feb_vm.FebVM()

    def test_vm_initial_state(self):
        self.assertEqual(self.vm.pc, 0x200)
        self.assertFalse(self.vm.exited)
        self.assertFalse(self.vm.schip_mode)
        self.assertEqual(self.vm.delay_timer, 0)
        # Check fonts loaded at 0x000 and 0x050
        self.assertEqual(self.vm.memory[0], 0xF0)
        self.assertEqual(self.vm.memory[0x50], 0x3C)

    def test_schip_high_low_opcodes(self):
        # 00FF (HIGH), 00FE (LOW)
        self.vm.load_rom(bytes([0x00, 0xFF, 0x00, 0xFE]))
        self.vm.step()
        self.assertTrue(self.vm.schip_mode)
        self.vm.step()
        self.assertFalse(self.vm.schip_mode)

    def test_vector_geometry_opcodes(self):
        # Set high res (00FF), draw mode SET (F098 with V0=1)
        # Draw rect (F194 with V1=10, V2=10, V3=20, V4=15)
        # Test pixel (F199 with V1=10, V2=10)
        rom = bytearray([
            0x00, 0xFF,        # HIGH
            0x60, 0x01,        # LD V0, 1
            0xF0, 0x98,        # DRAWMODE V0
            0x61, 10,          # LD V1, 10
            0x62, 10,          # LD V2, 10
            0x63, 20,          # LD V3, 20
            0x64, 15,          # LD V4, 15
            0xF1, 0x94,        # RECT V1
            0xF1, 0x99,        # TESTPIXEL V1
        ])
        self.vm.load_rom(bytes(rom))
        while self.vm.pc < 0x200 + len(rom) and not self.vm.exited:
            self.vm.step()

        self.assertTrue(self.vm.get_pixel(10, 10))
        self.assertTrue(self.vm.get_pixel(29, 10))
        self.assertEqual(self.vm.v[0xF], 1)
        self.assertFalse(self.vm.get_pixel(15, 15))  # Hollow inside

    def test_rotation_opcode(self):
        # Set high res, ROTATE V0 with V0=1 (90 deg CW portrait), draw pixel at (5, 10)
        rom = bytearray([
            0x00, 0xFF,        # HIGH
            0x60, 0x01,        # LD V0, 1 (ROTATE_90)
            0xF0, 0x9A,        # ROTATE V0
            0x61, 5,           # LD V1, 5
            0x62, 10,          # LD V2, 10
            0xF1, 0x90,        # PIXEL V1
            0xF1, 0x99,        # TESTPIXEL V1
        ])
        self.vm.load_rom(bytes(rom))
        while self.vm.pc < 0x200 + len(rom) and not self.vm.exited:
            self.vm.step()

        self.assertEqual(self.vm.rotation, 1)
        self.assertEqual(self.vm.v[0xF], 1)
        self.assertTrue(self.vm.get_pixel(5, 10))
        # Physically on display: x_phy = 127 - y = 127 - 10 = 117, y_phy = x = 5
        self.vm.rotation = 0
        self.assertTrue(self.vm.get_pixel(117, 5))

    def test_typography_opcodes(self):
        # Set high res, LD I to string "HI", TEXT V0 at (0, 0) font 0
        rom = bytearray([
            0x00, 0xFF,        # HIGH
            0xA2, 0x0E,        # LD I, 0x20E (address of string)
            0x60, 0,           # LD V0, 0 (x)
            0x61, 0,           # LD V1, 0 (y)
            0x62, 0,           # LD V2, 0 (font 0: 4x6)
            0xF0, 0xA0,        # TEXT V0
            0x00, 0xFD,        # EXIT
            ord("H"), ord("I"), 0x00
        ])
        self.vm.load_rom(bytes(rom))
        while not self.vm.exited:
            self.vm.step()

        # Test CHAR V0 (0xF0A1) with V0=20, V1=0, V2=0 (font 4x6), V3='Z'
        rom_char = bytearray([
            0x00, 0xFF,        # HIGH
            0x60, 20,          # LD V0, 20 (x)
            0x61, 0,           # LD V1, 0 (y)
            0x62, 0,           # LD V2, 0 (font 0)
            0x63, ord("Z"),    # LD V3, 'Z'
            0xF0, 0xA1,        # CHAR V0
            0x00, 0xFD         # EXIT
        ])
        self.vm = feb_vm.FebVM()
        self.vm.load_rom(bytes(rom_char))
        while not self.vm.exited:
            self.vm.step()
        char_pixels = sum(1 for y in range(8) for x in range(20, 26) if self.vm.get_pixel(x, y))
        self.assertGreater(char_pixels, 5)

    def test_button_polling_getkeys(self):
        # LD V0 via FXB0
        rom = bytes([0xF0, 0xB0, 0x00, 0xFD])
        self.vm.load_rom(rom)
        self.vm.keys = (1 << feb_vm.FEB_KEY_UP) | (1 << feb_vm.FEB_KEY_RIGHT)
        self.vm.step()
        # V0 should contain FEB_BTN_UP (0x01) | FEB_BTN_RIGHT (0x08) = 0x09
        self.assertEqual(self.vm.v[0], feb_vm.FEB_BTN_UP | feb_vm.FEB_BTN_RIGHT)

    def test_exit_chord_triggers_exit(self):
        self.vm.load_rom(bytes([0x12, 0x00]))  # Infinite jump loop (JP 0x200)
        self.vm.step()
        self.assertFalse(self.vm.exited)
        self.vm.press_key(feb_vm.FEB_KEY_UP)
        self.vm.press_key(feb_vm.FEB_KEY_DOWN)
        self.assertTrue(self.vm.exited)

    def test_rpl_flags_save_and_load(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            feb_path = os.path.join(tmpdir, "test_app.feb")
            sav_path = os.path.join(tmpdir, "test_app.sav")

            # Create dummy .feb
            payload = bytes([0x60, 42, 0x61, 99, 0xF1, 0x75, 0x00, 0xFD])
            header = struct.pack(
                "<IBBH24s16s8s32sII",
                feb_vm.FEB_MAGIC, 1, feb_vm.FEB_TYPE_CHIP8, 0,
                b"TestApp\x00", b"Author\x00", b"1.0\x00",
                b"\x00" * 32, len(payload), 0
            )
            with open(feb_path, "wb") as f:
                f.write(header + payload)

            # Load into VM and run
            vm = feb_vm.FebVM()
            vm.load_feb(feb_path)
            while not vm.exited:
                vm.step()

            self.assertEqual(vm.rpl_flags[0], 42)
            self.assertEqual(vm.rpl_flags[1], 99)
            self.assertTrue(vm.flags_dirty)

            # Flush save
            vm.flush_save_sidecar()
            self.assertTrue(os.path.exists(sav_path))

            # New VM loading the same .feb should restore rpl_flags
            vm2 = feb_vm.FebVM()
            vm2.load_feb(feb_path)
            self.assertEqual(vm2.rpl_flags[0], 42)
            self.assertEqual(vm2.rpl_flags[1], 99)


class TestFebSimulator(unittest.TestCase):
    """Verifies Pygame-based simulator integration and headless execution."""

    def test_simulator_headless_runs_all_sdk_games(self):
        items = [
            "2048", "button_demo", "draw_demo", "flappy_bird", "sokoban", "digital_pet",
            "template", "mastermind", "snake", "falling_blocks",
            "flashlight", "sos", "stopwatch", "std_dice", "dnd_dice"
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            for g in items:
                feb_file = os.path.join(BUILD_DIR, f"{g}.feb")
                if not os.path.exists(feb_file):
                    continue
                shot_file = os.path.join(tmpdir, f"{g}.png")
                sim = feb_sim.FebSimulator(
                    feb_path=feb_file,
                    scale=4,
                    theme="oled",
                    headless=True,
                    ips=1000
                )
                sim.run(max_frames=30, screenshot_path=shot_file)
                self.assertTrue(os.path.exists(shot_file), f"Screenshot was not generated for {g}")
                self.assertGreater(os.path.getsize(shot_file), 100)

    def test_digital_pet_simulation_and_persistence(self):
        pet_feb = os.path.join(BUILD_DIR, "digital_pet.feb")
        if not os.path.exists(pet_feb):
            return
        with tempfile.TemporaryDirectory() as tmpdir:
            dest_feb = os.path.join(tmpdir, "digital_pet.feb")
            import shutil
            shutil.copyfile(pet_feb, dest_feb)

            # Boot session 1
            vm1 = feb_vm.FebVM()
            vm1.load_feb(dest_feb)
            for _ in range(10):
                vm1.step_frame()

            # Verify initial defaults
            self.assertEqual(vm1.rpl_flags[0], 0x50)  # Magic 'P'
            self.assertEqual(vm1.rpl_flags[1], 0)     # Stage Egg
            self.assertEqual(vm1.rpl_flags[15], 1)    # Actions 1

            # Press UP to incubate egg
            vm1.press_key(feb_vm.FEB_KEY_UP)
            for _ in range(3):
                vm1.step_frame()
            vm1.release_key(feb_vm.FEB_KEY_UP)
            for _ in range(5):
                vm1.step_frame()

            # Should evolve to baby and action counter increments
            self.assertEqual(vm1.rpl_flags[1], 1)     # Stage Baby
            self.assertEqual(vm1.rpl_flags[15], 2)    # Actions 2
            vm1.flush_save_sidecar()

            # Boot session 2 from persistent .sav sidecar
            vm2 = feb_vm.FebVM()
            vm2.load_feb(dest_feb)
            for _ in range(5):
                vm2.step_frame()

            self.assertEqual(vm2.rpl_flags[0], 0x50)
            self.assertEqual(vm2.rpl_flags[1], 1)     # Preserved Stage Baby
            self.assertEqual(vm2.rpl_flags[15], 2)    # Preserved Actions


if __name__ == "__main__":
    unittest.main()
