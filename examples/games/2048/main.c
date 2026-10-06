/**
 * @file main.c
 * @brief 2048 Game for Flashiibo Pro Gen3 FEB Runner (.feb)
 *
 * Implements the classic 2048 tile puzzle matching the built-in firmware
 * 2048 game (games_2048_view.c) pixel-for-pixel:
 *   - 4x4 grid of 20x14 tiles with 1px outline spacing
 *   - Solid white tile boxes with clear (black) font_likeminecraft_te numbers
 *   - Right sidebar: "2048" header, horizontal rule, SCORE and BEST displays
 *   - Centered popup overlays for GAME OVER and YOU WIN!
 *   - Controls: UP/DOWN/LEFT(BACK)/RIGHT(OK)
 *   - UP+DOWN system exit chord back to FEB Runner menu
 */

#include "../../../include/feb.h"

#define BOARD_SIZE    16

#define STATE_PLAYING    0
#define STATE_GAME_OVER  1
#define STATE_WON        2

/* Board state: 16 tiles (4x4)
 *   0: Empty cell
 *   1: Tile "2"
 *   2: Tile "4"
 *   3: Tile "8"
 *  ...
 *  10: Tile "1024" (displays "1K")
 *  11: Tile "2048" (displays "2K" - TARGET WIN)
 *  12: Tile "4096" (displays "4K")
 */
static uint8_t board[BOARD_SIZE];
static uint8_t new_board[BOARD_SIZE];

static uint16_t score = 0;
static uint16_t high_score = 0;
static uint8_t state = STATE_PLAYING;
static uint8_t won_dismissed = 0;

/* Save buffer for RPL flags persistence */
static uint8_t save_buf[2];

/* -------------------------------------------------------------------------
 * Board Rendering matching games_2048_view.c pixel-for-pixel
 * ------------------------------------------------------------------------- */

static void draw_tile(uint8_t cx, uint8_t cy, uint8_t val) {
    if (val == 0) {
        feb_draw_rect(cx, cy, 20, 14);
        return;
    }

    /* Filled tile: solid white background with black text */
    feb_fill_rect(cx, cy, 20, 14);
    feb_set_draw_mode(FEB_DRAW_MODE_CLEAR);
    if (val == 1)       feb_draw_string(cx + 8, cy + 3, "2", FEB_FONT_RETRO_8X8);
    else if (val == 2)  feb_draw_string(cx + 8, cy + 3, "4", FEB_FONT_RETRO_8X8);
    else if (val == 3)  feb_draw_string(cx + 8, cy + 3, "8", FEB_FONT_RETRO_8X8);
    else if (val == 4)  feb_draw_string(cx + 6, cy + 3, "16", FEB_FONT_RETRO_8X8);
    else if (val == 5)  feb_draw_string(cx + 6, cy + 3, "32", FEB_FONT_RETRO_8X8);
    else if (val == 6)  feb_draw_string(cx + 6, cy + 3, "64", FEB_FONT_RETRO_8X8);
    else if (val == 7)  feb_draw_string(cx + 4, cy + 3, "128", FEB_FONT_RETRO_8X8);
    else if (val == 8)  feb_draw_string(cx + 4, cy + 3, "256", FEB_FONT_RETRO_8X8);
    else if (val == 9)  feb_draw_string(cx + 4, cy + 3, "512", FEB_FONT_RETRO_8X8);
    else if (val == 10) feb_draw_string(cx + 6, cy + 3, "1K", FEB_FONT_RETRO_8X8);
    else if (val == 11) feb_draw_string(cx + 6, cy + 3, "2K", FEB_FONT_RETRO_8X8);
    else                feb_draw_string(cx + 6, cy + 3, "4K", FEB_FONT_RETRO_8X8);
    feb_set_draw_mode(FEB_DRAW_MODE_SET);
}

static void draw_board(void) {
    uint8_t cy = 2;
    uint8_t idx = 0;
    for (uint8_t r = 0; r < 4; r++) {
        uint8_t cx = 1;
        for (uint8_t c = 0; c < 4; c++) {
            uint8_t val = board[idx];
            idx++;
            if (val == 0) {
                feb_draw_rect(cx, cy, 20, 14);
            } else {
                draw_tile(cx, cy, val);
            }
            cx += 21;
        }
        cy += 15;
    }
}

static void draw_sidebar(void) {
    feb_set_draw_mode(FEB_DRAW_MODE_SET);

    /* Header title */
    feb_draw_string(87, 4, "2048", FEB_FONT_RETRO_8X8);
    feb_draw_hline(86, 15, 41);

    /* SCORE */
    feb_draw_string(87, 18, "SCORE", FEB_FONT_4X6);
    feb_draw_number(87, 26, score, FEB_FONT_RETRO_8X8);

    /* BEST */
    feb_draw_string(87, 40, "BEST", FEB_FONT_4X6);
    feb_draw_number(87, 48, high_score, FEB_FONT_RETRO_8X8);
}

static void draw_overlays(void) {
    if (state == STATE_GAME_OVER) {
        feb_set_draw_mode(FEB_DRAW_MODE_CLEAR);
        feb_fill_rect(8, 14, 65, 34);
        feb_set_draw_mode(FEB_DRAW_MODE_SET);
        feb_draw_rect(8, 14, 65, 34);
        feb_draw_string(11, 19, "GAME OVER", FEB_FONT_RETRO_8X8);
        feb_draw_string(14, 34, "Press OK: New", FEB_FONT_4X6);
    } else if (state == STATE_WON && won_dismissed == 0) {
        feb_set_draw_mode(FEB_DRAW_MODE_CLEAR);
        feb_fill_rect(8, 14, 65, 34);
        feb_set_draw_mode(FEB_DRAW_MODE_SET);
        feb_draw_rect(8, 14, 65, 34);
        feb_draw_string(15, 19, "YOU WIN!", FEB_FONT_RETRO_8X8);
        feb_draw_string(13, 34, "Press OK: Keep", FEB_FONT_4X6);
    }
}

static void render_all(void) {
    feb_clear_screen();
    draw_board();
    draw_sidebar();
    if (state != STATE_PLAYING) {
        draw_overlays();
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
    return (r << 2) + c;
}

static bool slide(uint8_t key) {
    if (key != FEB_KEY_LEFT && key != FEB_KEY_RIGHT && key != FEB_KEY_UP && key != FEB_KEY_DOWN) {
        return false;
    }

    bool moved = false;
    uint16_t score_delta = 0;

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
                score_delta += (1 << (val + 1));
                last_val = 0;
                moved = true;
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

    if (moved) {
        score += score_delta;
        if (score > high_score) {
            high_score = score;
            save_buf[0] = (uint8_t)(high_score & 0xFF);
            save_buf[1] = (uint8_t)(high_score >> 8);
            feb_save_flags(save_buf, 2);
        }

        for (uint8_t pos = 0; pos < BOARD_SIZE; pos++) {
            board[pos] = new_board[pos];
            new_board[pos] = 0;
        }
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

static bool check_has_won(void) {
    for (uint8_t i = 0; i < BOARD_SIZE; i++) {
        if (board[i] >= 11) {
            return true;
        }
    }
    return false;
}

static bool check_is_game_over(void) {
    for (uint8_t r = 0; r < 4; r++) {
        for (uint8_t c = 0; c < 4; c++) {
            uint8_t idx = (r << 2) + c;
            uint8_t val = board[idx];
            if (val == 0) return false;
            if (c < 3 && val == board[idx + 1]) return false;
            if (r < 3 && val == board[idx + 4]) return false;
        }
    }
    return true;
}

static void new_game(void) {
    for (uint8_t i = 0; i < BOARD_SIZE; i++) {
        board[i] = 0;
        new_board[i] = 0;
    }
    score = 0;
    state = STATE_PLAYING;
    won_dismissed = 0;
    place_random_tile();
    place_random_tile();
}

/* -------------------------------------------------------------------------
 * Main Entry Point
 * ------------------------------------------------------------------------- */

int main(void) {
    feb_set_high_res(true);
    feb_set_draw_mode(FEB_DRAW_MODE_SET);

    /* Load persistent high score from companion .sav */
    feb_load_flags(save_buf, 2);
    high_score = (uint16_t)save_buf[0] | ((uint16_t)save_buf[1] << 8);

    new_game();
    render_all();

    while (1) {
        uint8_t key = feb_wait_key();

        if (state == STATE_GAME_OVER) {
            if (key == FEB_KEY_OK) {
                new_game();
                render_all();
            }
        } else if (state == STATE_WON && won_dismissed == 0) {
            if (key == FEB_KEY_OK) {
                won_dismissed = 1;
                state = STATE_PLAYING;
                render_all();
            }
        } else {
            bool moved = slide(key);
            if (moved) {
                place_random_tile();
                if (won_dismissed == 0 && check_has_won()) {
                    state = STATE_WON;
                } else if (check_is_game_over()) {
                    state = STATE_GAME_OVER;
                }
                render_all();
            }
        }
    }

    return 0;
}
