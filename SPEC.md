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
| `6..7` | `flags` | `uint16_t` | Reserved for future runtime flags (default `0x0000`) |
| `8..31` | `title` | `char[24]` | UTF-8 null-terminated application display title |
| `32..47`| `author` | `char[16]` | UTF-8 null-terminated author string |
| `48..55`| `version` | `char[8]` | Semantic version string (e.g. `"1.0.0"`) |
| `56..87`| `icon` | `uint8_t[32]` | 16×16 monochrome 1-bit icon bitmap |
| `88..91`| `payload_size` | `uint32_t` | Byte length of payload following header |
| `92..95`| `crc32` | `uint32_t` | Optional CRC-32 checksum of the payload |

### 2.2 16×16 Icon Bitmap Format

The 32-byte application icon occupies header offsets `56..87` and follows the Super-CHIP 16×16 sprite bitmap convention:
- **Dimensions:** 16 rows × 16 columns (256 pixels total).
- **Encoding:** Row-major order; each row is exactly 2 bytes (16 bits).
- **Bit Order:** Big-endian per byte pair:
  - Byte `y * 2 + 0`: Pixels `x = 0..7` (Bit 7 is `x = 0`, Bit 0 is `x = 7`).
  - Byte `y * 2 + 1`: Pixels `x = 8..15` (Bit 7 is `x = 8`, Bit 0 is `x = 15`).
- **Polarity:** `1` = Lit pixel (OLED ON / white), `0` = Unlit pixel (OLED OFF / black).
- **Tooling:** Developers can generate icons from PNG/JPEG/BMP images, ASCII text grids, or procedural text glyphs using `tools/make_icon.py`.

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

## 4. Hardware Button Contract

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

> **Mandatory Exit Chord:** Pressing **UP** and **DOWN** simultaneously guarantees immediate, uninterceptable return to the device menu.
