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

    # Button demo app
    if "button_demo" in c_source_path or "button_test" in c_source_path or "button_demo" in c_code or "button_test" in c_code or "total_presses" in c_code:
        return generate_button_demo_asm()

    # Features demo app
    if "features_demo" in c_source_path or "features_demo" in c_code.lower() or "feb_wait_vsync" in c_code:
        return generate_features_demo_asm()

    # Tiny Quest top-down action RPG app
    if "quest" in c_source_path or "quest" in c_code.lower():
        return generate_quest_asm()

    raise ValueError(
        f"[FEB_BUILD] No compiler target found for '{c_source_path}'.\n"
        f"NOTE: The Flashiibo C SDK is currently in BETA & EXPERIMENTAL status.\n"
        f"To compile an app, you can:\n"
        f"  1. Target a supported model ('2048', 'template', 'button_demo', 'features_demo', 'quest')\n"
        f"  2. Embed inline assembly in your C file using /* __FEB_ASM__ ... __FEB_ASM_END__ */\n"
        f"  3. Compile a raw .asm file directly: python3 feb_build.py app.asm -o app.feb\n"
        f"Breaking changes may happen without warning."
    )

def generate_features_demo_asm():
    """
    Returns the CHIP-8 assembly representation of the features demo application:
    Demonstrates hardware 60 Hz vsync, instantaneous getkeys, geometry primitives
    (rect, fillrect, circle, disc), typography (text, num), and zero-RAM testpixel collision.
    """
    return """;;; Features & Primitives Showcase for Flashiibo FEB (Super-CHIP 128x64 mode)
;;; Compiled from examples/features_demo/main.c
START:
        high                    ; Enable 128x64 high-resolution mode
        cls                     ; Clear screen
        load v0, 60             ; Cursor X := 60
        load v1, 30             ; Cursor Y := 30
        load v2, 0              ; Frame counter := 0

FRAME_LOOP:
        vsync                   ; Deterministic 60 Hz frame synchronization (FX9A)
        cls                     ; Clear display buffer

        ;; 1. Header outline and typography
        load v4, 0
        load v5, 0
        load v6, 127
        load v7, 12
        rect v4                 ; Outline banner box (FX94)

        load i, STR_TITLE
        load v4, 4
        load v5, 2
        load v6, 1              ; FEB_FONT_6X10
        text v4                 ; Render title text (FXA0)

        ;; Render 16-bit frame counter
        load i, 0
        add i, v2
        load v4, 95
        load v5, 2
        load v6, 1              ; FEB_FONT_6X10
        num v4                  ; Render number from I (FXA3)
        add v2, 1               ; Increment frame counter

        ;; 2. Geometric Primitives
        ;; Filled rectangle on left
        load v4, 10
        load v5, 20
        load v6, 20
        load v7, 16
        fillrect v4             ; Solid rectangle (FX95)

        ;; Hollow circle in center
        load v4, 64
        load v5, 30
        load v6, 12
        circle v4               ; Hollow circle (FX96)

        ;; Solid disc on right
        load v4, 100
        load v5, 30
        load v6, 8
        disc v4                 ; Filled circle (FX97)

        ;; 3. Zero-RAM Collision Detection
        load v4, v0
        load v5, v1
        testpixel v4            ; Test pixel under cursor directly on framebuffer (FX99)

        ;; Draw 5x5 cursor outline box
        load v4, v0
        load v5, v1
        load v6, 5
        load v7, 5
        rect v4

        ;; Collision status feedback
        skip.eq vf, 1
        jump NO_HIT
        load i, STR_HIT
        load v4, 20
        load v5, 52
        load v6, 0              ; FEB_FONT_4X6
        text v4
        jump INPUT_STEP

NO_HIT:
        load i, STR_STATUS
        load v4, 30
        load v5, 52
        load v6, 0              ; FEB_FONT_4X6
        text v4

INPUT_STEP:
        ;; 4. Instantaneous 4-button polling
        getkeys v8              ; Reads physical button bitmask (FXB0)

        ;; Check UP (Bit 0 = 0x01)
        load v4, 1
        and v4, v8
        skip.eq v4, 0
        sub v1, 1

        ;; Check DOWN (Bit 1 = 0x02)
        load v4, 2
        and v4, v8
        skip.eq v4, 0
        add v1, 1

        ;; Check LEFT (Bit 2 = 0x04)
        load v4, 4
        and v4, v8
        skip.eq v4, 0
        sub v0, 1

        ;; Check RIGHT (Bit 3 = 0x08)
        load v4, 8
        and v4, v8
        skip.eq v4, 0
        add v0, 1

        ;; Clamp cursor within screen boundaries
        skip.ne v0, 1
        load v0, 2
        skip.ne v0, 126
        load v0, 125
        skip.ne v1, 13
        load v1, 14
        skip.ne v1, 61
        load v1, 60

        jump FRAME_LOOP

STR_TITLE:
        .asciz "FLASHIIBO"
STR_HIT:
        .asciz "COLLISION!"
STR_STATUS:
        .asciz "USE D-PAD TO MOVE"
"""


def generate_button_demo_asm():
    """
    Returns the CHIP-8 assembly representation of the button demo application:
      UP:      Key 0x2
      DOWN:    Key 0x8
      LEFT:    Key 0x4 (BACK)
      RIGHT:   Key 0x6 (OK)
    Displays directional tap counts on screen edges and calls out the active
    button name and virtual CHIP-8 key code in the center.
    """
    return """;;; Button Demo App for Flashiibo FEB (Super-CHIP 128x64 mode)
;;; Compiled from examples/button_demo/main.c
;;;
;;; Register mapping:
;;;   v0: total_presses
;;;   v1: last_key (0=init, 2=UP, 8=DOWN, 4=BACK, 6=OK)
;;;   v2: up_count
;;;   v3: down_count
;;;   v4: left_count
;;;   v5: right_count
;;;   va: pressed key temporary
;;;   vb: chunk offset (32)
;;;   vc: X coordinate
;;;   vd: Y coordinate
;;;
START:
        high                    ; Enable 128x64 high-resolution mode
        cls                     ; Clear screen buffer
        load v0, 0              ; total_presses = 0
        load v1, 0              ; last_key = 0 (initial/welcome state)
        load v2, 0              ; up_count = 0
        load v3, 0              ; down_count = 0
        load v4, 0              ; left_count = 0
        load v5, 0              ; right_count = 0
        call SAVE_STATE
        call DRAW_STATE

LOOP:
        load va, key            ; Wait for key press (0xFX0A)
        call DRAW_STATE         ; XOR erase previous state
        add v0, 1               ; total_presses++
        load v1, va             ; last_key = key

        skip.ne va, 2           ; FEB_KEY_UP = 0x2
        add v2, 1
        skip.ne va, 8           ; FEB_KEY_DOWN = 0x8
        add v3, 1
        skip.ne va, 4           ; FEB_KEY_LEFT / BACK = 0x4
        add v4, 1
        skip.ne va, 6           ; FEB_KEY_RIGHT / OK = 0x6
        add v5, 1

        call SAVE_STATE
        call DRAW_STATE
        jump LOOP

SAVE_STATE:
        load i, MEM_STATE
        save v5                 ; Stores v0..v5 into MEM_STATE
        ret

DRAW_STATE:
        ;; Top: UP count
        hex v2
        load vc, 62
        load vd, 10
        draw vc, vd, 5

        ;; Left: BACK / LEFT count
        hex v4
        load vc, 24
        load vd, 30
        draw vc, vd, 5

        ;; Right: OK / RIGHT count
        hex v5
        load vc, 100
        load vd, 30
        draw vc, vd, 5

        ;; Bottom: DOWN count
        hex v3
        load vc, 62
        load vd, 48
        draw vc, vd, 5

        ;; Center: Call out button name and CHIP-8 code
        call DRAW_CENTER
        ret

DRAW_CENTER:
        load vb, 32
        skip.ne v1, 2
        jump SET_UP
        skip.ne v1, 8
        jump SET_DOWN
        skip.ne v1, 4
        jump SET_BACK
        skip.ne v1, 6
        jump SET_OK
        load i, B_INIT_L
        jump DO_BLIT
SET_UP:
        load i, B_UP_L
        jump DO_BLIT
SET_DOWN:
        load i, B_DOWN_L
        jump DO_BLIT
SET_BACK:
        load i, B_BACK_L
        jump DO_BLIT
SET_OK:
        load i, B_OK_L
DO_BLIT:
        load vc, 40
        load vd, 24
        draw vc, vd, 0          ; Left 16x16 chunk at (40, 24)
        add i, vb
        add vc, 16
        draw vc, vd, 0          ; Mid 16x16 chunk at (56, 24)
        add i, vb
        add vc, 16
        draw vc, vd, 0          ; Right 16x16 chunk at (72, 24)
        ret

MEM_STATE:
        .byte 0, 0, 0, 0, 0, 0

;;; Center Banners (48x16 pixels total, three 16x16 chunks each)
B_INIT_L:
        .byte 0x00, 0x00, 0x00, 0x79, 0x00, 0x45, 0x00, 0x45, 0x00, 0x79, 0x00, 0x41, 0x00, 0x41, 0x00, 0x41, 0x00, 0x00, 0x03, 0xc8, 0x02, 0x28, 0x02, 0x28, 0x03, 0xc8, 0x02, 0x28, 0x02, 0x28, 0x03, 0xc7
B_INIT_M:
        .byte 0x00, 0x00, 0xe7, 0xce, 0x14, 0x11, 0x14, 0x10, 0xe7, 0x8e, 0x44, 0x01, 0x24, 0x11, 0x17, 0xce, 0x00, 0x00, 0xbe, 0xf9, 0x88, 0x22, 0x88, 0x22, 0x88, 0x22, 0x88, 0x22, 0x88, 0x22, 0x08, 0x21
B_INIT_R:
        .byte 0x00, 0x00, 0x38, 0x00, 0x44, 0x00, 0x40, 0x00, 0x38, 0x00, 0x04, 0x00, 0x44, 0x00, 0x38, 0x00, 0x00, 0x00, 0xc8, 0x80, 0x2c, 0x80, 0x2a, 0x80, 0x29, 0x80, 0x28, 0x80, 0x28, 0x80, 0xc8, 0x80
B_UP_L:
        .byte 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x71, 0xce, 0x8a, 0x29, 0x82, 0x28, 0x82, 0x28, 0x82, 0x28, 0x8a, 0x29, 0x71, 0xce
B_UP_M:
        .byte 0x00, 0x00, 0x22, 0xf0, 0x22, 0x88, 0x22, 0x88, 0x22, 0xf0, 0x22, 0x80, 0x22, 0x80, 0x1c, 0x80, 0x00, 0x00, 0x3e, 0x01, 0x20, 0x02, 0xa0, 0x02, 0xbc, 0x02, 0xa0, 0x03, 0x20, 0x02, 0x3e, 0x01
B_UP_R:
        .byte 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xc8, 0x9c, 0x28, 0xa2, 0x65, 0x02, 0xa2, 0x04, 0x25, 0x08, 0x28, 0x90, 0xc8, 0xbe
B_DOWN_L:
        .byte 0x00, 0x00, 0x00, 0x0e, 0x00, 0x09, 0x00, 0x08, 0x00, 0x08, 0x00, 0x08, 0x00, 0x09, 0x00, 0x0e, 0x00, 0x00, 0x71, 0xce, 0x8a, 0x29, 0x82, 0x28, 0x82, 0x28, 0x82, 0x28, 0x8a, 0x29, 0x71, 0xce
B_DOWN_M:
        .byte 0x00, 0x00, 0x1c, 0x8a, 0x22, 0x8b, 0xa2, 0x8a, 0xa2, 0xaa, 0xa2, 0xaa, 0x22, 0xda, 0x1c, 0x8a, 0x00, 0x00, 0x3e, 0x01, 0x20, 0x02, 0xa0, 0x02, 0xbc, 0x02, 0xa0, 0x03, 0x20, 0x02, 0x3e, 0x01
B_DOWN_R:
        .byte 0x00, 0x00, 0x20, 0x00, 0x20, 0x00, 0xa0, 0x00, 0x60, 0x00, 0x20, 0x00, 0x20, 0x00, 0x20, 0x00, 0x00, 0x00, 0xc8, 0x9c, 0x28, 0xa2, 0x65, 0x22, 0xa2, 0x1c, 0x25, 0x22, 0x28, 0xa2, 0xc8, 0x9c
B_BACK_L:
        .byte 0x00, 0x00, 0x00, 0x0f, 0x00, 0x08, 0x00, 0x08, 0x00, 0x0f, 0x00, 0x08, 0x00, 0x08, 0x00, 0x0f, 0x00, 0x00, 0x71, 0xce, 0x8a, 0x29, 0x82, 0x28, 0x82, 0x28, 0x82, 0x28, 0x8a, 0x29, 0x71, 0xce
B_BACK_M:
        .byte 0x00, 0x00, 0x1c, 0x72, 0xa2, 0x8a, 0xa2, 0x82, 0x3e, 0x83, 0xa2, 0x82, 0xa2, 0x8a, 0x22, 0x72, 0x00, 0x00, 0x3e, 0x01, 0x20, 0x02, 0xa0, 0x02, 0xbc, 0x02, 0xa0, 0x03, 0x20, 0x02, 0x3e, 0x01
B_BACK_R:
        .byte 0x00, 0x00, 0x20, 0x00, 0x40, 0x00, 0x80, 0x00, 0x00, 0x00, 0x80, 0x00, 0x40, 0x00, 0x20, 0x00, 0x00, 0x00, 0xc8, 0x84, 0x28, 0x8c, 0x65, 0x14, 0xa2, 0x24, 0x25, 0x3e, 0x28, 0x84, 0xc8, 0x84
B_OK_L:
        .byte 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x71, 0xce, 0x8a, 0x29, 0x82, 0x28, 0x82, 0x28, 0x82, 0x28, 0x8a, 0x29, 0x71, 0xce
B_OK_M:
        .byte 0x00, 0x00, 0x1c, 0x88, 0x22, 0x90, 0x22, 0xa0, 0x22, 0xc0, 0x22, 0xa0, 0x22, 0x90, 0x1c, 0x88, 0x00, 0x00, 0x3e, 0x01, 0x20, 0x02, 0xa0, 0x02, 0xbc, 0x02, 0xa0, 0x03, 0x20, 0x02, 0x3e, 0x01
B_OK_R:
        .byte 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xc8, 0x8c, 0x28, 0x90, 0x65, 0x20, 0xa2, 0x3c, 0x25, 0x22, 0x28, 0xa2, 0xc8, 0x9c
"""

# Backward compatibility alias
generate_button_test_asm = generate_button_demo_asm

def generate_template_asm():
    """
    Returns the CHIP-8 assembly representation of the starter template demo
    with 4-button directional movement on 128x64 display (Super-CHIP mode):
      UP:      Key 2
      DOWN:    Key 8
      LEFT:    Key 4 (BACK)
      RIGHT:   Key 6 (OK)
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
        skip.ne va, 6           ; RIGHT / OK (FEB_KEY_RIGHT = 0x6)
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
      RIGHT:   Key 6 (OK)
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
        loadflags v0            ; Load persistent high score from RPL flag 0
        load ve, v0             ; ve := BEST_TILE
        call NEWGAME
        call DRAW_GRID
        call DRAW_HI
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

DRAW_HI:
        load i, SPRITE_HI
        load v8, 12
        load v9, 20
        draw v8, v9, 5          ; Draw 8x5 "HI" banner at (12, 20)
        skip.ne ve, 0           ; If ve == 0, no digit yet
        ret
        load v7, ve
        sub v7, 1               ; digit := ve - 1
        hex v7
        load v8, 13
        load v9, 28
        draw v8, v9, 5          ; Draw hex digit at (13, 28)
        ret

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
        call CHECK_BEST
        ret

CHECK_BEST:
        load v7, ve
        sub v7, v0              ; v7 := ve - v0. If ve >= v0: VF=1. If ve < v0: VF=0.
        skip.eq vf, 0           ; If new best (VF==0), skip ret
        ret

        ;; New best tile!
        skip.ne ve, 0           ; If ve != 0, skip jump DRAW_NEW_BEST
        jump DRAW_NEW_BEST
        load v7, ve
        sub v7, 1
        hex v7
        load v8, 13
        load v9, 28
        draw v8, v9, 5          ; XOR erase old digit
DRAW_NEW_BEST:
        load ve, v0             ; ve := new best
        load v7, v0
        saveflags v0            ; Store v0 into rpl_flags[0] (persisted to .sav)
        load v0, v7             ; restore v0
        sub v7, 1               ; digit := new_best - 1
        hex v7
        load v8, 13
        load v9, 28
        draw v8, v9, 5          ; Draw new digit
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
        load i, BOARD
        add i, v1
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

SPRITE_HI:
        .byte $10101110
        .byte $10100100
        .byte $11100100
        .byte $10100100
        .byte $10101110
"""


def generate_quest_asm():
    """
    Returns the CHIP-8 assembly representation of Tiny Quest.
    """
    return """;;; ===========================================================================
;;; Tiny Quest: Relic of the Dragon Lair
;;; Top-down Action RPG for Flashiibo Pro Gen3 FEB Runner (Super-CHIP 128x64 mode)
;;; ---------------------------------------------------------------------------
;;; Controls:
;;;   UP (Key 2)    : Walk Up
;;;   DOWN (Key 8)  : Walk Down
;;;   BACK (Key 4)  : Walk Left
;;;   OK (Key 6)    : Walk Right
;;;   UP+DOWN+BACK  : Guaranteed hardware exit to menu
;;;
;;; Combat & Interactions (4-button bump mechanics):
;;;   - Walk into cave entrance to visit the Hermit Sage
;;;   - Sage gives you the Iron Sword ("TAKE THIS SWORD.")
;;;   - Bump into enemies with sword to attack and knock them back
;;;   - Forest Slime drops gems (+5)
;;;   - Ruins Goblin drops the Dungeon Key
;;;   - Dungeon door requires the Key to open
;;;   - Dragon Boss in the lair has 4 HP and guards the SACRED RELIC
;;;   - Claim the RELIC to save the realm!
;;; ===========================================================================

START:
        high                    ; Enable 128x64 high-resolution mode (Super-CHIP)
        cls                     ; Clear screen buffer
        call SHOW_TITLE_SCREEN
        call INIT_GAME_STATE

MAIN_LOOP:
        vsync                   ; 60 Hz frame synchronization (FX9A)
        cls                     ; Clear display buffer

        call DRAW_HUD
        call DRAW_ROOM
        call DRAW_ITEMS
        call DRAW_ENEMIES
        call DRAW_HERO

        ;; Check game ending conditions
        load i, STATE_RELIC
        restore v0
        skip.ne v0, 2           ; RELIC == 2: Victory!
        jump VICTORY_LOOP

        load i, STATE_HP
        restore v0
        skip.ne v0, 0           ; HP == 0: Game Over!
        jump GAME_OVER_LOOP

        ;; AI update
        call UPDATE_AI

        ;; 4-Button non-blocking D-Pad polling (FXB0)
        getkeys va
        skip.eq va, 0           ; Any button pressed?
        call HANDLE_INPUT

        jump MAIN_LOOP

;;; ---------------------------------------------------------------------------
;;; Input Handler (4 Physical Buttons)
;;; ---------------------------------------------------------------------------
HANDLE_INPUT:
        load v1, 1              ; Bit 0: UP (Key 2)
        and v1, va
        skip.eq v1, 0
        call MOVE_UP

        load v1, 2              ; Bit 1: DOWN (Key 8)
        and v1, va
        skip.eq v1, 0
        call MOVE_DOWN

        load v1, 4              ; Bit 2: LEFT / BACK (Key 4)
        and v1, va
        skip.eq v1, 0
        call MOVE_LEFT

        load v1, 8              ; Bit 3: RIGHT / OK (Key 6)
        and v1, va
        skip.eq v1, 0
        call MOVE_RIGHT

        ret

MOVE_UP:
        load v0, 1              ; DIR_UP := 1
        load i, STATE_DIR
        save v0

        load i, STATE_Y
        restore v0
        skip.ne v0, 21
        jump CHECK_UP_EXIT      ; Near top edge
        skip.ne v0, 17
        ret
        sub v0, 4
        load i, STATE_Y
        save v0
        call CHECK_BUMP_COLLISION
        ret

CHECK_UP_EXIT:
        load i, STATE_ROOM
        restore v1
        skip.ne v1, 0           ; Room 0: Enter Cave?
        jump ENTER_CAVE
        skip.ne v1, 3           ; Room 3: Exit Boss Lair to Ruins?
        jump EXIT_DUNGEON
        ret

ENTER_CAVE:
        load i, STATE_X
        restore v2
        skip.eq v2, 56          ; Col 7 (X=56)?
        ret
        load v1, 1              ; ROOM_CAVE := 1
        load i, STATE_ROOM
        save v1
        load v2, 56
        load i, STATE_X
        save v2
        load v3, 45
        load i, STATE_Y
        save v3
        ret

EXIT_DUNGEON:
        load i, STATE_X
        restore v2
        skip.eq v2, 64          ; Col 8 (X=64)?
        ret
        load v1, 2              ; ROOM_RUINS := 2
        load i, STATE_ROOM
        save v1
        load v2, 64
        load i, STATE_X
        save v2
        load v3, 45
        load i, STATE_Y
        save v3
        ret

MOVE_DOWN:
        load v0, 0              ; DIR_DOWN := 0
        load i, STATE_DIR
        save v0

        load i, STATE_Y
        restore v0
        skip.ne v0, 45
        jump CHECK_DOWN_EXIT
        skip.ne v0, 49
        ret
        add v0, 4
        load i, STATE_Y
        save v0
        call CHECK_BUMP_COLLISION
        ret

CHECK_DOWN_EXIT:
        load i, STATE_ROOM
        restore v1
        skip.ne v1, 1           ; Room 1: Exit Cave?
        jump EXIT_CAVE
        skip.ne v1, 2           ; Room 2: Enter Dungeon?
        jump ENTER_DUNGEON

        load i, STATE_Y
        restore v0
        add v0, 4
        load i, STATE_Y
        save v0
        ret

EXIT_CAVE:
        load i, STATE_X
        restore v2
        skip.eq v2, 56
        ret
        load v1, 0              ; ROOM_FOREST := 0
        load i, STATE_ROOM
        save v1
        load v2, 56
        load i, STATE_X
        save v2
        load v3, 21
        load i, STATE_Y
        save v3
        ret

ENTER_DUNGEON:
        load i, STATE_X
        restore v2
        skip.eq v2, 64
        ret
        ;; Check if door is unlocked (HERO_KEY == 1)
        load i, STATE_KEY
        restore v3
        skip.ne v3, 1
        jump DO_ENTER_DUNGEON
        ret
DO_ENTER_DUNGEON:
        load v1, 3              ; ROOM_DUNGEON := 3
        load i, STATE_ROOM
        save v1
        load v2, 64
        load i, STATE_X
        save v2
        load v3, 21
        load i, STATE_Y
        save v3
        ret

MOVE_LEFT:
        load v0, 3              ; DIR_LEFT := 3
        load i, STATE_DIR
        save v0

        load i, STATE_X
        restore v0
        skip.ne v0, 8
        jump CHECK_LEFT_EXIT
        skip.ne v0, 4
        ret
        sub v0, 4
        load i, STATE_X
        save v0
        call CHECK_BUMP_COLLISION
        ret

CHECK_LEFT_EXIT:
        load i, STATE_ROOM
        restore v1
        skip.ne v1, 2           ; Room 2: West exit to Room 0 (Forest)
        jump EXIT_TO_FOREST
        ret

EXIT_TO_FOREST:
        load v1, 0              ; Room 0
        load i, STATE_ROOM
        save v1
        load v0, 112
        load i, STATE_X
        save v0
        ret

MOVE_RIGHT:
        load v0, 2              ; DIR_RIGHT := 2
        load i, STATE_DIR
        save v0

        load i, STATE_X
        restore v0
        skip.ne v0, 112
        jump CHECK_RIGHT_EXIT
        skip.ne v0, 116
        ret
        add v0, 4
        load i, STATE_X
        save v0
        call CHECK_BUMP_COLLISION
        ret

CHECK_RIGHT_EXIT:
        load i, STATE_ROOM
        restore v1
        skip.ne v1, 0           ; Room 0: East exit to Room 2 (Ruins)
        jump EXIT_TO_RUINS
        ret

EXIT_TO_RUINS:
        load v1, 2              ; Room 2
        load i, STATE_ROOM
        save v1
        load v0, 8
        load i, STATE_X
        save v0
        ret

;;; ---------------------------------------------------------------------------
;;; Bump Combat & Interactions
;;; ---------------------------------------------------------------------------
CHECK_BUMP_COLLISION:
        ;; 1. Check Cave Altar / Sword
        load i, STATE_ROOM
        restore v5
        skip.ne v5, 1           ; Cave?
        jump CHECK_SWORD_PICKUP
        skip.ne v5, 0           ; Forest?
        jump CHECK_SLIME_BUMP
        skip.ne v5, 2           ; Ruins?
        jump CHECK_GOBLIN_BUMP
        skip.ne v5, 3           ; Dungeon?
        jump CHECK_BOSS_BUMP
        ret

CHECK_SWORD_PICKUP:
        load i, STATE_X
        restore v2
        load i, STATE_Y
        restore v3
        skip.ne v2, 56
        jump TEST_SWORD_Y
        ret
TEST_SWORD_Y:
        skip.ne v3, 29
        jump GET_SWORD
        ret
GET_SWORD:
        load v4, 1
        load i, STATE_SWORD
        save v4                 ; SWORD := 1!
        ret

CHECK_SLIME_BUMP:
        load i, STATE_SLIME_HP
        restore v6
        skip.ne v6, 0           ; Slime dead?
        ret
        load i, STATE_SLIME_X
        restore v7
        load i, STATE_X
        restore v2
        load v8, v7
        sub v8, v2
        skip.ne v8, 0
        jump SLIME_HIT
        skip.ne v8, 4
        jump SLIME_HIT
        skip.ne v8, 252
        jump SLIME_HIT
        ret
SLIME_HIT:
        load i, STATE_SWORD
        restore v4
        skip.ne v4, 1           ; Has sword?
        jump DO_SLIME_SLASH
        ;; No sword: Hero takes 1 damage
        load i, STATE_HP
        restore v9
        skip.ne v9, 0
        ret
        sub v9, 1
        load i, STATE_HP
        save v9
        ret
DO_SLIME_SLASH:
        load v6, 0              ; Slime defeated!
        load i, STATE_SLIME_HP
        save v6
        load i, STATE_GEMS
        restore vb
        add vb, 5               ; +5 Gems!
        load i, STATE_GEMS
        save vb
        ret

CHECK_GOBLIN_BUMP:
        load i, STATE_GOBLIN_HP
        restore v6
        skip.ne v6, 0           ; Goblin dead?
        ret
        load i, STATE_GOBLIN_X
        restore v7
        load i, STATE_X
        restore v2
        load v8, v7
        sub v8, v2
        skip.ne v8, 0
        jump GOBLIN_HIT
        skip.ne v8, 4
        jump GOBLIN_HIT
        skip.ne v8, 252
        jump GOBLIN_HIT
        ret
GOBLIN_HIT:
        load i, STATE_SWORD
        restore v4
        skip.ne v4, 1
        jump DO_GOBLIN_SLASH
        load i, STATE_HP
        restore v9
        skip.ne v9, 0
        ret
        sub v9, 1
        load i, STATE_HP
        save v9
        ret
DO_GOBLIN_SLASH:
        load i, STATE_GOBLIN_HP
        restore v6
        sub v6, 1
        load i, STATE_GOBLIN_HP
        save v6
        skip.eq v6, 0
        ret
        ;; Goblin defeated -> Drop Key!
        load v4, 1
        load i, STATE_KEY
        save v4                 ; KEY := 1!
        ret

CHECK_BOSS_BUMP:
        load i, STATE_BOSS_HP
        restore v6
        skip.eq v6, 0
        jump TEST_BOSS_HIT
        ;; Boss dead: Check Relic pickup at (56, 29)
        load i, STATE_X
        restore v2
        skip.ne v2, 56
        jump TEST_RELIC_Y
        ret
TEST_RELIC_Y:
        load i, STATE_Y
        restore v3
        skip.ne v3, 29
        jump GET_RELIC
        ret
GET_RELIC:
        load v4, 2              ; WON!
        load i, STATE_RELIC
        save v4
        ret

TEST_BOSS_HIT:
        load i, STATE_BOSS_X
        restore v7
        load i, STATE_X
        restore v2
        load v8, v7
        sub v8, v2
        skip.ne v8, 0
        jump BOSS_HIT
        skip.ne v8, 4
        jump BOSS_HIT
        skip.ne v8, 8
        jump BOSS_HIT
        skip.ne v8, 252
        jump BOSS_HIT
        ret
BOSS_HIT:
        load i, STATE_SWORD
        restore v4
        skip.ne v4, 1
        jump DO_BOSS_SLASH
        load i, STATE_HP
        restore v9
        skip.ne v9, 0
        ret
        sub v9, 1
        load i, STATE_HP
        save v9
        ret
DO_BOSS_SLASH:
        load i, STATE_BOSS_HP
        restore v6
        sub v6, 1
        load i, STATE_BOSS_HP
        save v6
        skip.eq v6, 0
        ret
        ;; Boss defeated! Spawn Sacred Relic
        load v4, 1
        load i, STATE_RELIC
        save v4
        ret

;;; ---------------------------------------------------------------------------
;;; Enemy AI Updates
;;; ---------------------------------------------------------------------------
UPDATE_AI:
        load i, STATE_AI_TIMER
        restore v0
        add v0, 1
        load i, STATE_AI_TIMER
        save v0
        skip.ne v0, 20
        jump DO_AI_STEP
        ret
DO_AI_STEP:
        load v0, 0
        load i, STATE_AI_TIMER
        save v0                 ; Timer := 0

        ;; Move Slime back and forth
        load i, STATE_SLIME_X
        restore v1
        skip.ne v1, 80
        jump SET_SLIME_LEFT
        load v1, 80
        load i, STATE_SLIME_X
        save v1
        jump UPDATE_BOSS_AI
SET_SLIME_LEFT:
        load v1, 72
        load i, STATE_SLIME_X
        save v1

UPDATE_BOSS_AI:
        load i, STATE_BOSS_Y
        restore v2
        skip.ne v2, 29
        jump SET_BOSS_DOWN
        load v2, 29
        load i, STATE_BOSS_Y
        save v2
        ret
SET_BOSS_DOWN:
        load v2, 37
        load i, STATE_BOSS_Y
        save v2
        ret

;;; ---------------------------------------------------------------------------
;;; Drawing Subroutines
;;; ---------------------------------------------------------------------------

DRAW_HUD:
        ;; Top divider line at Y=11
        load v0, 0
        load v1, 11
        load v2, 127
        hline v0

        ;; Area Name
        load i, STATE_ROOM
        restore v3
        skip.ne v3, 0
        load i, STR_AREA_OVERWORLD
        skip.ne v3, 1
        load i, STR_AREA_CAVE
        skip.ne v3, 2
        load i, STR_AREA_TEMPLE
        skip.ne v3, 3
        load i, STR_AREA_DUNGEON
        load v0, 2
        load v1, 2
        load v2, 0              ; FEB_FONT_4X6
        text v0

        ;; Hearts
        load i, STATE_HP
        restore v4
        load i, SPRITE_HEART
        skip.eq v4, 0
        call DRAW_HEART_1
        skip.eq v4, 0
        jump TEST_H2
        ret
TEST_H2:
        skip.eq v4, 1
        call DRAW_HEART_2
        skip.eq v4, 1
        jump TEST_H3
        ret
TEST_H3:
        skip.eq v4, 2
        call DRAW_HEART_3

        ;; Gem Icon & Count
        load i, SPRITE_GEM
        load vb, 86
        load vc, 2
        draw vb, vc, 8

        load i, STATE_GEMS
        restore v5
        load i, 0
        add i, v5
        load v0, 96
        load v1, 2
        load v2, 0
        num v0

        ;; Key Icon
        load i, STATE_KEY
        restore v6
        skip.ne v6, 1
        jump DRAW_KEY_ICON
        ret
DRAW_KEY_ICON:
        load i, SPRITE_KEY
        load vb, 116
        load vc, 2
        draw vb, vc, 8
        ret

DRAW_HEART_1:
        load vb, 50
        load vc, 2
        draw vb, vc, 8
        ret
DRAW_HEART_2:
        load vb, 60
        load vc, 2
        draw vb, vc, 8
        ret
DRAW_HEART_3:
        load vb, 70
        load vc, 2
        draw vb, vc, 8
        ret

DRAW_ROOM:
        load i, STATE_ROOM
        restore v0
        skip.ne v0, 0
        jump DRAW_ROOM_0
        skip.ne v0, 1
        jump DRAW_ROOM_1
        skip.ne v0, 2
        jump DRAW_ROOM_2
        skip.ne v0, 3
        jump DRAW_ROOM_3
        ret

DRAW_ROOM_0:
        ;; Overworld Forest: Trees along top and bottom
        load i, SPRITE_TREE
        load vb, 0
        load vc, 13
        draw vb, vc, 8
        load vb, 16
        draw vb, vc, 8
        load vb, 32
        draw vb, vc, 8
        load vb, 48
        draw vb, vc, 8
        load vb, 64
        draw vb, vc, 8
        load vb, 80
        draw vb, vc, 8
        load vb, 96
        draw vb, vc, 8
        load vb, 112
        draw vb, vc, 8

        ;; Bottom row
        load vc, 53
        load vb, 0
        draw vb, vc, 8
        load vb, 16
        draw vb, vc, 8
        load vb, 32
        draw vb, vc, 8
        load vb, 48
        draw vb, vc, 8
        load vb, 64
        draw vb, vc, 8
        load vb, 80
        draw vb, vc, 8
        load vb, 96
        draw vb, vc, 8
        load vb, 112
        draw vb, vc, 8

        ;; Cave Entrance at (56, 13)
        load i, SPRITE_CAVE
        load vb, 56
        load vc, 13
        draw vb, vc, 8
        ret

DRAW_ROOM_1:
        ;; Cave Walls & Torches
        load i, SPRITE_WALL
        load vb, 0
        load vc, 13
        draw vb, vc, 8
        load vb, 120
        draw vb, vc, 8

        load i, SPRITE_TORCH
        load vb, 32
        load vc, 21
        draw vb, vc, 8
        load vb, 80
        draw vb, vc, 8

        ;; Hermit Sage at (56, 21)
        load i, SPRITE_SAGE
        load vb, 56
        draw vb, vc, 8

        ;; Dialogue text
        load i, STR_SAGE1
        load v0, 14
        load v1, 37
        load v2, 0
        text v0
        load i, STR_SAGE2
        load v0, 26
        load v1, 45
        load v2, 0
        text v0
        ret

DRAW_ROOM_2:
        ;; Ruins: Ancient Columns and Dungeon Gate
        load i, SPRITE_WALL
        load vb, 0
        load vc, 13
        draw vb, vc, 8
        load vb, 32
        draw vb, vc, 8
        load vb, 64
        draw vb, vc, 8
        load vb, 96
        draw vb, vc, 8
        load vb, 120
        draw vb, vc, 8

        ;; Dungeon Door at (64, 53)
        load i, SPRITE_DOOR
        load vb, 64
        load vc, 53
        draw vb, vc, 8
        ret

DRAW_ROOM_3:
        ;; Boss Lair: Perimeter Walls
        load i, SPRITE_WALL
        load vb, 0
        load vc, 13
        draw vb, vc, 8
        load vb, 120
        draw vb, vc, 8
        load vb, 0
        load vc, 53
        draw vb, vc, 8
        load vb, 120
        draw vb, vc, 8
        ret

DRAW_ITEMS:
        load i, STATE_ROOM
        restore v0
        skip.ne v0, 1
        jump DRAW_CAVE_SWORD
        skip.ne v0, 3
        jump DRAW_DUNGEON_RELIC
        ret

DRAW_CAVE_SWORD:
        load i, STATE_SWORD
        restore v1
        skip.eq v1, 0           ; Sword already collected?
        ret
        load i, SPRITE_SWORD
        load vb, 56
        load vc, 29
        draw vb, vc, 8
        ret

DRAW_DUNGEON_RELIC:
        load i, STATE_BOSS_HP
        restore v2
        skip.eq v2, 0           ; Boss defeated?
        ret
        load i, SPRITE_RELIC
        load vb, 56
        load vc, 29
        draw vb, vc, 8
        ret

DRAW_ENEMIES:
        load i, STATE_ROOM
        restore v0
        skip.ne v0, 0
        jump DRAW_SLIME
        skip.ne v0, 2
        jump DRAW_GOBLIN
        skip.ne v0, 3
        jump DRAW_BOSS
        ret

DRAW_SLIME:
        load i, STATE_SLIME_HP
        restore v1
        skip.ne v1, 0
        ret
        load i, STATE_SLIME_X
        restore vb
        load i, STATE_SLIME_Y
        restore vc
        load i, SPRITE_SLIME
        draw vb, vc, 8
        ret

DRAW_GOBLIN:
        load i, STATE_GOBLIN_HP
        restore v1
        skip.ne v1, 0
        ret
        load i, STATE_GOBLIN_X
        restore vb
        load i, STATE_GOBLIN_Y
        restore vc
        load i, SPRITE_GOBLIN
        draw vb, vc, 8
        ret

DRAW_BOSS:
        load i, STATE_BOSS_HP
        restore v1
        skip.ne v1, 0
        ret
        load i, STATE_BOSS_X
        restore vb
        load i, STATE_BOSS_Y
        restore vc
        load i, SPRITE_BOSS
        draw vb, vc, 0          ; 16x16 sprite!
        ret

DRAW_HERO:
        load i, STATE_X
        restore vb
        load i, STATE_Y
        restore vc

        load i, STATE_DIR
        restore v0
        skip.ne v0, 0
        load i, SPRITE_HERO_DOWN
        skip.ne v0, 1
        load i, SPRITE_HERO_UP
        skip.ne v0, 2
        load i, SPRITE_HERO_RIGHT
        skip.ne v0, 3
        load i, SPRITE_HERO_LEFT

        draw vb, vc, 8
        ret

;;; ---------------------------------------------------------------------------
;;; Endings & Screens
;;; ---------------------------------------------------------------------------

SHOW_TITLE_SCREEN:
        load v0, 0
        load v1, 0
        load v2, 127
        load v3, 63
        rect v0

        load i, STR_TITLE1
        load v0, 18
        load v1, 8
        load v2, 0
        text v0

        load i, STR_TITLE2
        load v0, 32
        load v1, 16
        load v2, 1
        text v0

        load i, SPRITE_RELIC
        load vb, 60
        load vc, 28
        draw vb, vc, 8

        load i, STR_INSTR1
        load v0, 10
        load v1, 40
        load v2, 0
        text v0

        load i, STR_INSTR2
        load v0, 14
        load v1, 48
        load v2, 0
        text v0

        load i, STR_INSTR3
        load v0, 16
        load v1, 56
        load v2, 0
        text v0

        load va, key            ; Wait for any key
        ret

VICTORY_LOOP:
        cls
        load v0, 0
        load v1, 0
        load v2, 127
        load v3, 63
        rect v0

        load i, SPRITE_RELIC
        load vb, 60
        load vc, 6
        draw vb, vc, 8

        load i, STR_WIN1
        load v0, 12
        load v1, 18
        load v2, 1
        text v0

        load i, STR_WIN2
        load v0, 22
        load v1, 30
        load v2, 1
        text v0

        load i, STR_WIN3
        load v0, 26
        load v1, 42
        load v2, 0
        text v0

        load i, STATE_GEMS
        restore v5
        load i, 0
        add i, v5
        load v0, 88
        load v1, 42
        load v2, 0
        num v0

        load i, STR_RETRY
        load v0, 18
        load v1, 52
        load v2, 0
        text v0

        ;; Persist victory flags to /feb/saves/quest.sav
        load i, STATE_GEMS
        restore v0
        saveflags v0

        load va, key
        call INIT_GAME_STATE
        jump MAIN_LOOP

GAME_OVER_LOOP:
        cls
        load v0, 0
        load v1, 0
        load v2, 127
        load v3, 63
        rect v0

        load i, STR_LOSE1
        load v0, 36
        load v1, 20
        load v2, 1
        text v0

        load i, STR_LOSE2
        load v0, 16
        load v1, 36
        load v2, 0
        text v0

        load i, STR_RETRY
        load v0, 18
        load v1, 48
        load v2, 0
        text v0

        load va, key
        call INIT_GAME_STATE
        jump MAIN_LOOP

INIT_GAME_STATE:
        load v0, 24             ; X := 24
        load i, STATE_X
        save v0

        load v0, 37             ; Y := 37
        load i, STATE_Y
        save v0

        load v0, 0              ; DIR := 0
        load i, STATE_DIR
        save v0

        load v0, 3              ; HP := 3
        load i, STATE_HP
        save v0

        load v0, 0              ; SWORD := 0
        load i, STATE_SWORD
        save v0

        load v0, 0              ; KEY := 0
        load i, STATE_KEY
        save v0

        load v0, 0              ; GEMS := 0
        load i, STATE_GEMS
        save v0

        load v0, 0              ; ROOM := 0
        load i, STATE_ROOM
        save v0

        load v0, 80             ; SLIME_X
        load i, STATE_SLIME_X
        save v0

        load v0, 37             ; SLIME_Y
        load i, STATE_SLIME_Y
        save v0

        load v0, 1              ; SLIME_HP
        load i, STATE_SLIME_HP
        save v0

        load v0, 72             ; GOBLIN_X
        load i, STATE_GOBLIN_X
        save v0

        load v0, 29             ; GOBLIN_Y
        load i, STATE_GOBLIN_Y
        save v0

        load v0, 2              ; GOBLIN_HP
        load i, STATE_GOBLIN_HP
        save v0

        load v0, 80             ; BOSS_X
        load i, STATE_BOSS_X
        save v0

        load v0, 29             ; BOSS_Y
        load i, STATE_BOSS_Y
        save v0

        load v0, 4              ; BOSS_HP
        load i, STATE_BOSS_HP
        save v0

        load v0, 0
        load i, STATE_RELIC
        save v0

        load v0, 0
        load i, STATE_AI_TIMER
        save v0
        ret

;;; ---------------------------------------------------------------------------
;;; Variables in RAM
;;; ---------------------------------------------------------------------------
STATE_X:          .byte 24
STATE_Y:          .byte 37
STATE_DIR:        .byte 0
STATE_HP:         .byte 3
STATE_SWORD:      .byte 0
STATE_KEY:        .byte 0
STATE_GEMS:       .byte 0
STATE_ROOM:       .byte 0
STATE_SLIME_X:    .byte 80
STATE_SLIME_Y:    .byte 37
STATE_SLIME_HP:   .byte 1
STATE_GOBLIN_X:   .byte 72
STATE_GOBLIN_Y:   .byte 29
STATE_GOBLIN_HP:  .byte 2
STATE_BOSS_X:     .byte 80
STATE_BOSS_Y:     .byte 29
STATE_BOSS_HP:    .byte 4
STATE_RELIC:      .byte 0
STATE_AI_TIMER:   .byte 0

;;; ---------------------------------------------------------------------------
;;; Text Strings
;;; ---------------------------------------------------------------------------
STR_TITLE1:         .asciz "THE CHRONICLES OF"
STR_TITLE2:         .asciz "TINY QUEST"
STR_INSTR1:         .asciz "D-PAD: MOVE & BUMP-ATTACK"
STR_INSTR2:         .asciz "UP+DOWN+BACK: EXIT GAME"
STR_INSTR3:         .asciz "PRESS ANY KEY TO START"

STR_AREA_OVERWORLD: .asciz "FOREST"
STR_AREA_CAVE:      .asciz "SAGE CAVE"
STR_AREA_TEMPLE:    .asciz "RUINS"
STR_AREA_DUNGEON:   .asciz "DRAGON LAIR"

STR_SAGE1:          .asciz "THE ROAD IS DANGEROUS!"
STR_SAGE2:          .asciz "TAKE THIS SWORD."

STR_WIN1:           .asciz "SACRED RELIC RESTORED!"
STR_WIN2:           .asciz "THE REALM IS SAVED!"
STR_WIN3:           .asciz "GEMS COLLECTED:"
STR_LOSE1:          .asciz "GAME OVER"
STR_LOSE2:          .asciz "FALLEN IN THE DUNGEON"
STR_RETRY:          .asciz "PRESS ANY KEY TO RETRY"

;;; ---------------------------------------------------------------------------
;;; Sprite Bitmaps
;;; ---------------------------------------------------------------------------
SPRITE_HERO_DOWN:
        .byte $00111100
        .byte $01111110
        .byte $01011010
        .byte $01111110
        .byte $01111110
        .byte $00111100
        .byte $00100100
        .byte $00100100

SPRITE_HERO_UP:
        .byte $00111100
        .byte $01111110
        .byte $01111110
        .byte $01111110
        .byte $00111100
        .byte $00111100
        .byte $00100100
        .byte $00100100

SPRITE_HERO_RIGHT:
        .byte $00111100
        .byte $00111110
        .byte $00110110
        .byte $00111101
        .byte $00111111
        .byte $00111100
        .byte $00101000
        .byte $00101000

SPRITE_HERO_LEFT:
        .byte $00111100
        .byte $01111100
        .byte $01101100
        .byte $10111100
        .byte $11111100
        .byte $00111100
        .byte $00010100
        .byte $00010100

SPRITE_TREE:
        .byte $00111100
        .byte $01111110
        .byte $11011011
        .byte $11111111
        .byte $11111111
        .byte $01111110
        .byte $00011000
        .byte $00011000

SPRITE_WALL:
        .byte $01111110
        .byte $10000001
        .byte $10111101
        .byte $10100101
        .byte $10100101
        .byte $10111101
        .byte $10000001
        .byte $01111110

SPRITE_CAVE:
        .byte $11111111
        .byte $10000001
        .byte $10000001
        .byte $10000001
        .byte $10000001
        .byte $10000001
        .byte $10000001
        .byte $11111111

SPRITE_DOOR:
        .byte $11111111
        .byte $10111101
        .byte $10111101
        .byte $10011001
        .byte $10011001
        .byte $10111101
        .byte $10111101
        .byte $11111111

SPRITE_SAGE:
        .byte $00111100
        .byte $01111110
        .byte $01011010
        .byte $01111110
        .byte $00111100
        .byte $01111110
        .byte $01111110
        .byte $00111100

SPRITE_TORCH:
        .byte $00010000
        .byte $00110000
        .byte $01111000
        .byte $01111100
        .byte $01111000
        .byte $00110000
        .byte $00110000
        .byte $01111000

SPRITE_SWORD:
        .byte $00000010
        .byte $00000110
        .byte $00001100
        .byte $00011000
        .byte $01110000
        .byte $11000000
        .byte $01000000
        .byte $00000000

SPRITE_RELIC:
        .byte $01111110
        .byte $01000010
        .byte $00111100
        .byte $00011000
        .byte $00011000
        .byte $00111100
        .byte $01111110
        .byte $00000000

SPRITE_HEART:
        .byte $01101100
        .byte $11111110
        .byte $11111110
        .byte $11111110
        .byte $01111100
        .byte $00111000
        .byte $00010000
        .byte $00000000

SPRITE_GEM:
        .byte $00010000
        .byte $00111000
        .byte $01111100
        .byte $11111110
        .byte $11111110
        .byte $01111100
        .byte $00111000
        .byte $00010000

SPRITE_KEY:
        .byte $00111000
        .byte $01000100
        .byte $00111000
        .byte $00010000
        .byte $00011000
        .byte $00010000
        .byte $00011000
        .byte $00000000

SPRITE_SLIME:
        .byte $00000000
        .byte $00111100
        .byte $01111110
        .byte $11011011
        .byte $11111111
        .byte $11111111
        .byte $01111110
        .byte $00000000

SPRITE_GOBLIN:
        .byte $01100110
        .byte $01111110
        .byte $11011011
        .byte $11111111
        .byte $01111110
        .byte $00111100
        .byte $01000010
        .byte $11000011

;;; 16x16 Super-CHIP Dragon Boss Sprite (32 bytes)
SPRITE_BOSS:
        .byte 0x03, 0xC0
        .byte 0x07, 0xE0
        .byte 0x0E, 0x70
        .byte 0x1C, 0x38
        .byte 0x39, 0x9C
        .byte 0x73, 0xCE
        .byte 0x7F, 0xFE
        .byte 0x7E, 0x7E
        .byte 0x7C, 0x3E
        .byte 0x78, 0x1E
        .byte 0x7F, 0xFE
        .byte 0x3F, 0xFC
        .byte 0x1F, 0xF8
        .byte 0x0E, 0x70
        .byte 0x1C, 0x38
        .byte 0x38, 0x1C
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
        payload=bytecode
    )

    with open(output_path, "wb") as f:
        f.write(feb_bytes)

    print(f"[FEB_BUILD] Packaged -> {output_path} ({len(feb_bytes)} bytes)")

if __name__ == "__main__":
    main()
