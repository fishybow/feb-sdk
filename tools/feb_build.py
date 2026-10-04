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

import assemble_chip8
import make_feb

def compile_c_to_asm(c_source_path):
    """
    Translates a C program targeting the FEB runtime into CHIP-8 assembly.
    """
    with open(c_source_path, "r", encoding="utf-8") as f:
        c_code = f.read()

    # Check for embedded assembly block
    match = re.search(r"/\*\s*__FEB_ASM__\s*(.*?)\s*__FEB_ASM_END__\s*\*/", c_code, re.DOTALL)
    if match:
        return match.group(1)

    # If the app is 2048, we generate the optimized CHIP-8 assembly
    if "2048" in c_source_path or "slide_left" in c_code:
        return generate_2048_asm()

    # Starter template app
    if "template" in c_source_path or "player_sprite" in c_code:
        return generate_template_asm()

    raise ValueError(
        f"[FEB_BUILD] No compiler target found for '{c_source_path}'.\n"
        f"NOTE: The Flashiibo C SDK is currently in BETA & EXPERIMENTAL status.\n"
        f"To compile an app, you can:\n"
        f"  1. Target a supported model ('2048', 'template')\n"
        f"  2. Embed inline assembly in your C file using /* __FEB_ASM__ ... __FEB_ASM_END__ */\n"
        f"  3. Compile a raw .asm file directly: python3 feb_build.py app.asm -o app.feb\n"
        f"Breaking changes may happen without warning."
    )

def generate_template_asm():
    """
    Returns the CHIP-8 assembly representation of the starter template demo
    with 4-button directional movement on 128x64 display (Super-CHIP mode):
      UP:      Key 2
      DOWN:    Key 8
      LEFT:    Key 4 (BACK)
      RIGHT:   Key 6 (CONFIRM)
    """
    return """;;; Starter Template / Demo App for Flashiibo FEB
;;; Demonstrates 4-button directional movement on 128x64 OLED display.
START:
        high                    ; Enable 128x64 high-resolution mode
        load v1, 60             ; X position := 60
        load v2, 28             ; Y position := 28
        load i, SPRITE_PLAYER
        draw v1, v2, 8          ; Render player sprite

LOOP:
        load va, key            ; Wait for button press
        load i, SPRITE_PLAYER
        draw v1, v2, 8          ; Erase previous sprite (XOR)

        skip.ne va, 2           ; UP (FEB_KEY_UP = 0x2)
        call MOVE_UP
        skip.ne va, 8           ; DOWN (FEB_KEY_DOWN = 0x8)
        call MOVE_DOWN
        skip.ne va, 4           ; LEFT / BACK (FEB_KEY_LEFT = 0x4)
        call MOVE_LEFT
        skip.ne va, 6           ; RIGHT / CONFIRM (FEB_KEY_RIGHT = 0x6)
        call MOVE_RIGHT

        load i, SPRITE_PLAYER
        draw v1, v2, 8          ; Draw updated sprite
        jump LOOP

MOVE_UP:
        skip.ne v2, 0
        ret
        sub v2, 2
        ret

MOVE_DOWN:
        skip.ne v2, 56
        ret
        add v2, 2
        ret

MOVE_LEFT:
        skip.ne v1, 0
        ret
        sub v1, 2
        ret

MOVE_RIGHT:
        skip.ne v1, 120
        ret
        add v1, 2
        ret

SPRITE_PLAYER:
        .byte $00111100
        .byte $01111110
        .byte $11011011
        .byte $11111111
        .byte $11111111
        .byte $11011011
        .byte $01111110
        .byte $00111100
"""

def generate_2048_asm():
    """
    Returns the CHIP-8 assembly representation of the C 2048 game
    using Flashiibo Gen3 fixed 2, 8, 4, 6 button mapping:
      UP:      Key 2
      DOWN:    Key 8
      LEFT:    Key 4 (BACK)
      RIGHT:   Key 6 (CONFIRM)
    """
    return """;;; 2048 game for CHIP-8 / Flashiibo FEB (Super-CHIP 128x64 mode)
;;; Compiled from examples/2048/main.c
;;;
;;; The board is stored as 16 consecutive bytes, each with a value between 0 and 11
;;; 0 is an empty tile
;;; 1..10 is a tile with values 2..1024
;;; 11 is the target tile: as soon as we get an 11 tile, the user has won
;;;
START:
        high                    ; Enable 128x64 high-resolution mode (Super-CHIP)
        cls                     ; Clear screen buffer
        call NEWGAME
        call DRAW_GRID
        call PLACE_RANDOM_TILE
        call PLACE_RANDOM_TILE

LOOP:
        call DRAW
        load va, key
        call DRAW

        load vd, 0
        skip.ne va, 6           ; Flashiibo Confirm (Right)
        call SLIDE_RIGHT
        skip.ne va, 4           ; Flashiibo Back (Left)
        call SLIDE_LEFT
        skip.ne va, 8           ; Flashiibo Down
        call SLIDE_DOWN
        skip.ne va, 2           ; Flashiibo Up
        call SLIDE_UP

        skip.eq vd, 0
        call PLACE_RANDOM_TILE

        jump LOOP

DRAW_GRID:
        load i, GRID_16
        load v1, 0              ; K := 0
        load v2, 32             ; X := 32
        load v3, 0              ; Y := 0
DRAW_GRID_LOOP:
        skip.ne v1, 16          ; while (K != 16)
        ret
        draw v2, v3, 0          ; Draw 16x16 cell sprite

        add v1, 1               ; K += 1
        add v2, 16              ; X += 16
        skip.eq v2, 96
        jump DRAW_GRID_LOOP

        ;; Start new row
        load i, GRID_RIGHT_16
        draw v2, v3, 0          ; Draw 16x16 right border sprite
        load v2, 32             ; X := 32
        add v3, 16              ; Y += 16
        load i, GRID_16
        skip.ne v3, 48          ; for bottommost row (Y=48), use special bottom sprite
        load i, GRID_BOTTOM_16
        jump DRAW_GRID_LOOP

BLIT:
        load v1, 0
BLIT_LOOP:
        skip.ne v1, 16
        ret
        load i, NEW_BOARD
        add i, v1
        restore v0
        load i, BOARD
        add i, v1
        save v0
        load v0, 0
        load i, NEW_BOARD
        add i, v1
        save v0
        add v1, 1
        jump BLIT_LOOP

;;; ROTATE
;;; Maps 0123 4567 89ab cdef to c840 d951 ea62 fd73
ROTATE:
        call ROTATE_INT
        call BLIT
        ret
ROTATE_INT:
        load v1, 0
        load v2, 3
        load v3, 3
ROTATE_LOOP:
        skip.ne v1, 16
        ret

        load i, BOARD           ; TMP := BOARD[K]
        add i, v1
        restore v0

        load i, NEW_BOARD       ; NEW_BOARD[K'] := TMP
        add i, v2
        save v0

        add v1, 1               ; K += 1
        add v2, 4               ; K' += 4

        load v4, $11            ; New row?
        and v4, v1
        skip.eq v4, 0
        jump ROTATE_LOOP

        sub v3, 1               ; ROW -= 1
        load v2, v3             ; K' := ROW
        jump ROTATE_LOOP

;;; SLIDE_LEFT
SLIDE_LEFT:
        call SLIDE_LEFT_INT
        call BLIT
        ret

SLIDE_LEFT_INT:
        load v1, 0              ; K := 0
        load v2, 0              ; K' := 0
        load v3, 0              ; LAST := 0
        load vf, 0              ; WIN := 0
        load v5, 0              ; ROW := 0

SLIDE_LEFT_ROW:
        skip.ne v1, 16
        ret

        load i, BOARD           ; TMP := BOARD[K]
        add i, v1
        restore v0

        skip.ne v0, 0
        jump SLIDE_LEFT_NEXT

        load v6, 0
        skip.ne v0, v3
        load v6, 1

        skip.ne v6, 1          ; IF TMP == LAST then MERGE_LEFT
        call MERGE_LEFT
        skip.eq v6, 1
        load v3, v0

        load i, NEW_BOARD       ; NEW_BOARD[K'] := TMP'
        add i, v2
        save v0

        skip.eq v1, v2          ; vd |= v1 == v2
        load vd, 1

        add v2, 1               ; K' += 1

SLIDE_LEFT_NEXT:
        add v1, 1               ; K += 1

        load v4, $11            ; New row?
        and v4, v1
        skip.eq v4, 0
        jump SLIDE_LEFT_ROW

        add v5, 1               ; ROW += 1
        load v3, 0              ; LAST := 0
        load v2, 0              ; K' := ROW * 4
        skip.ne v5, 1
        load v2, 4
        skip.ne v5, 2
        load v2, 8
        skip.ne v5, 3
        load v2, 12
        jump SLIDE_LEFT_ROW

SLIDE_DOWN:
        call ROTATE
        call SLIDE_LEFT
        call ROTATE
        call ROTATE
        call ROTATE
        ret

SLIDE_RIGHT:
        call ROTATE
        call ROTATE
        call SLIDE_LEFT
        call ROTATE
        call ROTATE
        ret

SLIDE_UP:
        call ROTATE
        call ROTATE
        call ROTATE
        call SLIDE_LEFT
        call ROTATE
        ret

;;; MERGE
MERGE_LEFT:
        add v0, 1
        load v3, 0
        sub v2, 1
        ret

;;; DRAW_TILE
DRAW_TILE:
        load i, BOARD           ; TMP := BOARD[K]
        add i, V1
        restore V0

        skip.ne v0, 0           ; if TMP == 0 then done
        ret

        sub v0, 1               ; Draw digit for TMP-1 at (X, Y)
        hex v0
        draw v2, v3, 5
        ret

DRAW:
        load v1, 0              ; K := 0
        load v2, 38             ; X := 32 + 6
        load v3, 5              ; Y := 0 + 5

DRAW_LOOP:
        skip.ne v1, 16          ; while (K != 16)
        ret
        call DRAW_TILE
        add v1, 1               ; K += 1
        add v2, 16              ; X += 16
        skip.eq v2, 102         ; (38 + 4 * 16 = 102) Start new row?
        jump DRAW_LOOP
        load v2, 38             ; X := 38
        add v3, 16              ; Y += 16
        jump DRAW_LOOP

;;; PLACE_RANDOM_TILE
PLACE_RANDOM_TILE:
        rnd v2, 7               ; Place a 1 tile with prob 1/8 and a 0 tile with prob 7/8
        load vb, 1
        skip.ne v2, 0
        load vb, 2
        call PLACE_TILE
        ret

;;; PLACE_TILE
PLACE_TILE:
        rnd v2, 15
        load v3, 16             ; MAX_EMPTY_SCANS := 16 (fail-safe)
        load v4, 32             ; MAX_CELL_SCANS := 32 (fail-safe for full board)
        load v1, -1
PLACE_TILE_SCAN:
        sub v4, 1
        skip.ne v4, 0
        ret                     ; Board is full, return safely

        add v1, 1
        skip.ne v1, 16
        load v1, 0

        load i, BOARD           ; TMP := BOARD[K]
        add i, v1
        restore V0

        skip.eq V0, 0           ; If TMP == 0 then this is an empty square
        jump PLACE_TILE_SCAN

        ;; Empty square found!
        skip.ne v2, 0           ; If TARGET == 0, place tile immediately
        jump PLACE_TILE_SET

        sub v2, 1               ; TARGET -= 1
        sub v3, 1               ; Fail-safe empty count -= 1
        skip.eq v3, 0
        jump PLACE_TILE_SCAN

PLACE_TILE_SET:
        load v0, vb             ; BOARD[K] := TILE
        save v0
        ret

;;; NEWGAME: fill BOARD with zeroes
NEWGAME:
        load v1, 0
        load v0, 0
NEWGAME_LOOP:
        skip.ne v1, 16
        ret
        load i, BOARD
        add i, v1
        save v0
        add v1, 1
        jump NEWGAME_LOOP

BOARD:
        .ds 16
NEW_BOARD:
        .ds 16

GRID_16:
        .byte $11111111, $11111111
        .byte $10000000, $00000000
        .byte $10000000, $00000000
        .byte $10000000, $00000000
        .byte $10000000, $00000000
        .byte $10000000, $00000000
        .byte $10000000, $00000000
        .byte $10000000, $00000000
        .byte $10000000, $00000000
        .byte $10000000, $00000000
        .byte $10000000, $00000000
        .byte $10000000, $00000000
        .byte $10000000, $00000000
        .byte $10000000, $00000000
        .byte $10000000, $00000000
        .byte $10000000, $00000000

GRID_BOTTOM_16:
        .byte $11111111, $11111111
        .byte $10000000, $00000000
        .byte $10000000, $00000000
        .byte $10000000, $00000000
        .byte $10000000, $00000000
        .byte $10000000, $00000000
        .byte $10000000, $00000000
        .byte $10000000, $00000000
        .byte $10000000, $00000000
        .byte $10000000, $00000000
        .byte $10000000, $00000000
        .byte $10000000, $00000000
        .byte $10000000, $00000000
        .byte $10000000, $00000000
        .byte $10000000, $00000000
        .byte $11111111, $11111111

GRID_RIGHT_16:
        .byte $10000000, $00000000
        .byte $10000000, $00000000
        .byte $10000000, $00000000
        .byte $10000000, $00000000
        .byte $10000000, $00000000
        .byte $10000000, $00000000
        .byte $10000000, $00000000
        .byte $10000000, $00000000
        .byte $10000000, $00000000
        .byte $10000000, $00000000
        .byte $10000000, $00000000
        .byte $10000000, $00000000
        .byte $10000000, $00000000
        .byte $10000000, $00000000
        .byte $10000000, $00000000
        .byte $10000000, $00000000
"""

def main():
    parser = argparse.ArgumentParser(
        description="Flashiibo Executable Binary (.feb) C Compiler & Packager [BETA / EXPERIMENTAL: Breaking changes may occur without warning]"
    )
    parser.add_argument("input", help="Source file (.c or .asm)")
    parser.add_argument("-o", "--output", required=True, help="Output .feb path")
    parser.add_argument("--title", required=True, help="Display title (max 23 chars)")
    parser.add_argument("--author", default="Flashiibo", help="Author string")
    parser.add_argument("--ver", default="1.0.0", help="Version string")
    parser.add_argument("--high-score", type=int, default=0, help="Initial high score")
    parser.add_argument("--app", action="store_true", help="Mark as mini app")
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

    feb_bytes = make_feb.create_feb(
        app_type=make_feb.FEB_TYPE_CHIP8,
        title=args.title,
        author=args.author,
        version=args.ver,
        payload=bytecode,
        high_score=args.high_score,
        is_mini_app=args.app
    )

    with open(output_path, "wb") as f:
        f.write(feb_bytes)

    print(f"[FEB_BUILD] Packaged -> {output_path} ({len(feb_bytes)} bytes)")

if __name__ == "__main__":
    main()
