# Flashiibo Executable Binary (.feb) Specification

> [!WARNING]
> **BETA & EXPERIMENTAL NOTICE:**
> This container specification is in **Beta & Experimental** status.
> Header fields, flags, and runtime contracts may change without warning as the Flashiibo ecosystem evolves.

**Specification Version:** 1.0 (Beta)  
**Target Platform:** Flashiibo Pro Gen3 (Firmware >= 26.10.4)  
**Host Applet:** FEB Runner  
**File Extension:** `.feb`  

---

## 1. Overview

The `.feb` (Flashiibo Executable Binary) format is a lightweight, sandboxed executable container designed for running user-created games and mini-applications inside the **FEB Runner** app on Flashiibo Pro Gen3 hardware (requires firmware >= 26.10.4) without reflashing MCU firmware.

---

## 2. Header Layout (Exactly 96 Bytes, Packed Little-Endian)

```
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                       Magic: '.FEB'                           |  [0..3]
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
| Format Version|   App Type    |             Flags             |  [4..7]
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                                                               |
+                    Title (24 bytes, UTF-8)                    +  [8..31]
|                                                               |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                   Author (16 bytes, UTF-8)                    |  [32..47]
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                   Version (8 bytes, UTF-8)                    |  [48..55]
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                                                               |
+              16x16 1-bit Icon Bitmap (32 bytes)               +  [56..87]
|                                                               |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                         Payload Size                          |  [88..91]
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                            CRC-32                             |  [92..95]
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                       Executable Payload                      |
|                  (Bytecode: 0..3584 Bytes)                    |
|                               ...                             |
```

### 2.1 Field Definitions

| Offset | Field | Type | Description |
|---|---|---|---|
| `0..3` | `magic` | `uint32_t` | Fixed magic `0x4245462E` (`.FEB` in little-endian ASCII) |
| `4` | `format_version` | `uint8_t` | Format version (currently `1`) |
| `5` | `app_type` | `uint8_t` | Virtual machine bytecode type (`0` = CHIP-8) |
| `6..7` | `flags` | `uint16_t` | Runtime bitmask flags: Bit 0 (`0x0001`) = `FEB_FLAG_REQUIRE_BACK_BUTTON` (requires physical BACK button, e.g. 4-button hardware) |
| `8..31` | `title` | `char[24]` | UTF-8 null-terminated application display title |
| `32..47`| `author` | `char[16]` | UTF-8 null-terminated author string |
| `48..55`| `version` | `char[8]` | Semantic version string (e.g. `"1.0.0"`) |
| `56..87`| `icon` | `uint8_t[32]` | 16×16 monochrome 1-bit icon bitmap |
| `88..91`| `payload_size` | `uint32_t` | Byte length of payload following header |
| `92..95`| `crc32` | `uint32_t` | Optional CRC-32 checksum of the payload |

---

## 3. Persistent Storage Specification (`.sav` Sidecar Files)

Executable `.feb` binaries are strictly **read-only and immutable** on flash storage.
Persistent user state (scores, progression, and settings) is stored in a dedicated companion save file under `/feb/saves/<app_name>.sav`.

### 3.1 Save File Header Layout (Exactly 32 Bytes, Packed Little-Endian)

```
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                       Magic: 'FSAV'                           |  [0..3]
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
| Format Version|             Flags             |   Reserved    |  [4..7]
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                 High Score / Persistent State                 |  [8..11]
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                                                               |
+      Super-CHIP / XO-CHIP Persistent RPL Flags (16 Bytes)     +  [12..27]
|                      (FX75 / FX85 Opcodes)                    |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|           Extra Length        |           Reserved            |  [28..31]
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                       Optional Extra Data                     |
|                           (0..512 B)                          |
```

| Offset | Field | Type | Description |
|---|---|---|---|
| `0..3` | `magic` | `uint32_t` | Fixed magic `0x56415346` (`FSAV` in little-endian ASCII) |
| `4..5` | `format_version` | `uint16_t` | Save format version (`1`) |
| `6..7` | `flags` | `uint16_t` | Bitmask flags: Bit 0 = `high_score` valid |
| `8..11`| `high_score` | `uint32_t` | Quick-access 32-bit score / state |
| `12..27`| `rpl_flags` | `uint8_t[16]` | Super-CHIP and XO-CHIP persistent user flags (`FX75`/`FX85`) |
| `28..29`| `extra_len` | `uint16_t` | Length of optional trailing data (0..512 bytes) |
| `30..31`| `reserved` | `uint16_t` | Header alignment padding |

---

## 4. Hardware Button Contract & Controls

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

| Physical Button | CHIP-8 Keypad Code | C Macro / Constant | Primary Role |
|---|---|---|---|
| **UP** | `0x2` | `FEB_KEY_UP` | Directional UP / Jump / Rotate |
| **DOWN** | `0x8` | `FEB_KEY_DOWN` | Directional DOWN / Crouch |
| **BACK** | `0x4` | `FEB_KEY_LEFT` / `FEB_KEY_BACK` | Directional LEFT / Cancel |
| **OK** | `0x6` | `FEB_KEY_RIGHT` / `FEB_KEY_OK` | Directional RIGHT / Action |

### 4.1 Hardware Exit Contract (UP + DOWN Chord)
> **Hardware Exit Chord:** Pressing **UP** and **DOWN** simultaneously guarantees an immediate, uninterceptable exit back to the FEB Runner main menu.
>
> - **OS & VM Interception:** The UP + DOWN chord is detected at both the native MUI input dispatcher and inside the CHIP-8 virtual machine execution loop.
> - **State Preservation:** Upon hardware exit, any modified RPL persistent flags (`FX75` / `feb_save_flags()`) are automatically flushed to the companion sidecar save container (`/feb/saves/<app_name>.sav`) on the SPI flash before unloading.
> - **BACK Button Usability:** Long-press on BACK is deliberately **not** an exit trigger in the FEB runtime, allowing games and applications to freely use BACK as a full-fledged directional or action button (e.g., Left) without risking accidental termination.

### 4.2 Programmatic Exit
> Programs can immediately exit back to the FEB Runner menu at any time by executing opcode `00FD` (`EXIT` / `QUIT` / `feb_exit()`).

---

## 5. Custom Virtual Machine Extension Opcodes

Flashiibo Pro Gen3 extends the CHIP-8 / Super-CHIP instruction set with hardware-accelerated opcodes under unused `0xFX..` opcode space (firmware >= 26.10.4):

### 5.1 Geometry & Drawing Modes

| Opcode | Mnemonic | Parameters | Description |
|---|---|---|---|
| `FX90` | `PIXEL Vx` | `Vx`=X, `Vx+1`=Y | Draws a single pixel at `(Vx, Vx+1)` using the active draw mode. |
| `FX91` | `LINE Vx` | `Vx`=X0, `Vx+1`=Y0, `Vx+2`=X1, `Vx+3`=Y1 | Draws a line between `(Vx, Vx+1)` and `(Vx+2, Vx+3)` via Bresenham's algorithm. |
| `FX92` | `HLINE Vx` | `Vx`=X, `Vx+1`=Y, `Vx+2`=Len | Draws a horizontal line of length `Vx+2` starting at `(Vx, Vx+1)`. |
| `FX93` | `VLINE Vx` | `Vx`=X, `Vx+1`=Y, `Vx+2`=Len | Draws a vertical line of height `Vx+2` starting at `(Vx, Vx+1)`. |
| `FX94` | `RECT Vx` | `Vx`=X, `Vx+1`=Y, `Vx+2`=W, `Vx+3`=H | Draws an outline hollow rectangle at `(Vx, Vx+1)`. |
| `FX95` | `FILLRECT Vx` | `Vx`=X, `Vx+1`=Y, `Vx+2`=W, `Vx+3`=H | Draws a solid filled rectangle at `(Vx, Vx+1)`. |
| `FX96` | `CIRCLE Vx` | `Vx`=X, `Vx+1`=Y, `Vx+2`=Radius | Draws an outline hollow circle centered at `(Vx, Vx+1)`. |
| `FX97` | `DISC Vx` | `Vx`=X, `Vx+1`=Y, `Vx+2`=Radius | Draws a solid filled circle (disc) centered at `(Vx, Vx+1)`. |
| `FX98` | `DRAWMODE Vx` | `Vx`=Mode (0..4) | Sets active drawing mode: `0`=XOR, `1`=SET, `2`=CLEAR, `3`=OPAQUE, `4`=INVERTED_OPAQUE. |
| `FX99` | `TESTPIXEL Vx` | `Vx`=X, `Vx+1`=Y | Zero-RAM collision detection: reads pixel at `(Vx, Vx+1)` into register `VF` (`1` if lit, `0` if off). Framebuffer is unmodified. |
| `FX9A` | `ROTATE Vx` | `Vx`=Rotation (0..3) | Sets display rotation transformation mode: `0`=0° (128×64 Landscape), `1`=90° CW (64×128 Portrait), `2`=180°, `3`=270° CW. All drawing operations and pixel tests are transformed. |
| `FX9B` | `TRIANGLE Vx` | `Vx`=X0, `Vx+1`=Y0, `Vx+2`=X1, `Vx+3`=Y1, `Vx+4`=X2, `Vx+5`=Y2 | Draws an outline triangle connecting 3 vertices via Bresenham's algorithm. Sets `VF` on collision. |
| `FX9C` | `RRECT Vx` | `Vx`=X, `Vx+1`=Y, `Vx+2`=W, `Vx+3`=H | Draws an outline rounded rectangle with 1px corner radius bevels. Sets `VF` on collision. |
| `FX9D` | `FILLRRECT Vx` | `Vx`=X, `Vx+1`=Y, `Vx+2`=W, `Vx+3`=H | Draws a solid filled rounded rectangle with 1px corner radius bevels. Sets `VF` on collision. |

### 5.2 Deterministic Input Polling

| Opcode | Mnemonic | Parameters | Description |
|---|---|---|---|
| `FXB0` | `GETKEYS Vx` | `Vx`=Destination | Reads instantaneous 4-button hardware bitmask into `Vx`: Bit 0=`UP` (`0x01`), Bit 1=`DOWN` (`0x02`), Bit 2=`LEFT` (`0x04`), Bit 3=`RIGHT` (`0x08`). Non-blocking. |

### 5.3 Typography & Number Formatting

All typography opcodes render using built-in u8g2 bitmap fonts:
- `Font 0`: `u8g2_font_4x6_tr` (4×6 compact numeric & ASCII)
- `Font 1`: `u8g2_font_siji_t_6x10` (6×10 standard UI)
- `Font 2`: `u8g2_font_likeminecraft_te` (8×8 retro arcade)

| Opcode | Mnemonic | Parameters | Description |
|---|---|---|---|
| `FXA0` | `TEXT Vx` | `Vx`=X, `Vx+1`=Y, `Vx+2`=Font | Renders null-terminated ASCII string pointed to by address `I` at `(Vx, Vx+1)`. Advances `Vx` to the end X coordinate. |
| `FXA1` | `CHAR Vx` | `Vx`=X, `Vx+1`=Y, `Vx+2`=Font, `Vx+3`=Char | Renders single ASCII character `Vx+3` at `(Vx, Vx+1)`. Advances `Vx` to the end X coordinate. |
| `FXA2` | `TEXTLEN Vx`| `Vx`=Out, `Vx+1`=Unused, `Vx+2`=Font | Measures pixel width of string pointed to by address `I` using font `Vx+2`. Stores width in `Vx`. |
| `FXA3` | `NUM Vx` | `Vx`=X, `Vx+1`=Y, `Vx+2`=Font | Formats 16-bit unsigned integer stored in register `I` (`0`..`65535`) at `(Vx, Vx+1)`. Advances `Vx` to the end X coordinate. |

