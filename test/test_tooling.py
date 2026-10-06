#!/usr/bin/env python3
"""
test_tooling.py - Automated Verification Suite for FEB Tooling & SDK
"""

import unittest
import os
import sys
import tempfile
import struct
import random

# Add repo tools and include to path
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS_DIR = os.path.join(REPO_ROOT, "tools")
sys.path.insert(0, TOOLS_DIR)

import assemble_chip8
import make_feb
import feb_build

def find_example_c(app):
    for sub in ["games", "demos", "apps"]:
        p = os.path.join(REPO_ROOT, "examples", sub, app, "main.c")
        if os.path.exists(p):
            return p
    return os.path.join(REPO_ROOT, "examples", app, "main.c")

class SimChip8:
    """Headless CHIP-8 / SCHIP + Flashiibo FEB virtual machine for automated testing."""
    def __init__(self, rom):
        self.mem = bytearray(4096)
        self.mem[0x200:0x200+len(rom)] = rom
        self.pc = 0x200
        self.v = bytearray(16)
        self.i = 0
        self.stack = []
        self.waiting_for_key = False
        self.key_reg = 0
        self.key_queue = []
        self.keys_pressed = 0
        self.exited = False
        self.dt = 0
        self.rpl_flags = bytearray(16)
        self.rng = random.Random(12345)

    def step(self):
        if self.exited:
            return
        # Hardware exit chord: UP + DOWN
        if (self.keys_pressed & 0x03) == 0x03 or (self.keys_pressed & ((1 << 0x2) | (1 << 0x8))) == ((1 << 0x2) | (1 << 0x8)):
            self.exited = True
            return
        if self.dt > 0:
            self.dt -= 1
        if self.waiting_for_key:
            if self.key_queue:
                k = self.key_queue.pop(0)
                self.v[self.key_reg] = k
                self.waiting_for_key = False
            elif self.keys_pressed:
                if self.keys_pressed & 0x01: k = 0x2
                elif self.keys_pressed & 0x02: k = 0x8
                elif self.keys_pressed & 0x04: k = 0x4
                elif self.keys_pressed & 0x08: k = 0x6
                else: k = 0
                self.v[self.key_reg] = k
                self.waiting_for_key = False
            else:
                return

        op = (self.mem[self.pc] << 8) | self.mem[self.pc + 1]
        self.pc += 2
        o1 = (op >> 12) & 0xF
        x = (op >> 8) & 0xF
        y = (op >> 4) & 0xF
        n = op & 0xF
        nn = op & 0xFF
        nnn = op & 0xFFF

        if op == 0x00FD:
            self.exited = True
        elif op in (0x00E0, 0x00FF, 0x00FE):
            pass
        elif op == 0x00EE:
            if not self.stack:
                self.exited = True
            else:
                self.pc = self.stack.pop()
        elif o1 == 0x1:
            self.pc = nnn
        elif o1 == 0x2:
            self.stack.append(self.pc)
            self.pc = nnn
        elif o1 == 0x3:
            if self.v[x] == nn: self.pc += 2
        elif o1 == 0x4:
            if self.v[x] != nn: self.pc += 2
        elif o1 == 0x5 and n == 0:
            if self.v[x] == self.v[y]: self.pc += 2
        elif o1 == 0x6:
            self.v[x] = nn
        elif o1 == 0x7:
            self.v[x] = (self.v[x] + nn) & 0xFF
        elif o1 == 0x8:
            if n == 0:
                self.v[x] = self.v[y]
            elif n == 1:
                self.v[x] |= self.v[y]
            elif n == 2:
                self.v[x] &= self.v[y]
            elif n == 3:
                self.v[x] ^= self.v[y]
            elif n == 4:
                s = self.v[x] + self.v[y]
                self.v[0xF] = 1 if s > 255 else 0
                self.v[x] = s & 0xFF
            elif n == 5:
                sub = self.v[x] - self.v[y]
                self.v[0xF] = 1 if sub >= 0 else 0
                self.v[x] = sub & 0xFF
            elif n == 6:
                self.v[0xF] = self.v[x] & 1
                self.v[x] = (self.v[x] >> 1) & 0xFF
            elif n == 7:
                sub = self.v[y] - self.v[x]
                self.v[0xF] = 1 if sub >= 0 else 0
                self.v[x] = sub & 0xFF
            elif n == 0xE:
                self.v[0xF] = (self.v[x] >> 7) & 1
                self.v[x] = (self.v[x] << 1) & 0xFF
        elif o1 == 0x9 and n == 0:
            if self.v[x] != self.v[y]: self.pc += 2
        elif o1 == 0xA:
            self.i = nnn
        elif o1 == 0xB:
            self.pc = (nnn + self.v[0]) & 0xFFF
        elif o1 == 0xC:
            self.v[x] = self.rng.randint(0, 255) & nn
        elif o1 == 0xD:
            pass
        elif o1 == 0xE:
            if nn == 0x9E:
                if (self.keys_pressed & (1 << self.v[x])): self.pc += 2
            elif nn == 0xA1:
                if not (self.keys_pressed & (1 << self.v[x])): self.pc += 2
        elif o1 == 0xF:
            if nn == 0x07:
                self.v[x] = self.dt
            elif nn == 0x0A:
                if self.key_queue:
                    self.v[x] = self.key_queue.pop(0)
                else:
                    self.waiting_for_key = True
                    self.key_reg = x
            elif nn == 0x15:
                self.dt = self.v[x]
            elif nn == 0x18:
                pass
            elif nn == 0x1E:
                self.i = (self.i + self.v[x]) & 0xFFF
            elif nn == 0x29:
                self.i = (self.v[x] * 5) & 0xFFF
            elif nn == 0x30:
                self.i = (self.v[x] * 10) & 0xFFF
            elif nn == 0x33:
                val = self.v[x]
                self.mem[self.i] = val // 100
                self.mem[self.i+1] = (val // 10) % 10
                self.mem[self.i+2] = val % 10
            elif nn == 0x55:
                for r in range(x + 1): self.mem[self.i + r] = self.v[r]
            elif nn == 0x65:
                for r in range(x + 1): self.v[r] = self.mem[self.i + r]
            elif nn == 0x75:
                for r in range(x + 1): self.rpl_flags[r] = self.v[r]
            elif nn == 0x85:
                for r in range(x + 1): self.v[r] = self.rpl_flags[r]
            elif 0x90 <= nn <= 0x97:
                pass
            elif nn in (0x98, 0x99, 0x9A, 0xA0, 0xA1, 0xA3):
                pass
            elif nn == 0xA2:
                self.v[0] = 0
            elif nn == 0xB0:
                self.v[x] = self.keys_pressed & 0xFF

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
        c_path = find_example_c("template")
        asm = feb_build.compile_c_to_asm(c_path)
        code = assemble_chip8.assemble(asm)
        self.assertGreater(len(code), 50)
        self.assertEqual(len(code), 154)

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

    def test_assemble_exit_quit_instructions(self):
        asm = """
        START:
            exit
            quit
        """
        code = assemble_chip8.assemble(asm)
        self.assertEqual(code, bytes([0x00, 0xFD, 0x00, 0xFD]))

    def test_assemble_custom_geometry_instructions(self):
        asm = """
        START:
            pixel v0
            line v1
            hline v2
            vline v3
            rect v4
            fillrect v5
            circle v6
            disc v7
            triangle v8
            rrect v9
            fillrrect va
        """
        code = assemble_chip8.assemble(asm)
        expected = bytes([
            0xF0, 0x90,  # pixel v0
            0xF1, 0x91,  # line v1
            0xF2, 0x92,  # hline v2
            0xF3, 0x93,  # vline v3
            0xF4, 0x94,  # rect v4
            0xF5, 0x95,  # fillrect v5
            0xF6, 0x96,  # circle v6
            0xF7, 0x97,  # disc v7
            0xF8, 0x9B,  # triangle v8
            0xF9, 0x9C,  # rrect v9
            0xFA, 0x9D,  # fillrrect va
        ])
        self.assertEqual(code, expected)

    def test_assemble_custom_features_instructions(self):
        asm = """
        START:
            drawmode v1
            testpixel v2
            rotate v3
            num v4
            getkeys v5
        """
        code = assemble_chip8.assemble(asm)
        expected = bytes([
            0xF1, 0x98,  # drawmode v1
            0xF2, 0x99,  # testpixel v2
            0xF3, 0x9A,  # rotate v3
            0xF4, 0xA3,  # num v4
            0xF5, 0xB0,  # getkeys v5
        ])
        self.assertEqual(code, expected)

    def test_assemble_custom_typography_instructions(self):
        asm = """
        START:
            text v1
            char v2
            textlen v3
            .ascii "HI"
            .asciz "OK"
        """
        code = assemble_chip8.assemble(asm)
        expected = bytes([
            0xF1, 0xA0,  # text v1
            0xF2, 0xA1,  # char v2
            0xF3, 0xA2,  # textlen v3
            0x48, 0x49,  # 'H', 'I'
            0x4F, 0x4B, 0x00, # 'O', 'K', '\0'
        ])
        self.assertEqual(code, expected)

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

    def test_header_require_back_button_flag(self):
        payload = b"\x12\x00"
        feb_data = make_feb.create_feb(
            app_type=make_feb.FEB_TYPE_CHIP8,
            title="Back Required",
            payload=payload,
            flags=make_feb.FEB_FLAG_REQUIRE_BACK_BUTTON
        )
        magic, ver, app_type, flags = struct.unpack_from("<IBBH", feb_data, 0)
        self.assertEqual(magic, make_feb.FEB_MAGIC)
        self.assertEqual(flags, make_feb.FEB_FLAG_REQUIRE_BACK_BUTTON)
        self.assertTrue(flags & 0x0001)

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
        c_path = find_example_c("2048")
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
            self.assertEqual(len(feb_data), 96 + len(bytecode))
            self.assertLess(len(bytecode), 2500)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_build_template_c(self):
        c_path = find_example_c("template")
        asm_code = feb_build.compile_c_to_asm(c_path)
        bytecode = assemble_chip8.assemble(asm_code)
        self.assertEqual(len(bytecode), 154)

    def test_build_button_demo_c(self):
        c_path = find_example_c("button_demo")
        asm_code = feb_build.compile_c_to_asm(c_path)
        bytecode = assemble_chip8.assemble(asm_code)
        self.assertEqual(len(bytecode), 1192)

    def test_build_draw_demo_c(self):
        c_path = find_example_c("draw_demo")
        asm_code = feb_build.compile_c_to_asm(c_path)
        bytecode = assemble_chip8.assemble(asm_code)
        self.assertEqual(len(bytecode), 392)

    def test_build_flappy_bird_c(self):
        c_path = find_example_c("flappy_bird")
        asm_code = feb_build.compile_c_to_asm(c_path)
        bytecode = assemble_chip8.assemble(asm_code)
        self.assertEqual(len(bytecode), 1829)

    def test_build_sokoban_c(self):
        c_path = find_example_c("sokoban")
        asm_code = feb_build.compile_c_to_asm(c_path)
        bytecode = assemble_chip8.assemble(asm_code)
        self.assertEqual(len(bytecode), 3118)
        self.assertLess(len(bytecode), 3200)

    def test_build_mastermind_c(self):
        c_path = find_example_c("mastermind")
        asm_code = feb_build.compile_c_to_asm(c_path)
        bytecode = assemble_chip8.assemble(asm_code)
        self.assertEqual(len(bytecode), 2358)
        self.assertLess(len(bytecode), 2600)

    def test_build_snake_c(self):
        c_path = find_example_c("snake")
        asm_code = feb_build.compile_c_to_asm(c_path)
        bytecode = assemble_chip8.assemble(asm_code)
        self.assertEqual(len(bytecode), 3472)
        self.assertLess(len(bytecode), 3584)

    def test_build_falling_blocks_c(self):
        c_path = find_example_c("falling_blocks")
        asm_code = feb_build.compile_c_to_asm(c_path)
        bytecode = assemble_chip8.assemble(asm_code)
        self.assertEqual(len(bytecode), 3575)
        self.assertLess(len(bytecode), 3584)

    def test_build_flashlight_c(self):
        c_path = find_example_c("flashlight")
        asm_code = feb_build.compile_c_to_asm(c_path)
        bytecode = assemble_chip8.assemble(asm_code)
        self.assertEqual(len(bytecode), 36)
        self.assertLess(len(bytecode), 200)

    def test_build_sos_c(self):
        c_path = find_example_c("sos")
        asm_code = feb_build.compile_c_to_asm(c_path)
        bytecode = assemble_chip8.assemble(asm_code)
        self.assertEqual(len(bytecode), 146)
        self.assertLess(len(bytecode), 300)

    def test_build_stopwatch_c(self):
        c_path = find_example_c("stopwatch")
        asm_code = feb_build.compile_c_to_asm(c_path)
        bytecode = assemble_chip8.assemble(asm_code)
        self.assertEqual(len(bytecode), 959)
        self.assertLess(len(bytecode), 1200)

    def test_build_dice_c(self):
        c_path = find_example_c("dice")
        asm_code = feb_build.compile_c_to_asm(c_path)
        bytecode = assemble_chip8.assemble(asm_code)
        self.assertEqual(len(bytecode), 1415)
        self.assertLess(len(bytecode), 2000)

    def test_build_dnd_dice_c(self):
        c_path = find_example_c("dnd_dice")
        asm_code = feb_build.compile_c_to_asm(c_path)
        bytecode = assemble_chip8.assemble(asm_code)
        self.assertEqual(len(bytecode), 1512)
        self.assertLess(len(bytecode), 2000)

    def test_c_compiler_geometry_primitives(self):
        import compiler
        with tempfile.NamedTemporaryFile("w", suffix=".c", delete=False) as f:
            f.write("""
            #include "../../include/feb.h"
            int main(void) {
                feb_draw_triangle(10, 20, 30, 40, 50, 60);
                feb_draw_rrect(5, 5, 20, 30);
                feb_fill_rrect(40, 40, 15, 25);
                return 0;
            }
            """)
            tmp_path = f.name
        try:
            asm_code = compiler.compile_c_to_asm(tmp_path)
            self.assertIn("triangle va", asm_code)
            self.assertIn("rrect va", asm_code)
            self.assertIn("fillrrect va", asm_code)
            bytecode = assemble_chip8.assemble(asm_code)
            self.assertTrue(len(bytecode) > 0)
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def test_modular_compiler_equivalence(self):
        import compiler
        import c_compiler
        all_targets = [
            "template", "button_demo", "draw_demo",
            "flappy_bird", "2048", "sokoban", "digital_pet", "mastermind", "snake", "falling_blocks",
            "flashlight", "sos", "stopwatch", "dice", "dnd_dice"
        ]
        for app in all_targets:
            c_path = find_example_c(app)
            asm_mod = compiler.compile_c_to_asm(c_path)
            asm_facade = c_compiler.compile_c_to_asm(c_path)
            self.assertEqual(asm_mod, asm_facade, f"Compiler output mismatch on {app}")

class TestToolingGuards(unittest.TestCase):
    def test_guard_no_embedded_asm_in_examples(self):
        """Guard: No SDK examples may contain inline or embedded assembly blocks."""
        examples_dir = os.path.join(REPO_ROOT, "examples")
        for root, _, files in os.walk(examples_dir):
            for file in files:
                if file.endswith((".c", ".h")):
                    path = os.path.join(root, file)
                    with open(path, "r", encoding="utf-8") as f:
                        content = f.read()
                    self.assertNotIn("__FEB_ASM__", content, f"Embedded assembly found in {path}")
                    self.assertNotIn("__asm__", content, f"Embedded assembly found in {path}")
                    self.assertNotIn("__asm", content, f"Embedded assembly found in {path}")

    def test_guard_local_variables_limit_enforced(self):
        """Guard: Functions with > 9 local variables must fail cleanly, not corrupt registers."""
        c_code_ok = """
        void ok_func(void) {
            uint8_t a = 1; uint8_t b = 2; uint8_t c = 3;
            uint8_t d = 4; uint8_t e = 5; uint8_t f = 6;
            uint8_t g = 7; uint8_t h = 8; uint8_t i = 9;
        }
        """
        with tempfile.NamedTemporaryFile(suffix=".c", mode="w", delete=False) as tf:
            tf.write(c_code_ok)
            p_ok = tf.name
        try:
            asm = feb_build.compile_c_to_asm(p_ok)
            self.assertIn("OK_FUNC:", asm)
        finally:
            if os.path.exists(p_ok):
                os.remove(p_ok)

        c_code_bad = """
        void bad_func(void) {
            uint8_t a = 1; uint8_t b = 2; uint8_t c = 3;
            uint8_t d = 4; uint8_t e = 5; uint8_t f = 6;
            uint8_t g = 7; uint8_t h = 8; uint8_t i = 9;
            uint8_t j = 10;
        }
        """
        with tempfile.NamedTemporaryFile(suffix=".c", mode="w", delete=False) as tf:
            tf.write(c_code_bad)
            p_bad = tf.name
        try:
            with self.assertRaises(ValueError) as cm:
                feb_build.compile_c_to_asm(p_bad)
            self.assertIn("exceeds maximum 9 registers", str(cm.exception))
        finally:
            if os.path.exists(p_bad):
                os.remove(p_bad)

    def test_guard_relational_comparisons_and_loops(self):
        """Guard: Relational operators (<, <=, >, >=, ==, !=) and loops must branch correctly."""
        c_code = """
        #include <feb.h>
        int main(void) {
            uint8_t count = 0;
            uint8_t k = 0;
            while (k < 5) {
                count += 1;
                k += 1;
            }
            if (count == 5) {
                count += 10;
            }
            uint8_t a = 3;
            uint8_t b = 7;
            if (a <= b) {
                count += 20;
            }
            if (b > a) {
                count += 30;
            }
            if (a >= b) {
                count += 100;
            }
            return count;
        }
        """
        with tempfile.NamedTemporaryFile(suffix=".c", mode="w", delete=False) as tf:
            tf.write(c_code)
            p = tf.name
        try:
            asm = feb_build.compile_c_to_asm(p)
            bc = assemble_chip8.assemble(asm)
            sim = SimChip8(bc)
            steps = 0
            while not sim.exited and steps < 2000:
                sim.step()
                steps += 1
            self.assertTrue(sim.exited)
            self.assertEqual(sim.v[0], 65)
        finally:
            if os.path.exists(p):
                os.remove(p)

    def test_guard_array_assignment_and_expression_integrity(self):
        """Guard: Array indexing expressions and assignments preserve registers and memory."""
        c_code = """
        #include <feb.h>
        static uint8_t arr[8];
        int main(void) {
            for (uint8_t i = 0; i < 8; i++) {
                arr[i] = i * 3;
            }
            uint8_t sum = 0;
            for (uint8_t j = 0; j < 8; j++) {
                sum += arr[j];
            }
            return sum;
        }
        """
        with tempfile.NamedTemporaryFile(suffix=".c", mode="w", delete=False) as tf:
            tf.write(c_code)
            p = tf.name
        try:
            asm = feb_build.compile_c_to_asm(p)
            bc = assemble_chip8.assemble(asm)
            sim = SimChip8(bc)
            steps = 0
            while not sim.exited and steps < 2000:
                sim.step()
                steps += 1
            self.assertTrue(sim.exited)
            self.assertEqual(sim.v[0], 84)
        finally:
            if os.path.exists(p):
                os.remove(p)

    def test_guard_arithmetic_optimizations(self):
        """Guard: Constant arithmetic optimizations (power-of-2 mul, div, mod, shifts) execute correctly."""
        c_code = """
        #include <feb.h>
        uint8_t test_arith(uint8_t x) {
            uint8_t a = x * 4;
            uint8_t b = x / 2;
            uint8_t c = x % 8;
            uint8_t d = x << 2;
            uint8_t e = x >> 1;
            return a + b + c + d + e;
        }
        int main(void) {
            return test_arith(10);
        }
        """
        with tempfile.NamedTemporaryFile(suffix=".c", mode="w", delete=False) as tf:
            tf.write(c_code)
            p = tf.name
        try:
            asm = feb_build.compile_c_to_asm(p)
            bc = assemble_chip8.assemble(asm)
            sim = SimChip8(bc)
            steps = 0
            while not sim.exited and steps < 1000:
                sim.step()
                steps += 1
            self.assertTrue(sim.exited)
            self.assertEqual(sim.v[0], 92)
        finally:
            if os.path.exists(p):
                os.remove(p)

    def test_guard_global_augmented_assignment_preserves_rhs(self):
        """Guard: Global variable augmented assignment (+=, -=) preserves RHS register."""
        c_code = """
        #include <feb.h>
        static uint8_t g_val = 20;
        int main(void) {
            uint8_t delta = 5;
            g_val += delta; // 25
            uint8_t sub_val = 3;
            g_val -= sub_val; // 22
            return g_val;
        }
        """
        with tempfile.NamedTemporaryFile(suffix=".c", mode="w", delete=False) as tf:
            tf.write(c_code)
            p = tf.name
        try:
            asm = feb_build.compile_c_to_asm(p)
            bc = assemble_chip8.assemble(asm)
            sim = SimChip8(bc)
            steps = 0
            while not sim.exited and steps < 1000:
                sim.step()
                steps += 1
            self.assertTrue(sim.exited)
            self.assertEqual(sim.v[0], 22)
        finally:
            if os.path.exists(p):
                os.remove(p)

    def test_guard_control_flow_switch_hardware_keys(self):
        """Guard: Switch statement correctly resolves hardware key constants and compound exit mask."""
        c_code = """
        #include <feb.h>
        uint8_t handle_key(uint8_t k) {
            uint8_t action = 0;
            switch (k) {
                case (FEB_KEY_UP | FEB_KEY_DOWN):
                    action = 99;
                    break;
                case FEB_KEY_UP:
                    action = 10;
                    break;
                case FEB_KEY_DOWN:
                    action = 20;
                    break;
                case FEB_KEY_LEFT:
                    action = 30;
                    break;
                case FEB_KEY_RIGHT:
                    action = 40;
                    break;
                default:
                    action = 1;
                    break;
            }
            return action;
        }
        int main(void) {
            uint8_t a = handle_key(FEB_KEY_UP);
            uint8_t b = handle_key(FEB_KEY_DOWN);
            uint8_t c = handle_key(FEB_KEY_LEFT);
            uint8_t d = handle_key(FEB_KEY_RIGHT);
            uint8_t e = handle_key(FEB_KEY_UP | FEB_KEY_DOWN);
            uint8_t f = handle_key(0xFF);
            return a + b + c + d + e + f;
        }
        """
        with tempfile.NamedTemporaryFile(suffix=".c", mode="w", delete=False) as tf:
            tf.write(c_code)
            p = tf.name
        try:
            asm = feb_build.compile_c_to_asm(p)
            bc = assemble_chip8.assemble(asm)
            sim = SimChip8(bc)
            steps = 0
            while not sim.exited and steps < 2000:
                sim.step()
                steps += 1
            self.assertTrue(sim.exited)
            self.assertEqual(sim.v[0], 200)
        finally:
            if os.path.exists(p):
                os.remove(p)

    def test_guard_call_argument_complex_expressions_preserve_scratch_registers(self):
        """Guard: Complex expressions in function/built-in arguments do not clobber other argument registers."""
        c_code = """
        #include <feb.h>
        static uint8_t res_x = 0;
        static uint8_t res_y = 0;
        static uint8_t res_z = 0;

        void helper(uint8_t a, uint8_t b, uint8_t c) {
            res_x = a;
            res_y = b;
            res_z = c;
        }

        int main(void) {
            uint8_t x = 40;
            uint8_t y = 20;
            uint8_t val = 5;
            helper(x, y, val - 1);
            if (res_x == 40 && res_y == 20 && res_z == 4) {
                return 100;
            }
            return 0;
        }
        """
        with tempfile.NamedTemporaryFile(suffix=".c", mode="w", delete=False) as tf:
            tf.write(c_code)
            p = tf.name
        try:
            asm = feb_build.compile_c_to_asm(p)
            bc = assemble_chip8.assemble(asm)
            sim = SimChip8(bc)
            steps = 0
            while not sim.exited and steps < 2000:
                sim.step()
                steps += 1
            self.assertTrue(sim.exited)
            self.assertEqual(sim.v[0], 100, f"Expected 100 but got {sim.v[0]} (res_y was likely clobbered)")
        finally:
            if os.path.exists(p):
                os.remove(p)

    def test_guard_2048_pure_c_simulation_and_step_budget(self):
        """Guard: 2048 boot and turns meet step budgets and preserve tile/score state."""
        c_path = find_example_c("2048")
        asm = feb_build.compile_c_to_asm(c_path)
        rom = assemble_chip8.assemble(asm)

        sim = SimChip8(rom)
        boot_steps = 0
        while not sim.waiting_for_key and not sim.exited and boot_steps < 5000:
            sim.step()
            boot_steps += 1

        self.assertTrue(sim.waiting_for_key, "2048 failed to reach initial key wait")
        self.assertLess(boot_steps, 2000, f"2048 boot step budget exceeded: {boot_steps} >= 2000")

        moves = [4, 8, 6, 2, 4, 8, 6, 2]
        for idx, key in enumerate(moves):
            sim.key_queue.append(key)
            steps = 0
            sim.step()
            steps += 1
            while not sim.waiting_for_key and not sim.exited and steps < 5000:
                sim.step()
                steps += 1

            self.assertTrue(sim.waiting_for_key, f"2048 failed to return to key wait after move {idx}")
            self.assertLess(steps, 5000, f"Move {idx} exceeded 5000 step budget: {steps}")

    def test_guard_all_sdk_examples_pure_c_compilation_and_packaging(self):
        """Guard: All SDK examples compile, assemble, and package into valid .feb binaries within budgets."""
        examples = [
            "template", "button_demo", "draw_demo",
            "flappy_bird", "2048", "sokoban", "digital_pet", "mastermind", "snake", "falling_blocks",
            "flashlight", "sos", "stopwatch", "dice", "dnd_dice"
        ]
        for app in examples:
            c_path = find_example_c(app)
            asm = feb_build.compile_c_to_asm(c_path)
            bytecode = assemble_chip8.assemble(asm)

            budget = 3584 if app in ("digital_pet", "snake", "falling_blocks") else (3200 if app == "sokoban" else (2600 if app in ("mastermind", "dice", "dnd_dice") else 2500))
            self.assertLess(len(bytecode), budget, f"Bytecode for {app} exceeds {budget} bytes budget: {len(bytecode)}")

            feb_data = make_feb.create_feb(
                app_type=make_feb.FEB_TYPE_CHIP8,
                title=app,
                author="Flashiibo",
                version="1.0.0",
                payload=bytecode
            )

            self.assertEqual(len(feb_data), 96 + len(bytecode))
            magic, ver, app_type, flags = struct.unpack_from("<IBBH", feb_data, 0)
            self.assertEqual(magic, make_feb.FEB_MAGIC)
            self.assertEqual(ver, 1)
            self.assertEqual(app_type, make_feb.FEB_TYPE_CHIP8)
            payload_size = struct.unpack_from("<I", feb_data, 88)[0]

    def test_guard_apps_no_require_back_flag(self):
        """Guard: All apps in examples/apps/ must NOT require physical BACK button (available on both Gen2 and Gen3)."""
        apps_dir = os.path.join(REPO_ROOT, "examples", "apps")
        for app_name in os.listdir(apps_dir):
            makefile_path = os.path.join(apps_dir, app_name, "Makefile")
            if os.path.exists(makefile_path):
                with open(makefile_path, "r", encoding="utf-8") as f:
                    content = f.read()
                self.assertNotIn("--require-back", content, f"App {app_name} must not specify --require-back")
    def test_guard_logical_and_or_operators_and_short_circuiting(self):
        """Guard: Logical AND (&&) and OR (||) compile correctly with short-circuit semantics."""
        c_code = """
        #include <feb.h>
        static uint8_t side_effect = 0;

        uint8_t inc_side_effect(void) {
            side_effect++;
            return 1;
        }

        int main(void) {
            uint8_t a = 0;
            uint8_t b = 1;
            uint8_t passed = 0;

            // False AND right -> right side must not execute
            if (a && inc_side_effect()) {
                return 99;
            }
            if (side_effect == 0) {
                passed++;
            }

            // True OR right -> right side must not execute
            if (b || inc_side_effect()) {
                passed++;
            }
            if (side_effect == 0) {
                passed++;
            }

            // Relational compound AND
            uint8_t x = 5;
            uint8_t y = 10;
            if (x < 10 && y > 8) {
                passed++;
            }

            // Expression assignment
            uint8_t and_val = (x == 5 && y == 10);
            uint8_t or_val = (x == 0 || y == 10);
            if (and_val == 1 && or_val == 1) {
                passed++;
            }

            return passed; // Should be 5
        }
        """
        with tempfile.NamedTemporaryFile(suffix=".c", mode="w", delete=False) as tf:
            tf.write(c_code)
            p = tf.name
        try:
            asm = feb_build.compile_c_to_asm(p)
            bc = assemble_chip8.assemble(asm)
            sim = SimChip8(bc)
            steps = 0
            while not sim.exited and steps < 2000:
                sim.step()
                steps += 1
            self.assertTrue(sim.exited)
            self.assertEqual(sim.v[0], 5)
        finally:
            if os.path.exists(p):
                os.remove(p)

    def test_guard_2048_game_over_detection_and_reset(self):
        """Guard: 2048 game over detection accurately identifies full non-mergeable boards vs valid boards."""
        c_code = """
        #include <feb.h>
        static uint8_t board[16];
        static uint8_t p1[16] = {1, 1, 2, 3, 4, 5, 6, 7, 8, 9, 1, 2, 3, 4, 5, 6};
        static uint8_t p2[16] = {1, 2, 3, 4, 1, 5, 6, 7, 8, 9, 1, 2, 3, 4, 5, 6};
        static uint8_t p3[16] = {1, 2, 1, 2, 2, 1, 2, 1, 1, 2, 1, 2, 2, 1, 2, 1};

        bool is_game_over(void) {
            for (uint8_t r = 0; r < 4; r++) {
                for (uint8_t c = 0; c < 4; c++) {
                    uint8_t idx = (r << 2) + c;
                    uint8_t val = board[idx];
                    if (val == 0) {
                        return false;
                    }
                    if (c < 3 && val == board[idx + 1]) {
                        return false;
                    }
                    if (r < 3 && val == board[idx + 4]) {
                        return false;
                    }
                }
            }
            return true;
        }

        int main(void) {
            for (uint8_t i = 0; i < 16; i++) board[i] = 0;
            if (is_game_over()) return 10;

            for (uint8_t i = 0; i < 16; i++) board[i] = p1[i];
            if (is_game_over()) return 20;

            for (uint8_t i = 0; i < 16; i++) board[i] = p2[i];
            if (is_game_over()) return 30;

            for (uint8_t i = 0; i < 16; i++) board[i] = p3[i];
            if (!is_game_over()) return 40;

            return 100;
        }
        """
        with tempfile.NamedTemporaryFile(suffix=".c", mode="w", delete=False) as tf:
            tf.write(c_code)
            p = tf.name
        try:
            asm = feb_build.compile_c_to_asm(p)
            bc = assemble_chip8.assemble(asm)
            sim = SimChip8(bc)
            steps = 0
            while not sim.exited and steps < 10000:
                sim.step()
                steps += 1
            self.assertTrue(sim.exited)
            self.assertEqual(sim.v[0], 100)
        finally:
            if os.path.exists(p):
                os.remove(p)

    def test_guard_flappy_bird_programmatic_exit(self):
        """Guard: Flappy Bird demonstrates programmatic exit on BACK button press both on title and in-game."""
        c_path = find_example_c("flappy_bird")
        asm = feb_build.compile_c_to_asm(c_path)
        bc = assemble_chip8.assemble(asm)

        # 1. Title screen exit on BACK (0x04)
        sim = SimChip8(bc)
        steps = 0
        while not sim.waiting_for_key and steps < 300:
            sim.step()
            steps += 1
        self.assertTrue(sim.waiting_for_key, "Flappy Bird should reach wait_key on title screen")
        self.assertFalse(sim.exited, "Flappy Bird should not exit prematurely on title screen")

        sim.keys_pressed = 0x04  # Press BACK
        for _ in range(50):
            sim.step()
            if sim.exited:
                break
        self.assertTrue(sim.exited, "Flappy Bird failed to programmatically exit on BACK key press from title")

        # 2. In-game exit on BACK
        sim2 = SimChip8(bc)
        steps = 0
        while not sim2.waiting_for_key and steps < 300:
            sim2.step()
            steps += 1
        self.assertTrue(sim2.waiting_for_key)

        sim2.keys_pressed = 0x08  # Press OK to start
        for _ in range(10):
            sim2.step()
        sim2.keys_pressed = 0x00  # Release
        for _ in range(50):
            sim2.step()
        self.assertFalse(sim2.exited, "Flappy Bird exited during gameplay")

        sim2.keys_pressed = 0x04  # Press BACK in game
        for _ in range(100):
            sim2.step()
            if sim2.exited:
                break
        self.assertTrue(sim2.exited, "Flappy Bird failed to programmatically exit on BACK key press during gameplay")

    def test_guard_flappy_bird_ceiling_gravity_no_stick(self):
        """Guard: Flappy Bird does not stick to ceiling; jump_timer decays cleanly and bird falls under gravity."""
        c_path = find_example_c("flappy_bird")
        asm = feb_build.compile_c_to_asm(c_path)
        bc = assemble_chip8.assemble(asm)

        data_pattern = bytes([0x16, 0x00, 0x00, 0x00])
        data_offset = bc.find(data_pattern)
        self.assertNotEqual(data_offset, -1)
        by_addr = 0x200 + data_offset
        jt_addr = 0x200 + data_offset + 1

        sim = SimChip8(bc)
        while not sim.waiting_for_key:
            sim.step()

        # Start game
        sim.keys_pressed = 0x08
        for _ in range(10):
            sim.step()
        sim.keys_pressed = 0x00

        def step_frame(press_flap=False):
            sim.keys_pressed = 0x08 if press_flap else 0x00
            for _ in range(2000):
                sim.step()
                if sim.dt == 0 and _ > 200:
                    break

        # Flap to ceiling
        for f in range(15):
            step_frame(press_flap=(f % 2 == 0))

        self.assertEqual(sim.mem[by_addr], 1, "Bird should reach ceiling at bird_y == 1")
        self.assertNotEqual(sim.mem[jt_addr], 255, "jump_timer must not underflow to 255")

        # Step frames with no input; bird must fall under gravity
        for _ in range(10):
            step_frame(press_flap=False)

        self.assertGreater(sim.mem[by_addr], 1, "Bird remained stuck at ceiling; gravity failed to pull it down")
        self.assertNotEqual(sim.mem[jt_addr], 255, "jump_timer underflowed to 255")

    def test_guard_draw_demo_execution(self):
        """Guard: draw_demo executes vector drawing and responds to UP+DOWN chord exit."""
        c_path = find_example_c("draw_demo")
        asm = feb_build.compile_c_to_asm(c_path)
        bc = assemble_chip8.assemble(asm)
        sim = SimChip8(bc)

        # Run several iterations
        for _ in range(200):
            sim.step()
            if sim.exited:
                break
        self.assertFalse(sim.exited)

        # UP+DOWN chord (0x01 | 0x02 = 0x03)
        sim.keys_pressed = 0x03
        for _ in range(100):
            sim.step()
            if sim.exited:
                break
        self.assertTrue(sim.exited, "draw_demo failed to exit on UP+DOWN chord")

    def test_guard_sokoban_level_solving_and_immovable_blocks(self):
        """Guard: Sokoban loads levels, enforces immovable block obstacles, solves levels, and handles restart/exit chords."""
        c_path = find_example_c("sokoban")
        asm = feb_build.compile_c_to_asm(c_path)
        bc = assemble_chip8.assemble(asm)
        self.assertLess(len(bc), 3200, f"Sokoban bytecode exceeds 3200 bytes budget: {len(bc)}")

        # Locate symbol addresses from known sprite pattern
        sprite_wall = bytes([0xff, 0x89, 0x89, 0xff, 0x91, 0x91, 0xff, 0x00])
        off = bc.find(sprite_wall)
        self.assertNotEqual(off, -1, "Wall sprite not found in bytecode")

        board_addr = 0x200 + off + 760
        cur_lvl_addr = board_addr + 72
        player_r_addr = cur_lvl_addr + 2
        player_c_addr = cur_lvl_addr + 3
        moves_addr = cur_lvl_addr + 4
        pushes_addr = cur_lvl_addr + 5
        game_state_addr = cur_lvl_addr + 6

        sim = SimChip8(bc)

        def step_until_getkeys(sim_inst, max_steps=10000):
            steps = 0
            while steps < max_steps and not sim_inst.exited:
                op = (sim_inst.mem[sim_inst.pc] << 8) | sim_inst.mem[sim_inst.pc + 1]
                if (op & 0xF0FF) == 0xF0B0:
                    return steps
                sim_inst.step()
                steps += 1
            return steps

        def send_button(sim_inst, mask):
            step_until_getkeys(sim_inst)
            sim_inst.keys_pressed = mask
            sim_inst.step()
            step_until_getkeys(sim_inst)
            sim_inst.keys_pressed = 0
            sim_inst.step()
            step_until_getkeys(sim_inst)

        # Boot until initial frame rendered and waiting for keys
        step_until_getkeys(sim)
        self.assertEqual(sim.mem[cur_lvl_addr], 0)
        self.assertEqual(sim.mem[player_r_addr], 2)
        self.assertEqual(sim.mem[player_c_addr], 2)
        self.assertEqual(sim.mem[game_state_addr], 0)

        # Level 1 Solution: 3x RIGHT (0x08)
        # Move 1: RIGHT to (2, 3)
        send_button(sim, 0x08)
        self.assertEqual(sim.mem[player_r_addr], 2)
        self.assertEqual(sim.mem[player_c_addr], 3)
        self.assertEqual(sim.mem[moves_addr], 1)
        self.assertEqual(sim.mem[pushes_addr], 0)

        # Move 2: RIGHT pushes box to (2, 5), player to (2, 4)
        send_button(sim, 0x08)
        self.assertEqual(sim.mem[player_r_addr], 2)
        self.assertEqual(sim.mem[player_c_addr], 4)
        self.assertEqual(sim.mem[moves_addr], 2)
        self.assertEqual(sim.mem[pushes_addr], 1)

        # Move 3: RIGHT pushes box to target diamond at (2, 6), player to (2, 5)
        send_button(sim, 0x08)
        self.assertEqual(sim.mem[player_r_addr], 2)
        self.assertEqual(sim.mem[player_c_addr], 5)
        self.assertEqual(sim.mem[moves_addr], 3)
        self.assertEqual(sim.mem[pushes_addr], 2)
        self.assertEqual(sim.mem[game_state_addr], 1, "Level 1 should transition to STATE_LEVEL_CLEAR")

        # Press key to advance to Level 2
        send_button(sim, 0x08)
        self.assertEqual(sim.mem[cur_lvl_addr], 1)
        self.assertEqual(sim.mem[game_state_addr], 0)
        self.assertEqual(sim.mem[player_r_addr], 2)
        self.assertEqual(sim.mem[player_c_addr], 2)

        # On Level 2, player moves RIGHT to (2, 3)
        send_button(sim, 0x08)
        self.assertEqual(sim.mem[player_c_addr], 3)
        self.assertEqual(sim.mem[moves_addr], 1)

        # Verify immovable obstacle: immovable wall at (2, 4) blocks further RIGHT movement
        send_button(sim, 0x08)
        self.assertEqual(sim.mem[player_c_addr], 3, "Player must not move through immovable wall obstacle")
        self.assertEqual(sim.mem[moves_addr], 1, "Moves count must not increment on blocked move")

        # Restart chord: BACK + OK (LEFT + RIGHT: 0x04 | 0x08 = 0x0C)
        send_button(sim, 0x0C)
        self.assertEqual(sim.mem[player_r_addr], 2)
        self.assertEqual(sim.mem[player_c_addr], 2)
        self.assertEqual(sim.mem[moves_addr], 0, "Restart chord must reset level moves")
        self.assertFalse(sim.exited, "Restart chord should not exit application")

        # Exit chord: UP + DOWN (0x01 | 0x02 = 0x03)
        sim.keys_pressed = 0x03
        sim.step()
        self.assertTrue(sim.exited, "Sokoban failed to exit on UP+DOWN hardware chord")

if __name__ == "__main__":
    unittest.main()

