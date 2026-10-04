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
 * Pressing UP + DOWN together guarantees immediate game exit back to the FEB Runner menu.
 */

#include "../../include/feb.h"

#define BOARD_SIZE    16

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
    0x80, 0x00, 0x80, 0x00, 0x80, 0x00,
    0x80, 0x00, 0x80, 0x00, 0x80, 0x00,
    0x80, 0x00, 0x80, 0x00, 0x80, 0x00,
    0x80, 0x00, 0x80, 0x00, 0x80, 0x00,
    0x80, 0x00, 0x80, 0x00, 0x80, 0x00
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

    while (k != BOARD_SIZE) {
        if (y == 48) {
            feb_draw_sprite16(x, y, SPRITE_GRID_BOTTOM_16);
        } else {
            feb_draw_sprite16(x, y, SPRITE_GRID_16);
        }

        k++;
        x += CELL_SIZE;
        if (x == 96) {
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

    while (k != BOARD_SIZE) {
        uint8_t val = board[k];
        if (val > 0) {
            feb_draw_digit(x, y, val - 1);
        }

        k++;
        x += CELL_SIZE;
        if (x == 102) {
            x = GRID_ORIGIN_X + TILE_OFFSET_X;
            y += CELL_SIZE;
        }
    }
}

static void draw_best(void) {
    feb_draw_sprite(12, 20, SPRITE_HI, 5);
    if (best_tile > 0) {
        feb_draw_digit(13, 28, best_tile - 1);
    }
}

static void update_best(uint8_t val) {
    if (val > best_tile) {
        if (best_tile > 0) {
            feb_draw_digit(13, 28, best_tile - 1);
        }
        best_tile = val;
        feb_draw_digit(13, 28, best_tile - 1);
        feb_save_flags(&best_tile, 1);
    }
}

/* -------------------------------------------------------------------------
 * Board Manipulation & Sliding Algorithms
 * ------------------------------------------------------------------------- */

static uint8_t get_idx(uint8_t key, uint8_t line, uint8_t pos) {
    uint8_t r = line;
    uint8_t c = pos;
    if (key == FEB_KEY_RIGHT) {
        c = 3 - pos;
    } else if (key == FEB_KEY_UP) {
        r = pos;
        c = line;
    } else if (key == FEB_KEY_DOWN) {
        r = 3 - pos;
        c = line;
    }
    return (r * 4) + c;
}

static bool slide(uint8_t key) {
    bool moved = false;
    for (uint8_t line = 0; line != 4; line++) {
        uint8_t write_pos = 0;
        uint8_t last_val = 0;
        for (uint8_t pos = 0; pos != 4; pos++) {
            uint8_t target_idx = get_idx(key, line, pos);
            uint8_t val = board[target_idx];
            if (val == 0) continue;

            if (val == last_val) {
                target_idx = get_idx(key, line, write_pos - 1);
                new_board[target_idx] = val + 1;
                last_val = 0;
                moved = true;
                update_best(val + 1);
            } else {
                last_val = val;
                target_idx = get_idx(key, line, write_pos);
                new_board[target_idx] = val;
                if (pos != write_pos) {
                    moved = true;
                }
                write_pos++;
            }
        }
    }

    for (uint8_t pos = 0; pos != BOARD_SIZE; pos++) {
        board[pos] = new_board[pos];
        new_board[pos] = 0;
    }
    return moved;
}

/* -------------------------------------------------------------------------
 * Random Tile Spawning & Initialization
 * ------------------------------------------------------------------------- */

static void place_random_tile(void) {
    uint8_t tile_val = 1;
    if (feb_rand(7) == 0) {
        tile_val = 2;
    }

    uint8_t target = feb_rand(15);
    uint8_t scans = 32;
    uint8_t idx = 0;

    while (scans != 0) {
        scans--;
        if (board[idx] == 0) {
            if (target == 0) {
                board[idx] = tile_val;
                return;
            }
            target--;
        }
        idx = (idx + 1) & 15;
    }
}

static void new_game(void) {
    for (uint8_t i = 0; i != BOARD_SIZE; i++) {
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

        bool moved = slide(key);
        if (moved) {
            place_random_tile();
        }
    }

    return 0;
}
