#!/usr/bin/env python3
"""
assemble_chip8.py - CHIP-8 Assembler

Assembles CHIP-8 / Chip8 1.1 assembly source into a raw .ch8 bytecode ROM.
Supports standard mnemonics, labels, expressions, and data directives (.byte, .ds).

Usage:
    python3 assemble_chip8.py input.asm -o output.ch8
"""

import sys
import os
import argparse
import re

def parse_val(token, labels=None):
    if labels is None:
        labels = {}
    token = token.strip()
    if token in labels:
        return labels[token]
    if token.startswith("$"):
        # Binary literal in Chip8 1.1 syntax (e.g. $11 = 3, $11111111 = 255)
        return int(token[1:], 2)
    # Evaluate arithmetic expressions safely
    return eval(token, {"__builtins__": None}, labels)

def is_reg(token):
    token = token.strip().lower()
    return token.startswith("v") and len(token) == 2 and token[1] in "0123456789abcdef"

def parse_reg(token):
    token = token.strip().lower()
    if is_reg(token):
        return int(token[1], 16)
    raise ValueError(f"Not a valid CHIP-8 register: {token}")

def assemble(asm_text):
    labels = {}
    raw_lines = []
    
    # Strip comments and collect non-empty lines
    for line_idx, line in enumerate(asm_text.splitlines(), 1):
        code = line.split(";")[0].strip()
        if code:
            raw_lines.append((line_idx, code))

    # Pass 1: Collect labels and calculate addresses
    pc = 0x200
    for line_idx, code in raw_lines:
        parts = code.split(None, 1)
        first = parts[0]
        rest = parts[1] if len(parts) > 1 else ""
        if first.endswith(":"):
            labels[first[:-1]] = pc
            if not rest:
                continue
            parts = rest.split(None, 1)
            first = parts[0]
            rest = parts[1] if len(parts) > 1 else ""

        mnem = first.lower()
        if mnem == ".byte":
            args = [a.strip() for a in rest.split(",")] if rest else []
            pc += len(args)
        elif mnem == ".ds":
            pc += parse_val(rest)
        else:
            pc += 2

    # Pass 2: Emit binary bytecode
    binary = bytearray()
    pc = 0x200

    for line_idx, code in raw_lines:
        parts = code.split(None, 1)
        first = parts[0]
        rest = parts[1] if len(parts) > 1 else ""
        if first.endswith(":"):
            if not rest:
                continue
            parts = rest.split(None, 1)
            first = parts[0]
            rest = parts[1] if len(parts) > 1 else ""

        mnem = first.lower()
        args = [a.strip() for a in rest.split(",")] if rest else []

        try:
            if mnem == ".byte":
                for arg in args:
                    val = parse_val(arg, labels)
                    binary.append(val & 0xFF)
                    pc += 1
            elif mnem == ".ds":
                count = parse_val(args[0], labels)
                binary.extend(b"\x00" * count)
                pc += count
            elif mnem == "cls":
                binary.extend((0x00, 0xE0))
                pc += 2
            elif mnem == "high":
                binary.extend((0x00, 0xFF))
                pc += 2
            elif mnem == "low":
                binary.extend((0x00, 0xFE))
                pc += 2
            elif mnem == "ret":
                binary.extend((0x00, 0xEE))
                pc += 2
            elif mnem == "jump":
                addr = parse_val(args[0], labels)
                binary.extend(((0x10 | ((addr >> 8) & 0x0F)), addr & 0xFF))
                pc += 2
            elif mnem == "call":
                addr = parse_val(args[0], labels)
                binary.extend(((0x20 | ((addr >> 8) & 0x0F)), addr & 0xFF))
                pc += 2
            elif mnem == "skip.eq":
                x = parse_reg(args[0])
                if is_reg(args[1]):
                    y = parse_reg(args[1])
                    binary.extend(((0x50 | x), (y << 4)))
                else:
                    val = parse_val(args[1], labels) & 0xFF
                    binary.extend(((0x30 | x), val))
                pc += 2
            elif mnem == "skip.ne":
                x = parse_reg(args[0])
                if is_reg(args[1]):
                    y = parse_reg(args[1])
                    binary.extend(((0x90 | x), (y << 4)))
                else:
                    val = parse_val(args[1], labels) & 0xFF
                    binary.extend(((0x40 | x), val))
                pc += 2
            elif mnem == "load":
                if args[0].lower() == "i":
                    addr = parse_val(args[1], labels)
                    binary.extend(((0xA0 | ((addr >> 8) & 0x0F)), addr & 0xFF))
                elif args[1].lower() == "key":
                    x = parse_reg(args[0])
                    binary.extend(((0xF0 | x), 0x0A))
                elif args[1].lower() == "dt":
                    x = parse_reg(args[0])
                    binary.extend(((0xF0 | x), 0x07))
                elif args[0].lower() == "dt":
                    x = parse_reg(args[1])
                    binary.extend(((0xF0 | x), 0x15))
                elif args[0].lower() == "st":
                    x = parse_reg(args[1])
                    binary.extend(((0xF0 | x), 0x18))
                elif is_reg(args[1]):
                    x = parse_reg(args[0])
                    y = parse_reg(args[1])
                    binary.extend(((0x80 | x), (y << 4)))
                else:
                    x = parse_reg(args[0])
                    val = parse_val(args[1], labels) & 0xFF
                    binary.extend(((0x60 | x), val))
                pc += 2
            elif mnem == "add":
                if args[0].lower() == "i":
                    x = parse_reg(args[1])
                    binary.extend(((0xF0 | x), 0x1E))
                elif is_reg(args[1]):
                    x = parse_reg(args[0])
                    y = parse_reg(args[1])
                    binary.extend(((0x80 | x), ((y << 4) | 0x04)))
                else:
                    x = parse_reg(args[0])
                    val = parse_val(args[1], labels) & 0xFF
                    binary.extend(((0x70 | x), val))
                pc += 2
            elif mnem == "sub":
                x = parse_reg(args[0])
                if is_reg(args[1]):
                    y = parse_reg(args[1])
                    binary.extend(((0x80 | x), ((y << 4) | 0x05)))
                else:
                    val = (-parse_val(args[1], labels)) & 0xFF
                    binary.extend(((0x70 | x), val))
                pc += 2
            elif mnem == "and":
                x = parse_reg(args[0])
                y = parse_reg(args[1])
                binary.extend(((0x80 | x), ((y << 4) | 0x02)))
                pc += 2
            elif mnem == "or":
                x = parse_reg(args[0])
                y = parse_reg(args[1])
                binary.extend(((0x80 | x), ((y << 4) | 0x01)))
                pc += 2
            elif mnem == "xor":
                x = parse_reg(args[0])
                y = parse_reg(args[1])
                binary.extend(((0x80 | x), ((y << 4) | 0x03)))
                pc += 2
            elif mnem == "rnd":
                x = parse_reg(args[0])
                mask = parse_val(args[1], labels) & 0xFF
                binary.extend(((0xC0 | x), mask))
                pc += 2
            elif mnem == "draw":
                x = parse_reg(args[0])
                y = parse_reg(args[1])
                n = parse_val(args[2], labels) & 0x0F
                binary.extend(((0xD0 | x), ((y << 4) | n)))
                pc += 2
            elif mnem == "hex":
                x = parse_reg(args[0])
                binary.extend(((0xF0 | x), 0x29))
                pc += 2
            elif mnem == "bighex":
                x = parse_reg(args[0])
                binary.extend(((0xF0 | x), 0x30))
                pc += 2
            elif mnem == "save":
                x = parse_reg(args[0])
                binary.extend(((0xF0 | x), 0x55))
                pc += 2
            elif mnem == "restore":
                x = parse_reg(args[0])
                binary.extend(((0xF0 | x), 0x65))
                pc += 2
            elif mnem in ("saveflags", "save.flags"):
                x = parse_reg(args[0])
                binary.extend(((0xF0 | x), 0x75))
                pc += 2
            elif mnem in ("loadflags", "load.flags"):
                x = parse_reg(args[0])
                binary.extend(((0xF0 | x), 0x85))
                pc += 2
            else:
                raise ValueError(f"Unknown mnemonic: '{mnem}'")
        except Exception as e:
            raise RuntimeError(f"Error at line {line_idx} ('{code}'): {e}") from e

    return bytes(binary)

def main():
    parser = argparse.ArgumentParser(description="CHIP-8 Assembler")
    parser.add_argument("input", help="Source assembly file (.asm)")
    parser.add_argument("-o", "--output", required=True, help="Output .ch8 file")
    args = parser.parse_args()

    with open(args.input, "r", encoding="utf-8") as f:
        asm_text = f.read()

    binary = assemble(asm_text)

    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    with open(args.output, "wb") as f:
        f.write(binary)

    print(f"Assembled {args.input} -> {args.output} ({len(binary)} bytes, load address 0x200)")

if __name__ == "__main__":
    main()
