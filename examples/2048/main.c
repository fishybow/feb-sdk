/**
 * @file main.c
 * @brief 2048 Game for Flashiibo Pro Gen3 FEB Runner (.feb)
 *
 * Implements the classic 2048 tile puzzle on a 4x4 grid optimized for
 * Flashiibo's 128x64 monochrome OLED display and 4 physical buttons:
 *   - UP:      Slide Up (Key 0x2)
 *   - DOWN:    Slide Down (Key 0x8)
 *   - BACK:    Slide Left (Key 0x4)
 *   - OK:      Slide Right (Key 0x6)
 * Pressing UP + DOWN + BACK together guarantees immediate game exit back to the FEB Runner menu.
 */

#include "../../include/feb.h"

#define BOARD_SIZE    16
#define GRID_WIDTH     4
#define GRID_HEIGHT    4

/* Grid screen placement: 4x4 cells of 16x16 pixels each centered on 128x64 display */
#define GRID_ORIGIN_X 32
#define GRID_ORIGIN_Y  0
#define CELL_SIZE     16
#define TILE_OFFSET_X  6
#define TILE_OFFSET_Y  5

/* 16x16 Grid line sprites (2 bytes per row * 16 rows = 32 bytes) */
static const uint8_t SPRITE_GRID_16[32] = {
    0xFF, 0xFF,
    0x80, 0x00, 0x80, 0x00, 0x80, 0x00,
    0x80, 0x00, 0x80, 0x00, 0x80, 0x00,
    0x80, 0x00, 0x80, 0x00, 0x80, 0x00,
    0x80, 0x00, 0x80, 0x00, 0x80, 0x00,
    0x80, 0x00, 0x80, 0x00
};

static const uint8_t SPRITE_GRID_BOTTOM_16[32] = {
    0xFF, 0xFF,
    0x80, 0x00, 0x80, 0x00, 0x80, 0x00,
    0x80, 0x00, 0x80, 0x00, 0x80, 0x00,
    0x80, 0x00, 0x80, 0x00, 0x80, 0x00,
    0x80, 0x00, 0x80, 0x00, 0x80, 0x00,
    0x80, 0x00, 0x80, 0x00,
    0xFF, 0xFF
};

static const uint8_t SPRITE_GRID_RIGHT_16[32] = {
    0x80, 0x00, 0x80, 0x00, 0x80, 0x00, 0x80, 0x00,
    0x80, 0x00, 0x80, 0x00, 0x80, 0x00, 0x80, 0x00,
    0x80, 0x00, 0x80, 0x00, 0x80, 0x00, 0x80, 0x00,
    0x80, 0x00, 0x80, 0x00, 0x80, 0x00, 0x80, 0x00
};

/* 8x5 "HI" banner sprite for high score label */
static const uint8_t SPRITE_HI[5] = {
    0xAE, 0xA4, 0xE4, 0xA4, 0xAE
};

/* Board state: 16 tiles (4x4)
 *   0: Empty cell
 *   1: Tile "2"    (displays hex digit '0')
 *   2: Tile "4"    (displays hex digit '1')
 *   3: Tile "8"    (displays hex digit '2')
 *  ...
 *  10: Tile "1024" (displays hex digit '9')
 *  11: Tile "2048" (displays hex digit 'A' - TARGET WIN)
 */
static uint8_t board[BOARD_SIZE];
static uint8_t new_board[BOARD_SIZE];

/* Persistent high score: highest tile level achieved (1..11) saved in /feb/saves/2048.sav */
static uint8_t best_tile = 0;

/* -------------------------------------------------------------------------
 * Board Rendering
 * ------------------------------------------------------------------------- */

static void draw_grid(void) {
    uint8_t k = 0;
    uint8_t x = GRID_ORIGIN_X;
    uint8_t y = GRID_ORIGIN_Y;

    while (k < BOARD_SIZE) {
        if (y == 48) {
            feb_draw_sprite16(x, y, SPRITE_GRID_BOTTOM_16);
        } else {
            feb_draw_sprite16(x, y, SPRITE_GRID_16);
        }

        k++;
        x += CELL_SIZE;
        if (x == 96) {
            /* Draw right-hand column border */
            feb_draw_sprite16(x, y, SPRITE_GRID_RIGHT_16);
            x = GRID_ORIGIN_X;
            y += CELL_SIZE;
        }
    }
}

static void draw_board(void) {
    uint8_t k = 0;
    uint8_t x = GRID_ORIGIN_X + TILE_OFFSET_X;
    uint8_t y = GRID_ORIGIN_Y + TILE_OFFSET_Y;

    while (k < BOARD_SIZE) {
        uint8_t val = board[k];
        if (val > 0) {
            /* Draw built-in hex digit glyph for tile level (val - 1) */
            feb_draw_digit(x, y, val - 1);
        }

        k++;
        x += CELL_SIZE;
        if (x == (GRID_ORIGIN_X + TILE_OFFSET_X + 64)) {
            x = GRID_ORIGIN_X + TILE_OFFSET_X;
            y += CELL_SIZE;
        }
    }
}

static void draw_best(void) {
    feb_draw_sprite(12, 20, 5, SPRITE_HI);
    if (best_tile > 0) {
        feb_draw_digit(13, 28, best_tile - 1);
    }
}

/* -------------------------------------------------------------------------
 * Board Manipulation & Sliding Algorithms
 * ------------------------------------------------------------------------- */

static void blit_board(void) {
    for (uint8_t i = 0; i < BOARD_SIZE; i++) {
        board[i] = new_board[i];
        new_board[i] = 0;
    }
}

/**
 * @brief Rotates the 4x4 board 90 degrees clockwise.
 *
 * Maps:
 *   0 1 2 3      c 8 4 0
 *   4 5 6 7  ->  d 9 5 1
 *   8 9 a b      e a 6 2
 *   c d e f      f b 7 3
 */
static void rotate_board_cw(void) {
    uint8_t k = 0;
    uint8_t k_prime = 3;
    int8_t row = 3;

    while (k < BOARD_SIZE) {
        new_board[k_prime] = board[k];
        k++;
        k_prime += 4;

        if ((k & 0x03) == 0) {
            row--;
            k_prime = row;
        }
    }
    blit_board();
}

/**
 * @brief Slides and merges tiles to the left on each 4-tile row.
 *
 * @return true if any tile moved or merged, false otherwise.
 */
static bool slide_left(void) {
    bool moved = false;

    for (uint8_t row = 0; row < GRID_HEIGHT; row++) {
        uint8_t write_idx = row * GRID_WIDTH;
        uint8_t last_val = 0;

        for (uint8_t col = 0; col < GRID_WIDTH; col++) {
            uint8_t read_idx = row * GRID_WIDTH + col;
            uint8_t val = board[read_idx];
            if (val == 0) continue;

            if (val == last_val) {
                /* Merge with previous tile in new row */
                uint8_t merged_val = val + 1;
                new_board[write_idx - 1] = merged_val;
                last_val = 0;
                moved = true;

                if (merged_val > best_tile) {
                    if (best_tile > 0) {
                        /* XOR erase previous high score digit */
                        feb_draw_digit(13, 28, best_tile - 1);
                    }
                    best_tile = merged_val;
                    feb_draw_digit(13, 28, best_tile - 1);
                    feb_save_flags(&best_tile, 1);
                }
            } else {
                last_val = val;
                new_board[write_idx] = val;
                if (read_idx != write_idx) {
                    moved = true;
                }
                write_idx++;
            }
        }
    }

    blit_board();
    return moved;
}

static bool slide_down(void) {
    rotate_board_cw();
    bool moved = slide_left();
    rotate_board_cw();
    rotate_board_cw();
    rotate_board_cw();
    return moved;
}

static bool slide_right(void) {
    rotate_board_cw();
    rotate_board_cw();
    bool moved = slide_left();
    rotate_board_cw();
    rotate_board_cw();
    return moved;
}

static bool slide_up(void) {
    rotate_board_cw();
    rotate_board_cw();
    rotate_board_cw();
    bool moved = slide_left();
    rotate_board_cw();
    return moved;
}

/* -------------------------------------------------------------------------
 * Random Tile Spawning & Initialization
 * ------------------------------------------------------------------------- */

static void place_random_tile(void) {
    /* Count empty tiles first to prevent infinite loop on full board */
    uint8_t empty_count = 0;
    for (uint8_t i = 0; i < BOARD_SIZE; i++) {
        if (board[i] == 0) empty_count++;
    }
    if (empty_count == 0) return;

    /* 1/8 chance of tile value 2 ("4"), 7/8 chance of tile value 1 ("2") */
    uint8_t tile_val = (feb_rand(0x07) == 0) ? 2 : 1;

    /* Pick a random empty position */
    uint8_t target_empty = feb_rand(0x0F) % empty_count;
    uint8_t scan_idx = 0;

    while (1) {
        if (board[scan_idx] == 0) {
            if (target_empty == 0) {
                board[scan_idx] = tile_val;
                return;
            }
            target_empty--;
        }
        scan_idx = (scan_idx + 1) & 0x0F;
    }
}

static void new_game(void) {
    for (uint8_t i = 0; i < BOARD_SIZE; i++) {
        board[i] = 0;
        new_board[i] = 0;
    }
}

/* -------------------------------------------------------------------------
 * Main Entry Point
 * ------------------------------------------------------------------------- */

int main(void) {
    feb_set_high_res(true);
    feb_clear_screen();

    /* Load persistent high score from companion /feb/saves/2048.sav */
    feb_load_flags(&best_tile, 1);
    if (best_tile > 15) {
        best_tile = 0;
    }

    new_game();
    draw_grid();
    draw_best();
    place_random_tile();
    place_random_tile();

    while (1) {
        draw_board();
        uint8_t key = feb_wait_key();
        draw_board(); /* XOR erase board before sliding */

        bool moved = false;
        switch (key) {
            case FEB_KEY_RIGHT: /* Flashiibo OK */
                moved = slide_right();
                break;
            case FEB_KEY_LEFT:  /* Flashiibo BACK */
                moved = slide_left();
                break;
            case FEB_KEY_DOWN:  /* Flashiibo DOWN */
                moved = slide_down();
                break;
            case FEB_KEY_UP:    /* Flashiibo UP */
                moved = slide_up();
                break;
            default:
                break;
        }

        if (moved) {
            place_random_tile();
        }
    }

    return 0;
}

/* __FEB_ASM__
;;; 2048 game for CHIP-8 / Flashiibo FEB (Super-CHIP 128x64 mode)
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

__FEB_ASM_END__ */
