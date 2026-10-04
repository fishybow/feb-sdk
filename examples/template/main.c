/**
 * @file main.c
 * @brief Starter Template Game for Flashiibo Gen3 FEB Runtime (Beta / Experimental)
 *
 * Demonstrates basic 4-button directional controls, XOR sprite rendering,
 * and screen boundaries on Flashiibo's 128x64 monochrome OLED display.
 *
 * Controls:
 *   - UP:      Move Up (FEB_KEY_UP = 0x2)
 *   - DOWN:    Move Down (FEB_KEY_DOWN = 0x8)
 *   - BACK:    Move Left (FEB_KEY_LEFT = 0x4)
 *   - OK:      Move Right (FEB_KEY_RIGHT = 0x6)
 *
 * Pressing UP and DOWN simultaneously exits immediately back to the device menu.
 */

#include "../../include/feb.h"

#define SPRITE_SIZE 8
#define MIN_X 0
#define MAX_X (FEB_SCREEN_WIDTH - SPRITE_SIZE)
#define MIN_Y 0
#define MAX_Y (FEB_SCREEN_HEIGHT - SPRITE_SIZE)

/* 8x8 player icon sprite */
static const uint8_t player_sprite[SPRITE_SIZE] = {
    0x3C, /* ..XXXX.. */
    0x7E, /* .XXXXXX. */
    0xDB, /* XX.XX.XX */
    0xFF, /* XXXXXXXX */
    0xFF, /* XXXXXXXX */
    0xDB, /* XX.XX.XX */
    0x7E, /* .XXXXXX. */
    0x3C  /* ..XXXX.. */
};

int main(void) {
    uint8_t x = 60;
    uint8_t y = 28;

    feb_set_high_res(true);
    feb_clear_screen();
    feb_draw_sprite(x, y, player_sprite, SPRITE_SIZE);

    while (1) {
        uint8_t key = feb_wait_key();

        /* Erase previous sprite via XOR */
        feb_draw_sprite(x, y, player_sprite, SPRITE_SIZE);

        /* Handle 4-button directional movement */
        switch (key) {
            case FEB_KEY_UP:
                if (y >= 2) y -= 2;
                break;
            case FEB_KEY_DOWN:
                if (y + 2 <= MAX_Y) y += 2;
                break;
            case FEB_KEY_LEFT:
                if (x >= 2) x -= 2;
                break;
            case FEB_KEY_RIGHT:
                if (x + 2 <= MAX_X) x += 2;
                break;
            default:
                break;
        }

        /* Draw sprite at updated coordinates */
        feb_draw_sprite(x, y, player_sprite, SPRITE_SIZE);
    }

    return 0;
}
