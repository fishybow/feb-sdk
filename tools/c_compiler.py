#!/usr/bin/env python3
"""
c_compiler.py - Generic C-to-CHIP-8 Compiler for Flashiibo Executable Binary (.feb)

Translates standard C source code targeting the Flashiibo FEB SDK (include/feb.h)
into valid CHIP-8 / Super-CHIP assembly code.

This module acts as a facade and CLI entrypoint delegating to the modular
compiler pipeline in tools/compiler/:
  - tools/compiler/lexer.py: Tokenizer and lexical scanner
  - tools/compiler/preprocessor.py: #include, #define, and conditional compilation
  - tools/compiler/parser.py: Recursive-descent AST parser and type checker
  - tools/compiler/codegen.py: CHIP-8/SCHIP instruction emitter and register allocator
"""

import os
import sys

# Ensure tools directory is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from compiler import CCompiler, compile_c_to_asm

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} input.c [-o output.asm]")
        sys.exit(1)
    src = sys.argv[1]
    asm = compile_c_to_asm(src)
    if "-o" in sys.argv:
        out_path = sys.argv[sys.argv.index("-o") + 1]
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(asm)
    else:
        print(asm)
