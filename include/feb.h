#ifndef FEB_H
#define FEB_H

/**
 * @file feb.h
 * @brief Flashiibo Executable Binary (.feb) C Application Development Kit (SDK)
 *
 * [BETA / EXPERIMENTAL]
 * This SDK, API, and runtime contract are in active development.
 * Breaking changes might happen without warning.
 *
 * Flashiibo Pro Gen3 executes .feb binaries inside a sandboxed virtual machine
 * via the FEB Runner applet (requires firmware >= 26.10.4). It provides a 60 Hz
 * timer tick, 128x64 default (or 64x32 legacy) display buffer, and deterministic
 * 4-button physical navigation mapping.
 */

#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

/* -------------------------------------------------------------------------
 * Flashiibo Pro Gen3 Deterministic 4-Button Hardware Mappings
 * -------------------------------------------------------------------------
 * Flashiibo hardware features 4 physical buttons mapped to fixed virtual keys:
 *   - UP:      Key 0x2
 *   - DOWN:    Key 0x8
 *   - BACK:    Key 0x4  (Acts as Left in games/apps)
 *   - OK:      Key 0x6  (Acts as Right in games/apps)
 * NOTE: Pressing UP and DOWN together guarantees immediate game exit back to
 * the "FEB Runner" menu. Long press on BACK is not an exit key and is fully
 * available for normal gameplay controls.
 */
#define FEB_KEY_UP        0x2
#define FEB_KEY_DOWN      0x8
#define FEB_KEY_LEFT      0x4   /* Physical BACK button */
#define FEB_KEY_RIGHT     0x6   /* Physical OK button */

/* Aliases for semantic clarity */
#define FEB_KEY_BACK      FEB_KEY_LEFT
#define FEB_KEY_OK        FEB_KEY_RIGHT
#define FEB_KEY_CONFIRM   FEB_KEY_OK   /* Legacy alias */

/* -------------------------------------------------------------------------
 * Display Dimensions
 * -------------------------------------------------------------------------
 * Default display resolution for FEB applications is 128x64 (Super-CHIP mode).
 * Legacy 64x32 mode is available when explicitly requested.
 */
#define FEB_SCREEN_WIDTH       128
#define FEB_SCREEN_HEIGHT       64
#define FEB_SCHIP_WIDTH        128
#define FEB_SCHIP_HEIGHT        64
#define FEB_LOWRES_WIDTH        64
#define FEB_LOWRES_HEIGHT       32

/* Built-in hex font glyph height (characters '0'-'F') */
#define FEB_FONT_DIGIT_HEIGHT    5

/* -------------------------------------------------------------------------
 * Core SDK API Declarations
 * ------------------------------------------------------------------------- */

/**
 * @brief Enables or disables high-resolution (128x64) Super-CHIP display mode.
 *
 * @param enable true for 128x64 mode (opcode 0x00FF), false for 64x32 mode (opcode 0x00FE).
 */
void feb_set_high_res(bool enable);

/**
 * @brief Clears the entire display screen buffer (sets all pixels to 0).
 */
void feb_clear_screen(void);

/**
 * @brief Draws or toggles (XOR) an 8-pixel wide sprite of specified height at (x, y).
 *
 * @param x Horizontal pixel position (0..127 in 128x64 mode, 0..63 in 64x32 mode)
 * @param y Vertical pixel position (0..63 in 128x64 mode, 0..31 in 64x32 mode)
 * @param sprite Pointer to sprite bitmap data (each byte is 1 row of 8 pixels)
 * @param height Height of sprite in rows (1..15)
 * @return true if any set pixel collided with an already-set pixel (VF flag)
 */
bool feb_draw_sprite(uint8_t x, uint8_t y, const uint8_t *sprite, uint8_t height);

/**
 * @brief Draws or toggles (XOR) a 16x16 pixel sprite at (x, y) in Super-CHIP mode.
 *
 * @param x Horizontal pixel position (0..127)
 * @param y Vertical pixel position (0..63)
 * @param sprite Pointer to 32 bytes of sprite bitmap data (2 bytes per row, 16 rows)
 * @return true if collision detected (VF flag)
 */
bool feb_draw_sprite16(uint8_t x, uint8_t y, const uint8_t *sprite);

/**
 * @brief Draws built-in single-digit hex glyph (0x0 to 0xF, 5 rows high).
 *
 * @param x Horizontal pixel position
 * @param y Vertical pixel position
 * @param digit Digit value (0..15)
 */
void feb_draw_digit(uint8_t x, uint8_t y, uint8_t digit);

/**
 * @brief Waits synchronously for a physical key press and returns the key code.
 *
 * On Flashiibo Gen3, returns FEB_KEY_UP (0x2), FEB_KEY_DOWN (0x8),
 * FEB_KEY_LEFT (0x4), or FEB_KEY_RIGHT (0x6).
 *
 * @return Key code of pressed button
 */
uint8_t feb_wait_key(void);

/**
 * @brief Checks if a specific key is currently held down.
 *
 * @param key Key code to test (e.g. FEB_KEY_UP)
 * @return true if the key is pressed, false otherwise
 */
bool feb_is_key_down(uint8_t key);

/**
 * @brief Generates a pseudo-random 8-bit integer masked with @p mask.
 *
 * @param mask Bitwise AND mask (e.g. 0x07 for 0..7, 0x0F for 0..15)
 * @return (rand() & mask)
 */
uint8_t feb_rand(uint8_t mask);

/**
 * @brief Sets the 60 Hz delay timer countdown register.
 *
 * @param val Value in 60 Hz ticks
 */
void feb_set_delay_timer(uint8_t val);

/**
 * @brief Reads the current value of the 60 Hz delay timer register.
 *
 * @return Value in 60 Hz ticks
 */
uint8_t feb_get_delay_timer(void);

/**
 * @brief Sleeps for the specified number of frames (~16.6 ms per frame @ 60 Hz).
 *
 * @param frames Number of frames to wait
 */
void feb_delay_frames(uint8_t frames);

/* -------------------------------------------------------------------------
 * Persistent Storage API (Sidecar .sav in /feb/saves/)
 * ------------------------------------------------------------------------- */

/**
 * @brief Saves up to 16 bytes of persistent application state (mapped to Super-CHIP RPL flags FX75).
 * Automatically flushed to /feb/saves/<app_name>.sav on application exit.
 *
 * @param data Pointer to buffer of bytes to persist (up to 16 bytes)
 * @param len Number of bytes to save (1..16)
 */
void feb_save_flags(const uint8_t *data, uint8_t len);

/**
 * @brief Loads up to 16 bytes of persistent application state (mapped to Super-CHIP RPL flags FX85).
 * Reads from /feb/saves/<app_name>.sav.
 *
 * @param data Destination buffer to receive persistent bytes (up to 16 bytes)
 * @param len Number of bytes to load (1..16)
 */
void feb_load_flags(uint8_t *data, uint8_t len);

#ifdef __cplusplus
}
#endif

#endif /* FEB_H */
