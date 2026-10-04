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

## 2. Header Layout (Exactly 100 Bytes, Packed Little-Endian)

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
|                 High Score / Persistent State                 |  [92..95]
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                            CRC-32                             |  [96..99]
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
| `6..7` | `flags` | `uint16_t` | Bitmask flags: Bit 0 = high score valid, Bit 1 = mini-app |
| `8..31` | `title` | `char[24]` | UTF-8 null-terminated application display title |
| `32..47`| `author` | `char[16]` | UTF-8 null-terminated author string |
| `48..55`| `version` | `char[8]` | Semantic version string (e.g. `"1.0.0"`) |
| `56..87`| `icon` | `uint8_t[32]` | 16×16 monochrome 1-bit icon bitmap |
| `88..91`| `payload_size` | `uint32_t` | Byte length of payload following header |
| `92..95`| `high_score` | `uint32_t` | Persistent high score or state |
| `96..99`| `crc32` | `uint32_t` | Optional CRC-32 checksum of the payload |

---

## 3. Hardware Button Contract

Flashiibo Gen3 features four physical buttons:

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

> **Mandatory Exit Chord:** Pressing **UP** and **DOWN** simultaneously guarantees immediate, uninterceptable return to the device menu.
