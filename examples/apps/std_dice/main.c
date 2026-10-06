/**
 * @file main.c
 * @brief Standard 6-Sided Dice Roller for Flashiibo Pro Gen2 & Gen3 FEB Runner (.feb)
 *
 * Replicates the firmware Standard Dice applet (applets_std_dice_view.c):
 *   - 1 to 6 customizable dice count
 *   - Single die mode: Large 50x50 die with authentic pip layouts
 *   - 2-3 dice mode: 25x25 dice in a single row
 *   - 4-6 dice mode: 25x25 dice in two rows
 *   - Rolling animation for ~0.7 seconds (40 frames)
 *   - Controls:
 *       OK: Roll dice
 *       UP: Increase count (1..6)
 *       DOWN: Decrease count (1..6)
 *       BACK: Exit application
 *       UP+DOWN: Hardware exit chord
 *   - Compatible with both 3-button (Gen2) and 4-button (Gen3) devices
 */

#include "../../../include/feb.h"

#define STATE_IDLE    0
#define STATE_ROLLING 1

static uint8_t dice_count;
static uint8_t dice_values[6];
static uint8_t state;
static uint8_t roll_frames;

static void draw_pip(uint8_t px, uint8_t py, uint8_t r) {
    if (r <= 2) {
        feb_fill_rect(px - 1, py - 1, 3, 3);
    } else {
        feb_fill_rect(px - 3, py - 2, 7, 5);
        feb_fill_rect(px - 2, py - 3, 5, 7);
    }
}

static void draw_die_face(uint8_t die_x, uint8_t die_y, uint8_t val, uint8_t scale) {
    if (val < 1 || val > 6) return;

    uint8_t o1 = 6;
    uint8_t o2 = 12;
    uint8_t o3 = 18;
    uint8_t rp = 1;
    uint8_t rp1 = 2;

    if (scale == 2) {
        feb_draw_rect(die_x, die_y, 50, 50);
        o1 = 12;
        o2 = 25;
        o3 = 38;
        rp = 2;
        rp1 = 4;
    } else {
        feb_draw_rect(die_x, die_y, 25, 25);
    }

    if (val == 1) {
        draw_pip(die_x + o2, die_y + o2, rp1);
    } else if (val == 2) {
        draw_pip(die_x + o1, die_y + o1, rp);
        draw_pip(die_x + o3, die_y + o3, rp);
    } else if (val == 3) {
        draw_pip(die_x + o1, die_y + o1, rp);
        draw_pip(die_x + o2, die_y + o2, rp);
        draw_pip(die_x + o3, die_y + o3, rp);
    } else if (val == 4) {
        draw_pip(die_x + o1, die_y + o1, rp);
        draw_pip(die_x + o3, die_y + o1, rp);
        draw_pip(die_x + o1, die_y + o3, rp);
        draw_pip(die_x + o3, die_y + o3, rp);
    } else if (val == 5) {
        draw_pip(die_x + o1, die_y + o1, rp);
        draw_pip(die_x + o3, die_y + o1, rp);
        draw_pip(die_x + o2, die_y + o2, rp);
        draw_pip(die_x + o1, die_y + o3, rp);
        draw_pip(die_x + o3, die_y + o3, rp);
    } else if (val == 6) {
        draw_pip(die_x + o1, die_y + o1, rp);
        draw_pip(die_x + o3, die_y + o1, rp);
        draw_pip(die_x + o1, die_y + o2, rp);
        draw_pip(die_x + o3, die_y + o2, rp);
        draw_pip(die_x + o1, die_y + o3, rp);
        draw_pip(die_x + o3, die_y + o3, rp);
    }
}

static void draw_dice_row(uint8_t start_idx, uint8_t count, uint8_t y, uint8_t start_x, uint8_t spacing) {
    for (uint8_t i = 0; i < count; i++) {
        draw_die_face(start_x + i * (25 + spacing), y, dice_values[start_idx + i], 1);
    }
}

static void randomize_values(void) {
    for (uint8_t i = 0; i < dice_count; i++) {
        dice_values[i] = feb_rand(6) + 1;
    }
}

static void render(void) {
    feb_clear_screen();
    feb_set_draw_mode(FEB_DRAW_MODE_SET);

    /* 1. Right Control Panel */
    feb_draw_string(114, 10, "^", FEB_FONT_6X10);
    feb_draw_number(114, 26, dice_count, FEB_FONT_6X10);
    feb_draw_string(114, 46, "v", FEB_FONT_6X10);

    /* 2. Dice Area (x: 0..105) */
    if (dice_count == 1) {
        draw_die_face(28, 7, dice_values[0], 2);
    } else if (dice_count == 2) {
        draw_dice_row(0, 2, 19, 22, 12);
    } else if (dice_count == 3) {
        draw_dice_row(0, 3, 19, 9, 6);
    } else if (dice_count == 4) {
        draw_dice_row(0, 2, 4, 22, 12);
        draw_dice_row(2, 2, 35, 22, 12);
    } else if (dice_count == 5) {
        draw_dice_row(0, 3, 4, 9, 6);
        draw_dice_row(3, 2, 35, 22, 12);
    } else if (dice_count == 6) {
        draw_dice_row(0, 3, 4, 9, 6);
        draw_dice_row(3, 3, 35, 9, 6);
    }
}

int main(void) {
    feb_set_high_res(true);

    dice_count = 1;
    randomize_values();
    state = STATE_IDLE;
    roll_frames = 0;

    uint8_t prev_buttons = 0;

    while (1) {
        uint8_t buttons = feb_get_keys();
        uint8_t just_pressed = buttons & ~prev_buttons;
        prev_buttons = buttons;

        if (state == STATE_ROLLING) {
            randomize_values();
            roll_frames++;
            if (roll_frames >= 40) {
                state = STATE_IDLE;
                roll_frames = 0;
            }
        } else {
            if (just_pressed & FEB_BTN_OK) {
                state = STATE_ROLLING;
                roll_frames = 0;
            } else if (just_pressed & FEB_BTN_UP) {
                if (dice_count < 6) {
                    dice_count++;
                } else {
                    dice_count = 1;
                }
                randomize_values();
            } else if (just_pressed & FEB_BTN_DOWN) {
                if (dice_count > 1) {
                    dice_count--;
                } else {
                    dice_count = 6;
                }
                randomize_values();
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
