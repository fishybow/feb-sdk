/**
 * @file main.c
 * @brief Flashlight App for Flashiibo Pro Gen2 & Gen3 FEB Runner (.feb)
 *
 * Replicates the firmware Flashlight applet (applets_flashlight_view.c):
 *   - Solid white illuminated display (128x64 OLED)
 *   - Any key press (OK, BACK, UP, DOWN) exits back to FEB Runner menu
 *   - Compatible with both 3-button (Gen2) and 4-button (Gen3) devices
 *   - Standard UP+DOWN exit chord supported
 */

#include "../../../include/feb.h"

int main(void) {
    feb_set_high_res(true);
    feb_set_draw_mode(FEB_DRAW_MODE_SET);
    feb_fill_rect(0, 0, FEB_SCREEN_WIDTH, FEB_SCREEN_HEIGHT);

    while (1) {
        uint8_t key = feb_wait_key();
        if (key != 0) {
            feb_exit();
        }
    }

    return 0;
}
