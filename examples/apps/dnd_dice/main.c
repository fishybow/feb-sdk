/**
 * @file main.c
 * @brief D&D Polyhedral Dice Roller for Flashiibo Pro Gen2 & Gen3 FEB Runner (.feb)
 *
 * Replicates the firmware D&D Dice applet (applets_dnd_dice_view.c):
 *   - Supports 7 standard RPG polyhedral dice: D4, D6, D8, D10, D12, D20, D100
 *   - Header selector with UP/DOWN arrows
 *   - Framed display area with IDLE ("PRESS OK"), ROLLING animation, and RESULT states
 *   - Controls:
 *       OK: Roll dice
 *       UP: Next dice type
 *       DOWN: Previous dice type
 *       BACK: Exit application
 *       UP+DOWN: Hardware exit chord
 *   - Compatible with both 3-button (Gen2) and 4-button (Gen3) devices
 */

#include "../../../include/feb.h"

#define STATE_IDLE    0
#define STATE_ROLLING 1
#define STATE_RESULT  2

#define DICE_COUNT 7

static const uint8_t SIDES[DICE_COUNT] = {4, 6, 8, 10, 12, 20, 100};

static uint8_t dice_idx;
static uint8_t state;
static uint8_t roll_frames;
static uint8_t current_val;

static void draw_header(void) {
    if (dice_idx == 0) {
        feb_draw_string(37, 3, "v  D4   ^", FEB_FONT_6X10);
    } else if (dice_idx == 1) {
        feb_draw_string(37, 3, "v  D6   ^", FEB_FONT_6X10);
    } else if (dice_idx == 2) {
        feb_draw_string(37, 3, "v  D8   ^", FEB_FONT_6X10);
    } else if (dice_idx == 3) {
        feb_draw_string(37, 3, "v  D10  ^", FEB_FONT_6X10);
    } else if (dice_idx == 4) {
        feb_draw_string(37, 3, "v  D12  ^", FEB_FONT_6X10);
    } else if (dice_idx == 5) {
        feb_draw_string(37, 3, "v  D20  ^", FEB_FONT_6X10);
    } else if (dice_idx == 6) {
        feb_draw_string(37, 3, "v D100  ^", FEB_FONT_6X10);
    }
}

static void draw_centered_number(uint8_t y, uint8_t val, uint8_t font) {
    uint8_t w = 6;
    if (font == FEB_FONT_RETRO_8X8) {
        w = 8;
    }
    uint8_t x = 60;
    if (val >= 100) {
        x = 64 - (w * 3) / 2;
    } else if (val >= 10) {
        x = 64 - w;
    } else {
        x = 64 - w / 2;
    }
    feb_draw_number(x, y, val, font);
}

static void render(void) {
    feb_clear_screen();
    feb_set_draw_mode(FEB_DRAW_MODE_SET);

    /* 1. Header with Selector */
    draw_header();

    /* 2. Middle Frame Box (x=10, y=16, w=108, h=44) */
    feb_draw_rect(10, 16, 108, 44);

    /* 3. Box Content based on State */
    if (state == STATE_IDLE) {
        feb_draw_string(40, 34, "PRESS OK", FEB_FONT_6X10);
    } else if (state == STATE_ROLLING) {
        draw_centered_number(24, current_val, FEB_FONT_6X10);
        feb_draw_string(44, 42, "ROLLING...", FEB_FONT_4X6);
    } else if (state == STATE_RESULT) {
        draw_centered_number(32, current_val, FEB_FONT_RETRO_8X8);
    }
}

int main(void) {
    feb_set_high_res(true);

    dice_idx = 5; /* D20 by default */
    state = STATE_IDLE;
    roll_frames = 0;
    current_val = 20;

    uint8_t prev_buttons = 0;

    while (1) {
        uint8_t buttons = feb_get_keys();
        uint8_t just_pressed = buttons & ~prev_buttons;
        prev_buttons = buttons;

        if (state == STATE_ROLLING) {
            uint8_t s = SIDES[dice_idx];
            current_val = feb_rand(s) + 1;
            roll_frames++;
            if (roll_frames >= 35) {
                state = STATE_RESULT;
                roll_frames = 0;
            }
        } else {
            if (just_pressed & FEB_BTN_OK) {
                state = STATE_ROLLING;
                roll_frames = 0;
            } else if (just_pressed & FEB_BTN_UP) {
                if (dice_idx < (DICE_COUNT - 1)) {
                    dice_idx++;
                } else {
                    dice_idx = 0;
                }
                state = STATE_IDLE;
            } else if (just_pressed & FEB_BTN_DOWN) {
                if (dice_idx > 0) {
                    dice_idx--;
                } else {
                    dice_idx = DICE_COUNT - 1;
                }
                state = STATE_IDLE;
            }
        }

        if (just_pressed & FEB_BTN_BACK) {
            feb_exit();
        }

        render();
        feb_delay_frames(1);
    }

    return 0;
}
