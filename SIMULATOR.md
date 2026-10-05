# Flashiibo FEB Desktop Simulator

A lightweight, high-fidelity desktop simulator for developing, testing, and debugging **Flashiibo Executable Binary (`.feb`)** applications and games without physical hardware.

Built with **Python 3 & Pygame**, the simulator provides byte-accurate parity with the physical Flashiibo Pro Gen3 hardware runtime (as implemented in `firmware-52832`), strictly constrained to the FEB execution sandbox.

---

## 1. Features & Architectural Parity

- **Authentic Display & Resolution**:
  - Native **128×64** Super-CHIP high-resolution OLED display mode (1:1 pixel rendering).
  - Legacy **64×32** standard CHIP-8 mode (2×2 integer scaled to 128×64).
  - High-performance 1-bit to 8-bit unpacked palette pipeline (sub-millisecond frame rendering).
  - Customizable integer scaling (default `6x` = 768×384 window) and fullscreen toggle.
  - Authentic OLED color themes: **OLED Ice Blue**, **Classic Monochrome**, **Amber CRT**, and **Phosphor Matrix Green**.
- **Hardware Button Mapping**:
  - Deterministic 4-button hardware mapping matching physical Flashiibo hardware: `UP` (`0x2`), `DOWN` (`0x8`), `BACK` (`0x4`), `OK` (`0x6`).
  - Hardware exit chord: pressing **UP + DOWN simultaneously** (or `Q`) immediately terminates execution.
  - Physical button hold timing (~66 ms hold frames) ensuring rapid key taps are never missed by polling loops.
- **Flashiibo Custom VM Extensions**:
  - **Vector Geometry (`FX90`..`FX99`)**: `pixel`, `line`, `hline`, `vline`, `rect`, `fillrect`, `circle`, `disc`, `drawmode`, `testpixel`.
  - **Typography & Formatting (`FXA0`..`FXA3`)**: Built-in u8g2 bitmap fonts (`4x6_tr`, `siji_t_6x10`, `likeminecraft_te`) for text, single characters, string measurement, and formatted integers.
  - **Deterministic Input Polling (`FXB0`)**: Instantaneous 4-button bitmask (`getkeys`).
  - **Persistent Storage (`FX75` / `FX85`)**: Automatic reading and writing of Super-CHIP RPL user flags to companion sidecar `.sav` containers (`FSAV` format).
- **Accurate Timing & Performance**:
  - 60 Hz delay timer (`DT`) and sound timer (`ST`) countdown.
  - Adaptive CPU loop with delay-loop detection (`is_in_delay_wait`), ensuring smooth 60 Hz frame pacing without burning 100% CPU.
- **Automation & Headless CI**:
  - Headless execution mode (`--headless` or `SDL_VIDEODRIVER=dummy`) requiring no X11 or display server.
  - Automated screenshot capture (`--screenshot output.png`).
  - Standalone Python VM API (`FebVM`) for writing programmatic unit tests and headless bot simulations.

---

## 2. Quick Start & Manual Testing

### 2.1 Prerequisites

Ensure Python 3 and Pygame are installed:

```bash
python3 --version  # Python 3.8+
pip install pygame
```

### 2.2 Launching an Application

From the root of the `feb-sdk` repository:

```bash
# Run the default game (build/2048.feb)
make sim

# Run a specific built game via Makefile
make sim GAME=sokoban
make sim GAME=flappy_bird
make sim GAME=button_demo
make sim GAME=draw_demo

# Run directly via tools/feb_sim.py
python3 tools/feb_sim.py build/2048.feb
python3 tools/feb_sim.py examples/sokoban/sokoban.feb
```

*(Note: You can pass either a `.feb` container or a raw `.ch8` bytecode file).*

---

## 3. Controls & Hotkeys

### 3.1 Flashiibo 4-Button Hardware Controls

The physical 4-button layout maps to intuitive keyboard equivalents:

```
                  ┌──────────────┐
                  │    [ UP ]    │
                  │   Key: 0x2   │
                  │   (W / ↑ / K)│
  ┌───────────────┴──────────────┴───────────────┐
  │   [ BACK ]                         [ OK ]    │
  │   Key: 0x4                        Key: 0x6   │
  │(A / ← / U / Esc)              (D / → / O / Enter)
  └───────────────┬──────────────┬───────────────┘
                  │   [ DOWN ]   │
                  │   Key: 0x8   │
                  │   (S / ↓ / J)│
                  └──────────────┘
```

| Flashiibo Button | Key Code | Primary PC Key | Alternative Keys | Bitmask (`FXB0`) | Function |
|---|---|---|---|---|---|
| **UP** | `0x2` | `W` | `Up Arrow`, `K` | `0x01` (`FEB_BTN_UP`) | Move cursor up / Jump / Rotate |
| **DOWN** | `0x8` | `S` | `Down Arrow`, `J` | `0x02` (`FEB_BTN_DOWN`) | Move cursor down / Crouch |
| **BACK** | `0x4` | `A` | `Left Arrow`, `U`, `Esc`, `Backspace` | `0x04` (`FEB_BTN_LEFT`) | Move left / Cancel / Navigate back |
| **OK** | `0x6` | `D` | `Right Arrow`, `O`, `Enter`, `Space` | `0x08` (`FEB_BTN_RIGHT`) | Move right / Action / Select |

### 3.2 System Exit Chord (UP + DOWN)

- Holding **UP** and **DOWN** simultaneously triggers the native Flashiibo hardware exit chord.
- In the simulator, you can also press **`Q`** to immediately trigger the exit chord.
- When an application exits, any dirty persistent user flags (`FX75`) are automatically flushed to the companion `.sav` file.

### 3.3 Simulator Hotkeys

| Hotkey | Action | Description |
|---|---|---|
| **`H`** / **`F1`** / **`Tab`** | **Toggle Help HUD** | Shows on-screen controls overlay. |
| **`F2`** / **`R`** | **Restart** | Resets registers and restarts the active binary from address `0x200`. |
| **`F3`** / **`T`** | **Cycle Palette** | Cycles through OLED Ice Blue, Classic White, Amber CRT, and Matrix Green. |
| **`F4`** | **Diagnostics OSD** | Displays live FPS, IPS, Program Counter (`PC`), Index (`I`), Timers, Registers (`V0..VF`), and Key bitmask. |
| **`P`** | **Pause / Resume** | Pauses VM execution and timer countdown. |
| **`F11`** / **`F`** | **Fullscreen** | Toggles borderless fullscreen display. |

---

## 4. CLI Options Reference

```bash
python3 tools/feb_sim.py [path] [options]
```

| Flag | Default | Description |
|---|---|---|
| `[file]` | `build/2048.feb` | Path to `.feb` binary or `.ch8` ROM. Auto-discovers if omitted. |
| `--scale <N>` | `6` | Integer window scaling factor (e.g. `4` for 512×256, `6` for 768×384, `8` for 1024×512). |
| `--theme <name>` | `oled` | Starting color theme (`oled`, `white`, `amber`, `green`). |
| `--ips <N>` | `1000` | CPU instruction budget per 60 Hz frame. |
| `--headless` | `False` | Run in headless mode without opening a physical graphical window. |
| `--frames <N>` | `None` | Automatically exit the simulator after executing `N` frames. |
| `--screenshot <path>` | `None` | Render and save the display framebuffer to a PNG image file upon exit. |

### Examples

```bash
# Launch with 8x scaling and Amber CRT theme
python3 tools/feb_sim.py build/sokoban.feb --scale 8 --theme amber

# Headless capture of 2048 start screen after 60 frames
python3 tools/feb_sim.py build/2048.feb --headless --frames 60 --screenshot /tmp/2048.png
```

---

## 5. Automated Testing & Headless CI

The simulator provides both a CLI screenshot/frame runner and a scriptable Python API (`feb_vm.FebVM`) for headless test suites.

### 5.1 Running the Automated Test Suite

Run the full verification suite (including compiler, assembler, packaging, and simulator tests):

```bash
make test
```

Or run the simulator-specific test suite directly:

```bash
python3 -m unittest test/test_sim.py -v
```

### 5.2 Python Test Automation API (`FebVM`)

`tools/feb_vm.FebVM` is completely decoupled from Pygame, allowing tests to run in microseconds without graphics overhead.

#### Example 1: Headless Frame Step and Pixel Assertion

```python
from tools.feb_vm import FebVM, FEB_KEY_UP

vm = FebVM()
vm.load_feb("build/button_demo.feb")

# Step 30 frames (~0.5 seconds at 60 Hz)
for _ in range(30):
    vm.step_frame()

# Verify initial screen rendering
assert vm.get_pixel(52, 19) is not None

# Simulate pressing UP key
vm.press_key(FEB_KEY_UP)

# Step 10 frames to allow application to process turn
for _ in range(10):
    vm.step_frame()

# Verify that application reacted and is not stuck
assert not vm.exited
```

#### Example 2: Verifying Save File Persistence (`.sav`)

```python
import os
from tools.feb_vm import FebVM

vm = FebVM()
vm.load_feb("build/sokoban.feb")

# Step frames
for _ in range(60):
    vm.step_frame()

# Verify RPL flags contain level progression
print("Current level flag:", vm.rpl_flags[0])

# Flush to .sav sidecar
vm.flush_save_sidecar()
assert os.path.exists("build/sokoban.sav")
```

#### Example 3: Automated Visual Regression Screenshot Capture

```python
from tools.feb_sim import FebSimulator

sim = FebSimulator(
    feb_path="build/2048.feb",
    scale=4,
    theme="oled",
    headless=True
)

# Run 60 frames and save screenshot
sim.run(max_frames=60, screenshot_path="artifacts/2048_boot.png")
```

---

## 6. Directory Structure

```
feb-sdk/
├── tools/
│   ├── feb_sim.py        <-- Pygame FEB Simulator (CLI & interactive GUI)
│   ├── feb_vm.py         <-- High-fidelity CHIP-8/SCHIP/Flashiibo VM engine
│   └── feb_fonts.py      <-- Embedded u8g2 bitmap fonts & glyph decoder
├── test/
│   ├── test_sim.py       <-- Unit & integration tests for simulator
│   └── test_tooling.py   <-- Verification suite for compiler and packaging
├── SIMULATOR.md          <-- This guide
└── Makefile              <-- Root orchestrator (`make sim`, `make test`)
```
