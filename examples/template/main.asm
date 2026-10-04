;;; Flashiibo FEB Starter Template (CHIP-8 Assembly)
;;; Targets Flashiibo Gen3 4-button directional layout and 128x64 OLED display.
;;;
;;; Controls:
;;;   UP:      0x2 (FEB_KEY_UP)
;;;   DOWN:    0x8 (FEB_KEY_DOWN)
;;;   LEFT:    0x4 (FEB_KEY_LEFT / BACK)
;;;   RIGHT:   0x6 (FEB_KEY_RIGHT / OK)

START:
        high                    ; Enable 128x64 high-resolution mode
        load v1, 60             ; X coordinate := 60
        load v2, 28             ; Y coordinate := 28
        load i, SPRITE_PLAYER
        draw v1, v2, 8          ; Draw initial sprite

LOOP:
        load va, key            ; Wait for key press
        load i, SPRITE_PLAYER
        draw v1, v2, 8          ; Erase previous sprite (XOR)

        skip.ne va, 2           ; Check UP
        call MOVE_UP
        skip.ne va, 8           ; Check DOWN
        call MOVE_DOWN
        skip.ne va, 4           ; Check LEFT
        call MOVE_LEFT
        skip.ne va, 6           ; Check RIGHT
        call MOVE_RIGHT

        load i, SPRITE_PLAYER
        draw v1, v2, 8          ; Draw new sprite
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
