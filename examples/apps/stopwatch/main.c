/**
 * @file main.c
 * @brief Precision Digital Stopwatch for Flashiibo Pro Gen2 & Gen3 FEB Runner (.feb)
 *
 * Replicates the firmware Stopwatch applet (applets_stopwatch_view.c):
 *   - Accurate 60 Hz timekeeping using virtual machine frame clock
 *   - Main digital readout: MM:SS.hs (hundredths of a second)
 *   - LAP snapshot support: Records split time at top of screen
 *   - PAUSED indicator when stopped with elapsed time
 *   - Controls:
 *       OK: Start / Pause
 *       UP: Lap snapshot
 *       DOWN: Reset time
 *       BACK: Exit application
 *       UP+DOWN: Hardware exit chord
 *   - Compatible with both 3-button (Gen2) and 4-button (Gen3) devices
 */

#include "../../../include/feb.h"

static uint8_t frames;
static uint8_t secs;
static uint8_t mins;
static uint8_t running;

static uint8_t lap_frames;
static uint8_t lap_secs;
static uint8_t lap_mins;
static uint8_t has_lap;

static void draw_2digits(uint8_t x, uint8_t y, uint8_t val, uint8_t font) {
    if (val < 10) {
        feb_draw_char(x, y, '0', font);
        feb_draw_number(x + 6, y, val, font);
    } else {
        feb_draw_number(x, y, val, font);
    }
}

static void render(void) {
    feb_clear_screen();
    feb_set_draw_mode(FEB_DRAW_MODE_SET);

    /* 1. Top Area: LAP Snapshot */
    if (has_lap) {
        feb_draw_string(25, 8, "LAP: ", FEB_FONT_6X10);
        draw_2digits(55, 8, lap_mins, FEB_FONT_6X10);
        feb_draw_char(67, 8, ':', FEB_FONT_6X10);
        draw_2digits(73, 8, lap_secs, FEB_FONT_6X10);
        feb_draw_char(85, 8, '.', FEB_FONT_6X10);
        uint8_t lap_hs = lap_frames + ((lap_frames << 1) / 3);
        draw_2digits(91, 8, lap_hs, FEB_FONT_6X10);
    }

    /* 2. Center Area: Main Elapsed Time (MM:SS.hs) */
    draw_2digits(40, 26, mins, FEB_FONT_6X10);
    feb_draw_char(52, 26, ':', FEB_FONT_6X10);
    draw_2digits(58, 26, secs, FEB_FONT_6X10);
    feb_draw_char(70, 26, '.', FEB_FONT_6X10);
    uint8_t hs = frames + ((frames << 1) / 3);
    draw_2digits(76, 26, hs, FEB_FONT_6X10);

    /* 3. Status Area: PAUSED */
    if (!running && (mins > 0 || secs > 0 || frames > 0)) {
        feb_draw_string(46, 42, "PAUSED", FEB_FONT_6X10);
    }

    /* 4. Bottom Area: Button Hints (UP triangle for LAP, DOWN triangle for RESET) */
    feb_draw_triangle(8, 57, 4, 61, 12, 61);
    feb_draw_string(16, 56, "LAP", FEB_FONT_4X6);
    feb_draw_string(93, 56, "RESET", FEB_FONT_4X6);
    feb_draw_triangle(115, 57, 123, 57, 119, 61);
}

int main(void) {
    feb_set_high_res(true);

    frames = 0;
    secs = 0;
    mins = 0;
    running = 0;
    has_lap = 0;

    uint8_t prev_buttons = 0;

    while (1) {
        uint8_t buttons = feb_get_keys();
        uint8_t just_pressed = buttons & ~prev_buttons;
        prev_buttons = buttons;

        if (just_pressed & FEB_BTN_OK) {
            running = !running;
        }

        if (just_pressed & FEB_BTN_UP) {
            lap_frames = frames;
            lap_secs = secs;
            lap_mins = mins;
            has_lap = 1;
        }

        if (just_pressed & FEB_BTN_DOWN) {
            frames = 0;
            secs = 0;
            mins = 0;
            if (!running) {
                has_lap = 0;
            }
        }

        if (just_pressed & FEB_BTN_BACK) {
            feb_exit();
        }

        if (running) {
            frames++;
            if (frames >= 60) {
                frames = 0;
                secs++;
                if (secs >= 60) {
                    secs = 0;
                    mins++;
                    if (mins >= 100) {
                        mins = 0;
                    }
                }
            }
        }

        render();
        feb_delay_frames(1);
    }

    return 0;
}
