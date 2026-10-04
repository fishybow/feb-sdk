/**
 * @file main.c
 * @brief Button Test Application for Flashiibo Gen3 FEB Runtime (.feb)
 *
 * Simple test utility to verify 4-button hardware input without double-pressing.
 * Displays:
 *   - Total button press count
 *   - Last pressed key code (UP=2, DOWN=8, LEFT=4, RIGHT=6)
 *   - Individual button press counts (UP, DOWN, LEFT, RIGHT)
 *
 * Each physical button tap must increment the press count by exactly 1.
 * Pressing UP + DOWN simultaneously exits back to the FEB Runner menu.
 */

#include "../../include/feb.h"

int main(void) {
    uint8_t total_presses = 0;
    uint8_t last_key = 0;
    uint8_t up_count = 0;
    uint8_t down_count = 0;
    uint8_t left_count = 0;
    uint8_t right_count = 0;

    feb_set_high_res(true);
    feb_clear_screen();

    while (1) {
        /* Draw current button test state:
         * Top: UP count (x=60, y=10)
         * Left: LEFT count (x=24, y=28)
         * Center: Last key (x=56, y=28), Total presses (x=68, y=28)
         * Right: RIGHT count (x=100, y=28)
         * Bottom: DOWN count (x=60, y=46)
         */
        feb_draw_digit(60, 10, up_count & 0x0F);
        feb_draw_digit(24, 28, left_count & 0x0F);
        feb_draw_digit(56, 28, last_key & 0x0F);
        feb_draw_digit(68, 28, total_presses & 0x0F);
        feb_draw_digit(100, 28, right_count & 0x0F);
        feb_draw_digit(60, 46, down_count & 0x0F);

        uint8_t key = feb_wait_key();

        /* XOR erase previous digits before updating */
        feb_draw_digit(60, 10, up_count & 0x0F);
        feb_draw_digit(24, 28, left_count & 0x0F);
        feb_draw_digit(56, 28, last_key & 0x0F);
        feb_draw_digit(68, 28, total_presses & 0x0F);
        feb_draw_digit(100, 28, right_count & 0x0F);
        feb_draw_digit(60, 46, down_count & 0x0F);

        total_presses++;
        last_key = key;

        switch (key) {
            case FEB_KEY_UP:
                up_count++;
                break;
            case FEB_KEY_DOWN:
                down_count++;
                break;
            case FEB_KEY_LEFT:
                left_count++;
                break;
            case FEB_KEY_RIGHT:
                right_count++;
                break;
            default:
                break;
        }
    }

    return 0;
}
