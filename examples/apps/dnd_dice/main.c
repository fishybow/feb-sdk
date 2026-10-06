/**
 * @file main.c
 * @brief D&D Polyhedral Dice Roller for Flashiibo Pro Gen2 & Gen3 FEB Runner (.feb)
 *
 * Authentic recreation of firmware D&D Dice applet (applets_dnd_dice_view.c):
 *   - Supports 7 standard RPG polyhedral dice: D4, D6, D8, D10, D12, D20, D100
 *   - Custom designed 16x16 big typography font for all 10 digits (0..9)
 *   - Header selector with solid DOWN and UP arrow icons and centered die name
 *   - Rounded frame display box (108x46)
 *   - Three states:
 *       IDLE: "Press OK to roll"
 *       ROLLING: High-speed animated number shuffling
 *       RESULT: Big digit readout of final roll result
 *   - Controls:
 *       OK: Roll dice
 *       UP: Next dice type
 *       DOWN: Previous dice type
 *       BACK: Exit application
 *       UP+DOWN: Hardware exit chord
 */

#include "../../../include/feb.h"

#define STATE_IDLE    0
#define STATE_ROLLING 1
#define STATE_RESULT  2

#define DICE_COUNT 7

static const uint8_t SIDES[DICE_COUNT] = {4, 6, 8, 10, 12, 20, 100};

static const uint8_t spr_arrow_up[7] = {
    0x10, /*    #    */
    0x38, /*   ###   */
    0x7C, /*  #####  */
    0xFE, /* ####### */
    0x38, /*   ###   */
    0x38, /*   ###   */
    0x38  /*   ###   */
};

static const uint8_t spr_arrow_down[7] = {
    0x38, /*   ###   */
    0x38, /*   ###   */
    0x38, /*   ###   */
    0xFE, /* ####### */
    0x7C, /*  #####  */
    0x38, /*   ###   */
    0x10  /*    #    */
};

/* Custom 16x16 Big Font for 10 Digits (0..9) */
static const uint8_t spr_dig_0[32] = {
    0x3E, 0x00, 0x63, 0x00, 0xC1, 0x80, 0xC1, 0x80,
    0xC1, 0x80, 0xC1, 0x80, 0xC1, 0x80, 0xC1, 0x80,
    0xC1, 0x80, 0xC1, 0x80, 0xC1, 0x80, 0xC1, 0x80,
    0x63, 0x00, 0x3E, 0x00, 0x00, 0x00, 0x00, 0x00,
};

static const uint8_t spr_dig_1[32] = {
    0x18, 0x00, 0x38, 0x00, 0x78, 0x00, 0x18, 0x00,
    0x18, 0x00, 0x18, 0x00, 0x18, 0x00, 0x18, 0x00,
    0x18, 0x00, 0x18, 0x00, 0x18, 0x00, 0x18, 0x00,
    0x7E, 0x00, 0x7E, 0x00, 0x00, 0x00, 0x00, 0x00,
};

static const uint8_t spr_dig_2[32] = {
    0x3E, 0x00, 0x63, 0x00, 0xC1, 0x80, 0x01, 0x80,
    0x03, 0x00, 0x06, 0x00, 0x0C, 0x00, 0x18, 0x00,
    0x30, 0x00, 0x60, 0x00, 0xC0, 0x00, 0xC0, 0x80,
    0xFF, 0x80, 0xFF, 0x80, 0x00, 0x00, 0x00, 0x00,
};

static const uint8_t spr_dig_3[32] = {
    0x3E, 0x00, 0x63, 0x00, 0xC1, 0x80, 0x01, 0x80,
    0x03, 0x00, 0x1E, 0x00, 0x1E, 0x00, 0x03, 0x00,
    0x01, 0x80, 0x01, 0x80, 0xC1, 0x80, 0x63, 0x00,
    0x3E, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
};

static const uint8_t spr_dig_4[32] = {
    0x03, 0x00, 0x07, 0x00, 0x0F, 0x00, 0x1B, 0x00,
    0x33, 0x00, 0x63, 0x00, 0xC3, 0x00, 0xFF, 0x80,
    0xFF, 0x80, 0x03, 0x00, 0x03, 0x00, 0x03, 0x00,
    0x0F, 0x80, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
};

static const uint8_t spr_dig_5[32] = {
    0xFF, 0x80, 0xFF, 0x80, 0xC0, 0x00, 0xC0, 0x00,
    0xFE, 0x00, 0xFF, 0x00, 0x01, 0x80, 0x01, 0x80,
    0x01, 0x80, 0x01, 0x80, 0xC1, 0x80, 0x63, 0x00,
    0x3E, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
};

static const uint8_t spr_dig_6[32] = {
    0x1F, 0x00, 0x33, 0x00, 0x61, 0x80, 0xC0, 0x00,
    0xC0, 0x00, 0xFE, 0x00, 0xC3, 0x00, 0xC1, 0x80,
    0xC1, 0x80, 0xC1, 0x80, 0x63, 0x00, 0x3E, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
};

static const uint8_t spr_dig_7[32] = {
    0xFF, 0x80, 0xFF, 0x80, 0x01, 0x80, 0x03, 0x00,
    0x06, 0x00, 0x0C, 0x00, 0x18, 0x00, 0x30, 0x00,
    0x30, 0x00, 0x60, 0x00, 0x60, 0x00, 0x60, 0x00,
    0x60, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
};

static const uint8_t spr_dig_8[32] = {
    0x3E, 0x00, 0x63, 0x00, 0xC1, 0x80, 0xC1, 0x80,
    0x63, 0x00, 0x3E, 0x00, 0x63, 0x00, 0xC1, 0x80,
    0xC1, 0x80, 0xC1, 0x80, 0x63, 0x00, 0x3E, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
};

static const uint8_t spr_dig_9[32] = {
    0x3E, 0x00, 0x63, 0x00, 0xC1, 0x80, 0xC1, 0x80,
    0xC1, 0x80, 0x63, 0x00, 0x3F, 0x80, 0x01, 0x80,
    0x01, 0x80, 0x03, 0x00, 0x06, 0x00, 0x3C, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
};

static uint8_t dice_idx;
static uint8_t state;
static uint8_t roll_frames;
static uint8_t current_val;

static void draw_big_digit(uint8_t x, uint8_t y, uint8_t d) {
    if (d == 0) feb_draw_sprite16(x, y, spr_dig_0);
    else if (d == 1) feb_draw_sprite16(x, y, spr_dig_1);
    else if (d == 2) feb_draw_sprite16(x, y, spr_dig_2);
    else if (d == 3) feb_draw_sprite16(x, y, spr_dig_3);
    else if (d == 4) feb_draw_sprite16(x, y, spr_dig_4);
    else if (d == 5) feb_draw_sprite16(x, y, spr_dig_5);
    else if (d == 6) feb_draw_sprite16(x, y, spr_dig_6);
    else if (d == 7) feb_draw_sprite16(x, y, spr_dig_7);
    else if (d == 8) feb_draw_sprite16(x, y, spr_dig_8);
    else if (d == 9) feb_draw_sprite16(x, y, spr_dig_9);
}

static void draw_big_number(uint8_t val) {
    if (val >= 100) {
        draw_big_digit(42, 29, 1);
        draw_big_digit(56, 29, 0);
        draw_big_digit(70, 29, 0);
    } else if (val >= 10) {
        uint8_t d1 = val / 10;
        uint8_t d2 = val % 10;
        draw_big_digit(49, 29, d1);
        draw_big_digit(64, 29, d2);
    } else {
        draw_big_digit(56, 29, val);
    }
}

static void draw_header(void) {
    if (dice_idx == 0) {
        feb_draw_sprite(47, 4, spr_arrow_down, 7);
        feb_draw_string(58, 3, "D4", FEB_FONT_6X10);
        feb_draw_sprite(74, 4, spr_arrow_up, 7);
    } else if (dice_idx == 1) {
        feb_draw_sprite(47, 4, spr_arrow_down, 7);
        feb_draw_string(58, 3, "D6", FEB_FONT_6X10);
        feb_draw_sprite(74, 4, spr_arrow_up, 7);
    } else if (dice_idx == 2) {
        feb_draw_sprite(47, 4, spr_arrow_down, 7);
        feb_draw_string(58, 3, "D8", FEB_FONT_6X10);
        feb_draw_sprite(74, 4, spr_arrow_up, 7);
    } else if (dice_idx == 3) {
        feb_draw_sprite(44, 4, spr_arrow_down, 7);
        feb_draw_string(55, 3, "D10", FEB_FONT_6X10);
        feb_draw_sprite(77, 4, spr_arrow_up, 7);
    } else if (dice_idx == 4) {
        feb_draw_sprite(44, 4, spr_arrow_down, 7);
        feb_draw_string(55, 3, "D12", FEB_FONT_6X10);
        feb_draw_sprite(77, 4, spr_arrow_up, 7);
    } else if (dice_idx == 5) {
        feb_draw_sprite(44, 4, spr_arrow_down, 7);
        feb_draw_string(55, 3, "D20", FEB_FONT_6X10);
        feb_draw_sprite(77, 4, spr_arrow_up, 7);
    } else if (dice_idx == 6) {
        feb_draw_sprite(41, 4, spr_arrow_down, 7);
        feb_draw_string(52, 3, "D100", FEB_FONT_6X10);
        feb_draw_sprite(80, 4, spr_arrow_up, 7);
    }
}

static void draw_rounded_box(void) {
    feb_draw_hline(13, 14, 102);
    feb_draw_hline(13, 59, 102);
    feb_draw_vline(10, 17, 40);
    feb_draw_vline(117, 17, 40);
    feb_draw_pixel(11, 15);
    feb_draw_pixel(12, 15);
    feb_draw_pixel(11, 16);
    feb_draw_pixel(116, 15);
    feb_draw_pixel(115, 15);
    feb_draw_pixel(116, 16);
    feb_draw_pixel(11, 58);
    feb_draw_pixel(12, 58);
    feb_draw_pixel(11, 57);
    feb_draw_pixel(116, 58);
    feb_draw_pixel(115, 58);
    feb_draw_pixel(116, 57);
}

static void render(void) {
    feb_clear_screen();
    feb_set_draw_mode(FEB_DRAW_MODE_SET);

    /* 1. Header with Selector */
    draw_header();

    /* 2. Middle Frame Box (x=10, y=14, w=108, h=46) */
    draw_rounded_box();

    /* 3. Box Content based on State */
    if (state == STATE_IDLE) {
        feb_draw_string(16, 33, "Press OK to roll", FEB_FONT_6X10);
    } else if (state == STATE_ROLLING) {
        draw_big_number(current_val);
    } else if (state == STATE_RESULT) {
        draw_big_number(current_val);
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
            roll_frames++;
            if ((roll_frames & 3) == 0) {
                uint8_t s = SIDES[dice_idx];
                current_val = (feb_rand(255) % s) + 1;
            }
            if (roll_frames >= 40) {
                uint8_t s = SIDES[dice_idx];
                current_val = (feb_rand(255) % s) + 1;
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
