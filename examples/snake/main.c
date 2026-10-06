/**
 * @file main.c
 * @brief Snake Game for Flashiibo Pro Gen3 FEB Runner (.feb)
 *
 * Implements the classic Snake arcade game matching the built-in firmware
 * Snake game (games_snake_view.c) pixel-for-pixel:
 *   - 31x15 playfield on 128x64 display with outer rounded border
 *   - 4x4 snake segments: rounded head with directional eyes, full body blocks,
 *     directional tail, and 1px black segment separation lines
 *   - Cross-shaped food pellet (2x4 + 4x2)
 *   - Progressive speedup as score increases
 *   - High-score persistence across sessions via RPL flags
 *   - Modal dialogs matching firmware layout (READY and GAME OVER)
 *   - Controls: UP / DOWN / LEFT (BACK) / RIGHT (OK)
 *   - Hardware UP+DOWN exit chord
 */

#include "../../include/feb.h"

#define GRID_COLS        31
#define GRID_ROWS        15
#define MAX_SNAKE_LENGTH 64

#define DIR_UP           0
#define DIR_DOWN         1
#define DIR_LEFT         2
#define DIR_RIGHT        3

#define STATE_READY      0
#define STATE_PLAYING    1
#define STATE_GAMEOVER   2

static uint8_t body_x[MAX_SNAKE_LENGTH];
static uint8_t body_y[MAX_SNAKE_LENGTH];
static uint8_t length;
static uint8_t dir;
static uint8_t next_dir;
static uint8_t food_x;
static uint8_t food_y;
static uint8_t state;
static uint16_t score;
static uint16_t high_score;
static uint8_t speed_frames;
static uint8_t rpl_buf[2];

/* -------------------------------------------------------------------------
 * High Score Persistence (RPL Flags)
 * ------------------------------------------------------------------------- */

static void load_high_score(void) {
    feb_load_flags(rpl_buf, 2);
    high_score = (rpl_buf[0] << 8) | rpl_buf[1];
    if (high_score > 9990) {
        high_score = 0;
    }
}

static void save_high_score(void) {
    rpl_buf[0] = (high_score >> 8) & 0xFF;
    rpl_buf[1] = high_score & 0xFF;
    feb_save_flags(rpl_buf, 2);
}

/* -------------------------------------------------------------------------
 * Food Spawning
 * ------------------------------------------------------------------------- */

static void spawn_food(void) {
    for (uint8_t attempts = 0; attempts < 100; attempts++) {
        uint8_t rx = feb_rand(31);
        uint8_t ry = feb_rand(15);
        if (rx < GRID_COLS && ry < GRID_ROWS) {
            bool collide = false;
            for (uint8_t i = 0; i < length; i++) {
                if (body_x[i] == rx && body_y[i] == ry) {
                    collide = true;
                    break;
                }
            }
            if (!collide) {
                food_x = rx;
                food_y = ry;
                return;
            }
        }
    }

    /* Fallback scan */
    for (uint8_t y = 0; y < GRID_ROWS; y++) {
        for (uint8_t x = 0; x < GRID_COLS; x++) {
            bool collide = false;
            for (uint8_t i = 0; i < length; i++) {
                if (body_x[i] == x && body_y[i] == y) {
                    collide = true;
                    break;
                }
            }
            if (!collide) {
                food_x = x;
                food_y = y;
                return;
            }
        }
    }
}

/* -------------------------------------------------------------------------
 * Game Initialization
 * ------------------------------------------------------------------------- */

static void reset_game(void) {
    length = 3;
    for (uint8_t i = 0; i < 3; i++) {
        body_x[i] = 10 - i;
        body_y[i] = 7;
    }

    dir = DIR_RIGHT;
    next_dir = DIR_RIGHT;
    score = 0;
    speed_frames = 9; /* ~150 ms at 60 Hz */
    state = STATE_READY;

    spawn_food();
}

/* -------------------------------------------------------------------------
 * Rendering (Matching games_snake_view.c)
 * ------------------------------------------------------------------------- */

static void draw_outer_border(void) {
    feb_draw_rect(0, 0, 128, 64);
    feb_set_draw_mode(FEB_DRAW_MODE_CLEAR);
    feb_draw_pixel(0, 0);
    feb_draw_pixel(127, 0);
    feb_draw_pixel(0, 63);
    feb_draw_pixel(127, 63);
    feb_set_draw_mode(FEB_DRAW_MODE_SET);
}

static void draw_modal_box(uint8_t y, uint8_t h) {
    feb_set_draw_mode(FEB_DRAW_MODE_CLEAR);
    feb_fill_rect(24, y, 80, h);
    feb_set_draw_mode(FEB_DRAW_MODE_SET);
    feb_draw_rect(24, y, 80, h);
    feb_set_draw_mode(FEB_DRAW_MODE_CLEAR);
    uint8_t bot = y + h - 1;
    feb_draw_pixel(24, y);
    feb_draw_pixel(103, y);
    feb_draw_pixel(24, bot);
    feb_draw_pixel(103, bot);
    feb_set_draw_mode(FEB_DRAW_MODE_SET);
}

static void draw_food(void) {
    uint8_t fx = 2 + (food_x << 2);
    uint8_t fy = 2 + (food_y << 2);
    feb_set_draw_mode(FEB_DRAW_MODE_SET);
    feb_fill_rect(fx + 1, fy, 2, 4);
    feb_fill_rect(fx, fy + 1, 4, 2);
}

static void draw_head(uint8_t x, uint8_t y, uint8_t d) {
    uint8_t hx = 2 + (x << 2);
    uint8_t hy = 2 + (y << 2);
    feb_set_draw_mode(FEB_DRAW_MODE_SET);
    feb_fill_rect(hx + 1, hy, 2, 4);
    feb_fill_rect(hx, hy + 1, 4, 2);
    feb_set_draw_mode(FEB_DRAW_MODE_CLEAR);
    if (d == DIR_RIGHT) {
        feb_draw_pixel(hx + 2, hy + 1);
        feb_draw_pixel(hx + 2, hy + 2);
    } else if (d == DIR_LEFT) {
        feb_draw_pixel(hx + 1, hy + 1);
        feb_draw_pixel(hx + 1, hy + 2);
    } else if (d == DIR_UP) {
        feb_draw_pixel(hx + 1, hy + 1);
        feb_draw_pixel(hx + 2, hy + 1);
    } else if (d == DIR_DOWN) {
        feb_draw_pixel(hx + 1, hy + 2);
        feb_draw_pixel(hx + 2, hy + 2);
    }
    feb_set_draw_mode(FEB_DRAW_MODE_SET);
}

static void draw_snake_body(void) {
    /* Head */
    if (length > 0) {
        draw_head(body_x[0], body_y[0], dir);
    }

    /* Body segments */
    for (uint8_t i = 1; i + 1 < length; i++) {
        uint8_t bx = 2 + (body_x[i] << 2);
        uint8_t by = 2 + (body_y[i] << 2);
        feb_fill_rect(bx, by, 4, 4);
    }
}

static void draw_snake_tail(void) {
    if (length >= 2) {
        uint8_t last = length - 1;
        uint8_t prev = last - 1;
        uint8_t tx = 2 + (body_x[last] << 2);
        uint8_t ty = 2 + (body_y[last] << 2);
        uint8_t lx = body_x[last];
        uint8_t px = body_x[prev];
        uint8_t ly = body_y[last];
        uint8_t py = body_y[prev];
        feb_set_draw_mode(FEB_DRAW_MODE_SET);

        if (lx < px) {
            /* Pointing left */
            feb_fill_rect(tx, ty + 1, 4, 2);
            feb_fill_rect(tx + 2, ty, 2, 4);
        } else if (lx > px) {
            /* Pointing right */
            feb_fill_rect(tx, ty + 1, 4, 2);
            feb_fill_rect(tx, ty, 2, 4);
        } else if (ly < py) {
            /* Pointing up */
            feb_fill_rect(tx + 1, ty, 2, 4);
            feb_fill_rect(tx, ty + 2, 4, 2);
        } else if (ly > py) {
            /* Pointing down */
            feb_fill_rect(tx + 1, ty, 2, 4);
            feb_fill_rect(tx, ty, 4, 2);
        } else {
            feb_fill_rect(tx, ty, 4, 4);
        }
    }
}

static void draw_separator(uint8_t x0, uint8_t y0, uint8_t x1, uint8_t y1) {
    uint8_t sx = 2 + (x0 << 2);
    uint8_t sy = 2 + (y0 << 2);
    feb_set_draw_mode(FEB_DRAW_MODE_CLEAR);
    if (x0 > x1) {
        feb_draw_vline(sx, sy, 4);
    } else if (x0 < x1) {
        feb_draw_vline(sx + 3, sy, 4);
    } else if (y0 > y1) {
        feb_draw_hline(sx, sy, 4);
    } else if (y0 < y1) {
        feb_draw_hline(sx, sy + 3, 4);
    }
    feb_set_draw_mode(FEB_DRAW_MODE_SET);
}

static void draw_snake_seps(void) {
    for (uint8_t i = 0; i + 1 < length; i++) {
        draw_separator(body_x[i], body_y[i], body_x[i + 1], body_y[i + 1]);
    }
}

static void draw_overlays(void) {
    if (state == STATE_READY) {
        draw_modal_box(15, 34);
        feb_draw_string(44, 20, "SNAKE", FEB_FONT_RETRO_8X8);
        feb_draw_string(44, 34, "BEST: ", FEB_FONT_4X6);
        feb_draw_number(68, 34, high_score, FEB_FONT_4X6);
    } else if (state == STATE_GAMEOVER) {
        draw_modal_box(13, 38);
        feb_draw_string(28, 18, "GAME OVER", FEB_FONT_RETRO_8X8);
        feb_draw_string(40, 29, "SCORE: ", FEB_FONT_4X6);
        feb_draw_number(68, 29, score, FEB_FONT_4X6);
        feb_draw_string(44, 37, "BEST: ", FEB_FONT_4X6);
        feb_draw_number(68, 37, high_score, FEB_FONT_4X6);
    }
}

static void render_world(void) {
    feb_clear_screen();
    feb_set_draw_mode(FEB_DRAW_MODE_SET);

    /* 1. Outer playfield border */
    draw_outer_border();

    /* 2. Draw food pellet */
    draw_food();

    /* 3. Draw snake */
    draw_snake_body();
    draw_snake_tail();
    draw_snake_seps();

    /* 4. Overlays */
    draw_overlays();
}

/* -------------------------------------------------------------------------
 * Snake Movement & Game Logic
 * ------------------------------------------------------------------------- */

static void step_snake(void) {
    if (state != STATE_PLAYING) return;

    dir = next_dir;

    uint8_t hx = body_x[0];
    uint8_t hy = body_y[0];
    uint8_t nx = hx;
    uint8_t ny = hy;

    if (dir == DIR_UP) {
        if (hy == 0) { state = STATE_GAMEOVER; return; }
        ny = hy - 1;
    } else if (dir == DIR_DOWN) {
        ny = hy + 1;
        if (ny >= GRID_ROWS) { state = STATE_GAMEOVER; return; }
    } else if (dir == DIR_LEFT) {
        if (hx == 0) { state = STATE_GAMEOVER; return; }
        nx = hx - 1;
    } else if (dir == DIR_RIGHT) {
        nx = hx + 1;
        if (nx >= GRID_COLS) { state = STATE_GAMEOVER; return; }
    }

    /* Self collision check (tail moves unless food eaten) */
    for (uint8_t i = 0; i + 1 < length; i++) {
        if (body_x[i] == nx && body_y[i] == ny) {
            state = STATE_GAMEOVER;
            return;
        }
    }

    /* Food collision */
    bool ate = (nx == food_x && ny == food_y);
    uint8_t new_len = length;

    if (ate) {
        if (new_len < (MAX_SNAKE_LENGTH - 1)) {
            new_len++;
        }
        score += 10;
        if (score > high_score) {
            high_score = score;
            save_high_score();
        }
        if (speed_frames > 4) {
            speed_frames--;
        }
        spawn_food();
    } else {
        /* Erase old tail block before shifting */
        feb_set_draw_mode(FEB_DRAW_MODE_CLEAR);
        feb_fill_rect(2 + (body_x[length - 1] << 2), 2 + (body_y[length - 1] << 2), 4, 4);
    }

    /* Shift body segments */
    for (uint8_t i = new_len - 1; i > 0; i--) {
        body_x[i] = body_x[i - 1];
        body_y[i] = body_y[i - 1];
    }
    body_x[0] = nx;
    body_y[0] = ny;
    length = new_len;

    /* If tail moved, redraw the new tail tip block */
    if (!ate) {
        draw_snake_tail();
    }

    /* Convert old head (now at body[1]) into filled body block + separator */
    feb_set_draw_mode(FEB_DRAW_MODE_SET);
    feb_fill_rect(2 + (hx << 2), 2 + (hy << 2), 4, 4);
    draw_separator(hx, hy, nx, ny);

    /* Draw new head at nx, ny */
    draw_head(nx, ny, dir);

    /* If food was eaten, draw new food */
    if (ate) {
        draw_food();
    }
}

/* -------------------------------------------------------------------------
 * Main Entry Point
 * ------------------------------------------------------------------------- */

int main(void) {
    feb_set_high_res(true);
    feb_set_draw_mode(FEB_DRAW_MODE_SET);

    load_high_score();
    reset_game();
    render_world();

    while (1) {
        if (state == STATE_READY) {
            uint8_t key = feb_wait_key();
            if (key == FEB_KEY_UP) {
                dir = DIR_UP;
                next_dir = DIR_UP;
            } else if (key == FEB_KEY_DOWN) {
                dir = DIR_DOWN;
                next_dir = DIR_DOWN;
            } else if (key == FEB_KEY_BACK) {
                dir = DIR_LEFT;
                next_dir = DIR_LEFT;
            } else {
                dir = DIR_RIGHT;
                next_dir = DIR_RIGHT;
            }
            state = STATE_PLAYING;
            render_world();
        } else if (state == STATE_PLAYING) {
            /* Active play: poll buttons between movement ticks */
            for (uint8_t f = 0; f < speed_frames; f++) {
                uint8_t buttons = feb_get_keys();
                if ((buttons & FEB_BTN_UP) && dir != DIR_DOWN) {
                    next_dir = DIR_UP;
                } else if ((buttons & FEB_BTN_DOWN) && dir != DIR_UP) {
                    next_dir = DIR_DOWN;
                } else if ((buttons & FEB_BTN_LEFT) && dir != DIR_RIGHT) {
                    next_dir = DIR_LEFT;
                } else if ((buttons & FEB_BTN_RIGHT) && dir != DIR_LEFT) {
                    next_dir = DIR_RIGHT;
                }
                feb_delay_frames(1);
            }

            step_snake();

            if (state == STATE_GAMEOVER) {
                if (score > high_score) {
                    high_score = score;
                    save_high_score();
                }
                render_world();
            }
        } else if (state == STATE_GAMEOVER) {
            uint8_t key = feb_wait_key();
            if (key == FEB_KEY_OK) {
                reset_game();
                state = STATE_PLAYING;
                render_world();
            }
        }
    }

    return 0;
}
