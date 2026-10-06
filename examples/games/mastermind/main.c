/**
 * @file main.c
 * @brief Master Mind Game for Flashiibo Pro Gen3 FEB Runner (.feb)
 *
 * Implements the classic code-breaking puzzle matching the built-in firmware
 * Master Mind game (games_mastermind_view.c) pixel-for-pixel:
 *   - 4-digit code (no duplicates, digits 0..9)
 *   - 6 guess attempts with row labels "1:" through "6:"
 *   - Active cursor highlight box on current digit
 *   - 3-column clue counters: Perfect (solid disc), Number Only (half circle), Incorrect (circle)
 *   - Header status: "MASTERMIND / TRY x/6", "! NO DUPLICATE DIGITS !", "* YOU WIN! *", "LOST! CODE:xxxx"
 *   - Controls: UP/DOWN cycle digits, OK advance/submit, BACK retreat/wrap cursor
 *   - UP+DOWN system exit chord back to FEB Runner menu
 */

#include "../../../include/feb.h"

#define MASTERMIND_CODE_LEN     4
#define MASTERMIND_MAX_GUESSES  6

#define STATE_PLAYING  0
#define STATE_WON      1
#define STATE_LOST     2

static uint8_t secret_code[MASTERMIND_CODE_LEN];
static uint8_t current_digits[MASTERMIND_CODE_LEN];
static uint8_t current_cursor;
static uint8_t guess_count;
static uint8_t state;
static uint8_t error_timer;

static uint8_t history_digits[24];
static uint8_t history_exact[MASTERMIND_MAX_GUESSES];
static uint8_t history_wrong_pos[MASTERMIND_MAX_GUESSES];
static uint8_t history_wrong_num[MASTERMIND_MAX_GUESSES];

static const uint8_t DIGIT_X[4] = {12, 24, 36, 48};
static uint8_t puzzle_digits[10];

/* -------------------------------------------------------------------------
 * Puzzle Generation & Clue Calculations
 * ------------------------------------------------------------------------- */

static void generate_puzzle(void) {
    for (uint8_t i = 0; i < 10; i++) {
        puzzle_digits[i] = i;
    }

    /* Fisher-Yates shuffle using feb_rand */
    for (uint8_t i = 9; i > 0; i--) {
        uint8_t j = feb_rand(15);
        while (j > i) {
            j -= (i + 1);
        }
        uint8_t tmp = puzzle_digits[i];
        puzzle_digits[i] = puzzle_digits[j];
        puzzle_digits[j] = tmp;
    }

    for (uint8_t i = 0; i < MASTERMIND_CODE_LEN; i++) {
        secret_code[i] = puzzle_digits[i];
    }
}

static bool has_duplicates(void) {
    for (uint8_t i = 0; i < MASTERMIND_CODE_LEN; i++) {
        for (uint8_t j = i + 1; j < MASTERMIND_CODE_LEN; j++) {
            if (current_digits[i] == current_digits[j]) {
                return true;
            }
        }
    }
    return false;
}

static void calculate_clues(uint8_t row) {
    uint8_t exact = 0;
    uint8_t wrong_pos = 0;

    for (uint8_t i = 0; i < MASTERMIND_CODE_LEN; i++) {
        if (current_digits[i] == secret_code[i]) {
            exact++;
        } else {
            for (uint8_t j = 0; j < MASTERMIND_CODE_LEN; j++) {
                if (current_digits[i] == secret_code[j]) {
                    wrong_pos++;
                    break;
                }
            }
        }
    }

    history_exact[row] = exact;
    history_wrong_pos[row] = wrong_pos;
    history_wrong_num[row] = MASTERMIND_CODE_LEN - exact - wrong_pos;
}

static void new_game(void) {
    generate_puzzle();
    current_digits[0] = 0;
    current_digits[1] = 1;
    current_digits[2] = 2;
    current_digits[3] = 3;
    current_cursor = 0;
    guess_count = 0;
    error_timer = 0;
    state = STATE_PLAYING;
}

/* -------------------------------------------------------------------------
 * Rendering (Matching games_mastermind_view.c)
 * ------------------------------------------------------------------------- */

static void render_header(void) {
    if (error_timer > 0) {
        feb_set_draw_mode(FEB_DRAW_MODE_SET);
        feb_fill_rect(0, 0, 128, 8);
        feb_set_draw_mode(FEB_DRAW_MODE_CLEAR);
        feb_draw_string(18, 1, "! NO DUPLICATE DIGITS !", FEB_FONT_4X6);
    } else if (state == STATE_WON) {
        feb_set_draw_mode(FEB_DRAW_MODE_SET);
        feb_fill_rect(0, 0, 128, 8);
        feb_set_draw_mode(FEB_DRAW_MODE_CLEAR);
        feb_draw_string(4, 1, "* YOU WIN! *", FEB_FONT_4X6);
        feb_draw_string(68, 1, "PRESS OK: AGAIN", FEB_FONT_4X6);
    } else if (state == STATE_LOST) {
        feb_set_draw_mode(FEB_DRAW_MODE_SET);
        feb_fill_rect(0, 0, 128, 8);
        feb_set_draw_mode(FEB_DRAW_MODE_CLEAR);
        feb_draw_string(4, 1, "LOST! CODE:", FEB_FONT_4X6);
        for (uint8_t d = 0; d < 4; d++) {
            feb_draw_char(48 + d * 5, 1, '0' + secret_code[d], FEB_FONT_4X6);
        }
        feb_draw_string(82, 1, "OK: AGAIN", FEB_FONT_4X6);
    } else {
        feb_set_draw_mode(FEB_DRAW_MODE_SET);
        feb_draw_string(2, 1, "MASTERMIND", FEB_FONT_4X6);
        feb_draw_string(94, 1, "TRY ", FEB_FONT_4X6);
        feb_draw_char(110, 1, '1' + guess_count, FEB_FONT_4X6);
        feb_draw_string(114, 1, "/6", FEB_FONT_4X6);
    }

    feb_set_draw_mode(FEB_DRAW_MODE_SET);
    feb_draw_hline(0, 8, 128);
    feb_draw_vline(60, 8, 56);
}

static void render_rows(void) {
    uint8_t row_y = 11;

    for (uint8_t r = 0; r < MASTERMIND_MAX_GUESSES; r++) {
        /* Row number "1:".."6:" */
        feb_set_draw_mode(FEB_DRAW_MODE_SET);
        feb_draw_char(2, row_y + 1, '1' + r, FEB_FONT_4X6);
        feb_draw_char(6, row_y + 1, ':', FEB_FONT_4X6);

        if (r < guess_count) {
            /* Past submitted digits */
            for (uint8_t d = 0; d < 4; d++) {
                feb_draw_char(DIGIT_X[d], row_y - 1, '0' + history_digits[(r << 2) + d], FEB_FONT_RETRO_8X8);
            }

            /* Clues: Perfect (solid disc), Number-only (half-filled), Incorrect (circle) */
            /* 1. Perfect */
            feb_fill_circle(66, row_y + 4, 2);
            feb_draw_char(76, row_y, '0' + history_exact[r], FEB_FONT_RETRO_8X8);

            /* 2. Number only: hollow circle with filled left half */
            feb_draw_circle(89, row_y + 4, 2);
            feb_draw_vline(88, row_y + 3, 3);
            feb_draw_vline(89, row_y + 2, 5);
            feb_draw_char(98, row_y, '0' + history_wrong_pos[r], FEB_FONT_RETRO_8X8);

            /* 3. Incorrect: hollow circle */
            feb_draw_circle(111, row_y + 4, 2);
            feb_draw_char(120, row_y, '0' + history_wrong_num[r], FEB_FONT_RETRO_8X8);

        } else if (r == guess_count && state == STATE_PLAYING) {
            /* Active current guess */
            for (uint8_t d = 0; d < 4; d++) {
                if (d == current_cursor) {
                    /* Highlight cursor */
                    feb_set_draw_mode(FEB_DRAW_MODE_SET);
                    feb_fill_rect(DIGIT_X[d] - 1, row_y - 1, 8, 9);
                    feb_set_draw_mode(FEB_DRAW_MODE_CLEAR);
                    feb_draw_char(DIGIT_X[d], row_y - 1, '0' + current_digits[d], FEB_FONT_RETRO_8X8);
                    feb_set_draw_mode(FEB_DRAW_MODE_SET);
                } else {
                    feb_draw_char(DIGIT_X[d], row_y - 1, '0' + current_digits[d], FEB_FONT_RETRO_8X8);
                }
            }
        } else {
            /* Future unreached row */
            for (uint8_t d = 0; d < 4; d++) {
                feb_draw_char(DIGIT_X[d] + 1, row_y + 1, '-', FEB_FONT_4X6);
            }
        }

        row_y += 9;
    }
}

static void render_all(void) {
    feb_clear_screen();
    render_header();
    render_rows();
}

/* -------------------------------------------------------------------------
 * Main Entry Point
 * ------------------------------------------------------------------------- */

int main(void) {
    feb_set_high_res(true);
    feb_set_draw_mode(FEB_DRAW_MODE_SET);

    new_game();
    render_all();

    while (1) {
        uint8_t key = feb_wait_key();

        if (state == STATE_WON || state == STATE_LOST) {
            if (key == FEB_KEY_OK) {
                new_game();
                render_all();
            }
        } else {
            if (key == FEB_KEY_UP) {
                error_timer = 0;
                current_digits[current_cursor] = (current_digits[current_cursor] + 1) % 10;
                render_all();
            } else if (key == FEB_KEY_DOWN) {
                error_timer = 0;
                current_digits[current_cursor] = (current_digits[current_cursor] + 9) % 10;
                render_all();
            } else if (key == FEB_KEY_BACK) {
                error_timer = 0;
                if (current_cursor > 0) {
                    current_cursor--;
                } else {
                    current_cursor = 3;
                }
                render_all();
            } else if (key == FEB_KEY_OK) {
                if (current_cursor < 3) {
                    current_cursor++;
                    render_all();
                } else {
                    /* Submit guess on slot 3 */
                    if (has_duplicates()) {
                        error_timer = 1;
                        render_all();
                    } else {
                        error_timer = 0;
                        for (uint8_t d = 0; d < 4; d++) {
                            history_digits[(guess_count << 2) + d] = current_digits[d];
                        }
                        calculate_clues(guess_count);

                        bool win = (history_exact[guess_count] == 4);
                        guess_count++;

                        if (win) {
                            state = STATE_WON;
                        } else if (guess_count >= MASTERMIND_MAX_GUESSES) {
                            state = STATE_LOST;
                        } else {
                            current_cursor = 0;
                        }
                        render_all();
                    }
                }
            }
        }
    }

    return 0;
}
