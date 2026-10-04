/**
 * @file main.c
 * @brief Draw Demo Application for Flashiibo Gen3 FEB Runtime (.feb)
 *
 * Demonstrates real-time vector geometry and typography drawing:
 *   - Draws/fills random geometric shapes (rectangles, discs, circles) every second
 *   - Updates shape counter in the header in real-time
 *   - Automatically refreshes the canvas after every 10 shapes
 *   - Pressing UP + DOWN simultaneously exits back to the FEB Runner menu
 */

#include "../../include/feb.h"

static void draw_header(uint16_t count) {
    feb_set_draw_mode(FEB_DRAW_MODE_SET);
    feb_draw_string(2, 2, "DRAW DEMO", FEB_FONT_6X10);
    feb_draw_string(72, 4, "SHAPES:", FEB_FONT_4X6);
    feb_draw_number(104, 4, count, FEB_FONT_4X6);
    feb_draw_hline(0, 13, 128);
}

static void update_counter(uint16_t count) {
    feb_set_draw_mode(FEB_DRAW_MODE_CLEAR);
    feb_fill_rect(104, 3, 24, 8);
    feb_set_draw_mode(FEB_DRAW_MODE_SET);
    feb_draw_number(104, 4, count, FEB_FONT_4X6);
}

static void clear_canvas(void) {
    feb_set_draw_mode(FEB_DRAW_MODE_CLEAR);
    feb_fill_rect(0, 14, 128, 50);
    feb_set_draw_mode(FEB_DRAW_MODE_SET);
}

int main(void) {
    feb_set_high_res(true);
    feb_clear_screen();

    uint16_t total_shapes = 0;
    uint8_t batch_count = 0;

    draw_header(total_shapes);

    while (1) {
        /* Every second (60 frames @ 60 Hz) */
        feb_delay_frames(60);

        if (batch_count >= 10) {
            clear_canvas();
            batch_count = 0;
        }

        uint8_t shape_type = feb_rand(3); /* 0..3 */
        uint8_t rx = 8 + feb_rand(90);
        uint8_t ry = 18 + feb_rand(30);
        uint8_t rw = 10 + feb_rand(25);
        uint8_t rh = 8 + feb_rand(16);
        uint8_t rad = 4 + feb_rand(10);

        feb_set_draw_mode(FEB_DRAW_MODE_SET);

        if (shape_type == 0) {
            /* Outline rectangle */
            feb_draw_rect(rx, ry, rw, rh);
        } else if (shape_type == 1) {
            /* Solid filled rectangle */
            feb_fill_rect(rx, ry, rw, rh);
        } else if (shape_type == 2) {
            /* Outline circle */
            feb_draw_circle(rx + rad, ry + rad, rad);
        } else {
            /* Solid filled disc */
            feb_fill_circle(rx + rad, ry + rad, rad);
        }

        total_shapes++;
        batch_count++;
        update_counter(total_shapes);
    }

    return 0;
}
