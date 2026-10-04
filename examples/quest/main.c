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

/* -------------------------------------------------------------------------
 * 8x8 & 16x16 Game Sprite Bitmaps
 * ------------------------------------------------------------------------- */

static const uint8_t SPRITE_HERO_DOWN[8] = {
    0x3C, 0x7E, 0x5A, 0x7E, 0x7E, 0x3C, 0x24, 0x24
};

static const uint8_t SPRITE_HERO_UP[8] = {
    0x3C, 0x7E, 0x7E, 0x7E, 0x3C, 0x3C, 0x24, 0x24
};

static const uint8_t SPRITE_HERO_RIGHT[8] = {
    0x3C, 0x3E, 0x36, 0x3D, 0x3F, 0x3C, 0x28, 0x28
};

static const uint8_t SPRITE_HERO_LEFT[8] = {
    0x3C, 0x7C, 0x6C, 0xBC, 0xFC, 0x3C, 0x14, 0x14
};

static const uint8_t SPRITE_TREE[8] = {
    0x3C, 0x7E, 0xDB, 0xFF, 0xFF, 0x7E, 0x18, 0x18
};

static const uint8_t SPRITE_WALL[8] = {
    0x7E, 0x81, 0xBD, 0xA5, 0xA5, 0xBD, 0x81, 0x7E
};

static const uint8_t SPRITE_CAVE[8] = {
    0xFF, 0x81, 0x81, 0x81, 0x81, 0x81, 0x81, 0xFF
};

static const uint8_t SPRITE_DOOR[8] = {
    0xFF, 0xBD, 0xBD, 0x99, 0x99, 0xBD, 0xBD, 0xFF
};

static const uint8_t SPRITE_SAGE[8] = {
    0x3C, 0x7E, 0x5A, 0x7E, 0x3C, 0x7E, 0x7E, 0x3C
};

static const uint8_t SPRITE_TORCH[8] = {
    0x10, 0x30, 0x78, 0x7C, 0x78, 0x30, 0x30, 0x78
};

static const uint8_t SPRITE_SWORD[8] = {
    0x02, 0x06, 0x0C, 0x18, 0x70, 0xC0, 0x40, 0x00
};

static const uint8_t SPRITE_RELIC[8] = {
    0x7E, 0x42, 0x3C, 0x18, 0x18, 0x3C, 0x7E, 0x00
};

static const uint8_t SPRITE_HEART[8] = {
    0x6C, 0xFE, 0xFE, 0xFE, 0x7C, 0x38, 0x10, 0x00
};

static const uint8_t SPRITE_GEM[8] = {
    0x10, 0x38, 0x7C, 0xFE, 0xFE, 0x7C, 0x38, 0x10
};

static const uint8_t SPRITE_KEY[8] = {
    0x38, 0x44, 0x38, 0x10, 0x18, 0x10, 0x18, 0x00
};

static const uint8_t SPRITE_SLIME[8] = {
    0x00, 0x3C, 0x7E, 0xDB, 0xFF, 0xFF, 0x7E, 0x00
};

static const uint8_t SPRITE_GOBLIN[8] = {
    0x66, 0x7E, 0xDB, 0xFF, 0x7E, 0x3C, 0x42, 0xC3
};

static const uint8_t SPRITE_BOSS[32] = {
    0x03, 0xC0, 0x07, 0xE0, 0x0E, 0x70, 0x1C, 0x38,
    0x39, 0x9C, 0x73, 0xCE, 0x7F, 0xFE, 0x7E, 0x7E,
    0x7C, 0x3E, 0x78, 0x1E, 0x7F, 0xFE, 0x3F, 0xFC,
    0x1F, 0xF8, 0x0E, 0x70, 0x1C, 0x38, 0x38, 0x1C
};

/* -------------------------------------------------------------------------
 * Game State Structure
 * ------------------------------------------------------------------------- */

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

/* -------------------------------------------------------------------------
 * Title Screen
 * ------------------------------------------------------------------------- */

static void show_title_screen(void) {
    feb_clear_screen();
    feb_draw_rect(0, 0, 127, 63);
    feb_draw_string(18, 8, "TINY QUEST", FEB_FONT_6X10);
    feb_draw_string(24, 20, "RELIC OF DRAGON LAIR", FEB_FONT_4X6);
    feb_draw_sprite(60, 28, SPRITE_RELIC, 8);
    feb_draw_string(12, 44, "UP/DOWN/BACK/OK TO MOVE", FEB_FONT_4X6);
    feb_draw_string(20, 52, "PRESS ANY KEY TO START", FEB_FONT_4X6);
    feb_wait_key();
}

/* -------------------------------------------------------------------------
 * Rendering Functions
 * ------------------------------------------------------------------------- */

static void draw_hud(void) {
    feb_draw_hline(0, 11, 127);

    // Draw Hearts for HP
    if (g_state.hero_hp >= 1) feb_draw_sprite(2, 2, SPRITE_HEART, 8);
    if (g_state.hero_hp >= 2) feb_draw_sprite(12, 2, SPRITE_HEART, 8);
    if (g_state.hero_hp >= 3) feb_draw_sprite(22, 2, SPRITE_HEART, 8);

    // Equipment Icons
    if (g_state.has_sword) feb_draw_sprite(40, 2, SPRITE_SWORD, 8);
    if (g_state.has_key) feb_draw_sprite(52, 2, SPRITE_KEY, 8);

    // Gems counter
    feb_draw_sprite(84, 2, SPRITE_GEM, 8);
    feb_draw_digit(96, 2, g_state.gems);
}

static void draw_room(void) {
    if (g_state.room == ROOM_FOREST) {
        // Overworld Forest: Trees along top and bottom
        feb_draw_sprite(0, 13, SPRITE_TREE, 8);
        feb_draw_sprite(16, 13, SPRITE_TREE, 8);
        feb_draw_sprite(32, 13, SPRITE_TREE, 8);
        feb_draw_sprite(48, 13, SPRITE_TREE, 8);
        feb_draw_sprite(64, 13, SPRITE_TREE, 8);
        feb_draw_sprite(80, 13, SPRITE_TREE, 8);
        feb_draw_sprite(96, 13, SPRITE_TREE, 8);
        feb_draw_sprite(112, 13, SPRITE_TREE, 8);

        // Bottom row trees
        feb_draw_sprite(0, 53, SPRITE_TREE, 8);
        feb_draw_sprite(16, 53, SPRITE_TREE, 8);
        feb_draw_sprite(32, 53, SPRITE_TREE, 8);
        feb_draw_sprite(48, 53, SPRITE_TREE, 8);
        feb_draw_sprite(64, 53, SPRITE_TREE, 8);
        feb_draw_sprite(80, 53, SPRITE_TREE, 8);
        feb_draw_sprite(96, 53, SPRITE_TREE, 8);
        feb_draw_sprite(112, 53, SPRITE_TREE, 8);

        // Cave Entrance at (56, 13)
        feb_draw_sprite(56, 13, SPRITE_CAVE, 8);
    } else if (g_state.room == ROOM_CAVE) {
        // Cave Walls & Torches
        feb_draw_sprite(0, 13, SPRITE_WALL, 8);
        feb_draw_sprite(120, 13, SPRITE_WALL, 8);
        feb_draw_sprite(32, 21, SPRITE_TORCH, 8);
        feb_draw_sprite(80, 21, SPRITE_TORCH, 8);

        // Hermit Sage at (56, 21)
        feb_draw_sprite(56, 21, SPRITE_SAGE, 8);

        // Sword item pickup altar
        if (!g_state.has_sword) {
            feb_draw_sprite(56, 29, SPRITE_SWORD, 8);
        }

        // Sage dialogue
        feb_draw_string(14, 37, "TAKE THIS SWORD, WARRIOR!", FEB_FONT_4X6);
        feb_draw_string(24, 45, "THE REALM DEPENDS ON THEE!", FEB_FONT_4X6);
    } else if (g_state.room == ROOM_RUINS) {
        // Ruins: Ancient Columns and Dungeon Gate
        feb_draw_sprite(0, 13, SPRITE_WALL, 8);
        feb_draw_sprite(32, 13, SPRITE_WALL, 8);
        feb_draw_sprite(64, 13, SPRITE_WALL, 8);
        feb_draw_sprite(96, 13, SPRITE_WALL, 8);
        feb_draw_sprite(120, 13, SPRITE_WALL, 8);

        // Dungeon Door at (64, 53)
        feb_draw_sprite(64, 53, SPRITE_DOOR, 8);
    } else if (g_state.room == ROOM_DUNGEON) {
        // Boss Lair: Perimeter Walls
        feb_draw_sprite(0, 13, SPRITE_WALL, 8);
        feb_draw_sprite(120, 13, SPRITE_WALL, 8);
        feb_draw_sprite(0, 53, SPRITE_WALL, 8);
        feb_draw_sprite(120, 53, SPRITE_WALL, 8);
        feb_draw_sprite(24, 21, SPRITE_TORCH, 8);
        feb_draw_sprite(104, 21, SPRITE_TORCH, 8);

        // Sacred Relic drops when Boss is defeated
        if (g_state.relic_state == 1) {
            feb_draw_sprite(56, 29, SPRITE_RELIC, 8);
        }
    }
}

static void draw_enemies(void) {
    if (g_state.room == ROOM_FOREST && g_state.slime_hp > 0) {
        feb_draw_sprite(g_state.slime_x, g_state.slime_y, SPRITE_SLIME, 8);
    } else if (g_state.room == ROOM_RUINS && g_state.goblin_hp > 0) {
        feb_draw_sprite(g_state.goblin_x, g_state.goblin_y, SPRITE_GOBLIN, 8);
    } else if (g_state.room == ROOM_DUNGEON && g_state.boss_hp > 0) {
        feb_draw_sprite16(g_state.boss_x, g_state.boss_y, SPRITE_BOSS);
    }
}

static void draw_hero(void) {
    if (g_state.hero_dir == DIR_DOWN) {
        feb_draw_sprite(g_state.hero_x, g_state.hero_y, SPRITE_HERO_DOWN, 8);
    } else if (g_state.hero_dir == DIR_UP) {
        feb_draw_sprite(g_state.hero_x, g_state.hero_y, SPRITE_HERO_UP, 8);
    } else if (g_state.hero_dir == DIR_LEFT) {
        feb_draw_sprite(g_state.hero_x, g_state.hero_y, SPRITE_HERO_LEFT, 8);
    } else {
        feb_draw_sprite(g_state.hero_x, g_state.hero_y, SPRITE_HERO_RIGHT, 8);
    }
}

/* -------------------------------------------------------------------------
 * Bump Combat & Collision Logic
 * ------------------------------------------------------------------------- */

static void check_bump_collision(void) {
    // 1. Cave Sword Pickup
    if (g_state.room == ROOM_CAVE && !g_state.has_sword) {
        if (g_state.hero_x >= 52 && g_state.hero_x <= 60 &&
            g_state.hero_y >= 25 && g_state.hero_y <= 33) {
            g_state.has_sword = 1;
        }
    }

    // 2. Forest Slime Combat
    if (g_state.room == ROOM_FOREST && g_state.slime_hp > 0) {
        if (g_state.hero_x >= g_state.slime_x - 6 && g_state.hero_x <= g_state.slime_x + 6 &&
            g_state.hero_y >= g_state.slime_y - 6 && g_state.hero_y <= g_state.slime_y + 6) {
            if (g_state.has_sword) {
                g_state.slime_hp = 0;
                g_state.gems += 5;
            } else {
                if (g_state.hero_hp > 0) g_state.hero_hp--;
            }
        }
    }

    // 3. Ruins Goblin Combat
    if (g_state.room == ROOM_RUINS && g_state.goblin_hp > 0) {
        if (g_state.hero_x >= g_state.goblin_x - 6 && g_state.hero_x <= g_state.goblin_x + 6 &&
            g_state.hero_y >= g_state.goblin_y - 6 && g_state.hero_y <= g_state.goblin_y + 6) {
            if (g_state.has_sword) {
                g_state.goblin_hp--;
                if (g_state.goblin_hp == 0) {
                    g_state.has_key = 1;
                }
            } else {
                if (g_state.hero_hp > 0) g_state.hero_hp--;
            }
        }
    }

    // 4. Dungeon Boss Combat
    if (g_state.room == ROOM_DUNGEON && g_state.boss_hp > 0) {
        if (g_state.hero_x >= g_state.boss_x - 6 && g_state.hero_x <= g_state.boss_x + 14 &&
            g_state.hero_y >= g_state.boss_y - 6 && g_state.hero_y <= g_state.boss_y + 14) {
            if (g_state.has_sword) {
                g_state.boss_hp--;
                if (g_state.boss_hp == 0) {
                    g_state.relic_state = 1; // Relic revealed!
                }
            } else {
                if (g_state.hero_hp > 0) g_state.hero_hp--;
            }
        }
    }

    // 5. Sacred Relic Pickup
    if (g_state.room == ROOM_DUNGEON && g_state.relic_state == 1) {
        if (g_state.hero_x >= 52 && g_state.hero_x <= 60 &&
            g_state.hero_y >= 25 && g_state.hero_y <= 33) {
            g_state.relic_state = 2; // Victory!
        }
    }
}

static void update_ai(void) {
    g_state.ai_timer++;
    if ((g_state.ai_timer & 0x03) == 0) {
        // Slime horizontal patrol
        if (g_state.slime_x > 90) {
            g_state.slime_x -= 4;
        } else {
            g_state.slime_x += 4;
        }

        // Goblin vertical patrol
        if (g_state.goblin_y > 40) {
            g_state.goblin_y -= 4;
        } else {
            g_state.goblin_y += 4;
        }
    }
}

/* -------------------------------------------------------------------------
 * Main Application Loop
 * ------------------------------------------------------------------------- */

int main(void) {
    feb_set_hires();
    feb_clear_screen();
    show_title_screen();
    init_game();

    while (1) {
        feb_clear_screen();

        // 1. Draw World & Actors
        draw_hud();
        draw_room();
        draw_enemies();
        draw_hero();

        // 2. Victory Check
        if (g_state.relic_state == 2) {
            feb_save_flags("/feb/saves/quest.sav", &g_state.gems, 1);
            feb_draw_string(12, 18, "SACRED RELIC RESTORED!", FEB_FONT_5X7);
            feb_draw_string(22, 30, "THE REALM IS SAVED!", FEB_FONT_5X7);
            feb_wait_key();
            show_title_screen();
            init_game();
            continue;
        }

        // 3. Game Over Check
        if (g_state.hero_hp == 0) {
            feb_draw_string(32, 22, "GAME OVER", FEB_FONT_6X10);
            feb_draw_string(24, 36, "THY SOUL IS LOST...", FEB_FONT_4X6);
            feb_wait_key();
            show_title_screen();
            init_game();
            continue;
        }

        // 4. Update Enemy AI
        update_ai();

        // 5. Read Button Input (Non-blocking)
        uint8_t keys = feb_read_buttons();

        // Check for hardware emergency exit chord: UP (1) + DOWN (2) + BACK (4)
        if ((keys & (FEB_BTN_UP | FEB_BTN_DOWN | FEB_BTN_BACK)) ==
            (FEB_BTN_UP | FEB_BTN_DOWN | FEB_BTN_BACK)) {
            feb_exit();
        }

        // Directional Movement & Room Transitions
        if (keys & FEB_BTN_UP) {
            g_state.hero_dir = DIR_UP;
            if (g_state.hero_y == 21) {
                // Check north exit
                if (g_state.room == ROOM_FOREST && g_state.hero_x >= 52 && g_state.hero_x <= 60) {
                    g_state.room = ROOM_CAVE;
                    g_state.hero_x = 56;
                    g_state.hero_y = 45;
                } else if (g_state.room == ROOM_DUNGEON && g_state.hero_x >= 60 && g_state.hero_x <= 68) {
                    g_state.room = ROOM_RUINS;
                    g_state.hero_x = 64;
                    g_state.hero_y = 45;
                }
            } else if (g_state.hero_y > 21) {
                g_state.hero_y -= 4;
            }
            check_bump_collision();
        } else if (keys & FEB_BTN_DOWN) {
            g_state.hero_dir = DIR_DOWN;
            if (g_state.hero_y == 45) {
                // Check south exit
                if (g_state.room == ROOM_CAVE && g_state.hero_x >= 52 && g_state.hero_x <= 60) {
                    g_state.room = ROOM_FOREST;
                    g_state.hero_x = 56;
                    g_state.hero_y = 21;
                } else if (g_state.room == ROOM_RUINS && g_state.hero_x >= 60 && g_state.hero_x <= 68) {
                    if (g_state.has_key) {
                        g_state.room = ROOM_DUNGEON;
                        g_state.hero_x = 64;
                        g_state.hero_y = 21;
                    }
                }
            } else if (g_state.hero_y < 45) {
                g_state.hero_y += 4;
            }
            check_bump_collision();
        } else if (keys & FEB_BTN_BACK) {
            g_state.hero_dir = DIR_LEFT;
            if (g_state.hero_x <= 8) {
                // Check west exit
                if (g_state.room == ROOM_RUINS) {
                    g_state.room = ROOM_FOREST;
                    g_state.hero_x = 112;
                }
            } else {
                g_state.hero_x -= 4;
            }
            check_bump_collision();
        } else if (keys & FEB_BTN_OK) {
            g_state.hero_dir = DIR_RIGHT;
            if (g_state.hero_x >= 112) {
                // Check east exit
                if (g_state.room == ROOM_FOREST) {
                    g_state.room = ROOM_RUINS;
                    g_state.hero_x = 8;
                }
            } else {
                g_state.hero_x += 4;
            }
            check_bump_collision();
        }
    }

    return 0;
}
