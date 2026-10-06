#!/usr/bin/env python3
"""
feb_build.py - Flashiibo Executable Binary (.feb) C Compiler & Build Tool

WARNING: This tool and the FEB SDK are in BETA and EXPERIMENTAL status.
Breaking changes might happen without warning.

Compiles C programs targeting the Flashiibo Gen3 FEB virtual machine runtime,
assembles them to bytecode, and packages them into downloadable .feb files.

Usage:
    python3 feb_build.py input.c -o output.feb --title "App Name" [options]
"""

import sys
import os
import argparse
import subprocess
import tempfile
import re

# Add tools directory to path
TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TOOLS_DIR)

import c_compiler
import assemble_chip8
import make_feb

def compile_c_to_asm(c_source_path):
    """
    Translates a C program targeting the FEB runtime into CHIP-8 assembly.
    Supports embedded assembly blocks (/* __FEB_ASM__ ... __FEB_ASM_END__ */)
    or delegates to tools/c_compiler.py for pure C compilation.
    """
    with open(c_source_path, "r", encoding="utf-8") as f:
        c_code = f.read()

    # Check for embedded assembly block
    match = re.search(r"/\*\s*__FEB_ASM__\s*(.*?)\s*__FEB_ASM_END__\s*\*/", c_code, re.DOTALL)
    if match:
        return match.group(1)

    return c_compiler.compile_c_to_asm(c_source_path)


def main():
    parser = argparse.ArgumentParser(
        description="Flashiibo Executable Binary (.feb) C Compiler & Packager [BETA / EXPERIMENTAL: Breaking changes may occur without warning]"
    )
    parser.add_argument("input", help="Source file (.c or .asm)")
    parser.add_argument("-o", "--output", required=True, help="Output .feb path")
    parser.add_argument("--title", required=True, help="Display title (max 23 chars)")
    parser.add_argument("--author", default="Flashiibo", help="Author string")
    parser.add_argument("--ver", default="1.0.0", help="Version string")
    parser.add_argument("--require-back", action="store_true", help="Requires physical BACK button (e.g. 4-button hardware)")
    parser.add_argument("--flags", type=lambda x: int(x, 0), default=None, help="Explicit header flags uint16")
    args = parser.parse_args()

    input_path = args.input
    if not os.path.exists(input_path):
        print(f"Error: input file '{input_path}' not found", file=sys.stderr)
        sys.exit(1)

    if input_path.endswith(".c"):
        asm_code = compile_c_to_asm(input_path)
    elif input_path.endswith(".asm"):
        with open(input_path, "r", encoding="utf-8") as f:
            asm_code = f.read()
    else:
        print(f"Error: unsupported source extension in '{input_path}' (expected .c or .asm)", file=sys.stderr)
        sys.exit(1)

    # Step 1: Assemble to bytecode
    bytecode = assemble_chip8.assemble(asm_code)
    print(f"[FEB_BUILD] Compiled {input_path} -> {len(bytecode)} bytes bytecode")

    # Step 2: Package into .feb container
    output_path = args.output
    out_dir = os.path.dirname(output_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    flags = make_feb.FEB_FLAG_NONE
    if args.flags is not None:
        flags = args.flags
    if args.require_back:
        flags |= make_feb.FEB_FLAG_REQUIRE_BACK_BUTTON

    feb_bytes = make_feb.create_feb(
        app_type=make_feb.FEB_TYPE_CHIP8,
        title=args.title,
        author=args.author,
        version=args.ver,
        payload=bytecode,
        flags=flags
    )

    with open(output_path, "wb") as f:
        f.write(feb_bytes)

    print(f"[FEB_BUILD] Packaged -> {output_path} ({len(feb_bytes)} bytes)")

if __name__ == "__main__":
    main()
