# Developing C Applications for Flashiibo Pro Gen3 ("FEB Runner")

> [!WARNING]
> **BETA & EXPERIMENTAL NOTICE:**
> The Flashiibo Executable Binary (`.feb`) format, C SDK (`feb.h`), build tooling, and runtime environment are currently in **Beta & Experimental** status.
> APIs, header specifications, and runtime behavior are under active development and **breaking changes might happen without warning**.

**Document Version:** 1.0 (Beta)  
**Target Platform:** Flashiibo Pro Gen3 (Firmware >= 26.10.4)  
**Host Applet:** FEB Runner  
**Runtime Environment:** Flashiibo Executable Binary (`.feb`) Virtual Machine  

---

## 1. Introduction & Overview

Flashiibo Pro Gen3 features a sandboxed virtual runtime for user-installable applications and games called **FEB Runner** (`.feb`, requires firmware >= 26.10.4). With the Flashiibo C SDK, developers can write applications in idiomatic C, compile them into self-contained `.feb` binary packages, and distribute them without modifying or reflashing the MCU firmware.

### 1.1 Key Technical Specifications

| Resource | Specification | Notes |
|---|---|---|
| **Target Platform** | Flashiibo Pro Gen3 | Requires firmware >= 26.10.4 (Sandboxed VM) |
| **Language** | C (C99 / C11) / Assembly | Standard types from `<stdint.h>` and `<stdbool.h>` |
| **Display** | 128×64 (default Super-CHIP) or 64×32 (legacy) Monochrome OLED | 1-bit per pixel (XOR sprite drawing) |
| **Frame Rate** | 60 Hz | Hardware timer-driven execution cycle |
| **Memory Limit** | 4,096 Bytes total address space | Sandboxed from system radio and kernel |
| **Input Controls** | 4 Physical buttons | UP, DOWN, BACK (Left), CONFIRM (Right) |
| **Container Format** | `.feb` (Flashiibo Executable Binary) | 100-byte metadata header + binary bytecode |
| **Distribution** | VFS `/feb/*.feb` on SPI NOR Flash | Loaded via Companion App over BLE or USB |

---

## 2. Flashiibo Gen3 Hardware Contract

### 2.1 Fixed Deterministic 4-Button Mapping

Flashiibo devices feature four physical buttons on the device body. In FEB Runner, these map to deterministic virtual key constants:

```
                  ┌──────────────┐
                  │   [ UP ]     │  Key: 0x2
                  │ (FEB_KEY_UP) │
  ┌───────────────┴──────────────┴───────────────┐
  │   [ BACK ]                      [ CONFIRM ]  │
  │ (FEB_KEY_LEFT)                (FEB_KEY_RIGHT)│
  │   Key: 0x4                       Key: 0x6    │
  └───────────────┬──────────────┬───────────────┘
                  │  [ DOWN ]    │  Key: 0x8
                  │(FEB_KEY_DOWN)│
                  └──────────────┘
```

| Physical Button | C Constant | Hex Code | Primary App Role |
|---|---|---|---|
| **UP** | `FEB_KEY_UP` | `0x2` | Move cursor up / Jump / Rotate |
| **DOWN** | `FEB_KEY_DOWN` | `0x8` | Move cursor down / Crouch / Soft drop |
| **BACK** | `FEB_KEY_LEFT` / `FEB_KEY_BACK` | `0x4` | Move cursor left / Navigate back |
| **CONFIRM** | `FEB_KEY_RIGHT` / `FEB_KEY_CONFIRM` | `0x6` | Move cursor right / Select / Action |

### 2.2 System Exit Contract (UP + DOWN Chord)

> [!IMPORTANT]
> **Pressing UP and DOWN simultaneously** is intercepted at both the OS and virtual machine engine level to guarantee an immediate, safe exit back to the "FEB Runner" main menu.
>
> Long press on BACK is deliberately **not** an exit trigger, ensuring that BACK (Key 0x4 / Left) is completely safe to hold down for continuous gameplay movement or action charging without accidental termination.

---

## 3. C SDK API Reference (`feb.h`)

Include the C SDK header in your application:

```c
#include "feb.h"
```

### 3.1 Display Functions

#### `void feb_clear_screen(void);`
Clears the entire display buffer (turns off all pixels).

#### `bool feb_draw_sprite(uint8_t x, uint8_t y, const uint8_t *sprite, uint8_t height);`
Draws an 8-pixel wide bitmap sprite of height `height` (1 to 15 rows) at coordinate `(x, y)`.
- Sprites use **XOR blitting**. If a pixel is drawn where a pixel is already turned on, it will invert (turn off).
- **Erase a sprite:** Call `feb_draw_sprite` a second time with the exact same coordinates and data.
- **Return value:** Returns `true` if any drawn pixel collided with an already active pixel on screen.

#### `void feb_draw_digit(uint8_t x, uint8_t y, uint8_t digit);`
Renders a built-in single-digit hexadecimal glyph (`0x0` through `0xF`, 5 pixels high by 4 pixels wide) at `(x, y)`.

### 3.2 Input Functions

#### `uint8_t feb_wait_key(void);`
Blocks execution until a physical button is pressed, and returns the key code (`0x2`, `0x8`, `0x4`, or `0x6`).

#### `bool feb_is_key_down(uint8_t key);`
Non-blocking check to determine if the specified key is currently held down. Ideal for continuous movement or action games.

### 3.3 Timing & Randomness

#### `uint8_t feb_rand(uint8_t mask);`
Returns an 8-bit pseudo-random integer masked with `mask` (e.g., `feb_rand(0x07)` produces `0`..`7`).

#### `void feb_set_delay_timer(uint8_t val);`
Sets the 60 Hz delay timer register. It automatically decrements by 1 every 16.6 ms until it reaches 0.

#### `uint8_t feb_get_delay_timer(void);`
Returns the current value of the 60 Hz delay timer register.

#### `void feb_delay_frames(uint8_t frames);`
Blocks execution for `frames` screen frames (~16.6 ms per frame).

### 3.4 Persistent Storage (Sidecar `.sav`)

Executable `.feb` files are strictly read-only. User save data, high scores, and settings are automatically persisted to `/feb/saves/<app_name>.sav` upon exit.

#### `void feb_save_flags(const uint8_t *data, uint8_t len);`
Saves up to 16 bytes of persistent application state (mapped to Super-CHIP RPL user flags). Flushed to the companion `.sav` file when the app closes.

#### `void feb_load_flags(uint8_t *data, uint8_t len);`
Loads up to 16 bytes of persistent application state previously saved by `feb_save_flags`.

---

## 4. Examples & Starter Template

### 4.1 Starter Template (`examples/template`)
A minimal moving sprite demo using 4-button directional keys:

```c
#include "../../include/feb.h"

static const uint8_t player_sprite[8] = {
    0x3C, 0x7E, 0xDB, 0xFF, 0xFF, 0xDB, 0x7E, 0x3C
};

int main(void) {
    uint8_t x = 60, y = 28;
    feb_set_high_res(true);
    feb_clear_screen();
    feb_draw_sprite(x, y, player_sprite, 8);

    while (1) {
        uint8_t key = feb_wait_key();
        feb_draw_sprite(x, y, player_sprite, 8); /* XOR erase */

        if (key == FEB_KEY_UP && y >= 2) y -= 2;
        else if (key == FEB_KEY_DOWN && y <= 54) y += 2;
        else if (key == FEB_KEY_LEFT && x >= 2) x -= 2;
        else if (key == FEB_KEY_RIGHT && x <= 118) x += 2;

        feb_draw_sprite(x, y, player_sprite, 8); /* redraw */
    }
    return 0;
}
```

### 4.2 Full Game: 2048 Puzzle (`examples/2048`)
The repository includes a complete, fully playable 2048 game in `examples/2048/main.c`.

---

## 5. Build System & Packaging

### 5.1 Project Layout

```
feb-sdk/
├── include/
│   └── feb.h              <-- Flashiibo SDK header
├── tools/
│   ├── feb_build.py       <-- Build orchestrator
│   ├── make_feb.py        <-- .feb container packager
│   └── assemble_chip8.py  <-- Bytecode assembler
└── examples/
    └── my_app/
        ├── Makefile       <-- App build script
        └── main.c         <-- Your C application
```

### 5.2 Compiling with `feb_build.py`

Compile your C application into a distributable `.feb` container:

```bash
python3 tools/feb_build.py examples/my_app/main.c -o examples/my_app/my_app.feb \
    --title "My App" \
    --author "Developer" \
    --ver "1.0.0"
```

### 5.3 Sample `Makefile`

```makefile
PYTHON ?= python3
BUILD_TOOL = ../../tools/feb_build.py

APP_TITLE = My App
APP_AUTHOR = Developer
APP_VER = 1.0.0
TARGET = my_app.feb

all: $(TARGET)

$(TARGET): main.c ../../include/feb.h
	$(PYTHON) $(BUILD_TOOL) main.c -o $(TARGET) \
		--title "$(APP_TITLE)" \
		--author "$(APP_AUTHOR)" \
		--ver "$(APP_VER)"

clean:
	rm -f $(TARGET)
```

---

## 6. Deploying to Flashiibo Pro Gen3 Hardware

> [!NOTE]
> Running `.feb` applications requires **Flashiibo Pro Gen3** firmware **>= 26.10.4**.

1. Connect your Flashiibo Pro Gen3 to your computer or phone via USB or Web Bluetooth.
2. In the Flashiibo companion application or Web Tool, open the File Manager.
3. Upload your `.feb` file into the `/feb/` folder on the device flash storage.
4. On your Flashiibo device, enter **FEB Runner** from the main menu, select your game, and press **CONFIRM** to launch!
