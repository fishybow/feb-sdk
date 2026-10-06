/**
 * @file main.c
 * @brief Falling Blocks Game for Flashiibo Pro Gen3 FEB Runner (.feb)
 *
 * Implements the classic Falling Blocks (Tetris clone) matching the built-in
 * firmware game (games_falling_blocks_view.c) pixel-for-pixel:
 *   - Screen rotation: Portrait mode 64x128 via FEB_ROTATION_90
 *   - 10x20 well with exact borders (x=6..57, y=24..125)
 *   - 7 Tetromino shapes with 4 rotation states (packed 112-byte table)
 *   - SRS-style wall kicks for smooth rotations near walls
 *   - Ghost piece projection preview
 *   - Next piece preview box in header
 *   - Level, line counter, score, and high score tracking
 *   - 7-bag randomizer sequence
 *   - Controls in portrait orientation:
 *       UP: Move left
 *       DOWN: Move right
 *       BACK: Hard drop
 *       OK: Rotate
 *       UP+DOWN: Hardware exit chord
 */

#include "../../include/feb.h"

#define BOARD_WIDTH      10
#define BOARD_HEIGHT     20
#define BOARD_CELLS      200

#define STATE_PLAYING    0
#define STATE_GAMEOVER   1

/* -------------------------------------------------------------------------
 * Packed Tetromino Shape Offsets: (y << 2) | x
 * 7 shapes x 4 rotations x 4 blocks = 112 bytes
 * ------------------------------------------------------------------------- */

static const uint8_t PIECE_COORDS[112] = {
    /* 0: I */
    0x04, 0x05, 0x06, 0x07,
    0x02, 0x06, 0x0a, 0x0e,
    0x08, 0x09, 0x0a, 0x0b,
    0x01, 0x05, 0x09, 0x0d,
    /* 1: O */
    0x01, 0x02, 0x05, 0x06,
    0x01, 0x02, 0x05, 0x06,
    0x01, 0x02, 0x05, 0x06,
    0x01, 0x02, 0x05, 0x06,
    /* 2: T */
    0x01, 0x04, 0x05, 0x06,
    0x01, 0x05, 0x06, 0x09,
    0x04, 0x05, 0x06, 0x09,
    0x01, 0x04, 0x05, 0x09,
    /* 3: S */
    0x01, 0x02, 0x04, 0x05,
    0x01, 0x05, 0x06, 0x0a,
    0x05, 0x06, 0x08, 0x09,
    0x00, 0x04, 0x05, 0x09,
    /* 4: Z */
    0x00, 0x01, 0x05, 0x06,
    0x02, 0x05, 0x06, 0x09,
    0x04, 0x05, 0x09, 0x0a,
    0x01, 0x04, 0x05, 0x08,
    /* 5: J */
    0x00, 0x04, 0x05, 0x06,
    0x01, 0x02, 0x05, 0x09,
    0x04, 0x05, 0x06, 0x0a,
    0x01, 0x05, 0x08, 0x09,
    /* 6: L */
    0x02, 0x04, 0x05, 0x06,
    0x01, 0x05, 0x09, 0x0a,
    0x04, 0x05, 0x06, 0x08,
    0x00, 0x01, 0x05, 0x09
};

static const int8_t KICK_X[5] = {0, -1, 1, -2, 2};

/* -------------------------------------------------------------------------
 * State Variables
 * ------------------------------------------------------------------------- */

static uint8_t board[BOARD_CELLS];
static uint16_t score;
static uint16_t high_score;
static uint16_t lines;
static uint8_t level;
static uint8_t state;
static int8_t cur_x;
static int8_t cur_y;
static uint8_t cur_type;
static uint8_t cur_rot;
static uint8_t next_type;
static uint8_t bag[7] = {0, 1, 2, 3, 4, 5, 6};
static uint8_t bag_idx;
static uint8_t drop_frames;
static uint8_t tick_counter;
static uint8_t rpl_buf[2];

/* -------------------------------------------------------------------------
 * Bag Randomizer
 * ------------------------------------------------------------------------- */

static void refill_bag(void) {
    for (uint8_t i = 6; i > 0; i--) {
        uint8_t j = feb_rand(7);
        while (j > i) {
            j -= (i + 1);
        }
        uint8_t tmp = bag[i];
        bag[i] = bag[j];
        bag[j] = tmp;
    }
    bag_idx = 0;
}

static uint8_t get_next_piece(void) {
    if (bag_idx >= 7) {
        refill_bag();
    }
    return bag[bag_idx++];
}

/* -------------------------------------------------------------------------
 * Collision Detection
 * ------------------------------------------------------------------------- */

static bool collides(int8_t px, int8_t py, uint8_t type, uint8_t rot) {
    if (type >= 7 || rot >= 4) return true;
    uint8_t base = (type << 4) + (rot << 2);

    for (uint8_t b = 0; b < 4; b++) {
        uint8_t coord = PIECE_COORDS[base + b];
        int8_t bx = px + (coord & 3);
        int8_t by = py + (coord >> 2);

        if (bx < 0 || bx >= BOARD_WIDTH) return true;
        if (by >= BOARD_HEIGHT) return true;
        if (by >= 0) {
            if (board[(by << 3) + (by << 1) + bx] != 0) return true;
        }
    }
    return false;
}

/* -------------------------------------------------------------------------
 * Piece Spawning & Game Reset
 * ------------------------------------------------------------------------- */

static void spawn_piece(void) {
    cur_type = next_type;
    next_type = get_next_piece();
    cur_rot = 0;
    cur_x = 3;
    cur_y = 0;

    if (collides(cur_x, cur_y, cur_type, cur_rot)) {
        state = STATE_GAMEOVER;
    }
}

static void reset_game(void) {
    for (uint8_t i = 0; i < BOARD_CELLS; i++) {
        board[i] = 0;
    }
    score = 0;
    lines = 0;
    level = 1;
    drop_frames = 48; /* ~800 ms at 60 Hz */
    tick_counter = 0;
    state = STATE_PLAYING;

    refill_bag();
    next_type = get_next_piece();
    spawn_piece();
}

/* -------------------------------------------------------------------------
 * Line Clearing
 * ------------------------------------------------------------------------- */

static void shift_row_down(int8_t from_row) {
    for (int8_t row = from_row; row > 0; row--) {
        uint8_t dst = (row << 3) + (row << 1);
        uint8_t src = dst - 10;
        for (uint8_t col = 0; col < BOARD_WIDTH; col++) {
            board[dst + col] = board[src + col];
        }
    }
    for (uint8_t col = 0; col < BOARD_WIDTH; col++) {
        board[col] = 0;
    }
}

static void clear_lines(void) {
    uint8_t cleared = 0;
    uint8_t r = BOARD_HEIGHT - 1;

    while (r < BOARD_HEIGHT) {
        bool full = true;
        uint8_t row_start = (r << 3) + (r << 1);
        for (uint8_t c = 0; c < BOARD_WIDTH; c++) {
            if (board[row_start + c] == 0) {
                full = false;
                break;
            }
        }

        if (full) {
            cleared++;
            shift_row_down(r);
        } else {
            if (r == 0) {
                break;
            }
            r--;
        }
    }

    if (cleared > 0) {
        uint16_t pts = 100;
        if (cleared == 2) pts = 300;
        else if (cleared == 3) pts = 500;
        else if (cleared >= 4) pts = 800;

        uint8_t lvl = level;
        while (lvl > 0) {
            score += pts;
            lvl--;
        }
        if (score > high_score) {
            high_score = score;
            rpl_buf[0] = (high_score >> 8) & 0xFF;
            rpl_buf[1] = high_score & 0xFF;
            feb_save_flags(rpl_buf, 2);
        }

        lines += cleared;
        level = 1;
        uint16_t thresh = 10;
        while (lines >= thresh) {
            level++;
            thresh += 10;
        }
        if (level >= 10) {
            drop_frames = 8;
        } else {
            drop_frames = 48 - (level - 1) * 4;
        }
    }
}

static void lock_piece(void) {
    uint8_t base = (cur_type << 4) + (cur_rot << 2);
    for (uint8_t b = 0; b < 4; b++) {
        uint8_t coord = PIECE_COORDS[base + b];
        int8_t bx = cur_x + (coord & 3);
        int8_t by = cur_y + (coord >> 2);
        if (by >= 0 && by < BOARD_HEIGHT && bx >= 0 && bx < BOARD_WIDTH) {
            board[(by << 3) + (by << 1) + bx] = 1;
        }
    }

    clear_lines();
    if (state == STATE_PLAYING) {
        spawn_piece();
    }
}

/* -------------------------------------------------------------------------
 * Piece Movement & Actions
 * ------------------------------------------------------------------------- */

static bool move_horizontal(int8_t dir) {
    if (state != STATE_PLAYING) return false;
    if (!collides(cur_x + dir, cur_y, cur_type, cur_rot)) {
        cur_x += dir;
        return true;
    }
    return false;
}

static bool rotate_piece(void) {
    if (state != STATE_PLAYING) return false;
    uint8_t new_rot = (cur_rot + 1) & 3;

    for (uint8_t k = 0; k < 5; k++) {
        int8_t tx = cur_x + KICK_X[k];
        if (!collides(tx, cur_y, cur_type, new_rot)) {
            cur_x = tx;
            cur_rot = new_rot;
            return true;
        }
    }
    return false;
}

static void hard_drop(void) {
    if (state != STATE_PLAYING) return;
    while (!collides(cur_x, cur_y + 1, cur_type, cur_rot)) {
        cur_y++;
        score++;
    }
    lock_piece();
}

static void step_down(void) {
    if (state != STATE_PLAYING) return;
    if (!collides(cur_x, cur_y + 1, cur_type, cur_rot)) {
        cur_y++;
    } else {
        lock_piece();
    }
}

/* -------------------------------------------------------------------------
 * Rendering (Matching games_falling_blocks_view.c)
 * ------------------------------------------------------------------------- */

static void draw_header(void) {
    feb_draw_string(2, 2, "SCORE", FEB_FONT_4X6);
    feb_draw_number(2, 9, score, FEB_FONT_4X6);

    feb_draw_string(2, 16, "L:", FEB_FONT_4X6);
    feb_draw_number(10, 16, level, FEB_FONT_4X6);
    feb_draw_string(20, 16, "R:", FEB_FONT_4X6);
    feb_draw_number(28, 16, lines, FEB_FONT_4X6);

    /* Next piece preview frame */
    feb_draw_rect(44, 2, 18, 18);
    if (next_type < 7) {
        uint8_t nbase = (next_type << 4);
        for (uint8_t b = 0; b < 4; b++) {
            uint8_t coord = PIECE_COORDS[nbase + b];
            uint8_t bx = coord & 3;
            uint8_t by = coord >> 2;
            feb_fill_rect(48 + bx * 3, 6 + by * 3, 2, 2);
        }
    }

    /* Well header separator */
    feb_draw_hline(0, 23, 64);
}

static void draw_board_and_well(void) {
    /* Well borders */
    feb_draw_vline(6, 24, 102);
    feb_draw_vline(57, 24, 102);
    feb_draw_hline(6, 125, 52);

    /* Placed blocks */
    for (uint8_t r = 0; r < BOARD_HEIGHT; r++) {
        uint8_t row_idx = (r << 3) + (r << 1);
        uint8_t by = 25 + r * 5;
        for (uint8_t c = 0; c < BOARD_WIDTH; c++) {
            if (board[row_idx + c] != 0) {
                feb_fill_rect(7 + c * 5, by, 4, 4);
            }
        }
    }
}

static void draw_tetromino(int8_t px, int8_t py, uint8_t hollow) {
    uint8_t base = (cur_type << 4) + (cur_rot << 2);
    for (uint8_t b = 0; b < 4; b++) {
        uint8_t coord = PIECE_COORDS[base + b];
        int8_t bx = px + (coord & 3);
        int8_t by = py + (coord >> 2);
        if (by >= 0 && by < BOARD_HEIGHT) {
            if (hollow) {
                feb_draw_rect(7 + bx * 5, 25 + by * 5, 4, 4);
            } else {
                feb_fill_rect(7 + bx * 5, 25 + by * 5, 4, 4);
            }
        }
    }
}

static void draw_pieces(void) {
    if (state != STATE_PLAYING) return;

    /* Ghost piece */
    int8_t gy = cur_y;
    while (!collides(cur_x, gy + 1, cur_type, cur_rot)) {
        gy++;
    }
    if (gy > cur_y) {
        draw_tetromino(cur_x, gy, 1);
    }

    /* Falling active piece */
    draw_tetromino(cur_x, cur_y, 0);
}

static void draw_gameover_modal(void) {
    if (state == STATE_GAMEOVER) {
        feb_set_draw_mode(FEB_DRAW_MODE_CLEAR);
        feb_fill_rect(4, 48, 56, 36);
        feb_set_draw_mode(FEB_DRAW_MODE_SET);
        feb_draw_rect(4, 48, 56, 36);

        feb_draw_string(8, 52, "GAME OVER", FEB_FONT_4X6);
        feb_draw_string(8, 62, "SCORE", FEB_FONT_4X6);
        feb_draw_number(32, 62, score, FEB_FONT_4X6);
        feb_draw_string(8, 72, "OK: REPLAY", FEB_FONT_4X6);
    }
}

static void render_all(void) {
    feb_clear_screen();
    feb_set_draw_mode(FEB_DRAW_MODE_SET);

    draw_header();
    draw_board_and_well();
    draw_pieces();
    draw_gameover_modal();
}

/* -------------------------------------------------------------------------
 * Main Entry Point
 * ------------------------------------------------------------------------- */

int main(void) {
    feb_set_high_res(true);
    feb_set_rotation(FEB_ROTATION_90);
    feb_set_draw_mode(FEB_DRAW_MODE_SET);

    /* Load persistent high score */
    feb_load_flags(rpl_buf, 2);
    high_score = (rpl_buf[0] << 8) | rpl_buf[1];
    if (high_score > 60000) {
        high_score = 0;
    }

    reset_game();
    render_all();

    uint8_t prev_buttons = 0;

    while (1) {
        if (state == STATE_GAMEOVER) {
            uint8_t key = feb_wait_key();
            if (key == FEB_KEY_OK) {
                reset_game();
                render_all();
            }
        } else {
            /* Active gameplay: poll buttons each frame */
            uint8_t buttons = feb_get_keys();
            uint8_t just_pressed = buttons & ~prev_buttons;
            prev_buttons = buttons;

            bool redraw = false;

            if (just_pressed & FEB_BTN_UP) {
                redraw = move_horizontal(-1);
            } else if (just_pressed & FEB_BTN_DOWN) {
                redraw = move_horizontal(1);
            } else if (just_pressed & FEB_BTN_RIGHT) {
                redraw = rotate_piece();
            } else if (just_pressed & FEB_BTN_LEFT) {
                hard_drop();
                tick_counter = 0;
                redraw = true;
            }

            tick_counter++;
            if (tick_counter >= drop_frames) {
                tick_counter = 0;
                step_down();
                redraw = true;
            }

            if (redraw) {
                render_all();
            }

            feb_delay_frames(1);
        }
    }

    return 0;
}
