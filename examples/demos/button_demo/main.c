/**
 * @file main.c
 * @brief Button Demo Application for Flashiibo Gen3 FEB Runtime (.feb)
 *
 * User-friendly demo utility to verify 4-button hardware input:
 *   - Displays active button name (UP, DOWN, BACK, OK) and virtual key code in the center
 *   - Highlights the active button on screen with filled vector geometry
 *   - Displays directional tap counts on each button box
 *   - Pure C using Flashiibo FEB SDK drawing APIs and typography fonts
 *
 * Pressing UP + DOWN simultaneously exits back to the FEB Runner menu.
 */

#include "../../../include/feb.h"

static void draw_btn(uint8_t btn_id, uint8_t count, bool active) {
    if (btn_id == 1) { /* UP */
        if (active) {
            feb_set_draw_mode(FEB_DRAW_MODE_SET);
            feb_fill_rect(48, 16, 32, 12);
            feb_set_draw_mode(FEB_DRAW_MODE_CLEAR);
            feb_draw_string(52, 19, "UP", FEB_FONT_4X6);
            feb_draw_number(70, 19, count, FEB_FONT_4X6);
            feb_set_draw_mode(FEB_DRAW_MODE_SET);
        } else {
            feb_draw_rect(48, 16, 32, 12);
            feb_draw_string(52, 19, "UP", FEB_FONT_4X6);
            feb_draw_number(70, 19, count, FEB_FONT_4X6);
        }
    } else if (btn_id == 2) { /* DOWN */
        if (active) {
            feb_set_draw_mode(FEB_DRAW_MODE_SET);
            feb_fill_rect(48, 50, 32, 12);
            feb_set_draw_mode(FEB_DRAW_MODE_CLEAR);
            feb_draw_string(52, 53, "DN", FEB_FONT_4X6);
            feb_draw_number(70, 53, count, FEB_FONT_4X6);
            feb_set_draw_mode(FEB_DRAW_MODE_SET);
        } else {
            feb_draw_rect(48, 50, 32, 12);
            feb_draw_string(52, 53, "DN", FEB_FONT_4X6);
            feb_draw_number(70, 53, count, FEB_FONT_4X6);
        }
    } else if (btn_id == 3) { /* LEFT / BACK */
        if (active) {
            feb_set_draw_mode(FEB_DRAW_MODE_SET);
            feb_fill_rect(2, 33, 36, 12);
            feb_set_draw_mode(FEB_DRAW_MODE_CLEAR);
            feb_draw_string(5, 36, "BACK", FEB_FONT_4X6);
            feb_draw_number(28, 36, count, FEB_FONT_4X6);
            feb_set_draw_mode(FEB_DRAW_MODE_SET);
        } else {
            feb_draw_rect(2, 33, 36, 12);
            feb_draw_string(5, 36, "BACK", FEB_FONT_4X6);
            feb_draw_number(28, 36, count, FEB_FONT_4X6);
        }
    } else if (btn_id == 4) { /* RIGHT / OK */
        if (active) {
            feb_set_draw_mode(FEB_DRAW_MODE_SET);
            feb_fill_rect(90, 33, 36, 12);
            feb_set_draw_mode(FEB_DRAW_MODE_CLEAR);
            feb_draw_string(94, 36, "OK", FEB_FONT_4X6);
            feb_draw_number(114, 36, count, FEB_FONT_4X6);
            feb_set_draw_mode(FEB_DRAW_MODE_SET);
        } else {
            feb_draw_rect(90, 33, 36, 12);
            feb_draw_string(94, 36, "OK", FEB_FONT_4X6);
            feb_draw_number(114, 36, count, FEB_FONT_4X6);
        }
    }
}

static void render_screen(uint8_t last_key, uint8_t up_count, uint8_t down_count, uint8_t left_count, uint8_t right_count, uint8_t total) {
    feb_clear_screen();
    feb_set_draw_mode(FEB_DRAW_MODE_SET);

    /* Header */
    feb_draw_string(28, 2, "BUTTON DEMO", FEB_FONT_6X10);
    feb_draw_hline(0, 13, 128);

    /* 4 Directional Buttons */
    draw_btn(1, up_count, last_key == FEB_KEY_UP);
    draw_btn(2, down_count, last_key == FEB_KEY_DOWN);
    draw_btn(3, left_count, last_key == FEB_KEY_LEFT);
    draw_btn(4, right_count, last_key == FEB_KEY_RIGHT);

    /* Center Callout Box */
    feb_draw_rect(42, 31, 44, 16);
    if (last_key == FEB_KEY_UP) {
        feb_draw_string(56, 33, "UP", FEB_FONT_6X10);
        feb_draw_string(54, 41, "0x2", FEB_FONT_4X6);
    } else if (last_key == FEB_KEY_DOWN) {
        feb_draw_string(50, 33, "DOWN", FEB_FONT_6X10);
        feb_draw_string(54, 41, "0x8", FEB_FONT_4X6);
    } else if (last_key == FEB_KEY_LEFT) {
        feb_draw_string(50, 33, "BACK", FEB_FONT_6X10);
        feb_draw_string(54, 41, "0x4", FEB_FONT_4X6);
    } else if (last_key == FEB_KEY_RIGHT) {
        feb_draw_string(56, 33, "OK", FEB_FONT_6X10);
        feb_draw_string(54, 41, "0x6", FEB_FONT_4X6);
    } else {
        feb_draw_string(48, 33, "READY", FEB_FONT_6X10);
        feb_draw_string(45, 41, "PRESS KEY", FEB_FONT_4X6);
    }

    /* Footer: Exit Hint and Total Count */
    feb_draw_string(2, 50, "EXIT:", FEB_FONT_4X6);
    feb_draw_string(2, 57, "UP+DN", FEB_FONT_4X6);

    feb_draw_string(92, 50, "TOTAL:", FEB_FONT_4X6);
    feb_draw_number(116, 50, total, FEB_FONT_4X6);
}

int main(void) {
    uint8_t total_presses = 0;
    uint8_t last_key = 0;
    uint8_t up_count = 0;
    uint8_t down_count = 0;
    uint8_t left_count = 0;
    uint8_t right_count = 0;

    feb_set_high_res(true);
    feb_set_draw_mode(FEB_DRAW_MODE_SET);

    render_screen(last_key, up_count, down_count, left_count, right_count, total_presses);

    while (1) {
        uint8_t key = feb_wait_key();
        total_presses++;
        last_key = key;

        if (key == FEB_KEY_UP) {
            up_count++;
        } else if (key == FEB_KEY_DOWN) {
            down_count++;
        } else if (key == FEB_KEY_LEFT) {
            left_count++;
        } else if (key == FEB_KEY_RIGHT) {
            right_count++;
        }

        render_screen(last_key, up_count, down_count, left_count, right_count, total_presses);
    }

    return 0;
}
