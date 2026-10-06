/**
 * @file main.c
 * @brief SOS Emergency Beacon App for Flashiibo Pro Gen2 & Gen3 FEB Runner (.feb)
 *
 * Replicates the firmware SOS applet (applets_sos_view.c):
 *   - International Morse Code SOS light sequence (... --- ...)
 *   - S: 3 short flashes (200 ms on, 200 ms off)
 *   - Inter-letter pause (600 ms off)
 *   - O: 3 long flashes (600 ms on, 200 ms off)
 *   - Inter-letter pause (600 ms off)
 *   - S: 3 short flashes (200 ms on, 200 ms off)
 *   - Repeat interval (1400 ms off)
 *   - Any button press (OK, BACK, UP, DOWN) exits back to FEB Runner menu
 *   - Compatible with both 3-button (Gen2) and 4-button (Gen3) devices
 *   - Standard UP+DOWN exit chord supported
 */

#include "../../../include/feb.h"

#define SOS_STEPS 18

static const uint8_t STEP_ON[SOS_STEPS] = {
    1, 0, 1, 0, 1, 0,
    1, 0, 1, 0, 1, 0,
    1, 0, 1, 0, 1, 0
};

static const uint8_t STEP_FRAMES[SOS_STEPS] = {
    12, 12, 12, 12, 12, 36,
    36, 12, 36, 12, 36, 36,
    12, 12, 12, 12, 12, 84
};

int main(void) {
    feb_set_high_res(true);

    while (1) {
        for (uint8_t i = 0; i < SOS_STEPS; i++) {
            if (STEP_ON[i]) {
                feb_set_draw_mode(FEB_DRAW_MODE_SET);
                feb_fill_rect(0, 0, FEB_SCREEN_WIDTH, FEB_SCREEN_HEIGHT);
            } else {
                feb_clear_screen();
            }

            uint8_t count = STEP_FRAMES[i];
            for (uint8_t f = 0; f < count; f++) {
                uint8_t keys = feb_get_keys();
                if (keys != 0) {
                    feb_exit();
                }
                feb_delay_frames(1);
            }
        }
    }

    return 0;
}
