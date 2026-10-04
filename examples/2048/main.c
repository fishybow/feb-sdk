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
 *
 * Built with pure C using Flashiibo FEB SDK geometry lines and typography fonts.
 */

#include "../../include/feb.h"

#define BOARD_SIZE    16

/* Board state: 16 tiles (4x4)
 *   0: Empty cell
 *   1: Tile "2"
 *   2: Tile "4"
 *   3: Tile "8"
 *  ...
 *  10: Tile "1024" (displays "1K")
 *  11: Tile "2048" (displays "2K" - TARGET WIN)
 */
static uint8_t board[BOARD_SIZE];
static uint8_t new_board[BOARD_SIZE];

/* Persistent high score: highest tile level achieved (1..11) saved in companion .sav */
static uint8_t best_tile = 0;

/* -------------------------------------------------------------------------
 * Board Rendering with Geometry and Typography
 * ------------------------------------------------------------------------- */

static void draw_grid(void) {
    /* Vertical grid lines: 5 lines bounding 4 columns of 16px */
    feb_draw_vline(32, 0, 64);
    feb_draw_vline(48, 0, 64);
    feb_draw_vline(64, 0, 64);
    feb_draw_vline(80, 0, 64);
    feb_draw_vline(96, 0, 64);

    /* Horizontal grid lines: 5 lines bounding 4 rows of 16px */
    feb_draw_hline(32, 0, 65);
    feb_draw_hline(32, 16, 65);
    feb_draw_hline(32, 32, 65);
    feb_draw_hline(32, 48, 65);
    feb_draw_hline(32, 63, 65);
}

static void draw_tile(uint8_t x, uint8_t y, uint8_t val) {
    if (val == 0) return;
    if (val == 1)       feb_draw_string(x + 6, y + 5, "2", FEB_FONT_4X6);
    else if (val == 2)  feb_draw_string(x + 6, y + 5, "4", FEB_FONT_4X6);
    else if (val == 3)  feb_draw_string(x + 6, y + 5, "8", FEB_FONT_4X6);
    else if (val == 4)  feb_draw_string(x + 4, y + 5, "16", FEB_FONT_4X6);
    else if (val == 5)  feb_draw_string(x + 4, y + 5, "32", FEB_FONT_4X6);
    else if (val == 6)  feb_draw_string(x + 4, y + 5, "64", FEB_FONT_4X6);
    else if (val == 7)  feb_draw_string(x + 2, y + 5, "128", FEB_FONT_4X6);
    else if (val == 8)  feb_draw_string(x + 2, y + 5, "256", FEB_FONT_4X6);
    else if (val == 9)  feb_draw_string(x + 2, y + 5, "512", FEB_FONT_4X6);
    else if (val == 10) feb_draw_string(x + 4, y + 5, "1K", FEB_FONT_4X6);
    else if (val == 11) feb_draw_string(x + 4, y + 5, "2K", FEB_FONT_4X6);
    else                feb_draw_string(x + 4, y + 5, "4K", FEB_FONT_4X6);
}

static void draw_best(void) {
    feb_draw_string(10, 14, "HI", FEB_FONT_6X10);
    feb_draw_hline(6, 25, 20);
    if (best_tile > 0) {
        draw_tile(6, 28, best_tile);
    }
}

static void draw_sidebar(void) {
    feb_draw_string(101, 14, "2048", FEB_FONT_6X10);
    feb_draw_hline(101, 25, 24);
}

static void draw_board(void) {
    for (uint8_t r = 0; r < 4; r++) {
        for (uint8_t c = 0; c < 4; c++) {
            uint8_t idx = (r << 2) + c;
            uint8_t val = board[idx];
            if (val > 0) {
                uint8_t cx = 32 + (c << 4);
                uint8_t cy = r << 4;
                draw_tile(cx, cy, val);
            }
        }
    }
}

static void render_all(void) {
    feb_clear_screen();
    draw_grid();
    draw_best();
    draw_sidebar();
    draw_board();
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
    return (r << 2) + c;
}

static bool slide(uint8_t key) {
    if (key != FEB_KEY_LEFT && key != FEB_KEY_RIGHT && key != FEB_KEY_UP && key != FEB_KEY_DOWN) {
        return false;
    }

    bool moved = false;
    for (uint8_t line = 0; line < 4; line++) {
        uint8_t write_pos = 0;
        uint8_t last_val = 0;
        for (uint8_t pos = 0; pos < 4; pos++) {
            uint8_t target_idx = get_idx(key, line, pos);
            uint8_t val = board[target_idx];
            if (val == 0) continue;

            if (val == last_val) {
                target_idx = get_idx(key, line, write_pos - 1);
                new_board[target_idx] = val + 1;
                last_val = 0;
                moved = true;
                if (val + 1 > best_tile) {
                    best_tile = val + 1;
                    feb_save_flags(&best_tile, 1);
                }
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

    for (uint8_t pos = 0; pos < BOARD_SIZE; pos++) {
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

    uint8_t empty_count = 0;
    for (uint8_t i = 0; i < BOARD_SIZE; i++) {
        if (board[i] == 0) {
            empty_count++;
        }
    }
    if (empty_count == 0) return;

    uint8_t target = feb_rand(15);
    while (target >= empty_count) {
        target -= empty_count;
    }

    for (uint8_t i = 0; i < BOARD_SIZE; i++) {
        if (board[i] == 0) {
            if (target == 0) {
                board[i] = tile_val;
                return;
            }
            target--;
        }
    }
}

static void new_game(void) {
    for (uint8_t i = 0; i < BOARD_SIZE; i++) {
        board[i] = 0;
        new_board[i] = 0;
    }
}

/* -------------------------------------------------------------------------
 * Game Over Detection & Screen
 * ------------------------------------------------------------------------- */

static bool is_game_over(void) {
    for (uint8_t r = 0; r < 4; r++) {
        for (uint8_t c = 0; c < 4; c++) {
            uint8_t idx = (r << 2) + c;
            uint8_t val = board[idx];
            if (val == 0) {
                return false;
            }
            if (c < 3 && val == board[idx + 1]) {
                return false;
            }
            if (r < 3 && val == board[idx + 4]) {
                return false;
            }
        }
    }
    return true;
}

static void draw_game_over(void) {
    feb_set_draw_mode(FEB_DRAW_MODE_CLEAR);
    feb_fill_rect(34, 15, 60, 34);
    feb_set_draw_mode(FEB_DRAW_MODE_SET);
    feb_draw_rect(34, 15, 60, 34);
    feb_draw_string(37, 20, "GAME OVER", FEB_FONT_6X10);
    feb_draw_string(42, 35, "OK: Restart", FEB_FONT_4X6);
}

/* -------------------------------------------------------------------------
 * Main Entry Point
 * ------------------------------------------------------------------------- */

int main(void) {
    feb_set_high_res(true);
    feb_set_draw_mode(FEB_DRAW_MODE_SET);

    /* Load persistent high score from companion .sav */
    feb_load_flags(&best_tile, 1);
    if (best_tile > 15) {
        best_tile = 0;
    }

    new_game();
    place_random_tile();
    place_random_tile();
    render_all();

    uint8_t game_over = 0;

    while (1) {
        uint8_t key = feb_wait_key();
        if (game_over != 0) {
            if (key == FEB_KEY_OK) {
                new_game();
                place_random_tile();
                place_random_tile();
                render_all();
                game_over = 0;
            }
        } else {
            bool moved = slide(key);
            if (moved) {
                place_random_tile();
                render_all();
                if (is_game_over()) {
                    game_over = 1;
                    draw_game_over();
                }
            }
        }
    }

    return 0;
}

