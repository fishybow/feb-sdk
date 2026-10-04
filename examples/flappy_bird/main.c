/**
 * @file main.c
 * @brief Flappy Bird FEB Example for Flashiibo Pro Gen3
 *
 * Demonstrates:
 *   - Animated 8x8 sprite rendering (feb_draw_sprite)
 *   - Fast 2D vector geometry drawing (feb_fill_rect, feb_draw_rect, feb_draw_hline)
 *   - High-performance input polling (feb_get_keys)
 *   - Programmatic application exit via BACK button (feb_exit)
 *   - Non-volatile high score persistence (feb_load_flags, feb_save_flags)
 *   - 30 FPS frame-pacing with hardware delay timer (feb_delay_frames)
 */

#include "feb.h"

#define STATE_TITLE     0
#define STATE_PLAYING   1
#define STATE_GAMEOVER  2

#define BIRD_X          24
#define GROUND_Y        56
#define PIPE_WIDTH      10
#define PIPE_GAP_H      28

/* 8x8 Bird Sprite: Gliding / Wings down */
static const uint8_t bird_glide[8] = {
    0x38, /* ..###... */
    0x44, /* .#...#.. */
    0x5e, /* .#.####. (eye) */
    0xff, /* ######## */
    0xfe, /* #######. */
    0x5c, /* .#.###.. */
    0x38, /* ..###... */
    0x00  /* ........ */
};

/* 8x8 Bird Sprite: Flapping / Wings up */
static const uint8_t bird_flap[8] = {
    0x78, /* .####... (wing up) */
    0x4c, /* .#..##.. */
    0x5e, /* .#.####. (eye) */
    0xdf, /* ##.##### */
    0xfe, /* #######. */
    0x5c, /* .#.###.. */
    0x38, /* ..###... */
    0x00  /* ........ */
};

static uint8_t game_state = STATE_TITLE;
static uint8_t bird_y = 22;
static uint8_t jump_timer = 0;
static uint8_t flap_anim = 0;
static uint8_t fall_speed = 0;
static uint8_t prev_flap = 0;

static uint8_t pipe1_x = 120;
static uint8_t pipe1_gap = 10;
static uint8_t pipe2_x = 192;
static uint8_t pipe2_gap = 14;

static uint8_t score = 0;
static uint8_t best_score = 0;

static void reset_game(void) {
    bird_y = 22;
    jump_timer = 5;
    flap_anim = 6;
    fall_speed = 0;
    prev_flap = 0;
    score = 0;
    pipe1_x = 120;
    pipe1_gap = 10;
    pipe2_x = 192;
    pipe2_gap = 14;
}

static void render_world(void) {
    feb_clear_screen();

    /* Draw Ground */
    feb_set_draw_mode(FEB_DRAW_MODE_SET);
    feb_draw_hline(0, GROUND_Y, 128);

    /* Draw Pipe 1 */
    if (pipe1_x < 128) {
        feb_fill_rect(pipe1_x, 0, PIPE_WIDTH, pipe1_gap);
        feb_fill_rect(pipe1_x, pipe1_gap + PIPE_GAP_H, PIPE_WIDTH, GROUND_Y - (pipe1_gap + PIPE_GAP_H));
        if (pipe1_x > 0 && pipe1_x < 126) {
            feb_draw_rect(pipe1_x - 1, pipe1_gap - 3, PIPE_WIDTH + 2, 3);
            feb_draw_rect(pipe1_x - 1, pipe1_gap + PIPE_GAP_H, PIPE_WIDTH + 2, 3);
        }
    }

    /* Draw Pipe 2 */
    if (pipe2_x < 128) {
        feb_fill_rect(pipe2_x, 0, PIPE_WIDTH, pipe2_gap);
        feb_fill_rect(pipe2_x, pipe2_gap + PIPE_GAP_H, PIPE_WIDTH, GROUND_Y - (pipe2_gap + PIPE_GAP_H));
        if (pipe2_x > 0 && pipe2_x < 126) {
            feb_draw_rect(pipe2_x - 1, pipe2_gap - 3, PIPE_WIDTH + 2, 3);
            feb_draw_rect(pipe2_x - 1, pipe2_gap + PIPE_GAP_H, PIPE_WIDTH + 2, 3);
        }
    }

    /* Draw Bird Sprite */
    if (flap_anim > 0) {
        feb_draw_sprite(BIRD_X, bird_y, bird_flap, 8);
    } else {
        feb_draw_sprite(BIRD_X, bird_y, bird_glide, 8);
    }

    /* HUD */
    feb_draw_string(2, 2, "SCORE", FEB_FONT_4X6);
    feb_draw_number(28, 2, score, FEB_FONT_4X6);
    feb_draw_string(76, 2, "BEST", FEB_FONT_4X6);
    feb_draw_number(100, 2, best_score, FEB_FONT_4X6);
}

int main(void) {
    feb_set_high_res(true);
    feb_load_flags(&best_score, 1);
    if (best_score > 99) {
        best_score = 0;
    }

    while (1) {
        if (game_state == STATE_TITLE) {
            feb_clear_screen();
            feb_set_draw_mode(FEB_DRAW_MODE_SET);
            feb_draw_string(24, 6, "FLAPPY BIRD", FEB_FONT_RETRO_8X8);
            feb_draw_sprite(60, 20, bird_flap, 8);
            feb_draw_string(36, 34, "OK: FLAP", FEB_FONT_6X10);
            feb_draw_string(32, 46, "BACK: EXIT", FEB_FONT_6X10);
            feb_draw_hline(0, GROUND_Y, 128);

            uint8_t key = feb_wait_key();
            if (key == FEB_KEY_BACK) {
                feb_exit();
            }
            if (key == FEB_KEY_OK || key == FEB_KEY_UP) {
                reset_game();
                game_state = STATE_PLAYING;
            }
        } else if (game_state == STATE_PLAYING) {
            uint8_t keys = feb_get_keys();

            /* Programmatic Exit: BACK button immediately returns to FEB Runner */
            if (keys & FEB_BTN_BACK) {
                feb_exit();
            }

            /* Edge detection for flap/action button (OK or UP) */
            uint8_t action_pressed = 0;
            if (keys & (FEB_BTN_OK | FEB_BTN_UP)) {
                if (prev_flap == 0) {
                    action_pressed = 1;
                }
                prev_flap = 1;
            } else {
                prev_flap = 0;
            }

            /* Input handling */
            if (action_pressed) {
                jump_timer = 5;
                fall_speed = 0;
                flap_anim = 6;
            }

            /* Flap animation decay */
            if (flap_anim > 0) {
                flap_anim--;
            }

            /* Physics: jump vs gravity */
            if (jump_timer > 0) {
                uint8_t dy = 2;
                if (jump_timer >= 4) {
                    dy = 3;
                } else if (jump_timer == 1) {
                    dy = 1;
                }

                if (bird_y > dy + 1) {
                    bird_y -= dy;
                } else {
                    bird_y = 1;
                    jump_timer = 0;
                }
                jump_timer--;
                fall_speed = 0;
            } else {
                if (fall_speed < 10) {
                    fall_speed++;
                }
                uint8_t dy = 1;
                if (fall_speed >= 6) {
                    dy = 2;
                } else if (fall_speed <= 2) {
                    if ((fall_speed & 1) == 0) {
                        dy = 0;
                    }
                }
                bird_y += dy;
            }

            /* Pipe scrolling & wrapping */
            pipe1_x--;
            if (pipe1_x == 0) {
                pipe1_x = 144;
                pipe1_gap = 8 + (feb_rand(0x07));
            }
            if (pipe1_x == 14) {
                score++;
            }

            pipe2_x--;
            if (pipe2_x == 0) {
                pipe2_x = 144;
                pipe2_gap = 8 + (feb_rand(0x07));
            }
            if (pipe2_x == 14) {
                score++;
            }

            /* Collision Check: forgiving 1px margin around 8x8 sprite */
            uint8_t hit = 0;
            if (bird_y >= 49) {
                hit = 1;
            }

            if (pipe1_x >= 16 && pipe1_x <= 30) {
                if ((bird_y + 1) < pipe1_gap || (bird_y + 6) > (pipe1_gap + PIPE_GAP_H)) {
                    hit = 1;
                }
            }

            if (pipe2_x >= 16 && pipe2_x <= 30) {
                if ((bird_y + 1) < pipe2_gap || (bird_y + 6) > (pipe2_gap + PIPE_GAP_H)) {
                    hit = 1;
                }
            }

            if (hit) {
                if (score > best_score) {
                    best_score = score;
                    feb_save_flags(&best_score, 1);
                }
                game_state = STATE_GAMEOVER;
            }

            render_world();
            feb_delay_frames(2);
        } else if (game_state == STATE_GAMEOVER) {
            render_world();

            /* Game Over Modal Box */
            feb_set_draw_mode(FEB_DRAW_MODE_CLEAR);
            feb_fill_rect(20, 10, 88, 42);
            feb_set_draw_mode(FEB_DRAW_MODE_SET);
            feb_draw_rect(20, 10, 88, 42);

            feb_draw_string(32, 14, "GAME OVER", FEB_FONT_6X10);
            feb_draw_string(28, 26, "SCORE:", FEB_FONT_4X6);
            feb_draw_number(56, 26, score, FEB_FONT_4X6);
            feb_draw_string(28, 34, "BEST:", FEB_FONT_4X6);
            feb_draw_number(56, 34, best_score, FEB_FONT_4X6);
            feb_draw_string(24, 42, "OK:PLAY  BACK:EXIT", FEB_FONT_4X6);

            uint8_t key = feb_wait_key();
            if (key == FEB_KEY_BACK) {
                feb_exit();
            }
            if (key == FEB_KEY_OK || key == FEB_KEY_UP) {
                reset_game();
                game_state = STATE_PLAYING;
            }
        }
    }

    return 0;
}
