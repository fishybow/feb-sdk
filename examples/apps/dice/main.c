/**
 * @file main.c
 * @brief Standard 6-Sided Dice Roller for Flashiibo Pro Gen2 & Gen3 FEB Runner (.feb)
 *
 * Authentic recreation of firmware Standard Dice applet (applets_std_dice_view.c):
 *   - 1 to 6 customizable dice count
 *   - Fixed-size 16x16 pixel dice rendered entirely with custom face sprites
 *   - Clean multi-dice layouts (1, 2-3 row, 4-6 two-row grids)
 *   - Right-side vertical control panel with UP icon, count digit, DOWN icon
 *   - 45-frame rolling animation with rapid intermediate face shuffling
 *   - Preserves existing dice values when cycling dice count
 *   - Controls:
 *       OK: Roll dice
 *       UP: Increase count (1..6)
 *       DOWN: Decrease count (1..6)
 *       BACK: Exit application
 *       UP+DOWN: Hardware exit chord
 */

#include "../../../include/feb.h"

#define STATE_IDLE    0
#define STATE_ROLLING 1

static const uint8_t spr_die_1[32] = {
    0x3F, 0xFC, 0x7F, 0xFE, 0xC0, 0x03, 0x80, 0x01,
    0x80, 0x01, 0x80, 0x01, 0x81, 0x81, 0x83, 0xC1,
    0x83, 0xC1, 0x81, 0x81, 0x80, 0x01, 0x80, 0x01,
    0x80, 0x01, 0xC0, 0x03, 0x7F, 0xFE, 0x3F, 0xFC,
};

static const uint8_t spr_die_2[32] = {
    0x3F, 0xFC, 0x7F, 0xFE, 0xC0, 0x03, 0x98, 0x01,
    0x98, 0x01, 0x80, 0x01, 0x80, 0x01, 0x80, 0x01,
    0x80, 0x01, 0x80, 0x01, 0x80, 0x01, 0x80, 0x19,
    0x80, 0x19, 0xC0, 0x03, 0x7F, 0xFE, 0x3F, 0xFC,
};

static const uint8_t spr_die_3[32] = {
    0x3F, 0xFC, 0x7F, 0xFE, 0xC0, 0x03, 0x98, 0x01,
    0x98, 0x01, 0x80, 0x01, 0x80, 0x01, 0x81, 0x81,
    0x81, 0x81, 0x80, 0x01, 0x80, 0x01, 0x80, 0x19,
    0x80, 0x19, 0xC0, 0x03, 0x7F, 0xFE, 0x3F, 0xFC,
};

static const uint8_t spr_die_4[32] = {
    0x3F, 0xFC, 0x7F, 0xFE, 0xC0, 0x03, 0x98, 0x19,
    0x98, 0x19, 0x80, 0x01, 0x80, 0x01, 0x80, 0x01,
    0x80, 0x01, 0x80, 0x01, 0x80, 0x01, 0x98, 0x19,
    0x98, 0x19, 0xC0, 0x03, 0x7F, 0xFE, 0x3F, 0xFC,
};

static const uint8_t spr_die_5[32] = {
    0x3F, 0xFC, 0x7F, 0xFE, 0xC0, 0x03, 0x98, 0x19,
    0x98, 0x19, 0x80, 0x01, 0x80, 0x01, 0x81, 0x81,
    0x81, 0x81, 0x80, 0x01, 0x80, 0x01, 0x98, 0x19,
    0x98, 0x19, 0xC0, 0x03, 0x7F, 0xFE, 0x3F, 0xFC,
};

static const uint8_t spr_die_6[32] = {
    0x3F, 0xFC, 0x7F, 0xFE, 0xC0, 0x03, 0x98, 0x19,
    0x98, 0x19, 0x80, 0x01, 0x80, 0x01, 0x98, 0x19,
    0x98, 0x19, 0x80, 0x01, 0x80, 0x01, 0x98, 0x19,
    0x98, 0x19, 0xC0, 0x03, 0x7F, 0xFE, 0x3F, 0xFC,
};

static uint8_t dice_count;
static uint8_t dice_values[6];
static uint8_t state;
static uint8_t roll_frames;

static void draw_die(uint8_t x, uint8_t y, uint8_t val) {
    if (val == 1) feb_draw_sprite16(x, y, spr_die_1);
    else if (val == 2) feb_draw_sprite16(x, y, spr_die_2);
    else if (val == 3) feb_draw_sprite16(x, y, spr_die_3);
    else if (val == 4) feb_draw_sprite16(x, y, spr_die_4);
    else if (val == 5) feb_draw_sprite16(x, y, spr_die_5);
    else if (val == 6) feb_draw_sprite16(x, y, spr_die_6);
}

static void randomize_values(void) {
    for (uint8_t i = 0; i < dice_count; i++) {
        dice_values[i] = (feb_rand(255) % 6) + 1;
    }
}

static void render(void) {
    feb_clear_screen();
    feb_set_draw_mode(FEB_DRAW_MODE_SET);

    /* 1. Left Playfield Box & Right Control Panel Box */
    feb_draw_rrect(2, 3, 105, 58);
    feb_draw_rrect(109, 3, 17, 58);

    /* 2. Right Control Panel (Arrow triangles & count digit) */
    feb_draw_triangle(113, 14, 121, 14, 117, 8);
    feb_draw_number(115, 27, dice_count, FEB_FONT_6X10);
    feb_draw_triangle(113, 50, 121, 50, 117, 56);

    /* 3. Left Playfield (Dice Area) */
    if (dice_count == 1) {
        draw_die(45, 24, dice_values[0]);
    } else if (dice_count == 2) {
        draw_die(25, 24, dice_values[0]);
        draw_die(65, 24, dice_values[1]);
    } else if (dice_count == 3) {
        draw_die(15, 24, dice_values[0]);
        draw_die(45, 24, dice_values[1]);
        draw_die(75, 24, dice_values[2]);
    } else if (dice_count == 4) {
        draw_die(25, 10, dice_values[0]);
        draw_die(65, 10, dice_values[1]);
        draw_die(25, 38, dice_values[2]);
        draw_die(65, 38, dice_values[3]);
    } else if (dice_count == 5) {
        draw_die(15, 10, dice_values[0]);
        draw_die(45, 10, dice_values[1]);
        draw_die(75, 10, dice_values[2]);
        draw_die(25, 38, dice_values[3]);
        draw_die(65, 38, dice_values[4]);
    } else if (dice_count == 6) {
        draw_die(15, 10, dice_values[0]);
        draw_die(45, 10, dice_values[1]);
        draw_die(75, 10, dice_values[2]);
        draw_die(15, 38, dice_values[3]);
        draw_die(45, 38, dice_values[4]);
        draw_die(75, 38, dice_values[5]);
    }
}

int main(void) {
    feb_set_high_res(true);

    dice_count = 1;
    for (uint8_t i = 0; i < 6; i++) {
        dice_values[i] = (feb_rand(255) % 6) + 1;
    }
    state = STATE_IDLE;
    roll_frames = 0;

    uint8_t prev_buttons = 0;

    while (1) {
        uint8_t buttons = feb_get_keys();
        uint8_t just_pressed = buttons & ~prev_buttons;
        prev_buttons = buttons;

        if (state == STATE_ROLLING) {
            roll_frames++;
            if ((roll_frames & 3) == 0) {
                randomize_values();
            }
            if (roll_frames >= 45) {
                state = STATE_IDLE;
                roll_frames = 0;
            }
        } else {
            if (just_pressed & FEB_BTN_OK) {
                state = STATE_ROLLING;
                roll_frames = 0;
                randomize_values();
            } else if (just_pressed & FEB_BTN_UP) {
                if (dice_count < 6) {
                    dice_count++;
                } else {
                    dice_count = 1;
                }
            } else if (just_pressed & FEB_BTN_DOWN) {
                if (dice_count > 1) {
                    dice_count--;
                } else {
                    dice_count = 6;
                }
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
