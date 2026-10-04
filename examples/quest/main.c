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
        feb_wait_vsync();
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

/* __FEB_ASM__
;;; ===========================================================================
;;; Tiny Quest: Relic of the Dragon Lair
;;; CHIP-8 / Super-CHIP Assembly Implementation for Flashiibo Pro Gen3
;;; ===========================================================================

START:
        high                    ; Enable 128x64 high-resolution mode (Super-CHIP)
        cls                     ; Clear screen buffer
        call SHOW_TITLE_SCREEN
        call INIT_GAME_STATE

MAIN_LOOP:
        vsync                   ; 60 Hz frame synchronization (FX9A)
        cls                     ; Clear display buffer

        call DRAW_HUD
        call DRAW_ROOM
        call DRAW_ITEMS
        call DRAW_ENEMIES
        call DRAW_HERO

        ;; Check game ending conditions
        load i, STATE_RELIC
        restore v0
        skip.ne v0, 2           ; RELIC == 2: Victory!
        jump VICTORY_LOOP

        load i, STATE_HP
        restore v0
        skip.ne v0, 0           ; HP == 0: Game Over!
        jump GAME_OVER_LOOP

        ;; AI update
        call UPDATE_AI

        ;; 4-Button non-blocking D-Pad polling (FXB0)
        getkeys va
        skip.eq va, 0           ; Any button pressed?
        call HANDLE_INPUT

        jump MAIN_LOOP

;;; ---------------------------------------------------------------------------
;;; Input Handler (4 Physical Buttons)
;;; ---------------------------------------------------------------------------
HANDLE_INPUT:
        load v1, 1              ; Bit 0: UP (Key 2)
        and v1, va
        skip.eq v1, 0
        call MOVE_UP

        load v1, 2              ; Bit 1: DOWN (Key 8)
        and v1, va
        skip.eq v1, 0
        call MOVE_DOWN

        load v1, 4              ; Bit 2: LEFT / BACK (Key 4)
        and v1, va
        skip.eq v1, 0
        call MOVE_LEFT

        load v1, 8              ; Bit 3: RIGHT / OK (Key 6)
        and v1, va
        skip.eq v1, 0
        call MOVE_RIGHT

        ret

MOVE_UP:
        load v0, 1              ; DIR_UP := 1
        load i, STATE_DIR
        save v0

        load i, STATE_Y
        restore v0
        skip.ne v0, 21
        jump CHECK_UP_EXIT      ; Near top edge
        skip.ne v0, 17
        ret
        sub v0, 4
        load i, STATE_Y
        save v0
        call CHECK_BUMP_COLLISION
        ret

CHECK_UP_EXIT:
        load i, STATE_ROOM
        restore v1
        skip.ne v1, 0           ; Room 0: Enter Cave?
        jump ENTER_CAVE
        skip.ne v1, 3           ; Room 3: Exit Boss Lair to Ruins?
        jump EXIT_DUNGEON
        ret

ENTER_CAVE:
        load i, STATE_X
        restore v2
        skip.eq v2, 56          ; Col 7 (X=56)?
        ret
        load v1, 1              ; ROOM_CAVE := 1
        load i, STATE_ROOM
        save v1
        load v2, 56
        load i, STATE_X
        save v2
        load v3, 45
        load i, STATE_Y
        save v3
        ret

EXIT_DUNGEON:
        load i, STATE_X
        restore v2
        skip.eq v2, 64          ; Col 8 (X=64)?
        ret
        load v1, 2              ; ROOM_RUINS := 2
        load i, STATE_ROOM
        save v1
        load v2, 64
        load i, STATE_X
        save v2
        load v3, 45
        load i, STATE_Y
        save v3
        ret

MOVE_DOWN:
        load v0, 0              ; DIR_DOWN := 0
        load i, STATE_DIR
        save v0

        load i, STATE_Y
        restore v0
        skip.ne v0, 45
        jump CHECK_DOWN_EXIT
        skip.ne v0, 49
        ret
        add v0, 4
        load i, STATE_Y
        save v0
        call CHECK_BUMP_COLLISION
        ret

CHECK_DOWN_EXIT:
        load i, STATE_ROOM
        restore v1
        skip.ne v1, 1           ; Room 1: Exit Cave?
        jump EXIT_CAVE
        skip.ne v1, 2           ; Room 2: Enter Dungeon?
        jump ENTER_DUNGEON

        load i, STATE_Y
        restore v0
        add v0, 4
        load i, STATE_Y
        save v0
        ret

EXIT_CAVE:
        load i, STATE_X
        restore v2
        skip.eq v2, 56
        ret
        load v1, 0              ; ROOM_FOREST := 0
        load i, STATE_ROOM
        save v1
        load v2, 56
        load i, STATE_X
        save v2
        load v3, 21
        load i, STATE_Y
        save v3
        ret

ENTER_DUNGEON:
        load i, STATE_X
        restore v2
        skip.eq v2, 64
        ret
        ;; Check if door is unlocked (HERO_KEY == 1)
        load i, STATE_KEY
        restore v3
        skip.ne v3, 1
        jump DO_ENTER_DUNGEON
        ret
DO_ENTER_DUNGEON:
        load v1, 3              ; ROOM_DUNGEON := 3
        load i, STATE_ROOM
        save v1
        load v2, 64
        load i, STATE_X
        save v2
        load v3, 21
        load i, STATE_Y
        save v3
        ret

MOVE_LEFT:
        load v0, 3              ; DIR_LEFT := 3
        load i, STATE_DIR
        save v0

        load i, STATE_X
        restore v0
        skip.ne v0, 8
        jump CHECK_LEFT_EXIT
        skip.ne v0, 4
        ret
        sub v0, 4
        load i, STATE_X
        save v0
        call CHECK_BUMP_COLLISION
        ret

CHECK_LEFT_EXIT:
        load i, STATE_ROOM
        restore v1
        skip.ne v1, 2           ; Room 2: West exit to Room 0 (Forest)
        jump EXIT_TO_FOREST
        ret

EXIT_TO_FOREST:
        load v1, 0              ; Room 0
        load i, STATE_ROOM
        save v1
        load v0, 112
        load i, STATE_X
        save v0
        ret

MOVE_RIGHT:
        load v0, 2              ; DIR_RIGHT := 2
        load i, STATE_DIR
        save v0

        load i, STATE_X
        restore v0
        skip.ne v0, 112
        jump CHECK_RIGHT_EXIT
        skip.ne v0, 116
        ret
        add v0, 4
        load i, STATE_X
        save v0
        call CHECK_BUMP_COLLISION
        ret

CHECK_RIGHT_EXIT:
        load i, STATE_ROOM
        restore v1
        skip.ne v1, 0           ; Room 0: East exit to Room 2 (Ruins)
        jump EXIT_TO_RUINS
        ret

EXIT_TO_RUINS:
        load v1, 2              ; Room 2
        load i, STATE_ROOM
        save v1
        load v0, 8
        load i, STATE_X
        save v0
        ret

;;; ---------------------------------------------------------------------------
;;; Bump Combat & Interactions
;;; ---------------------------------------------------------------------------
CHECK_BUMP_COLLISION:
        ;; 1. Check Cave Altar / Sword
        load i, STATE_ROOM
        restore v5
        skip.ne v5, 1           ; Cave?
        jump CHECK_SWORD_PICKUP
        skip.ne v5, 0           ; Forest?
        jump CHECK_SLIME_BUMP
        skip.ne v5, 2           ; Ruins?
        jump CHECK_GOBLIN_BUMP
        skip.ne v5, 3           ; Dungeon?
        jump CHECK_BOSS_BUMP
        ret

CHECK_SWORD_PICKUP:
        load i, STATE_X
        restore v2
        load i, STATE_Y
        restore v3
        skip.ne v2, 56
        jump TEST_SWORD_Y
        ret
TEST_SWORD_Y:
        skip.ne v3, 29
        jump GET_SWORD
        ret
GET_SWORD:
        load v4, 1
        load i, STATE_SWORD
        save v4                 ; SWORD := 1!
        ret

CHECK_SLIME_BUMP:
        load i, STATE_SLIME_HP
        restore v6
        skip.ne v6, 0           ; Slime dead?
        ret
        load i, STATE_SLIME_X
        restore v7
        load i, STATE_X
        restore v2
        load v8, v7
        sub v8, v2
        skip.ne v8, 0
        jump SLIME_HIT
        skip.ne v8, 4
        jump SLIME_HIT
        skip.ne v8, 252
        jump SLIME_HIT
        ret
SLIME_HIT:
        load i, STATE_SWORD
        restore v4
        skip.ne v4, 1           ; Has sword?
        jump DO_SLIME_SLASH
        ;; No sword: Hero takes 1 damage
        load i, STATE_HP
        restore v9
        skip.ne v9, 0
        ret
        sub v9, 1
        load i, STATE_HP
        save v9
        ret
DO_SLIME_SLASH:
        load v6, 0              ; Slime defeated!
        load i, STATE_SLIME_HP
        save v6
        load i, STATE_GEMS
        restore vb
        add vb, 5               ; +5 Gems!
        load i, STATE_GEMS
        save vb
        ret

CHECK_GOBLIN_BUMP:
        load i, STATE_GOBLIN_HP
        restore v6
        skip.ne v6, 0           ; Goblin dead?
        ret
        load i, STATE_GOBLIN_X
        restore v7
        load i, STATE_X
        restore v2
        load v8, v7
        sub v8, v2
        skip.ne v8, 0
        jump GOBLIN_HIT
        skip.ne v8, 4
        jump GOBLIN_HIT
        skip.ne v8, 252
        jump GOBLIN_HIT
        ret
GOBLIN_HIT:
        load i, STATE_SWORD
        restore v4
        skip.ne v4, 1
        jump DO_GOBLIN_SLASH
        load i, STATE_HP
        restore v9
        skip.ne v9, 0
        ret
        sub v9, 1
        load i, STATE_HP
        save v9
        ret
DO_GOBLIN_SLASH:
        load i, STATE_GOBLIN_HP
        restore v6
        sub v6, 1
        load i, STATE_GOBLIN_HP
        save v6
        skip.eq v6, 0
        ret
        ;; Goblin defeated -> Drop Key!
        load v4, 1
        load i, STATE_KEY
        save v4                 ; KEY := 1!
        ret

CHECK_BOSS_BUMP:
        load i, STATE_BOSS_HP
        restore v6
        skip.eq v6, 0
        jump TEST_BOSS_HIT
        ;; Boss dead: Check Relic pickup at (56, 29)
        load i, STATE_X
        restore v2
        skip.ne v2, 56
        jump TEST_RELIC_Y
        ret
TEST_RELIC_Y:
        load i, STATE_Y
        restore v3
        skip.ne v3, 29
        jump GET_RELIC
        ret
GET_RELIC:
        load v4, 2              ; WON!
        load i, STATE_RELIC
        save v4
        ret

TEST_BOSS_HIT:
        load i, STATE_BOSS_X
        restore v7
        load i, STATE_X
        restore v2
        load v8, v7
        sub v8, v2
        skip.ne v8, 0
        jump BOSS_HIT
        skip.ne v8, 4
        jump BOSS_HIT
        skip.ne v8, 8
        jump BOSS_HIT
        skip.ne v8, 252
        jump BOSS_HIT
        ret
BOSS_HIT:
        load i, STATE_SWORD
        restore v4
        skip.ne v4, 1
        jump DO_BOSS_SLASH
        load i, STATE_HP
        restore v9
        skip.ne v9, 0
        ret
        sub v9, 1
        load i, STATE_HP
        save v9
        ret
DO_BOSS_SLASH:
        load i, STATE_BOSS_HP
        restore v6
        sub v6, 1
        load i, STATE_BOSS_HP
        save v6
        skip.eq v6, 0
        ret
        ;; Boss defeated! Spawn Sacred Relic
        load v4, 1
        load i, STATE_RELIC
        save v4
        ret

;;; ---------------------------------------------------------------------------
;;; Enemy AI Updates
;;; ---------------------------------------------------------------------------
UPDATE_AI:
        load i, STATE_AI_TIMER
        restore v0
        add v0, 1
        load i, STATE_AI_TIMER
        save v0
        skip.ne v0, 20
        jump DO_AI_STEP
        ret
DO_AI_STEP:
        load v0, 0
        load i, STATE_AI_TIMER
        save v0                 ; Timer := 0

        ;; Move Slime back and forth
        load i, STATE_SLIME_X
        restore v1
        skip.ne v1, 80
        jump SET_SLIME_LEFT
        load v1, 80
        load i, STATE_SLIME_X
        save v1
        jump UPDATE_BOSS_AI
SET_SLIME_LEFT:
        load v1, 72
        load i, STATE_SLIME_X
        save v1

UPDATE_BOSS_AI:
        load i, STATE_BOSS_Y
        restore v2
        skip.ne v2, 29
        jump SET_BOSS_DOWN
        load v2, 29
        load i, STATE_BOSS_Y
        save v2
        ret
SET_BOSS_DOWN:
        load v2, 37
        load i, STATE_BOSS_Y
        save v2
        ret

;;; ---------------------------------------------------------------------------
;;; Drawing Subroutines
;;; ---------------------------------------------------------------------------

DRAW_HUD:
        ;; Top divider line at Y=11
        load v0, 0
        load v1, 11
        load v2, 127
        hline v0

        ;; Area Name
        load i, STATE_ROOM
        restore v3
        skip.ne v3, 0
        load i, STR_AREA_OVERWORLD
        skip.ne v3, 1
        load i, STR_AREA_CAVE
        skip.ne v3, 2
        load i, STR_AREA_TEMPLE
        skip.ne v3, 3
        load i, STR_AREA_DUNGEON
        load v0, 2
        load v1, 2
        load v2, 0              ; FEB_FONT_4X6
        text v0

        ;; Hearts
        load i, STATE_HP
        restore v4
        load i, SPRITE_HEART
        skip.eq v4, 0
        call DRAW_HEART_1
        skip.eq v4, 0
        jump TEST_H2
        ret
TEST_H2:
        skip.eq v4, 1
        call DRAW_HEART_2
        skip.eq v4, 1
        jump TEST_H3
        ret
TEST_H3:
        skip.eq v4, 2
        call DRAW_HEART_3

        ;; Gem Icon & Count
        load i, SPRITE_GEM
        load vb, 86
        load vc, 2
        draw vb, vc, 8

        load i, STATE_GEMS
        restore v5
        load i, 0
        add i, v5
        load v0, 96
        load v1, 2
        load v2, 0
        num v0

        ;; Key Icon
        load i, STATE_KEY
        restore v6
        skip.ne v6, 1
        jump DRAW_KEY_ICON
        ret
DRAW_KEY_ICON:
        load i, SPRITE_KEY
        load vb, 116
        load vc, 2
        draw vb, vc, 8
        ret

DRAW_HEART_1:
        load vb, 50
        load vc, 2
        draw vb, vc, 8
        ret
DRAW_HEART_2:
        load vb, 60
        load vc, 2
        draw vb, vc, 8
        ret
DRAW_HEART_3:
        load vb, 70
        load vc, 2
        draw vb, vc, 8
        ret

DRAW_ROOM:
        load i, STATE_ROOM
        restore v0
        skip.ne v0, 0
        jump DRAW_ROOM_0
        skip.ne v0, 1
        jump DRAW_ROOM_1
        skip.ne v0, 2
        jump DRAW_ROOM_2
        skip.ne v0, 3
        jump DRAW_ROOM_3
        ret

DRAW_ROOM_0:
        ;; Overworld Forest: Trees along top and bottom
        load i, SPRITE_TREE
        load vb, 0
        load vc, 13
        draw vb, vc, 8
        load vb, 16
        draw vb, vc, 8
        load vb, 32
        draw vb, vc, 8
        load vb, 48
        draw vb, vc, 8
        load vb, 64
        draw vb, vc, 8
        load vb, 80
        draw vb, vc, 8
        load vb, 96
        draw vb, vc, 8
        load vb, 112
        draw vb, vc, 8

        ;; Bottom row
        load vc, 53
        load vb, 0
        draw vb, vc, 8
        load vb, 16
        draw vb, vc, 8
        load vb, 32
        draw vb, vc, 8
        load vb, 48
        draw vb, vc, 8
        load vb, 64
        draw vb, vc, 8
        load vb, 80
        draw vb, vc, 8
        load vb, 96
        draw vb, vc, 8
        load vb, 112
        draw vb, vc, 8

        ;; Cave Entrance at (56, 13)
        load i, SPRITE_CAVE
        load vb, 56
        load vc, 13
        draw vb, vc, 8
        ret

DRAW_ROOM_1:
        ;; Cave Walls & Torches
        load i, SPRITE_WALL
        load vb, 0
        load vc, 13
        draw vb, vc, 8
        load vb, 120
        draw vb, vc, 8

        load i, SPRITE_TORCH
        load vb, 32
        load vc, 21
        draw vb, vc, 8
        load vb, 80
        draw vb, vc, 8

        ;; Hermit Sage at (56, 21)
        load i, SPRITE_SAGE
        load vb, 56
        draw vb, vc, 8

        ;; Dialogue text
        load i, STR_SAGE1
        load v0, 14
        load v1, 37
        load v2, 0
        text v0
        load i, STR_SAGE2
        load v0, 26
        load v1, 45
        load v2, 0
        text v0
        ret

DRAW_ROOM_2:
        ;; Ruins: Ancient Columns and Dungeon Gate
        load i, SPRITE_WALL
        load vb, 0
        load vc, 13
        draw vb, vc, 8
        load vb, 32
        draw vb, vc, 8
        load vb, 64
        draw vb, vc, 8
        load vb, 96
        draw vb, vc, 8
        load vb, 120
        draw vb, vc, 8

        ;; Dungeon Door at (64, 53)
        load i, SPRITE_DOOR
        load vb, 64
        load vc, 53
        draw vb, vc, 8
        ret

DRAW_ROOM_3:
        ;; Boss Lair: Perimeter Walls
        load i, SPRITE_WALL
        load vb, 0
        load vc, 13
        draw vb, vc, 8
        load vb, 120
        draw vb, vc, 8
        load vb, 0
        load vc, 53
        draw vb, vc, 8
        load vb, 120
        draw vb, vc, 8
        ret

DRAW_ITEMS:
        load i, STATE_ROOM
        restore v0
        skip.ne v0, 1
        jump DRAW_CAVE_SWORD
        skip.ne v0, 3
        jump DRAW_DUNGEON_RELIC
        ret

DRAW_CAVE_SWORD:
        load i, STATE_SWORD
        restore v1
        skip.eq v1, 0           ; Sword already collected?
        ret
        load i, SPRITE_SWORD
        load vb, 56
        load vc, 29
        draw vb, vc, 8
        ret

DRAW_DUNGEON_RELIC:
        load i, STATE_BOSS_HP
        restore v2
        skip.eq v2, 0           ; Boss defeated?
        ret
        load i, SPRITE_RELIC
        load vb, 56
        load vc, 29
        draw vb, vc, 8
        ret

DRAW_ENEMIES:
        load i, STATE_ROOM
        restore v0
        skip.ne v0, 0
        jump DRAW_SLIME
        skip.ne v0, 2
        jump DRAW_GOBLIN
        skip.ne v0, 3
        jump DRAW_BOSS
        ret

DRAW_SLIME:
        load i, STATE_SLIME_HP
        restore v1
        skip.ne v1, 0
        ret
        load i, STATE_SLIME_X
        restore vb
        load i, STATE_SLIME_Y
        restore vc
        load i, SPRITE_SLIME
        draw vb, vc, 8
        ret

DRAW_GOBLIN:
        load i, STATE_GOBLIN_HP
        restore v1
        skip.ne v1, 0
        ret
        load i, STATE_GOBLIN_X
        restore vb
        load i, STATE_GOBLIN_Y
        restore vc
        load i, SPRITE_GOBLIN
        draw vb, vc, 8
        ret

DRAW_BOSS:
        load i, STATE_BOSS_HP
        restore v1
        skip.ne v1, 0
        ret
        load i, STATE_BOSS_X
        restore vb
        load i, STATE_BOSS_Y
        restore vc
        load i, SPRITE_BOSS
        draw vb, vc, 0          ; 16x16 sprite!
        ret

DRAW_HERO:
        load i, STATE_X
        restore vb
        load i, STATE_Y
        restore vc

        load i, STATE_DIR
        restore v0
        skip.ne v0, 0
        load i, SPRITE_HERO_DOWN
        skip.ne v0, 1
        load i, SPRITE_HERO_UP
        skip.ne v0, 2
        load i, SPRITE_HERO_RIGHT
        skip.ne v0, 3
        load i, SPRITE_HERO_LEFT

        draw vb, vc, 8
        ret

;;; ---------------------------------------------------------------------------
;;; Endings & Screens
;;; ---------------------------------------------------------------------------

SHOW_TITLE_SCREEN:
        load v0, 0
        load v1, 0
        load v2, 127
        load v3, 63
        rect v0

        load i, STR_TITLE1
        load v0, 18
        load v1, 8
        load v2, 0
        text v0

        load i, STR_TITLE2
        load v0, 32
        load v1, 16
        load v2, 1
        text v0

        load i, SPRITE_RELIC
        load vb, 60
        load vc, 28
        draw vb, vc, 8

        load i, STR_INSTR1
        load v0, 10
        load v1, 40
        load v2, 0
        text v0

        load i, STR_INSTR2
        load v0, 14
        load v1, 48
        load v2, 0
        text v0

        load i, STR_INSTR3
        load v0, 16
        load v1, 56
        load v2, 0
        text v0

        load va, key            ; Wait for any key
        ret

VICTORY_LOOP:
        cls
        load v0, 0
        load v1, 0
        load v2, 127
        load v3, 63
        rect v0

        load i, SPRITE_RELIC
        load vb, 60
        load vc, 6
        draw vb, vc, 8

        load i, STR_WIN1
        load v0, 12
        load v1, 18
        load v2, 1
        text v0

        load i, STR_WIN2
        load v0, 22
        load v1, 30
        load v2, 1
        text v0

        load i, STR_WIN3
        load v0, 26
        load v1, 42
        load v2, 0
        text v0

        load i, STATE_GEMS
        restore v5
        load i, 0
        add i, v5
        load v0, 88
        load v1, 42
        load v2, 0
        num v0

        load i, STR_RETRY
        load v0, 18
        load v1, 52
        load v2, 0
        text v0

        ;; Persist victory flags to /feb/saves/quest.sav
        load i, STATE_GEMS
        restore v0
        saveflags v0

        load va, key
        call INIT_GAME_STATE
        jump MAIN_LOOP

GAME_OVER_LOOP:
        cls
        load v0, 0
        load v1, 0
        load v2, 127
        load v3, 63
        rect v0

        load i, STR_LOSE1
        load v0, 36
        load v1, 20
        load v2, 1
        text v0

        load i, STR_LOSE2
        load v0, 16
        load v1, 36
        load v2, 0
        text v0

        load i, STR_RETRY
        load v0, 18
        load v1, 48
        load v2, 0
        text v0

        load va, key
        call INIT_GAME_STATE
        jump MAIN_LOOP

INIT_GAME_STATE:
        load v0, 24             ; X := 24
        load i, STATE_X
        save v0

        load v0, 37             ; Y := 37
        load i, STATE_Y
        save v0

        load v0, 0              ; DIR := 0
        load i, STATE_DIR
        save v0

        load v0, 3              ; HP := 3
        load i, STATE_HP
        save v0

        load v0, 0              ; SWORD := 0
        load i, STATE_SWORD
        save v0

        load v0, 0              ; KEY := 0
        load i, STATE_KEY
        save v0

        load v0, 0              ; GEMS := 0
        load i, STATE_GEMS
        save v0

        load v0, 0              ; ROOM := 0
        load i, STATE_ROOM
        save v0

        load v0, 80             ; SLIME_X
        load i, STATE_SLIME_X
        save v0

        load v0, 37             ; SLIME_Y
        load i, STATE_SLIME_Y
        save v0

        load v0, 1              ; SLIME_HP
        load i, STATE_SLIME_HP
        save v0

        load v0, 72             ; GOBLIN_X
        load i, STATE_GOBLIN_X
        save v0

        load v0, 29             ; GOBLIN_Y
        load i, STATE_GOBLIN_Y
        save v0

        load v0, 2              ; GOBLIN_HP
        load i, STATE_GOBLIN_HP
        save v0

        load v0, 80             ; BOSS_X
        load i, STATE_BOSS_X
        save v0

        load v0, 29             ; BOSS_Y
        load i, STATE_BOSS_Y
        save v0

        load v0, 4              ; BOSS_HP
        load i, STATE_BOSS_HP
        save v0

        load v0, 0
        load i, STATE_RELIC
        save v0

        load v0, 0
        load i, STATE_AI_TIMER
        save v0
        ret

;;; ---------------------------------------------------------------------------
;;; Variables in RAM
;;; ---------------------------------------------------------------------------
STATE_X:          .byte 24
STATE_Y:          .byte 37
STATE_DIR:        .byte 0
STATE_HP:         .byte 3
STATE_SWORD:      .byte 0
STATE_KEY:        .byte 0
STATE_GEMS:       .byte 0
STATE_ROOM:       .byte 0
STATE_SLIME_X:    .byte 80
STATE_SLIME_Y:    .byte 37
STATE_SLIME_HP:   .byte 1
STATE_GOBLIN_X:   .byte 72
STATE_GOBLIN_Y:   .byte 29
STATE_GOBLIN_HP:  .byte 2
STATE_BOSS_X:     .byte 80
STATE_BOSS_Y:     .byte 29
STATE_BOSS_HP:    .byte 4
STATE_RELIC:      .byte 0
STATE_AI_TIMER:   .byte 0

;;; ---------------------------------------------------------------------------
;;; Text Strings
;;; ---------------------------------------------------------------------------
STR_TITLE1:         .asciz "THE CHRONICLES OF"
STR_TITLE2:         .asciz "TINY QUEST"
STR_INSTR1:         .asciz "D-PAD: MOVE & BUMP-ATTACK"
STR_INSTR2:         .asciz "UP+DOWN+BACK: EXIT GAME"
STR_INSTR3:         .asciz "PRESS ANY KEY TO START"

STR_AREA_OVERWORLD: .asciz "FOREST"
STR_AREA_CAVE:      .asciz "SAGE CAVE"
STR_AREA_TEMPLE:    .asciz "RUINS"
STR_AREA_DUNGEON:   .asciz "DRAGON LAIR"

STR_SAGE1:          .asciz "THE ROAD IS DANGEROUS!"
STR_SAGE2:          .asciz "TAKE THIS SWORD."

STR_WIN1:           .asciz "SACRED RELIC RESTORED!"
STR_WIN2:           .asciz "THE REALM IS SAVED!"
STR_WIN3:           .asciz "GEMS COLLECTED:"
STR_LOSE1:          .asciz "GAME OVER"
STR_LOSE2:          .asciz "FALLEN IN THE DUNGEON"
STR_RETRY:          .asciz "PRESS ANY KEY TO RETRY"

;;; ---------------------------------------------------------------------------
;;; Sprite Bitmaps
;;; ---------------------------------------------------------------------------
SPRITE_HERO_DOWN:
        .byte $00111100
        .byte $01111110
        .byte $01011010
        .byte $01111110
        .byte $01111110
        .byte $00111100
        .byte $00100100
        .byte $00100100

SPRITE_HERO_UP:
        .byte $00111100
        .byte $01111110
        .byte $01111110
        .byte $01111110
        .byte $00111100
        .byte $00111100
        .byte $00100100
        .byte $00100100

SPRITE_HERO_RIGHT:
        .byte $00111100
        .byte $00111110
        .byte $00110110
        .byte $00111101
        .byte $00111111
        .byte $00111100
        .byte $00101000
        .byte $00101000

SPRITE_HERO_LEFT:
        .byte $00111100
        .byte $01111100
        .byte $01101100
        .byte $10111100
        .byte $11111100
        .byte $00111100
        .byte $00010100
        .byte $00010100

SPRITE_TREE:
        .byte $00111100
        .byte $01111110
        .byte $11011011
        .byte $11111111
        .byte $11111111
        .byte $01111110
        .byte $00011000
        .byte $00011000

SPRITE_WALL:
        .byte $01111110
        .byte $10000001
        .byte $10111101
        .byte $10100101
        .byte $10100101
        .byte $10111101
        .byte $10000001
        .byte $01111110

SPRITE_CAVE:
        .byte $11111111
        .byte $10000001
        .byte $10000001
        .byte $10000001
        .byte $10000001
        .byte $10000001
        .byte $10000001
        .byte $11111111

SPRITE_DOOR:
        .byte $11111111
        .byte $10111101
        .byte $10111101
        .byte $10011001
        .byte $10011001
        .byte $10111101
        .byte $10111101
        .byte $11111111

SPRITE_SAGE:
        .byte $00111100
        .byte $01111110
        .byte $01011010
        .byte $01111110
        .byte $00111100
        .byte $01111110
        .byte $01111110
        .byte $00111100

SPRITE_TORCH:
        .byte $00010000
        .byte $00110000
        .byte $01111000
        .byte $01111100
        .byte $01111000
        .byte $00110000
        .byte $00110000
        .byte $01111000

SPRITE_SWORD:
        .byte $00000010
        .byte $00000110
        .byte $00001100
        .byte $00011000
        .byte $01110000
        .byte $11000000
        .byte $01000000
        .byte $00000000

SPRITE_RELIC:
        .byte $01111110
        .byte $01000010
        .byte $00111100
        .byte $00011000
        .byte $00011000
        .byte $00111100
        .byte $01111110
        .byte $00000000

SPRITE_HEART:
        .byte $01101100
        .byte $11111110
        .byte $11111110
        .byte $11111110
        .byte $01111100
        .byte $00111000
        .byte $00010000
        .byte $00000000

SPRITE_GEM:
        .byte $00010000
        .byte $00111000
        .byte $01111100
        .byte $11111110
        .byte $11111110
        .byte $01111100
        .byte $00111000
        .byte $00010000

SPRITE_KEY:
        .byte $00111000
        .byte $01000100
        .byte $00111000
        .byte $00010000
        .byte $00011000
        .byte $00010000
        .byte $00011000
        .byte $00000000

SPRITE_SLIME:
        .byte $00000000
        .byte $00111100
        .byte $01111110
        .byte $11011011
        .byte $11111111
        .byte $11111111
        .byte $01111110
        .byte $00000000

SPRITE_GOBLIN:
        .byte $01100110
        .byte $01111110
        .byte $11011011
        .byte $11111111
        .byte $01111110
        .byte $00111100
        .byte $01000010
        .byte $11000011

;;; 16x16 Super-CHIP Dragon Boss Sprite (32 bytes)
SPRITE_BOSS:
        .byte 0x03, 0xC0
        .byte 0x07, 0xE0
        .byte 0x0E, 0x70
        .byte 0x1C, 0x38
        .byte 0x39, 0x9C
        .byte 0x73, 0xCE
        .byte 0x7F, 0xFE
        .byte 0x7E, 0x7E
        .byte 0x7C, 0x3E
        .byte 0x78, 0x1E
        .byte 0x7F, 0xFE
        .byte 0x3F, 0xFC
        .byte 0x1F, 0xF8
        .byte 0x0E, 0x70
        .byte 0x1C, 0x38
        .byte 0x38, 0x1C
__FEB_ASM_END__ */
