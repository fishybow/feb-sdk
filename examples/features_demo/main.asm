;;; Features & Primitives Showcase for Flashiibo FEB (Super-CHIP 128x64 mode)
;;;
;;; Demonstrates custom opcodes:
;;;   - vsync (FX9A)
;;;   - rect (FX94), fillrect (FX95), circle (FX96), disc (FX97)
;;;   - text (FXA0), num (FXA3)
;;;   - testpixel (FX99)
;;;   - getkeys (FXB0)
;;;
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
