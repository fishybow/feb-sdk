/**
 * @file main.c
 * @brief Advanced Digital Pet (TamaPet) for Flashiibo Pro Gen3 (.feb)
 *
 * An advanced virtual pet simulation taking full advantage of the Flashiibo FEB runtime:
 *   - 128x64 Super-CHIP display mode with real-time vector geometry and typography
 *   - 16-byte persistent state stored in /feb/saves/digital_pet.sav via FX75/FX85
 *   - Evolution Stages: Egg -> Baby -> Teen -> Adult (Cyber Dragon / Pixel Cat)
 *   - Vital Stats: Hunger, Happiness, Energy, Hygiene, Age, and Weight
 *   - Interactive Modes: Feed, Play Mini-Game, Clean Bath, Sleep/Lights, Heal, Stats
 *   - Playable Heart Catcher mini-game with real-time collision detection
 *   - 4-Button Navigation:
 *       BACK (Left):  Move cursor / Move pet left
 *       OK (Right):   Move cursor / Move pet right
 *       UP:           Select menu / Feed / Jump / Catch
 *       DOWN:         Back / Pet creature / Wake up
 *       UP + DOWN:    System emergency exit (state is flushed automatically)
 */

#include "../../include/feb.h"

/* -------------------------------------------------------------------------
 * Persistent Save State Layout (16 Bytes in RPL Flags)
 * ------------------------------------------------------------------------- */
#define SAVE_MAGIC_PET          0x50  /* 'P' */

/* Evolution Stages */
#define STAGE_EGG               0
#define STAGE_BABY              1
#define STAGE_TEEN              2
#define STAGE_ADULT             3

/* Adult Species */
#define SPECIES_DRAGON          0  /* High care */
#define SPECIES_CAT             1  /* Pampered */

/* UI Screens & States */
#define MODE_ARENA              0
#define MODE_MINIGAME           1
#define MODE_STATS_SCREEN       2

/* Menu Items (0..5) */
#define MENU_FEED               0
#define MENU_PLAY               1
#define MENU_CLEAN              2
#define MENU_SLEEP              3
#define MENU_HEAL               4
#define MENU_STATS              5
#define MENU_COUNT              6

/* Banner notification IDs */
#define BANNER_NONE             0
#define BANNER_WELCOME          1
#define BANNER_FEED             2
#define BANNER_CLEAN            3
#define BANNER_SLEEP            4
#define BANNER_WAKE             5
#define BANNER_HEAL             6
#define BANNER_EVOLVE           7

/* -------------------------------------------------------------------------
 * 16x16 Pixel Sprites (32 Bytes Each)
 * ------------------------------------------------------------------------- */

/* Egg */
static const uint8_t spr_egg[32] = {
    0x03, 0xC0, 0x0C, 0x30, 0x18, 0x18, 0x31, 0x8C,
    0x22, 0x44, 0x61, 0x86, 0x42, 0x42, 0x40, 0x02,
    0x41, 0x82, 0x60, 0x06, 0x20, 0x04, 0x30, 0x0C,
    0x18, 0x18, 0x0C, 0x30, 0x03, 0xC0, 0x00, 0x00
};

/* Baby Blob */
static const uint8_t spr_baby[32] = {
    0x00, 0x00, 0x07, 0xE0, 0x08, 0x10, 0x10, 0x08,
    0x20, 0x04, 0x40, 0x02, 0x49, 0x92, 0x49, 0x92,
    0x40, 0x02, 0x44, 0x22, 0x23, 0xC4, 0x10, 0x08,
    0x08, 0x10, 0x07, 0xE0, 0x04, 0x20, 0x00, 0x00
};

/* Teen Maru */
static const uint8_t spr_teen[32] = {
    0x42, 0x42, 0x66, 0x66, 0x3F, 0xFC, 0x20, 0x04,
    0x52, 0x4A, 0x52, 0x4A, 0x40, 0x02, 0x44, 0x22,
    0x23, 0xC4, 0x1F, 0xF8, 0x10, 0x08, 0x10, 0x08,
    0x10, 0x18, 0x1F, 0xF0, 0x09, 0x90, 0x00, 0x00
};

/* Adult: Cyber Dragon */
static const uint8_t spr_dragon[32] = {
    0x81, 0x81, 0xC3, 0xC3, 0x7E, 0x7E, 0x3C, 0x3C,
    0x5A, 0x5A, 0x5A, 0x5A, 0x3C, 0x3C, 0x18, 0x18,
    0x7E, 0x7E, 0xFF, 0xFF, 0x99, 0x99, 0x99, 0x99,
    0x7E, 0x7E, 0x3C, 0x3C, 0x42, 0x42, 0x81, 0x81
};

/* Adult: Pixel Cat */
static const uint8_t spr_cat[32] = {
    0xC0, 0x03, 0xE0, 0x07, 0x7F, 0xFE, 0x49, 0x92,
    0x5D, 0xBA, 0x49, 0x92, 0x40, 0x02, 0x43, 0xC2,
    0x20, 0x04, 0x1F, 0xF8, 0x18, 0x18, 0x14, 0x28,
    0x14, 0x28, 0x1F, 0xF8, 0x11, 0x88, 0x00, 0x00
};

/* -------------------------------------------------------------------------
 * 8x8 Pixel Item & Status Sprites (8 Bytes Each)
 * ------------------------------------------------------------------------- */

/* Food: Apple with Leaf */
static const uint8_t spr_apple[8] = {
    0x0C, 0x06, 0x3A, 0x7F, 0x7F, 0x7F, 0x3E, 0x1C
};

/* Poop Pile */
static const uint8_t spr_poop[8] = {
    0x08, 0x14, 0x22, 0x77, 0x7F, 0xFF, 0xFF, 0x7E
};

/* Happy Heart */
static const uint8_t spr_heart[8] = {
    0x00, 0x66, 0xFF, 0xFF, 0x7E, 0x3C, 0x18, 0x00
};

/* Sick Skull */
static const uint8_t spr_skull[8] = {
    0x3C, 0x7E, 0xDB, 0xFF, 0x7E, 0x3C, 0x5A, 0x00
};

/* Sleep Zzz */
static const uint8_t spr_zzz[8] = {
    0x78, 0x10, 0x20, 0x7E, 0x03, 0x04, 0x08, 0x1F
};

/* Medicine Pill */
static const uint8_t spr_pill[8] = {
    0x1C, 0x3E, 0x7F, 0x7F, 0xFE, 0xFC, 0x78, 0x30
};

/* Bath Water Droplets */
static const uint8_t spr_droplet[8] = {
    0x10, 0x10, 0x28, 0x28, 0x44, 0x44, 0x38, 0x00
};

/* -------------------------------------------------------------------------
 * Persistent Pet State (16 Bytes - Maps directly to RPL Flags)
 * ------------------------------------------------------------------------- */
struct PetState {
    uint8_t magic;
    uint8_t stage;
    uint8_t species;
    uint8_t hunger;
    uint8_t happy;
    uint8_t energy;
    uint8_t hygiene;
    uint8_t sick;
    uint8_t age;
    uint8_t weight;
    uint8_t care;
    uint8_t poop;
    uint8_t lights;
    uint8_t hiscore;
    uint8_t gen;
    uint8_t actions;
};

static struct PetState pet;

/* UI State */
static uint8_t g_mode = MODE_ARENA;
static uint8_t g_menu_sel = 0;
static uint8_t g_anim_frame = 0;
static uint8_t g_pet_x = 56;
static uint8_t g_pet_y = 26;
static uint8_t g_pet_dir = 1;
static uint8_t g_tick = 0;
static uint8_t g_banner_id = 0;
static uint8_t g_banner_timer = 0;

/* Buttons */
static uint8_t g_prev_keys = 0;
static uint8_t g_cur_keys = 0;
static uint8_t g_just_keys = 0;

/* Mini-game state */
static uint8_t g_game_pos = 56;
static uint8_t g_item_x = 64;
static uint8_t g_item_y = 16;
static uint8_t g_item_type = 0; /* 0=Heart, 1=Rock */
static uint8_t g_game_score = 0;
static uint8_t g_game_lives = 3;
static uint8_t g_game_timer = 200;

/* -------------------------------------------------------------------------
 * Persistence Subsystem
 * ------------------------------------------------------------------------- */

static void save_state(void) {
    pet.actions++;
    feb_save_flags(pet, 16);
}

static void init_pet(void) {
    pet.magic = SAVE_MAGIC_PET;
    pet.stage = STAGE_EGG;
    pet.hunger = 80;
    pet.happy = 80;
    pet.energy = 80;
    pet.hygiene = 80;
    pet.weight = 5;
    pet.care = 10;
    pet.gen = 1;
    save_state();
}

static void load_state(void) {
    feb_load_flags(pet, 16);
    if (pet.magic != SAVE_MAGIC_PET) {
        init_pet();
    }
}

/* -------------------------------------------------------------------------
 * Graphics & UI Drawing Helpers
 * ------------------------------------------------------------------------- */

static void show_banner(uint8_t banner_id, uint8_t duration_frames) {
    g_banner_id = banner_id;
    g_banner_timer = duration_frames;
}

static void draw_banner_msg(void) {
    if (g_banner_timer == 0) return;
    feb_set_draw_mode(FEB_DRAW_MODE_CLEAR);
    feb_fill_rect(8, 22, 112, 16);
    feb_set_draw_mode(FEB_DRAW_MODE_SET);
    feb_draw_rect(8, 22, 112, 16);

    if (g_banner_id == BANNER_WELCOME)      feb_draw_string(40, 27, "WELCOME!", FEB_FONT_4X6);
    else if (g_banner_id == BANNER_FEED)    feb_draw_string(32, 27, "YUMMY! +20", FEB_FONT_4X6);
    else if (g_banner_id == BANNER_CLEAN)   feb_draw_string(32, 27, "CLEANED!", FEB_FONT_4X6);
    else if (g_banner_id == BANNER_SLEEP)   feb_draw_string(24, 27, "LIGHTS OFF: ZZZ", FEB_FONT_4X6);
    else if (g_banner_id == BANNER_WAKE)    feb_draw_string(30, 27, "GOOD MORNING!", FEB_FONT_4X6);
    else if (g_banner_id == BANNER_HEAL)    feb_draw_string(36, 27, "HEALED!", FEB_FONT_4X6);
    else if (g_banner_id == BANNER_EVOLVE)  feb_draw_string(30, 27, "PET EVOLVED!", FEB_FONT_4X6);
}

static void draw_icon(uint8_t x, uint8_t y, uint8_t icon_id) {
    if (icon_id == 0) feb_draw_sprite(x, y, spr_apple, 8);
    else if (icon_id == 1) feb_draw_sprite(x, y, spr_heart, 8);
    else if (icon_id == 2) feb_draw_sprite(x, y, spr_droplet, 8);
    else if (icon_id == 3) feb_draw_sprite(x, y, spr_zzz, 8);
    else if (icon_id == 4) feb_draw_sprite(x, y, spr_pill, 8);
    else {
        feb_draw_rect(x + 1, y + 1, 6, 6);
        feb_draw_pixel(x + 3, y + 3);
    }
}

static void draw_top_menu(void) {
    feb_set_draw_mode(FEB_DRAW_MODE_SET);
    feb_draw_hline(0, 13, 128);

    for (uint8_t i = 0; i < MENU_COUNT; i++) {
        uint8_t x = 8 + (i << 4) + (i << 2);
        if (i == g_menu_sel) {
            feb_set_draw_mode(FEB_DRAW_MODE_SET);
            feb_draw_rect(x - 3, 1, 14, 11);
        }
        draw_icon(x, 3, i);
    }
}

static void draw_status_bar(void) {
    feb_set_draw_mode(FEB_DRAW_MODE_SET);
    feb_draw_hline(0, 54, 128);

    feb_draw_string(2, 56, "HNG", FEB_FONT_4X6);
    feb_draw_number(18, 56, pet.hunger, FEB_FONT_4X6);

    feb_draw_string(44, 56, "HAP", FEB_FONT_4X6);
    feb_draw_number(60, 56, pet.happy, FEB_FONT_4X6);

    feb_draw_string(86, 56, "NRG", FEB_FONT_4X6);
    feb_draw_number(102, 56, pet.energy, FEB_FONT_4X6);
}

static void draw_active_pet(void) {
    uint8_t py = g_pet_y - g_anim_frame;
    if (pet.stage == STAGE_EGG) {
        feb_draw_sprite16(g_pet_x, py, spr_egg);
    } else if (pet.stage == STAGE_BABY) {
        feb_draw_sprite16(g_pet_x, py, spr_baby);
    } else if (pet.stage == STAGE_TEEN) {
        feb_draw_sprite16(g_pet_x, py, spr_teen);
    } else if (pet.species == SPECIES_DRAGON) {
        feb_draw_sprite16(g_pet_x, py, spr_dragon);
    } else {
        feb_draw_sprite16(g_pet_x, py, spr_cat);
    }
}

static void draw_arena(void) {
    feb_clear_screen();

    if (pet.lights != 0) {
        feb_set_draw_mode(FEB_DRAW_MODE_SET);
        draw_top_menu();
        feb_draw_string(44, 28, "SLEEPING", FEB_FONT_6X10);
        feb_draw_sprite(74, 20, spr_zzz, 8);
        draw_status_bar();
        draw_banner_msg();
        return;
    }

    draw_top_menu();

    feb_set_draw_mode(FEB_DRAW_MODE_SET);
    draw_active_pet();

    if (pet.sick != 0) {
        feb_draw_sprite(g_pet_x + 16, g_pet_y - 4, spr_skull, 8);
    } else if (pet.happy >= 80) {
        feb_draw_sprite(g_pet_x + 16, g_pet_y - 4, spr_heart, 8);
    }

    if (pet.poop >= 1) feb_draw_sprite(16, 42, spr_poop, 8);
    if (pet.poop >= 2) feb_draw_sprite(28, 44, spr_poop, 8);
    if (pet.poop >= 3) feb_draw_sprite(104, 43, spr_poop, 8);

    draw_status_bar();
    draw_banner_msg();
}

/* -------------------------------------------------------------------------
 * Stats Screen
 * ------------------------------------------------------------------------- */

static void draw_stats_screen(void) {
    feb_clear_screen();
    feb_set_draw_mode(FEB_DRAW_MODE_SET);

    feb_draw_string(32, 4, "PET STATUS", FEB_FONT_6X10);
    feb_draw_hline(0, 16, 128);

    feb_draw_string(16, 22, "STAGE", FEB_FONT_4X6);
    feb_draw_number(46, 22, pet.stage, FEB_FONT_4X6);

    feb_draw_string(16, 32, "AGE", FEB_FONT_4X6);
    feb_draw_number(46, 32, pet.age, FEB_FONT_4X6);

    feb_draw_string(74, 22, "WEIGHT", FEB_FONT_4X6);
    feb_draw_number(106, 22, pet.weight, FEB_FONT_4X6);

    feb_draw_string(74, 32, "BEST", FEB_FONT_4X6);
    feb_draw_number(106, 32, pet.hiscore, FEB_FONT_4X6);

    feb_draw_hline(0, 50, 128);
    feb_draw_string(24, 54, "DOWN TO RETURN", FEB_FONT_4X6);
}

/* -------------------------------------------------------------------------
 * Playable Mini-Game: Heart Catcher
 * ------------------------------------------------------------------------- */

static void reset_minigame_item(void) {
    g_item_y = 16;
    g_item_x = 24 + (feb_rand(63));
    g_item_type = feb_rand(1);
}

static void init_minigame(void) {
    g_mode = MODE_MINIGAME;
    g_game_pos = 56;
    g_game_score = 0;
    g_game_lives = 3;
    g_game_timer = 200;
    reset_minigame_item();
}

static void update_minigame(void) {
    if (g_just_keys & FEB_BTN_LEFT) {
        if (g_game_pos > 16) g_game_pos -= 8;
    }
    if (g_just_keys & FEB_BTN_RIGHT) {
        if (g_game_pos < 96) g_game_pos += 8;
    }

    g_item_y += 2;
    g_game_timer--;

    if (g_item_y >= 46) {
        if (g_item_x >= g_game_pos && g_item_x <= g_game_pos + 16) {
            if (g_item_type == 0) {
                g_game_score++;
            } else if (g_game_lives > 0) {
                g_game_lives--;
            }
            reset_minigame_item();
        } else if (g_item_y >= 54) {
            reset_minigame_item();
        }
    }

    if (g_game_lives == 0 || g_game_timer == 0) {
        if (g_game_score > pet.hiscore) {
            pet.hiscore = g_game_score;
        }
        pet.happy += (g_game_score << 1);
        if (pet.happy > 100) pet.happy = 100;
        if (pet.energy > 15) pet.energy -= 15;
        if (pet.weight > 2) pet.weight--;
        save_state();
        g_mode = MODE_ARENA;
    }
}

static void draw_minigame(void) {
    feb_clear_screen();
    feb_set_draw_mode(FEB_DRAW_MODE_SET);

    feb_draw_string(4, 2, "CATCH!", FEB_FONT_6X10);
    feb_draw_string(60, 4, "SCORE:", FEB_FONT_4X6);
    feb_draw_number(88, 4, g_game_score, FEB_FONT_4X6);

    feb_draw_string(104, 4, "LV:", FEB_FONT_4X6);
    feb_draw_number(118, 4, g_game_lives, FEB_FONT_4X6);
    feb_draw_hline(0, 13, 128);

    if (g_item_type == 0) {
        feb_draw_sprite(g_item_x, g_item_y, spr_heart, 8);
    } else {
        feb_draw_rect(g_item_x, g_item_y, 8, 8);
    }

    feb_fill_rect(g_game_pos, 50, 16, 4);

    feb_draw_hline(0, 56, 128);
    feb_draw_string(24, 57, "<-- LEFT    RIGHT -->", FEB_FONT_4X6);
}

/* -------------------------------------------------------------------------
 * Simulation & Care Interactions
 * ------------------------------------------------------------------------- */

static void do_feed(void) {
    if (pet.hunger < 100) {
        pet.hunger += 20;
        if (pet.hunger > 100) pet.hunger = 100;
        pet.weight++;
        pet.care++;
        save_state();
        show_banner(BANNER_FEED, 30);
    }
}

static void do_clean(void) {
    pet.poop = 0;
    pet.hygiene = 100;
    save_state();
    show_banner(BANNER_CLEAN, 30);
}

static void do_sleep_toggle(void) {
    pet.lights = 1 - pet.lights;
    save_state();
    if (pet.lights != 0) {
        show_banner(BANNER_SLEEP, 30);
    } else {
        show_banner(BANNER_WAKE, 30);
    }
}

static void do_heal(void) {
    if (pet.sick != 0) {
        pet.sick = 0;
        save_state();
        show_banner(BANNER_HEAL, 30);
    }
}

static void check_evolution(void) {
    if (pet.stage == STAGE_EGG && pet.age >= 1) {
        pet.stage = STAGE_BABY;
        save_state();
        show_banner(BANNER_EVOLVE, 50);
        return;
    }

    if (pet.stage == STAGE_BABY && pet.age >= 4) {
        pet.stage = STAGE_TEEN;
        save_state();
        show_banner(BANNER_EVOLVE, 50);
        return;
    }

    if (pet.stage == STAGE_TEEN && pet.age >= 8) {
        pet.stage = STAGE_ADULT;
        if (pet.care >= 20) {
            pet.species = SPECIES_DRAGON;
        } else {
            pet.species = SPECIES_CAT;
        }
        save_state();
        show_banner(BANNER_EVOLVE, 60);
    }
}

static void tick_simulation(void) {
    g_tick++;

    if ((g_tick & 31) == 0) {
        g_anim_frame = 1 - g_anim_frame;
        if (pet.lights == 0 && g_mode == MODE_ARENA) {
            if (g_pet_dir != 0) {
                if (g_pet_x < 80) g_pet_x += 2; else g_pet_dir = 0;
            } else {
                if (g_pet_x > 32) g_pet_x -= 2; else g_pet_dir = 1;
            }
        }
    }

    if (g_banner_timer > 0) {
        g_banner_timer--;
    }

    if (g_tick == 0) {
        pet.age++;
        check_evolution();

        if (pet.lights != 0) {
            if (pet.energy < 100) pet.energy += 10;
        } else {
            if (pet.hunger > 3) pet.hunger -= 2;
            if (pet.happy > 3) pet.happy -= 2;
            if (pet.energy > 3) pet.energy -= 2;
            if (pet.hunger < 70 && pet.poop < 3) pet.poop++;
        }

        if (pet.hunger <= 10 || pet.poop >= 3) {
            pet.sick = 1;
        }

        save_state();
    }
}

/* -------------------------------------------------------------------------
 * Main Entry Point
 * ------------------------------------------------------------------------- */

int main(void) {
    feb_set_high_res(true);
    feb_clear_screen();

    load_state();

    show_banner(BANNER_WELCOME, 45);

    while (1) {
        feb_delay_frames(1);

        g_cur_keys = feb_get_keys();
        g_just_keys = g_cur_keys;
        if (g_cur_keys == g_prev_keys) {
            g_just_keys = 0;
        }
        g_prev_keys = g_cur_keys;

        tick_simulation();

        if (g_mode == MODE_MINIGAME) {
            update_minigame();
            draw_minigame();
            continue;
        }

        if (g_mode == MODE_STATS_SCREEN) {
            draw_stats_screen();
            if (g_just_keys & FEB_BTN_DOWN) {
                g_mode = MODE_ARENA;
            }
            continue;
        }

        if (g_just_keys & FEB_BTN_LEFT) {
            if (g_menu_sel > 0) g_menu_sel--;
        }
        if (g_just_keys & FEB_BTN_RIGHT) {
            if (g_menu_sel < MENU_COUNT - 1) g_menu_sel++;
        }

        if (g_just_keys & FEB_BTN_UP) {
            if (pet.stage == STAGE_EGG) {
                pet.age++;
                check_evolution();
                show_banner(BANNER_EVOLVE, 25);
            } else if (g_menu_sel == MENU_FEED) {
                do_feed();
            } else if (g_menu_sel == MENU_PLAY) {
                init_minigame();
            } else if (g_menu_sel == MENU_CLEAN) {
                do_clean();
            } else if (g_menu_sel == MENU_SLEEP) {
                do_sleep_toggle();
            } else if (g_menu_sel == MENU_HEAL) {
                do_heal();
            } else {
                g_mode = MODE_STATS_SCREEN;
            }
        }

        if (g_just_keys & FEB_BTN_DOWN) {
            if (pet.happy < 100) pet.happy += 5;
            save_state();
        }

        draw_arena();
    }

    return 0;
}
