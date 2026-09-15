# Preonic Studio Web GUI & Firmware Protocol Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a standalone, real-time Web GUI (Preonic Studio) and matching Zephyr C firmware subsystem for the Keyboardio Preonic to dynamically configure keymaps, macros, rotary knob, password generator, mouse keys, and piezo audio with physical presence security unlock (`Fn + Z`).

**Architecture:** A USB CDC ACM serial link communicates with the browser via the native Web Serial API (`navigator.serial`). A lightweight, robust binary packet framing protocol (`[0xAB][CMD][SEQ][LEN][DATA][CHKSUM][0xAD]`) delivers sub-millisecond round-trip command execution. Keymaps are modified dynamically using ZMK's `zmk_keymap_set_layer_binding_at_idx` and committed to NVS flash via `zmk_keymap_save_changes`. Dynamic macros, rotary encoder sensitivity, password generation parameters, mouse acceleration curves, and piezo audio parameters are persistently stored in Zephyr NVS. Mutating and private operations are guarded by a physical presence lock verified by `Fn + Z` matrix position detection.

**Tech Stack:** C (Zephyr RTOS / ZMK Firmware API, NVS Settings, CDC ACM UART, PWM Piezo), HTML5 / CSS3 / JavaScript (Web Serial API, Canvas API, SVG, Single-File Zero-Dependency Web App), Python 3 (Protocol test harness).

**Spec:** [`docs/superpowers/specs/2026-09-15-preonic-studio-web-design.md`](file:///root/samake-preonic-config/docs/superpowers/specs/2026-09-15-preonic-studio-web-design.md)

## Global Constraints
- **License**: 100% clean-room MIT license. Zero GPL code (no VIAL/QMK code snippets or GPL contaminated libraries).
- **Standalone Web App**: Single-file `web/preonic-studio.html`. Zero build step, zero npm dependencies, runs directly in browser.
- **Hardware Profile**: Keyboardio Preonic MIT Layout (5x12 grid + 3 top keys, EC11 encoder, MAX17048 battery gauge, 4 butterfly SK6812 LEDs, piezo buzzer on P0.28).
- **Security Lock**: Default locked on boot/disconnect/5-min timeout; unlocked physically by `Fn + Z` on physical keyboard.

---

### Task 1: Protocol Constants & Data Structures Header

**Files:**
- Create: `samake-preonic-config/include/preonic_studio.h`
- Test: `samake-preonic-config/scripts/test_preonic_studio_protocol.py`

**Interfaces:**
- Produces: `preonic_studio.h` with packet framing constants, opcodes, error codes, and configuration structures.
- Consumes: Standard `<stdint.h>`, `<stdbool.h>`, `<zephyr/types.h>`.

- [ ] **Step 1: Write protocol test harness**

```python
# samake-preonic-config/scripts/test_preonic_studio_protocol.py
import unittest

SOF = 0xAB
EOF = 0xAD

CMD_PING = 0x01
CMD_HANDSHAKE = 0x02
CMD_GET_LOCK_STATUS = 0x03
CMD_LOCK = 0x04
CMD_GET_STATUS = 0x05
CMD_GET_KEY = 0x10
CMD_SET_KEY = 0x11
CMD_SAVE_KEYMAP = 0x12
CMD_DISCARD_KEYMAP = 0x13
CMD_GET_KNOB = 0x20
CMD_SET_KNOB = 0x21
CMD_GET_MACRO = 0x30
CMD_SET_MACRO = 0x31
CMD_PLAY_MACRO = 0x32
CMD_GET_PW_CONFIG = 0x40
CMD_SET_PW_CONFIG = 0x41
CMD_GET_MOUSE_CFG = 0x50
CMD_SET_MOUSE_CFG = 0x51
CMD_GET_AUDIO_CFG = 0x60
CMD_SET_AUDIO_CFG = 0x61
CMD_TEST_PIEZO = 0x62
EVT_UNLOCKED = 0xFE
EVT_LOCKED = 0xFD

ERR_OK = 0x00
ERR_INVALID = 0x01
ERR_LOCKED = 0xEE

def calc_checksum(cmd, seq, length, data):
    total = cmd + seq + length + sum(data)
    return total & 0xFF

def encode_packet(cmd, seq, data=b""):
    length = len(data)
    chk = calc_checksum(cmd, seq, length, data)
    return bytes([SOF, cmd, seq, length]) + data + bytes([chk, EOF])

def decode_packet(buf):
    if len(buf) < 6:
        return None
    if buf[0] != SOF or buf[-1] != EOF:
        return None
    cmd = buf[1]
    seq = buf[2]
    length = buf[3]
    if len(buf) != 6 + length:
        return None
    data = buf[4:4+length]
    chk = buf[4+length]
    if chk != calc_checksum(cmd, seq, length, data):
        return None
    return {"cmd": cmd, "seq": seq, "data": data}

class TestPreonicStudioProtocol(unittest.TestCase):
    def test_packet_encode_decode(self):
        pkt = encode_packet(CMD_PING, 1, b"")
        self.assertEqual(len(pkt), 6)
        decoded = decode_packet(pkt)
        self.assertIsNotNone(decoded)
        self.assertEqual(decoded["cmd"], CMD_PING)
        self.assertEqual(decoded["seq"], 1)
        self.assertEqual(decoded["data"], b"")

    def test_packet_with_data(self):
        data = bytes([0x01, 0x02, 0x03, 0x04])
        pkt = encode_packet(CMD_SET_KEY, 42, data)
        self.assertEqual(len(pkt), 6 + 4)
        decoded = decode_packet(pkt)
        self.assertIsNotNone(decoded)
        self.assertEqual(decoded["cmd"], CMD_SET_KEY)
        self.assertEqual(decoded["seq"], 42)
        self.assertEqual(decoded["data"], data)

    def test_corrupted_checksum(self):
        pkt = bytearray(encode_packet(CMD_PING, 1, b""))
        pkt[-2] ^= 0xFF # corrupt checksum
        self.assertIsNone(decode_packet(pkt))

if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify protocol encoding logic**

Run: `python3 /root/samake-preonic-config/scripts/test_preonic_studio_protocol.py`
Expected: 3 tests PASS.

- [ ] **Step 3: Create `include/preonic_studio.h`**

```c
/*
 * Copyright (c) 2026 Keyboardio Preonic Custom Firmware
 * SPDX-License-Identifier: MIT
 */

#pragma once

#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

#define PREONIC_STUDIO_SOF 0xAB
#define PREONIC_STUDIO_EOF 0xAD
#define PREONIC_STUDIO_MAX_PAYLOAD 64

#define CMD_PING            0x01
#define CMD_HANDSHAKE       0x02
#define CMD_GET_LOCK_STATUS 0x03
#define CMD_LOCK            0x04
#define CMD_GET_STATUS      0x05

#define CMD_GET_KEY         0x10
#define CMD_SET_KEY         0x11
#define CMD_SAVE_KEYMAP     0x12
#define CMD_DISCARD_KEYMAP  0x13

#define CMD_GET_KNOB        0x20
#define CMD_SET_KNOB        0x21

#define CMD_GET_MACRO       0x30
#define CMD_SET_MACRO       0x31
#define CMD_PLAY_MACRO      0x32

#define CMD_GET_PW_CONFIG   0x40
#define CMD_SET_PW_CONFIG   0x41

#define CMD_GET_MOUSE_CFG   0x50
#define CMD_SET_MOUSE_CFG   0x51

#define CMD_GET_AUDIO_CFG   0x60
#define CMD_SET_AUDIO_CFG   0x61
#define CMD_TEST_PIEZO      0x62

#define EVT_UNLOCKED        0xFE
#define EVT_LOCKED          0xFD

#define STATUS_OK           0x00
#define STATUS_ERR_INVALID  0x01
#define STATUS_ERR_LOCKED   0xEE

void preonic_studio_init(void);
bool preonic_studio_is_locked(void);
void preonic_studio_unlock(void);
void preonic_studio_lock(void);
void preonic_studio_process_byte(uint8_t byte);

#ifdef __cplusplus
}
#endif
```

- [ ] **Step 4: Verify header validity**

Run: `gcc -fsyntax-only -I /root/samake-preonic-config/include /root/samake-preonic-config/include/preonic_studio.h`
Expected: Return code 0 (No syntax errors).

- [ ] **Step 5: Commit**

```bash
git add include/preonic_studio.h scripts/test_preonic_studio_protocol.py
git commit -m "feat(studio): add Preonic Studio protocol definitions and test harness"
```

---

### Task 2: Sound & Butterfly Visual Unlock Feedback

**Files:**
- Modify: `samake-preonic-config/include/preonic_sound.h:45-55`
- Modify: `samake-preonic-config/src/preonic_sound.c:220-250`
- Modify: `samake-preonic-config/include/butterfly_status.h:35-50`
- Modify: `samake-preonic-config/src/butterfly_status.c:200-240`

**Interfaces:**
- Produces: `preonic_sound_play_studio_unlock()`, `preonic_sound_play_studio_lock()`, `butterfly_show_studio_unlock()`
- Consumes: Existing PWM piezo driver in `preonic_sound.c` and SK6812 LED strip driver in `butterfly_status.c`.

- [ ] **Step 1: Declare unlock sound functions in `include/preonic_sound.h`**

Add declarations:
```c
void preonic_sound_play_studio_unlock(void);
void preonic_sound_play_studio_lock(void);
void preonic_sound_play_tone_ms(uint32_t freq_hz, uint32_t dur_ms);
```

- [ ] **Step 2: Implement unlock and lock tunes in `src/preonic_sound.c`**

Add ascending two-tone unlock tune (`2000Hz` for 60ms -> `3000Hz` for 80ms) and descending lock tone (`3000Hz` for 60ms -> `2000Hz` for 80ms), and direct frequency player:
```c
void preonic_sound_play_studio_unlock(void) {
    if (!sound_master_enabled) return;
    play_piezo_freq(2000);
    k_msleep(60);
    play_piezo_freq(3000);
    k_msleep(80);
    stop_piezo();
}

void preonic_sound_play_studio_lock(void) {
    if (!sound_master_enabled) return;
    play_piezo_freq(3000);
    k_msleep(60);
    play_piezo_freq(2000);
    k_msleep(80);
    stop_piezo();
}

void preonic_sound_play_tone_ms(uint32_t freq_hz, uint32_t dur_ms) {
    if (!sound_master_enabled) return;
    if (dur_ms > 2000) dur_ms = 2000;
    play_piezo_freq(freq_hz);
    k_msleep(dur_ms);
    stop_piezo();
}
```

- [ ] **Step 3: Declare and implement butterfly double-blink in `include/butterfly_status.h` and `src/butterfly_status.c`**

Add `void butterfly_show_studio_unlock(void);` to `include/butterfly_status.h`.
In `src/butterfly_status.c`, flash all 4 wings with warm amber (`RGB: 220, 120, 0`) twice with 80ms intervals, then restore current status.

- [ ] **Step 4: Verify syntax and compilation readiness**

Run: `git diff samake-preonic-config/include/preonic_sound.h samake-preonic-config/src/preonic_sound.c`
Expected: Clean additions of the sound and LED helper functions.

- [ ] **Step 5: Commit**

```bash
git add include/preonic_sound.h src/preonic_sound.c include/butterfly_status.h src/butterfly_status.c
git commit -m "feat(sound,led): add Preonic Studio physical unlock sound and visual indication"
```

---

### Task 3: Dynamic Macro & Password Generator API Extension

**Files:**
- Modify: `samake-preonic-config/include/dynamic_macro.h:45-55`
- Modify: `samake-preonic-config/src/dynamic_macro.c:120-170`
- Modify: `samake-preonic-config/include/password_generator.h:40-48`
- Modify: `samake-preonic-config/src/password_generator.c:70-120`

**Interfaces:**
- Produces:
  - `int dynamic_macro_set_slot_text(uint8_t slot_num, const char *text, uint16_t len)`
  - `uint16_t dynamic_macro_get_slot_steps(uint8_t slot_num, void *out_buf, uint16_t max_bytes)`
  - `void password_generator_get_config(uint8_t *default_len, uint8_t *interval_ms, char *specials, uint8_t *specials_len)`
  - `int password_generator_set_config(uint8_t default_len, uint8_t interval_ms, const char *specials, uint8_t specials_len)`
- Consumes: Internal buffers `slot1`, `slot2`, `slot3` in `dynamic_macro.c` and password generation pools in `password_generator.c`.

- [ ] **Step 1: Write unit test for ASCII text to HID keystroke conversion**

Add test in `scripts/test_preonic_studio_protocol.py` to test ASCII string encoding into keycode sequences (e.g. `'A'` -> `LSHFT + &kp A`, `'1'` -> `&kp N1`, `'!'` -> `LSHFT + &kp N1`).

- [ ] **Step 2: Run test to verify conversion logic**

Run: `python3 /root/samake-preonic-config/scripts/test_preonic_studio_protocol.py`
Expected: PASS.

- [ ] **Step 3: Implement macro text injection and retrieval in `src/dynamic_macro.c`**

Add `dynamic_macro_set_slot_text()`:
Converts an ASCII character stream into `struct dyn_macro_step` entries (handling Shift for uppercase and standard symbols), stores them in `get_slot_ptr(slot_num)`, updates `count`, and commits to flash via `dynamic_macro_save_slot(slot_num)`.
Add `dynamic_macro_get_slot_steps()` to allow Preonic Studio to read out slot contents.

- [ ] **Step 4: Implement password generator config getters & setters in `src/password_generator.c`**

Add `password_generator_get_config()` and `password_generator_set_config()`:
Allows runtime override of password length (12, 16, 20, 24), typing delay interval (5..50ms), and custom special characters pool with NVS persistence (`settings_save_one("pw_gen/config", ...)`).

- [ ] **Step 5: Commit**

```bash
git add include/dynamic_macro.h src/dynamic_macro.c include/password_generator.h src/password_generator.c scripts/test_preonic_studio_protocol.py
git commit -m "feat(macro,pwgen): expose dynamic text injection and configuration APIs"
```

---

### Task 4: Preonic Studio Firmware Engine (`src/preonic_studio.c`)

**Files:**
- Create: `samake-preonic-config/src/preonic_studio.c`
- Modify: `samake-preonic-config/CMakeLists.txt:1-17`
- Modify: `samake-preonic-config/Kconfig:1-115`
- Modify: `samake-preonic-config/config/keyboardio_preonic.conf:45-50`

**Interfaces:**
- Produces: `src/preonic_studio.c` USB CDC ACM serial message handler, command dispatcher, and physical unlock listener.
- Consumes:
  - `<zephyr/drivers/uart.h>`, `<zephyr/settings/settings.h>`
  - `<zmk/keymap.h>` (`zmk_keymap_get_layer_binding_at_idx`, `zmk_keymap_set_layer_binding_at_idx`, `zmk_keymap_save_changes`)
  - `preonic_sound.h`, `butterfly_status.h`, `dynamic_macro.h`, `password_generator.h`

- [ ] **Step 1: Write test for command dispatcher logic**

Extend `scripts/test_preonic_studio_protocol.py` to test parsing of:
- Handshake packet (`CMD_HANDSHAKE`)
- Lock check (`CMD_GET_LOCK_STATUS`)
- Lock rejection (`ERR_LOCKED`) when locked
- Unlocked execution of `CMD_SET_KEY` and `CMD_SET_MACRO`

- [ ] **Step 2: Run test to verify dispatcher requirements**

Run: `python3 /root/samake-preonic-config/scripts/test_preonic_studio_protocol.py`
Expected: All tests PASS.

- [ ] **Step 3: Implement `src/preonic_studio.c`**

Implement:
1. Packet receiver state machine (`preonic_studio_process_byte`).
2. Command handler functions for all opcodes (`CMD_PING` through `CMD_TEST_PIEZO`).
3. Physical unlock detection via `ZMK_SUBSCRIPTION(preonic_studio, zmk_position_state_changed)`:
   - When key position 40 (`Z` key) is pressed while `func_layer` (index 3) or `tri_layer` (index 4) is active:
     - `preonic_studio_unlock()`
     - Plays `preonic_sound_play_studio_unlock()`
     - Flashes `butterfly_show_studio_unlock()`
     - Sends `EVT_UNLOCKED` packet over serial!
4. Inactivity auto-lock workqueue (`k_work_delayable auto_lock_work`, 300s timeout).
5. USB CDC ACM UART callback registration and ring buffer TX.

- [ ] **Step 4: Update `CMakeLists.txt`, `Kconfig`, and `keyboardio_preonic.conf`**

Add `src/preonic_studio.c` to `CMakeLists.txt`.
Add `CONFIG_KEYBOARDIO_PREONIC_STUDIO=y` and `CONFIG_ZMK_KEYMAP_SETTINGS_STORAGE=y` to `keyboardio_preonic.conf`.
Ensure `CONFIG_ZMK_STUDIO=n` so that our custom Preonic Studio has exclusive, clean ownership of the CDC ACM UART port!

- [ ] **Step 5: Commit**

```bash
git add src/preonic_studio.c CMakeLists.txt Kconfig config/keyboardio_preonic.conf
git commit -m "feat(studio): implement Preonic Studio firmware engine with physical presence lock"
```

---

### Task 5: Standalone Single-File Web GUI (`web/preonic-studio.html`)

**Files:**
- Create: `samake-preonic-config/web/preonic-studio.html`
- Create: `samake-preonic-config/web/README.md`

**Interfaces:**
- Produces: Standalone single-file HTML5/CSS3/JavaScript Preonic Studio Web application.
- Consumes: Browser Web Serial API (`navigator.serial`).

- [ ] **Step 1: Create Web Serial communication core**

Implement in JavaScript:
- `PreonicConnection`: Web Serial port wrapper with auto-read loop and byte-by-byte packet framing matching `[0xAB][CMD][SEQ][LEN][DATA][CHKSUM][0xAD]`.
- Asynchronous request-response promise queue with timeout handling.
- Event listener for incoming `EVT_UNLOCKED` and `EVT_LOCKED` packets.

- [ ] **Step 2: Build Interactive Preonic MIT 5x12 Visual Keyboard**

Implement visual layout matching Keyboardio Preonic MIT layout:
- Top 3 system keys (PrtSc, Fn, Mute)
- 5x12 ortholinear key grid with centered 2u spacebar
- Visual layer selector (0: Base, 1: Lower, 2: Raise, 3: Function, 4: Tri)
- Click-to-edit modal with categorized keypicker (Letters, Numbers, Symbols, Modifiers, Layers, Media, System)
- Real-time binding updates and "Save to Keyboard" button

- [ ] **Step 3: Build Macro Manager Tab**

Implement:
- Slots 1, 2, 3 selector with live step counter
- Direct text input field to type a string and send directly into macro slot
- "Backup All Macros" to `.json` file on PC
- "Restore Macros" from `.json` file on PC
- "Test Play Macro" button to trigger slot playback from Web

- [ ] **Step 4: Build Rotary Knob, Password, Mouse, and Audio Tabs**

Implement:
- **Rotary Knob**: Layer dropdown, CW action selector, CCW action selector, Detent divider slider.
- **Password Generator**: Default length buttons (12, 16, 20, 24), custom special character pool editor, typing interval slider, instant generator test preview.
- **Mouse & Scroll**: MMV and MSC time-to-max speed sliders, acceleration exponent selector, and interactive test canvas.
- **Audio & Battery**: Master sound toggle, clicky pulse frequency slider with "Test Tone" live buzzer button, and real-time battery voltage & percentage gauge.
- **Security Lock Overlay**: Animated pulsing shield with instructions (*"Press Fn + Z on keyboard to unlock"*), which automatically disappears when `EVT_UNLOCKED` is received!

- [ ] **Step 5: Verify Web App standalone execution**

Open file locally and verify no syntax errors, verify Web Serial connection API bindings, verify layout rendering in viewport.

- [ ] **Step 6: Commit**

```bash
git add web/preonic-studio.html web/README.md
git commit -m "feat(web): create Preonic Studio standalone single-file Web GUI"
```

---

### Task 6: End-to-End Build, Test, and CI Verification

**Files:**
- Modify: `samake-preonic-config/scripts/wait_for_build.py`
- Test: GitHub Actions CI Build Workflow

- [ ] **Step 1: Run protocol and serialization test suite locally**

Run: `python3 /root/samake-preonic-config/scripts/test_preonic_studio_protocol.py`
Expected: All tests PASS.

- [ ] **Step 2: Push changes to GitHub repository**

```bash
cd /root/samake-preonic-config
git push origin master
```

- [ ] **Step 3: Monitor GitHub Actions build workflow**

Run: `python3 /root/samake-preonic-config/scripts/wait_for_build.py`
Expected: GitHub Actions build succeeds, producing `keyboardio_preonic__zmk.uf2`.

- [ ] **Step 4: Verify generated UF2 artifact**

Download and verify firmware artifact integrity and size.

- [ ] **Step 5: Tag release `v1.9.0` and update documentation**

Tag `v1.9.0` with release notes detailing Preonic Studio Web GUI and firmware protocol.
