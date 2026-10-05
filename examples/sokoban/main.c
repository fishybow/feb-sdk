/**
 * @file main.c
 * @brief Sokoban Box-Pushing Puzzle Game for Flashiibo Pro Gen3 FEB Runner (.feb)
 *
 * A classic 10-level Sokoban puzzle game optimized for Flashiibo's 128x64 monochrome
 * OLED display and 4-button hardware navigation:
 *   - UP:    Move character UP    (Key 0x2)
 *   - DOWN:  Move character DOWN  (Key 0x8)
 *   - BACK:  Move character LEFT  (Key 0x4)
 *   - OK:    Move character RIGHT (Key 0x6)
 *
 * Special hardware chords:
 *   - BACK + OK (LEFT + RIGHT): Restart current level instantly
 *   - UP + DOWN: Hardware emergency exit back to FEB Runner menu
 *
 * Game Mechanics:
 *   - Main character (@) pushes boxes ($) to target destinations (.)
 *   - Immovable stone blocks (#) act as strategic obstacles, corridors, and walls
 *   - Boxes turn into solid filled crates (*) when placed on destinations
 *   - 10 carefully designed levels from easy tutorial to grandmaster challenge
 *   - Persistent level progress automatically saved to companion .sav
 */

#include "../../include/feb.h"

#define CELL_EMPTY          0
#define CELL_WALL           1
#define CELL_TARGET         2
#define CELL_BOX            3
#define CELL_BOX_ON_TGT     4
#define CELL_PLAYER         5
#define CELL_PLAYER_ON_TGT  6

#define STATE_PLAYING       0
#define STATE_LEVEL_CLEAR   1
#define STATE_GAME_WON      2

/* -------------------------------------------------------------------------
 * 8x8 Pixel Sprites (Monochrome OLED)
 * ------------------------------------------------------------------------- */

/* Immovable Stone Obstacle / Brick Wall */
static const uint8_t sprite_wall[8] = {
    0xFF, /* ######## */
    0x89, /* #..#..#. */
    0x89, /* #..#..#. */
    0xFF, /* ######## */
    0x91, /* #..#..#. */
    0x91, /* #..#..#. */
    0xFF, /* ######## */
    0x00  /* ........ */
};

/* Target Destination / Goal Marker */
static const uint8_t sprite_target[8] = {
    0x00, /* ........ */
    0x18, /* ...##... */
    0x24, /* ..#..#.. */
    0x5A, /* .#.##.#. */
    0x5A, /* .#.##.#. */
    0x24, /* ..#..#.. */
    0x18, /* ...##... */
    0x00  /* ........ */
};

/* Pushable Wooden Crate / Box */
static const uint8_t sprite_box[8] = {
    0x7E, /* .######. */
    0xBD, /* #.####.# */
    0xDB, /* ##.##.## */
    0xE7, /* ###..### */
    0xE7, /* ###..### */
    0xDB, /* ##.##.## */
    0xBD, /* #.####.# */
    0x7E  /* .######. */
};

/* Completed Box on Destination (Filled Highlight) */
static const uint8_t sprite_box_on_tgt[8] = {
    0x7E, /* .######. */
    0xFF, /* ######## */
    0xBD, /* #.####.# */
    0x99, /* #..##..# */
    0x99, /* #..##..# */
    0xBD, /* #.####.# */
    0xFF, /* ######## */
    0x7E  /* .######. */
};

/* Main Character / Player */
static const uint8_t sprite_player[8] = {
    0x18, /* ...##... (cap) */
    0x3C, /* ..####.. (face) */
    0x7E, /* .######. (torso) */
    0x5A, /* .#.##.#. (hands) */
    0x7E, /* .######. (belt) */
    0x24, /* ..#..#.. (legs) */
    0x24, /* ..#..#.. (legs) */
    0x66  /* .##..##. (boots) */
};

/* -------------------------------------------------------------------------
 * 10 Progressive Level Layouts (Packed: 2 cells per byte, 32 bytes per level)
 * ------------------------------------------------------------------------- */

/* Levels 1 to 5 (5 levels x 32 bytes = 160 bytes) */
static const uint8_t levels_a[160] = {
    /* Level 1: First Push */
    0x11, 0x11, 0x11, 0x11, 0x10, 0x00, 0x00, 0x01, 0x10, 0x50, 0x30, 0x21, 0x10, 0x00, 0x00, 0x01,
    0x10, 0x00, 0x00, 0x01, 0x10, 0x00, 0x00, 0x01, 0x10, 0x00, 0x00, 0x01, 0x11, 0x11, 0x11, 0x11,
    /* Level 2: The Detour */
    0x11, 0x11, 0x11, 0x11, 0x10, 0x00, 0x00, 0x01, 0x10, 0x50, 0x10, 0x01, 0x10, 0x00, 0x13, 0x01,
    0x10, 0x00, 0x10, 0x01, 0x10, 0x00, 0x12, 0x01, 0x10, 0x00, 0x00, 0x01, 0x11, 0x11, 0x11, 0x11,
    /* Level 3: Twin Goals */
    0x11, 0x11, 0x11, 0x11, 0x10, 0x00, 0x00, 0x01, 0x10, 0x02, 0x00, 0x01, 0x10, 0x01, 0x30, 0x01,
    0x10, 0x01, 0x50, 0x01, 0x10, 0x01, 0x30, 0x01, 0x10, 0x02, 0x00, 0x01, 0x11, 0x11, 0x11, 0x11,
    /* Level 4: Pillar Pass */
    0x11, 0x11, 0x11, 0x11, 0x10, 0x00, 0x00, 0x01, 0x10, 0x02, 0x00, 0x01, 0x10, 0x01, 0x30, 0x01,
    0x10, 0x51, 0x00, 0x01, 0x10, 0x01, 0x30, 0x01, 0x10, 0x00, 0x20, 0x01, 0x11, 0x11, 0x11, 0x11,
    /* Level 5: Split Path */
    0x11, 0x11, 0x11, 0x11, 0x10, 0x00, 0x00, 0x01, 0x10, 0x20, 0x10, 0x01, 0x10, 0x30, 0x30, 0x01,
    0x10, 0x50, 0x10, 0x01, 0x10, 0x02, 0x10, 0x01, 0x10, 0x00, 0x00, 0x01, 0x11, 0x11, 0x11, 0x11
};

/* Levels 6 to 10 (5 levels x 32 bytes = 160 bytes) */
static const uint8_t levels_b[160] = {
    /* Level 6: The Chamber */
    0x11, 0x11, 0x11, 0x11, 0x10, 0x00, 0x00, 0x01, 0x10, 0x02, 0x00, 0x01, 0x10, 0x01, 0x03, 0x01,
    0x10, 0x01, 0x53, 0x01, 0x10, 0x01, 0x03, 0x01, 0x10, 0x02, 0x20, 0x01, 0x11, 0x11, 0x11, 0x11,
    /* Level 7: The Alcove */
    0x11, 0x11, 0x11, 0x11, 0x10, 0x00, 0x00, 0x01, 0x10, 0x01, 0x10, 0x01, 0x10, 0x01, 0x02, 0x01,
    0x10, 0x03, 0x03, 0x01, 0x10, 0x01, 0x52, 0x01, 0x10, 0x01, 0x10, 0x01, 0x11, 0x11, 0x11, 0x11,
    /* Level 8: The Corridor */
    0x11, 0x11, 0x11, 0x11, 0x10, 0x02, 0x00, 0x01, 0x10, 0x01, 0x03, 0x01, 0x10, 0x05, 0x03, 0x01,
    0x10, 0x01, 0x03, 0x01, 0x10, 0x01, 0x00, 0x01, 0x10, 0x02, 0x20, 0x01, 0x11, 0x11, 0x11, 0x11,
    /* Level 9: The Lock */
    0x11, 0x11, 0x11, 0x11, 0x10, 0x00, 0x20, 0x01, 0x10, 0x11, 0x21, 0x11, 0x10, 0x10, 0x30, 0x01,
    0x10, 0x10, 0x31, 0x01, 0x10, 0x15, 0x30, 0x01, 0x10, 0x10, 0x20, 0x01, 0x11, 0x11, 0x11, 0x11,
    /* Level 10: Grandmaster */
    0x11, 0x11, 0x11, 0x11, 0x10, 0x02, 0x00, 0x01, 0x10, 0x01, 0x03, 0x01, 0x10, 0x05, 0x03, 0x01,
    0x10, 0x01, 0x03, 0x01, 0x10, 0x01, 0x03, 0x01, 0x10, 0x22, 0x20, 0x01, 0x11, 0x11, 0x11, 0x11
};

/* -------------------------------------------------------------------------
 * Game State Variables
 * ------------------------------------------------------------------------- */

static uint8_t board[64];
static uint8_t current_level = 0;
static uint8_t saved_level = 0;
static uint8_t player_r = 0;
static uint8_t player_c = 0;
static uint8_t moves = 0;
static uint8_t pushes = 0;
static uint8_t game_state = STATE_PLAYING;

/* -------------------------------------------------------------------------
 * Level Management & Unpacking
 * ------------------------------------------------------------------------- */

static void load_level(uint8_t lvl) {
    current_level = lvl;
    moves = 0;
    pushes = 0;

    uint8_t base = lvl;
    if (lvl >= 5) {
        base = lvl - 5;
    }
    base = base << 5;

    for (uint8_t i = 0; i < 32; i++) {
        uint8_t b = 0;
        if (lvl < 5) {
            b = levels_a[base + i];
        } else {
            b = levels_b[base + i];
        }

        uint8_t cell = (b >> 4) & 15;
        uint8_t idx = i << 1;
        board[idx] = cell;
        if (cell == CELL_PLAYER || cell == CELL_PLAYER_ON_TGT) {
            player_r = idx >> 3;
            player_c = idx & 7;
        }

        cell = b & 15;
        idx = idx + 1;
        board[idx] = cell;
        if (cell == CELL_PLAYER || cell == CELL_PLAYER_ON_TGT) {
            player_r = idx >> 3;
            player_c = idx & 7;
        }
    }
}

static bool check_win(void) {
    for (uint8_t i = 0; i < 64; i++) {
        uint8_t cell = board[i];
        if (cell == CELL_BOX) {
            return false;
        }
    }
    return true;
}

/* -------------------------------------------------------------------------
 * Rendering & Graphics
 * ------------------------------------------------------------------------- */

static void draw_tile(uint8_t px, uint8_t py, uint8_t cell) {
    if (cell == CELL_WALL) {
        feb_draw_sprite(px, py, sprite_wall, 8);
    } else if (cell == CELL_TARGET) {
        feb_draw_sprite(px, py, sprite_target, 8);
    } else if (cell == CELL_BOX) {
        feb_draw_sprite(px, py, sprite_box, 8);
    } else if (cell == CELL_BOX_ON_TGT) {
        feb_draw_sprite(px, py, sprite_box_on_tgt, 8);
    } else {
        feb_draw_sprite(px, py, sprite_player, 8);
    }
}

static void draw_sidebar(void) {
    /* Title */
    feb_draw_string(72, 2, "SOKOBAN", FEB_FONT_6X10);
    feb_draw_hline(67, 13, 58);

    /* Level info */
    feb_draw_string(68, 17, "LVL:", FEB_FONT_4X6);
    feb_draw_number(88, 17, current_level + 1, FEB_FONT_4X6);
    feb_draw_string(98, 17, "/10", FEB_FONT_4X6);

    /* Move counter */
    feb_draw_string(68, 26, "MOVE:", FEB_FONT_4X6);
    feb_draw_number(92, 26, moves, FEB_FONT_4X6);

    /* Push counter */
    feb_draw_string(68, 35, "PUSH:", FEB_FONT_4X6);
    feb_draw_number(92, 35, pushes, FEB_FONT_4X6);

    /* Controls footer */
    feb_draw_hline(67, 44, 58);
    feb_draw_string(68, 48, "RST: L+R", FEB_FONT_4X6);
    feb_draw_string(68, 56, "EXIT:U+D", FEB_FONT_4X6);
}

static void render_screen(void) {
    feb_clear_screen();
    feb_set_draw_mode(FEB_DRAW_MODE_SET);

    /* Grid Divider */
    feb_draw_vline(64, 0, 64);
    draw_sidebar();

    /* Board Tiles */
    for (uint8_t i = 0; i < 64; i++) {
        uint8_t cell = board[i];
        if (cell != CELL_EMPTY) {
            uint8_t px = (i & 7) << 3;
            uint8_t py = (i >> 3) << 3;
            draw_tile(px, py, cell);
        }
    }
}

static void draw_overlay(void) {
    feb_set_draw_mode(FEB_DRAW_MODE_CLEAR);
    feb_fill_rect(8, 14, 112, 36);
    feb_set_draw_mode(FEB_DRAW_MODE_SET);
    feb_draw_rect(8, 14, 112, 36);

    if (game_state == STATE_GAME_WON) {
        feb_draw_string(34, 19, "VICTORY!", FEB_FONT_6X10);
        feb_draw_string(20, 32, "ALL 10 SOLVED!", FEB_FONT_4X6);
    } else {
        feb_draw_string(24, 20, "LEVEL CLEAR!", FEB_FONT_6X10);
        feb_draw_string(28, 33, "PRESS ANY KEY", FEB_FONT_4X6);
    }
}

/* -------------------------------------------------------------------------
 * Player Movement & Box Pushing
 * ------------------------------------------------------------------------- */

static bool push_box(uint8_t cur_r, uint8_t cur_c, uint8_t nr, uint8_t nc) {
    uint8_t b_r = (nr << 1) - cur_r;
    uint8_t b_c = (nc << 1) - cur_c;
    if (b_r > 7 || b_c > 7) {
        return false;
    }

    uint8_t b_idx = (b_r << 3) + b_c;
    uint8_t b_cell = board[b_idx];
    if (b_cell != CELL_EMPTY && b_cell != CELL_TARGET) {
        return false;
    }

    if (b_cell == CELL_TARGET) {
        board[b_idx] = CELL_BOX_ON_TGT;
    } else {
        board[b_idx] = CELL_BOX;
    }

    uint8_t target_idx = (nr << 3) + nc;
    if (board[target_idx] == CELL_BOX_ON_TGT) {
        board[target_idx] = CELL_TARGET;
    } else {
        board[target_idx] = CELL_EMPTY;
    }

    pushes++;
    return true;
}

static void try_move(uint8_t dir) {
    uint8_t cur_r = player_r;
    uint8_t cur_c = player_c;
    uint8_t nr = cur_r;
    uint8_t nc = cur_c;

    if (dir == 0) {
        if (cur_r == 0) return;
        nr = cur_r - 1;
    } else if (dir == 1) {
        if (cur_r >= 7) return;
        nr = cur_r + 1;
    } else if (dir == 2) {
        if (cur_c == 0) return;
        nc = cur_c - 1;
    } else if (dir == 3) {
        if (cur_c >= 7) return;
        nc = cur_c + 1;
    }

    uint8_t new_idx = (nr << 3) + nc;
    uint8_t cell = board[new_idx];

    /* Immovable block */
    if (cell == CELL_WALL) {
        return;
    }

    /* Pushing a box */
    if (cell == CELL_BOX || cell == CELL_BOX_ON_TGT) {
        if (!push_box(cur_r, cur_c, nr, nc)) {
            return;
        }
    }

    /* Move player into new cell */
    if (board[new_idx] == CELL_TARGET) {
        board[new_idx] = CELL_PLAYER_ON_TGT;
    } else {
        board[new_idx] = CELL_PLAYER;
    }

    /* Clear player's previous cell */
    uint8_t old_idx = (cur_r << 3) + cur_c;
    if (board[old_idx] == CELL_PLAYER_ON_TGT) {
        board[old_idx] = CELL_TARGET;
    } else {
        board[old_idx] = CELL_EMPTY;
    }

    player_r = nr;
    player_c = nc;
    moves++;
}

/* -------------------------------------------------------------------------
 * Main Program Loop
 * ------------------------------------------------------------------------- */

int main(void) {
    feb_set_high_res(true);
    feb_set_draw_mode(FEB_DRAW_MODE_SET);

    /* Load persistent saved level from companion .sav */
    feb_load_flags(&saved_level, 1);
    if (saved_level > 9) {
        saved_level = 0;
    }
    current_level = saved_level;

    load_level(current_level);
    render_screen();

    uint8_t prev_keys = 0;
    uint8_t repeat_timer = 0;

    while (1) {
        uint8_t keys = feb_get_keys();
        uint8_t pressed = 0;

        if (keys != 0) {
            if (prev_keys == 0) {
                /* Initial button tap */
                pressed = keys;
                repeat_timer = 18; /* ~300ms initial repeat delay */
            } else {
                /* Button held down */
                if (repeat_timer > 0) {
                    repeat_timer--;
                } else {
                    pressed = keys;
                    repeat_timer = 6; /* ~100ms subsequent repeat interval */
                }
            }
        }
        prev_keys = keys;

        if (pressed != 0) {
            if (game_state == STATE_PLAYING) {
                /* Emergency restart chord: BACK + OK (LEFT + RIGHT) */
                if ((keys & FEB_BTN_LEFT) && (keys & FEB_BTN_RIGHT)) {
                    load_level(current_level);
                    render_screen();
                } else {
                    if (pressed & FEB_BTN_UP) {
                        try_move(0);
                    } else if (pressed & FEB_BTN_DOWN) {
                        try_move(1);
                    } else if (pressed & FEB_BTN_LEFT) {
                        try_move(2);
                    } else if (pressed & FEB_BTN_RIGHT) {
                        try_move(3);
                    }

                    render_screen();

                    if (check_win()) {
                        if (current_level >= 9) {
                            game_state = STATE_GAME_WON;
                        } else {
                            game_state = STATE_LEVEL_CLEAR;
                        }
                        draw_overlay();
                    }
                }
            } else if (game_state == STATE_LEVEL_CLEAR) {
                /* Advance to next level */
                current_level++;
                if (current_level > saved_level && current_level < 10) {
                    saved_level = current_level;
                    feb_save_flags(&saved_level, 1);
                }
                load_level(current_level);
                game_state = STATE_PLAYING;
                render_screen();
            } else if (game_state == STATE_GAME_WON) {
                /* Restart game from level 1 */
                current_level = 0;
                load_level(current_level);
                game_state = STATE_PLAYING;
                render_screen();
            }
        }

        feb_delay_frames(1);
    }

    return 0;
}
