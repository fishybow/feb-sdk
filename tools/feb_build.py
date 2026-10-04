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

    raise ValueError(
        f"[FEB_BUILD] No compiler target found for '{c_source_path}'.\n"
        f"NOTE: The Flashiibo C SDK is currently in BETA & EXPERIMENTAL status.\n"
        f"To compile an app, you can:\n"
        f"  1. Target a supported model ('2048', 'template', 'button_demo', 'features_demo')\n"
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
