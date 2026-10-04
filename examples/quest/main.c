/**
 * @file main.c
 * @brief Tiny Quest: Relic of the Dragon Lair
 *
 * A retro top-down action RPG for the Flashiibo Executable Binary (.feb) runtime.
 * Inspired by classic 8-bit adventure games.
 *
 * 4-Button Hardware Controls (Flashiibo Pro Gen3):
 *   - UP    (Key 2): Move North
 *   - DOWN  (Key 8): Move South
 *   - BACK  (Key 4): Move West
 *   - OK    (Key 6): Move East
 *   - UP + DOWN + BACK (Held together): Hardware emergency exit to main menu
 *   - Programmatic exit via feb_exit() / feb_quit()
 *
 * Bump Combat & Interactions:
 *   - Bump into enemies with sword to attack and knock them back
 *   - Bumping enemies without a sword causes the Hero to take damage
 *   - Visit Hermit Sage in the cave to receive the Iron Sword
 *   - Defeat Forest Slime to collect Gems (+5)
 *   - Defeat Ruins Goblin to obtain the Dungeon Key
 *   - Unlock the Dungeon Gate with the Key
 *   - Defeat the Dragon Boss (4 HP) in the Lair to claim the Sacred Relic!
 *   - Sidecar save persistence: Gems are saved to /feb/saves/quest.sav
 */

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#include "../../include/feb.h"

#define SCREEN_W 128
#define SCREEN_H 64

#define DIR_DOWN  0
#define DIR_UP    1
#define DIR_RIGHT 2
#define DIR_LEFT  3

#define ROOM_FOREST  0
#define ROOM_CAVE    1
#define ROOM_RUINS   2
#define ROOM_DUNGEON 3

typedef struct {
    uint8_t hero_x;
    uint8_t hero_y;
    uint8_t hero_dir;
    uint8_t hero_hp;
    uint8_t has_sword;
    uint8_t has_key;
    uint8_t gems;
    uint8_t room;
    uint8_t slime_x;
    uint8_t slime_y;
    uint8_t slime_hp;
    uint8_t goblin_x;
    uint8_t goblin_y;
    uint8_t goblin_hp;
    uint8_t boss_x;
    uint8_t boss_y;
    uint8_t boss_hp;
    uint8_t relic_state; // 0=hidden, 1=revealed, 2=recovered
    uint8_t ai_timer;
} GameState;

static GameState g_state;

static void init_game(void) {
    g_state.hero_x = 24;
    g_state.hero_y = 37;
    g_state.hero_dir = DIR_DOWN;
    g_state.hero_hp = 3;
    g_state.has_sword = 0;
    g_state.has_key = 0;
    g_state.gems = 0;
    g_state.room = ROOM_FOREST;

    g_state.slime_x = 80;
    g_state.slime_y = 37;
    g_state.slime_hp = 1;

    g_state.goblin_x = 72;
    g_state.goblin_y = 29;
    g_state.goblin_hp = 2;

    g_state.boss_x = 80;
    g_state.boss_y = 29;
    g_state.boss_hp = 4;
    g_state.relic_state = 0;

    g_state.ai_timer = 0;
}

int main(void) {
    feb_set_hires();
    feb_clear_screen();
    init_game();

    while (1) {
        feb_clear_screen();

        // 1. Draw HUD
        feb_draw_hline(0, 11, SCREEN_W - 1);
        feb_draw_num(96, 2, g_state.gems, FEB_FONT_4X6);

        // 2. Poll buttons (Non-blocking)
        uint8_t keys = feb_read_buttons();

        // Check for manual exit chord: UP (0x01) + DOWN (0x02) + BACK (0x04)
        if ((keys & (FEB_BTN_UP | FEB_BTN_DOWN | FEB_BTN_BACK)) ==
            (FEB_BTN_UP | FEB_BTN_DOWN | FEB_BTN_BACK)) {
            feb_exit();
        }

        // Directional movement
        if (keys & FEB_BTN_UP) {
            g_state.hero_dir = DIR_UP;
            if (g_state.hero_y > 21) g_state.hero_y -= 4;
        } else if (keys & FEB_BTN_DOWN) {
            g_state.hero_dir = DIR_DOWN;
            if (g_state.hero_y < 45) g_state.hero_y += 4;
        } else if (keys & FEB_BTN_BACK) {
            g_state.hero_dir = DIR_LEFT;
            if (g_state.hero_x > 8) g_state.hero_x -= 4;
        } else if (keys & FEB_BTN_OK) {
            g_state.hero_dir = DIR_RIGHT;
            if (g_state.hero_x < 112) g_state.hero_x += 4;
        }

        // Check victory
        if (g_state.relic_state == 2) {
            // Save gems to sidecar save file /feb/saves/quest.sav
            feb_save_flags("/feb/saves/quest.sav", &g_state.gems, 1);
            feb_draw_text(12, 18, "SACRED RELIC RESTORED!", FEB_FONT_5X7);
            feb_draw_text(22, 30, "THE REALM IS SAVED!", FEB_FONT_5X7);
            feb_wait_key();
            init_game();
        }
    }

    return 0;
}
