/**
 * @file main.c
 * @brief Flashiibo FEB Custom Extensions Showcase & Feature Demo
 *
 * Demonstrates the powerful custom VM capabilities added to Flashiibo FEB:
 *   1. Hardware 60 Hz VSync (FX9A / feb_wait_vsync) for tear-free 60 FPS animation.
 *   2. Instantaneous 4-button polling (FXB0 / feb_get_keys) for zero-latency D-Pad controls.
 *   3. Zero-RAM Collision Detection (FX99 / feb_test_pixel) against on-screen shapes.
 *   4. Fast Geometric Primitives:
 *        - Outline & Filled Rectangles (FX94 / FX95: feb_draw_rect, feb_fill_rect)
 *        - Outline & Filled Circles (FX96 / FX97: feb_draw_circle, feb_fill_circle)
 *   5. Built-in Typography & Number Formatting:
 *        - String rendering in standard & compact fonts (FXA0: feb_draw_string)
 *        - Real-time 16-bit integer formatting (FXA3: feb_draw_number)
 *
 * Controls:
 *   - UP:    Move cursor UP
 *   - DOWN:  Move cursor DOWN
 *   - BACK:  Move cursor LEFT
 *   - OK:    Move cursor RIGHT
 *   - UP + DOWN + BACK: Exit to FEB Runner menu
 */

#include "../../include/feb.h"

int main(void) {
    uint8_t cursor_x = 60;
    uint8_t cursor_y = 30;
    uint16_t frame_count = 0;

    feb_set_high_res(true);

    while (1) {
        /* Wait for 60 Hz hardware vertical sync tick */
        feb_wait_vsync();
        feb_clear_screen();

        /* 1. Header Banner & Typography */
        feb_draw_rect(0, 0, 127, 12);
        feb_draw_string(4, 2, "FLASHIIBO", FEB_FONT_6X10);
        feb_draw_number(95, 2, frame_count++, FEB_FONT_6X10);

        /* 2. Geometric Primitives */
        feb_fill_rect(10, 20, 20, 16);     /* Solid rectangle */
        feb_draw_circle(64, 30, 12);        /* Outline circle */
        feb_fill_circle(100, 30, 8);        /* Solid disc */

        /* 3. Zero-RAM Collision Detection:
         * Tests whether pixel at cursor position is occupied by any shape.
         */
        bool hit = feb_test_pixel(cursor_x, cursor_y);

        /* Draw 5x5 cursor outline box */
        feb_draw_rect(cursor_x, cursor_y, 5, 5);

        /* Status feedback */
        if (hit) {
            feb_draw_string(20, 52, "COLLISION!", FEB_FONT_4X6);
        } else {
            feb_draw_string(30, 52, "USE D-PAD TO MOVE", FEB_FONT_4X6);
        }

        /* 4. Instantaneous 4-Button Input Polling */
        uint8_t keys = feb_get_keys();
        if (keys & FEB_BTN_UP)    cursor_y--;
        if (keys & FEB_BTN_DOWN)  cursor_y++;
        if (keys & FEB_BTN_LEFT)  cursor_x--;
        if (keys & FEB_BTN_RIGHT) cursor_x++;

        /* Boundary clamping */
        if (cursor_x < 2)   cursor_x = 2;
        if (cursor_x > 125) cursor_x = 125;
        if (cursor_y < 14)  cursor_y = 14;
        if (cursor_y > 60)  cursor_y = 60;
    }

    return 0;
}
