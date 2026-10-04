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
