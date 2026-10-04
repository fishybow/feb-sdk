# Flashiibo FEB SDK & Tooling

[![Status: Beta](https://img.shields.io/badge/status-beta%20%2F%20experimental-orange.svg)](#status--experimental-warning)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

> [!WARNING]
> ### BETA & EXPERIMENTAL WARNING
> **This repository, the FEB SDK, container format, and build tooling are in BETA and EXPERIMENTAL status.**  
> APIs, header definitions, and runtime contracts are under active development. **Breaking changes might happen without warning.**

The **Flashiibo Executable Binary (`.feb`)** ecosystem enables developers to write, compile, and distribute standalone games and mini-applications for the **Flashiibo Gen3** platform.

Applications run inside a sandboxed virtual runtime with a 60 Hz frame cycle, monochrome OLED graphics, and deterministic 4-button hardware navigation—without modifying or reflashing the MCU firmware.

---

## Hardware Specifications

| Property | Value | Notes |
|---|---|---|
| **Target Platform** | Flashiibo Pro Gen3 | Requires firmware >= 26.10.4 (Sandboxed VM) |
| **Display** | 128×64 (default) or 64×32 (legacy) Monochrome OLED | 1-bit per pixel (XOR sprite drawing) |
| **Frame Rate** | 60 Hz | Hardware timer-driven execution tick |
| **Address Space** | 4,096 Bytes | Deterministic memory layout |
| **Input Controls** | 4 Physical Buttons | Fixed directional mapping |
| **Container Format** | `.feb` (Flashiibo Executable Binary) | 100-byte packed header + bytecode |
| **Distribution** | `/feb/*.feb` on SPI Flash | Loaded over Web Bluetooth, USB, or Companion App |

---

## Deterministic Hardware Controls

Flashiibo Gen3 features four physical buttons:

```
                  ┌──────────────┐
                  │    [ UP ]    │
                  │ (FEB_KEY_UP) │
                  │   Key: 0x2   │
  ┌───────────────┴──────────────┴───────────────┐
  │   [ BACK ]                         [ OK ]    │
  │ (FEB_KEY_LEFT)                (FEB_KEY_RIGHT)│
  │   Key: 0x4                       Key: 0x6    │
  └───────────────┬──────────────┬───────────────┘
                  │   [ DOWN ]   │
                  │(FEB_KEY_DOWN)│
                  │   Key: 0x8   │
                  └──────────────┘
```

| Physical Button | C Constant | Hex Code | Primary Role |
|---|---|---|---|
| **UP** | `FEB_KEY_UP` | `0x2` | Directional UP / Jump / Rotate |
| **DOWN** | `FEB_KEY_DOWN` | `0x8` | Directional DOWN / Crouch |
| **BACK** | `FEB_KEY_LEFT` / `FEB_KEY_BACK` | `0x4` | Directional LEFT / Cancel |
| **OK** | `FEB_KEY_RIGHT` / `FEB_KEY_OK` | `0x6` | Directional RIGHT / Select |

> [!IMPORTANT]
> **Emergency Exit Chord:** Pressing **UP** and **DOWN** simultaneously guarantees immediate return to the Flashiibo device menu. Long-press on BACK is NOT used as an exit trigger, making BACK completely safe for gameplay movement.

---

## Quickstart

### Prerequisites
- Python 3.8 or newer
- GNU Make

### Build All Included Apps
```bash
# Clone the repository
git clone https://github.com/flashiibo/feb-sdk.git
cd feb-sdk

# Build all applications into build/
make all

# Run test suite
make test
```

### Build a Single App
```bash
cd examples/2048
make
# Generates 2048.feb
```

---

## Repository Layout

```
feb-sdk/
├── README.md               <-- This documentation
├── SPEC.md                 <-- 100-byte .feb binary container specification
├── LICENSE                 <-- MIT License
├── Makefile                <-- Root build and test orchestrator
├── include/
│   └── feb.h              <-- Flashiibo C SDK definitions & prototypes
├── tools/
│   ├── feb_build.py       <-- C / Assembly compiler and packager
│   ├── make_icon.py       <-- 16x16 app icon generator, converter & previewer
│   ├── feb_icon.py        <-- Icon tool alias
│   ├── make_feb.py        <-- .feb binary container generator
│   └── assemble_chip8.py  <-- Virtual machine bytecode assembler
├── examples/
│   ├── 2048/              <-- Full 2048 puzzle game implementation (128x64)
│   │   ├── main.c
│   │   └── Makefile
│   ├── button_test/       <-- Hardware 4-button input test & press counter (128x64)
│   │   ├── main.c
│   │   └── Makefile
│   └── template/          <-- Starter template with 4-way movement (128x64)
│       ├── main.c
│       ├── main.asm
│       └── Makefile
├── test/                  <-- Automated test suite
│   └── test_tooling.py
└── docs/
    └── c_development_guide.md <-- In-depth C programming guide
```

---

## C SDK API Reference (`feb.h`)

Include the C SDK header in your application:

```c
#include "feb.h"
```

### Display (Default: 128×64 Super-CHIP Mode)
- `void feb_set_high_res(bool enable);`: Switches between 128×64 high-resolution mode (`true`, default) and legacy 64×32 mode (`false`).
- `void feb_clear_screen(void);`: Clears the display buffer.
- `bool feb_draw_sprite(uint8_t x, uint8_t y, const uint8_t *sprite, uint8_t height);`: XOR draws an 8-pixel wide sprite of height 1..15. Calling it a second time at the same position erases the sprite. Returns `true` if a collision occurred.
- `bool feb_draw_sprite16(uint8_t x, uint8_t y, const uint8_t *sprite);`: XOR draws a 16×16 pixel sprite in 128×64 mode (32 bytes). Returns `true` if a collision occurred.
- `void feb_draw_digit(uint8_t x, uint8_t y, uint8_t digit);`: Renders built-in hex digit (0..15).

### Input
- `uint8_t feb_wait_key(void);`: Blocks until a button is pressed; returns key code (`0x2`, `0x8`, `0x4`, `0x6`).
- `bool feb_is_key_down(uint8_t key);`: Non-blocking check if a button is currently held.

### Timing & Randomness
- `uint8_t feb_rand(uint8_t mask);`: Returns pseudo-random 8-bit integer masked with `mask`.
- `void feb_set_delay_timer(uint8_t val);`: Sets the 60 Hz delay timer countdown.
- `uint8_t feb_get_delay_timer(void);`: Reads the current 60 Hz delay timer value.
- `void feb_delay_frames(uint8_t frames);`: Delays execution for N frames (~16.6 ms per frame).

---

## App Icon Generation (`make_icon.py`)

Flashiibo `.feb` executables feature a **16×16 monochrome 1-bit icon** (32 bytes) displayed on the device menu. The SDK provides `tools/make_icon.py` (aliased as `tools/feb_icon.py`) to easily create, preview, and convert icons.

### 1. From an Image (PNG, JPG, BMP)
```bash
# Convert any image to a 32-byte .bin icon:
python3 tools/make_icon.py my_icon.png -o icon.bin

# Resize modes: fit (default), crop, or stretch
python3 tools/make_icon.py artwork.png -o icon.bin --mode crop

# Apply Floyd-Steinberg dithering or invert polarity:
python3 tools/make_icon.py photo.png -o icon.bin --dither --invert
```

### 2. From an ASCII Text Grid (.txt)
Developers can design icons in any text editor without graphic design software:
```bash
# Generate an editable 16x16 ASCII template:
python3 tools/make_icon.py --template icon.txt

# Edit icon.txt using '#' for lit pixels and '.' for unlit pixels, then convert:
python3 tools/make_icon.py icon.txt -o icon.bin
```

### 3. Procedural Text / Letter Icons
Generate a clean retro icon directly from 1 to 4 characters:
```bash
# Single bold letter with border:
python3 tools/make_icon.py --text "A" --border -o icon.bin

# Two characters (e.g. game acronym or numbers):
python3 tools/make_icon.py --text "20" --border -o icon.bin

# Three characters (3x5 font):
python3 tools/make_icon.py --text "FEB" -o icon.bin
```

### 4. Terminal Preview & PNG Upscaling
```bash
# Visual Unicode block preview in terminal:
python3 tools/make_icon.py icon.bin --preview

# Inspect an existing .feb container's embedded icon:
python3 tools/make_icon.py build/2048.feb --preview

# Export upscaled 128x128 preview image:
python3 tools/make_icon.py icon.bin -o preview.png --scale 8
```

### 5. Automatic Build Integration
When compiling with `tools/feb_build.py`, if an `icon.txt`, `icon.png`, or `icon.bin` file exists alongside `main.c`, it is **automatically detected and embedded** into the `.feb` binary! You can also explicitly specify it:
```bash
python3 tools/feb_build.py main.c -o app.feb --title "My App" --icon icon.png
```

---

## Creating Your Own App

1. Copy the starter template:
   ```bash
   cp -r examples/template examples/my_app
   ```
2. Edit `examples/my_app/main.c` and customize your logic.
3. Customize your app icon by editing `examples/my_app/icon.txt` or providing `icon.png`.
4. Update `examples/my_app/Makefile` with your app title and author.
5. Build your `.feb` file:
   ```bash
   cd examples/my_app
   make
   ```
6. See [docs/c_development_guide.md](docs/c_development_guide.md) for full architectural patterns and best practices.

---

## Deploying to Hardware

> [!NOTE]
> Running `.feb` applications requires **Flashiibo Pro Gen3** firmware **>= 26.10.4**.

1. Connect your Flashiibo Pro Gen3 to your computer or smartphone (USB or Web Bluetooth).
2. Open the Flashiibo companion application or Web Tool.
3. Upload your `.feb` binary into the `/feb/` folder on device storage.
4. On your Flashiibo, scroll to **FEB Runner**, select your app, and press **OK**!

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
