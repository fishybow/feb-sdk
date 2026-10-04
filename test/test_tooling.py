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
        c_path = os.path.join(REPO_ROOT, "examples", "template", "main.c")
        asm = feb_build.compile_c_to_asm(c_path)
        code = assemble_chip8.assemble(asm)
        self.assertGreater(len(code), 50)
        self.assertEqual(len(code), 206)

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
        ])
        self.assertEqual(code, expected)

    def test_assemble_custom_features_instructions(self):
        asm = """
        START:
            drawmode v1
            testpixel v2
            num v4
            getkeys v5
        """
        code = assemble_chip8.assemble(asm)
        expected = bytes([
            0xF1, 0x98,  # drawmode v1
            0xF2, 0x99,  # testpixel v2
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
            self.assertEqual(len(feb_data), 96 + 1676)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_build_template_c(self):
        c_path = os.path.join(REPO_ROOT, "examples", "template", "main.c")
        asm_code = feb_build.compile_c_to_asm(c_path)
        bytecode = assemble_chip8.assemble(asm_code)
        self.assertEqual(len(bytecode), 206)

    def test_build_button_demo_c(self):
        c_path = os.path.join(REPO_ROOT, "examples", "button_demo", "main.c")
        asm_code = feb_build.compile_c_to_asm(c_path)
        bytecode = assemble_chip8.assemble(asm_code)
        self.assertEqual(len(bytecode), 906)

    def test_build_features_demo_c(self):
        c_path = os.path.join(REPO_ROOT, "examples", "features_demo", "main.c")
        asm_code = feb_build.compile_c_to_asm(c_path)
        bytecode = assemble_chip8.assemble(asm_code)
        self.assertEqual(len(bytecode), 423)

    def test_build_quest_c(self):
        c_path = os.path.join(REPO_ROOT, "examples", "quest", "main.c")
        asm_code = feb_build.compile_c_to_asm(c_path)
        bytecode = assemble_chip8.assemble(asm_code)
        self.assertEqual(len(bytecode), 3461)

    def test_modular_compiler_equivalence(self):
        import compiler
        import c_compiler
        for app in ["template", "button_demo", "features_demo", "2048", "quest"]:
            c_path = os.path.join(REPO_ROOT, "examples", app, "main.c")
            asm_mod = compiler.compile_c_to_asm(c_path)
            asm_facade = c_compiler.compile_c_to_asm(c_path)
            self.assertEqual(asm_mod, asm_facade, f"Compiler output mismatch on {app}")

if __name__ == "__main__":
    unittest.main()
