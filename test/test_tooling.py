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
        """
        code = assemble_chip8.assemble(asm)
        self.assertEqual(code, bytes([0x00, 0xFF, 0x00, 0xFE, 0xF5, 0x30]))

class TestMakeFeb(unittest.TestCase):
    def test_header_structure_and_magic(self):
        payload = bytes([0x00, 0xE0, 0x00, 0xEE])
        feb_data = make_feb.create_feb(
            app_type=make_feb.FEB_TYPE_CHIP8,
            title="Test App",
            author="Dev",
            version="1.0.0",
            payload=payload,
            high_score=100,
            is_mini_app=False
        )
        self.assertEqual(len(feb_data), 100 + len(payload))

        # Check magic (.FEB in LE: 0x4245462E)
        magic, ver, app_type, flags = struct.unpack_from("<IBBH", feb_data, 0)
        self.assertEqual(magic, make_feb.FEB_MAGIC)
        self.assertEqual(ver, 1)
        self.assertEqual(app_type, make_feb.FEB_TYPE_CHIP8)
        self.assertTrue(flags & make_feb.FEB_FLAG_HIGH_SCORE)

        # Check title and payload size
        title = feb_data[8:32].split(b'\x00')[0].decode('utf-8')
        self.assertEqual(title, "Test App")

        payload_size, high_score = struct.unpack_from("<II", feb_data, 88)
        self.assertEqual(payload_size, len(payload))
        self.assertEqual(high_score, 100)

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
            self.assertEqual(len(feb_data), 100 + 536)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_build_template_c(self):
        c_path = os.path.join(REPO_ROOT, "examples", "template", "main.c")
        asm_code = feb_build.compile_c_to_asm(c_path)
        bytecode = assemble_chip8.assemble(asm_code)
        self.assertEqual(len(bytecode), 78)

if __name__ == "__main__":
    unittest.main()
