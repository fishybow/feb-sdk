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

/* -------------------------------------------------------------------------
 * Hardware Button Bitmask (for feb_get_keys() / FXB0 GETKEYS)
 * -------------------------------------------------------------------------
 * Instantaneous 4-button polling bitmask.
 */
#define FEB_BTN_UP        (1 << 0)  /* Bit 0: UP button pressed */
#define FEB_BTN_DOWN      (1 << 1)  /* Bit 1: DOWN button pressed */
#define FEB_BTN_LEFT      (1 << 2)  /* Bit 2: BACK / Left button pressed */
#define FEB_BTN_RIGHT     (1 << 3)  /* Bit 3: OK / Right button pressed */

#define FEB_BTN_BACK      FEB_BTN_LEFT
#define FEB_BTN_OK        FEB_BTN_RIGHT

/* -------------------------------------------------------------------------
 * FEB Header Runtime Flags
 * -------------------------------------------------------------------------
 */
#define FEB_FLAG_NONE                 0x0000
#define FEB_FLAG_REQUIRE_BACK_BUTTON  0x0001 /* Requires physical BACK button (4-button layout) */

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
 * Built-in Typography Fonts (for feb_draw_string, feb_draw_char, etc.)
 * ------------------------------------------------------------------------- */
#define FEB_FONT_4X6         0   /* 4x6 tiny numeric & compact font (u8g2_font_4x6_tr) */
#define FEB_FONT_6X10        1   /* 6x10 standard UI font (u8g2_font_siji_t_6x10) */
#define FEB_FONT_RETRO_8X8   2   /* 8x8 blocky retro arcade font (u8g2_font_likeminecraft_te) */

/* -------------------------------------------------------------------------
 * Extended Drawing Modes (for feb_set_draw_mode / FX98 DRAWMODE)
 * ------------------------------------------------------------------------- */
#define FEB_DRAW_MODE_XOR             0   /* Invert pixels (standard CHIP-8) */
#define FEB_DRAW_MODE_SET             1   /* Solid write (turn pixels ON) */
#define FEB_DRAW_MODE_CLEAR           2   /* Eraser (turn pixels OFF) */
#define FEB_DRAW_MODE_OPAQUE          3   /* Set pixels ON with solid black background box */
#define FEB_DRAW_MODE_INVERTED_OPAQUE 4   /* Clear pixels OFF with solid white background box */

/* -------------------------------------------------------------------------
 * Core SDK API Declarations
 * ------------------------------------------------------------------------- */

/* -------------------------------------------------------------------------
 * Screen Rotation Modes (for feb_set_rotation / FX9A ROTATE)
 * ------------------------------------------------------------------------- */
#define FEB_ROTATION_0        0   /* 0 degrees - Normal Landscape (128x64 default) */
#define FEB_ROTATION_90       1   /* 90 degrees CW - Portrait (64x128, buttons right) */
#define FEB_ROTATION_180      2   /* 180 degrees - Inverted Landscape (128x64) */
#define FEB_ROTATION_270      3   /* 270 degrees CW - Inverted Portrait (64x128, buttons left) */

/**
 * @brief Sets the screen rotation transformation mode for display output.
 *
 * In 90 degree portrait mode (FEB_ROTATION_90), the virtual screen resolution is
 * 64 wide x 128 high, mapped to the physical OLED with buttons on the right.
 *
 * @param rotation FEB_ROTATION_0, FEB_ROTATION_90, FEB_ROTATION_180, or FEB_ROTATION_270
 */
void feb_set_rotation(uint8_t rotation);

/**
 * @brief Enables or disables high-resolution (128x64) Super-CHIP display mode.
 *
 * @param enable true for 128x64 mode (opcode 0x00FF), false for 64x32 mode (opcode 0x00FE).
 */
void feb_set_high_res(bool enable);

/**
 * @brief Immediately terminates the FEB application and returns to the FEB Runner menu.
 *
 * Emits Super-CHIP exit opcode 0x00FD.
 */
void feb_exit(void);

#define feb_quit() feb_exit()

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

/* -------------------------------------------------------------------------
 * Drawing Modes & Geometry Primitives
 * ------------------------------------------------------------------------- */

/**
 * @brief Sets the active drawing mode for all subsequent graphics operations.
 *
 * @param mode Drawing mode (FEB_DRAW_MODE_XOR, SET, CLEAR, OPAQUE, or INVERTED_OPAQUE)
 */
void feb_set_draw_mode(uint8_t mode);

/**
 * @brief Plots a single pixel at (x, y) using the active draw mode.
 *
 * @param x Horizontal coordinate (0..127)
 * @param y Vertical coordinate (0..63)
 */
void feb_draw_pixel(uint8_t x, uint8_t y);

/**
 * @brief Draws an arbitrary line between (x0, y0) and (x1, y1) using Bresenham's algorithm.
 *
 * @param x0 Starting horizontal coordinate
 * @param y0 Starting vertical coordinate
 * @param x1 Ending horizontal coordinate
 * @param y1 Ending vertical coordinate
 */
void feb_draw_line(uint8_t x0, uint8_t y0, uint8_t x1, uint8_t y1);

/**
 * @brief Draws a fast horizontal line starting at (x, y) of length @p len.
 *
 * @param x Starting horizontal coordinate
 * @param y Vertical coordinate
 * @param len Length in pixels
 */
void feb_draw_hline(uint8_t x, uint8_t y, uint8_t len);

/**
 * @brief Draws a fast vertical line starting at (x, y) of height @p len.
 *
 * @param x Horizontal coordinate
 * @param y Starting vertical coordinate
 * @param len Height in pixels
 */
void feb_draw_vline(uint8_t x, uint8_t y, uint8_t len);

/**
 * @brief Draws an unfilled outline rectangle at (x, y) with width @p w and height @p h.
 *
 * @param x Top-left horizontal coordinate
 * @param y Top-left vertical coordinate
 * @param w Width in pixels
 * @param h Height in pixels
 */
void feb_draw_rect(uint8_t x, uint8_t y, uint8_t w, uint8_t h);

/**
 * @brief Draws a filled solid rectangle at (x, y) with width @p w and height @p h.
 *
 * @param x Top-left horizontal coordinate
 * @param y Top-left vertical coordinate
 * @param w Width in pixels
 * @param h Height in pixels
 */
void feb_fill_rect(uint8_t x, uint8_t y, uint8_t w, uint8_t h);

/**
 * @brief Draws an unfilled outline triangle connecting 3 vertices using Bresenham's algorithm.
 *
 * @param x0 First vertex horizontal coordinate
 * @param y0 First vertex vertical coordinate
 * @param x1 Second vertex horizontal coordinate
 * @param y1 Second vertex vertical coordinate
 * @param x2 Third vertex horizontal coordinate
 * @param y2 Third vertex vertical coordinate
 */
void feb_draw_triangle(uint8_t x0, uint8_t y0, uint8_t x1, uint8_t y1, uint8_t x2, uint8_t y2);

/**
 * @brief Draws an unfilled outline rounded rectangle with 1px corner radius.
 *
 * @param x Top-left horizontal coordinate
 * @param y Top-left vertical coordinate
 * @param w Width in pixels
 * @param h Height in pixels
 */
void feb_draw_rrect(uint8_t x, uint8_t y, uint8_t w, uint8_t h);

/**
 * @brief Draws a filled solid rounded rectangle with 1px corner radius.
 *
 * @param x Top-left horizontal coordinate
 * @param y Top-left vertical coordinate
 * @param w Width in pixels
 * @param h Height in pixels
 */
void feb_fill_rrect(uint8_t x, uint8_t y, uint8_t w, uint8_t h);

/**
 * @brief Draws an unfilled outline circle centered at (x, y) with radius @p r.
 *
 * @param x Center horizontal coordinate
 * @param y Center vertical coordinate
 * @param r Radius in pixels
 */
void feb_draw_circle(uint8_t x, uint8_t y, uint8_t r);

/**
 * @brief Draws a filled solid circle centered at (x, y) with radius @p r.
 *
 * @param x Center horizontal coordinate
 * @param y Center vertical coordinate
 * @param r Radius in pixels
 */
void feb_fill_circle(uint8_t x, uint8_t y, uint8_t r);

/**
 * @brief Tests whether the pixel at (x, y) is currently active without altering screen state.
 *
 * Provides zero-RAM collision detection directly against the display buffer.
 *
 * @param x Horizontal coordinate
 * @param y Vertical coordinate
 * @return true if the pixel is turned on, false if off or out of bounds.
 */
bool feb_test_pixel(uint8_t x, uint8_t y);

/* -------------------------------------------------------------------------
 * Typography & String Formatting
 * ------------------------------------------------------------------------- */

/**
 * @brief Renders a null-terminated ASCII string starting at (x, y) using @p font_id.
 *
 * @param x Top-left horizontal coordinate
 * @param y Top-left vertical coordinate
 * @param str Null-terminated ASCII string to render
 * @param font_id Font ID (FEB_FONT_4X6, FEB_FONT_6X10, or FEB_FONT_RETRO_8X8)
 * @return Advance horizontal x-coordinate after the last rendered glyph.
 */
uint8_t feb_draw_string(uint8_t x, uint8_t y, const char *str, uint8_t font_id);

/**
 * @brief Renders a single ASCII character at (x, y) using @p font_id.
 *
 * @param x Top-left horizontal coordinate
 * @param y Top-left vertical coordinate
 * @param ch ASCII character
 * @param font_id Font ID (FEB_FONT_4X6, FEB_FONT_6X10, or FEB_FONT_RETRO_8X8)
 * @return Advance horizontal x-coordinate after the rendered glyph.
 */
uint8_t feb_draw_char(uint8_t x, uint8_t y, char ch, uint8_t font_id);

/**
 * @brief Calculates the exact pixel width of a string rendered in @p font_id.
 *
 * @param str Null-terminated ASCII string to measure
 * @param font_id Font ID (FEB_FONT_4X6, FEB_FONT_6X10, or FEB_FONT_RETRO_8X8)
 * @return Pixel width of the string.
 */
uint8_t feb_string_width(const char *str, uint8_t font_id);

/**
 * @brief Formats and renders a 16-bit unsigned integer (0..65535) at (x, y) using @p font_id.
 *
 * @param x Top-left horizontal coordinate
 * @param y Top-left vertical coordinate
 * @param num 16-bit unsigned integer value
 * @param font_id Font ID (FEB_FONT_4X6, FEB_FONT_6X10, or FEB_FONT_RETRO_8X8)
 * @return Advance horizontal x-coordinate after the rendered number.
 */
uint8_t feb_draw_number(uint8_t x, uint8_t y, uint16_t num, uint8_t font_id);

/* -------------------------------------------------------------------------
 * Hardware Synchronization & Input Polling
 * ------------------------------------------------------------------------- */


/**
 * @brief Reads the instantaneous 4-button hardware bitmask into an 8-bit integer.
 *
 * Returns a bitmask of FEB_BTN_UP (0x01), FEB_BTN_DOWN (0x02), FEB_BTN_LEFT (0x04),
 * and FEB_BTN_RIGHT (0x08). Supports multi-button simultaneous chords and zero-latency polling.
 *
 * @return Bitmask of currently held physical buttons.
 */
uint8_t feb_get_keys(void);

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
