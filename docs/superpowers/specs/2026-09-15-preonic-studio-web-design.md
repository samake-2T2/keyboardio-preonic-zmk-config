# Preonic Studio: Real-Time Web GUI & Firmware Protocol Specification
(Keyboardio Preonic MIT Layout Dynamic Configuration & Security Lock System)

- **Date**: 2026-09-15
- **Target Device**: Keyboardio Preonic (nRF52840 SoC, 5x12 MIT Ortholinear Grid, EC11 Rotary Encoder, MAX17048 Gauge, 4x SK6812 Butterfly LEDs, Piezo Buzzer)
- **Target Repository**: `samake-preonic-config`
- **Target Firmware**: ZMK Firmware (Zephyr RTOS)
- **License Compliance**: 100% Clean-Room MIT License (Strict zero-GPL policy; no QMK/VIAL code contamination)

---

## 1. Executive Summary & Goals

The standard ZMK Studio provides basic key remapping for standard alphanumeric keys, but lacks support for custom behaviors, rotary encoder layers, dynamic macro text editing/backup, hardware TRNG password generator tuning, mouse/smooth-scrolling parameters, and piezo buzzer audio feedback. Furthermore, existing tools like VIA and VIAL are licensed under GPLv2/GPLv3, which cannot be mixed into MIT-licensed ZMK firmware without copyright contamination.

**Preonic Studio** is a standalone, single-file Web application (`preonic-studio.html`) and matching Zephyr C firmware subsystem (`src/preonic_studio.c`) that provides:
1. **Dynamic Keymap Remapping**: Real-time layer-by-layer keycode reconfiguration (Layers 0..4, Row 0..4, Col 0..11) stored directly into NVS flash.
2. **Interactive Macro Manager**: Direct inspection, text editing, and injection into Dynamic Macro Slots 1, 2, and 3, plus JSON backup and restore on PC.
3. **Rotary Knob Configuration**: Per-layer CW/CCW behavior customization and sensitivity (pulses-per-detent divider) tuning.
4. **Hardware TRNG Password Generator Customization**: Default length (12, 16, 20, 24), customizable special character pool string, and typing speed delay.
5. **Mouse & Smooth Scrolling Optimization**: Mouse move (MMV) and mouse scroll (MSC) acceleration curve and time-to-max speed tuning.
6. **Piezo Audio & Live Battery Monitoring**: Master sound toggle, clicky pulse frequency/duration slider with live sound preview, and live battery percentage & voltage meter.
7. **Physical Security Lock**: Physical presence verification via `Fn + Z` on the keyboard matrix, auto-lock on disconnect and 5-minute inactivity, preventing malicious or unauthorized browser scripts from dumping sensitive macros or altering keys.

---

## 2. Communication Architecture & Transport Layer

### 2.1 Web Serial Transport
- **Protocol Endpoint**: USB CDC ACM Virtual COM Port (`snippet: studio-rpc-usb-uart` / `zephyr,cdc-acm-uart`).
- **Browser Compatibility**: Native Web Serial API (`navigator.serial`) supported in Google Chrome, Microsoft Edge, Opera, Brave without requiring driver installation or elevated administrator permissions on Linux, Windows, macOS, and Android.
- **Connection Configuration**:
  - Baud Rate: 115200 (USB full-speed virtual serial, 12 Mbps packet bus)
  - Data Bits: 8, Stop Bits: 1, Parity: None, Flow Control: None
  - USB Vendor ID (VID): `0x3496` (Keyboardio)
  - USB Product ID (PID): `0x00A1` (Preonic)

### 2.2 Packet Framing & Error Detection
Every packet between Preonic Studio (Browser) and Keyboard (Firmware) follows a bounded frame format:

```
+----------+----------+----------+----------+------------------+----------+----------+
|   SOF    |   CMD    |   SEQ    |   LEN    |     PAYLOAD      |  CHKSUM  |   EOF    |
|  (0xAB)  |  (1 Byte)|  (1 Byte)|  (1 Byte)|   (0..64 Bytes)  |  (1 Byte)|  (0xAD)  |
+----------+----------+----------+----------+------------------+----------+----------+
```

1. **SOF (Start of Frame)**: `0xAB` (Fixed marker)
2. **CMD (Command Opcode)**: Request / Response command identifier (`0x01`..`0xFE`)
3. **SEQ (Sequence ID)**: Client-generated 8-bit transaction counter; firmware echoes the exact SEQ in response to pair asynchronous transactions.
4. **LEN (Payload Length)**: Number of data bytes following (`0` to `64`). Packets with `LEN > 64` are rejected as framing errors.
5. **PAYLOAD (Data Bytes)**: Zero or more parameter bytes.
6. **CHKSUM (8-bit Checksum)**:
   $$\text{CHKSUM} = (\text{CMD} + \text{SEQ} + \text{LEN} + \sum_{i=0}^{\text{LEN}-1} \text{PAYLOAD}[i]) \pmod{256}$$
7. **EOF (End of Frame)**: `0xAD` (Fixed marker)

*Framing Immunity*: The receiver state machine uses `LEN` to read exactly `LEN` bytes before checking `CHKSUM` and `EOF`. Inner payload bytes matching `0xAB` or `0xAD` cannot trigger premature frame termination.

---

## 3. Command Protocol Specification

### 3.1 Status & Security
| CMD | Name | Direction | Payload (Req -> Resp) | Description |
|---|---|---|---|---|
| `0x01` | `CMD_PING` | Host -> Dev | None -> `[status(0)]` | Heartbeat / liveness check |
| `0x02` | `CMD_HANDSHAKE` | Host -> Dev | `[client_ver_maj, client_ver_min]` -> `[fw_maj, fw_min, fw_pat, locked(1B), layers(1B), rows(1B), cols(1B), name[16]]` | Negotiates protocol version & device geometry |
| `0x03` | `CMD_GET_LOCK_STATUS` | Host -> Dev | None -> `[locked(1B), timeout_s(2B)]` | Checks if `Fn + Z` unlock is active |
| `0x04` | `CMD_LOCK` | Host -> Dev | None -> `[status(0)]` | Immediately re-locks the keyboard |
| `0x05` | `CMD_GET_STATUS` | Host -> Dev | None -> `[batt_mv(2B), batt_pct(1B), active_prof(1B), usb_conn(1B), snd_master(1B), snd_clicky(1B)]` | Live telemetry readings |

### 3.2 Dynamic Keymap (Secured)
| CMD | Name | Direction | Payload (Req -> Resp) | Description |
|---|---|---|---|---|
| `0x10` | `CMD_GET_KEY` | Host -> Dev | `[layer(1B), key_idx(1B)]` -> `[layer, key_idx, beh_type(1B), param1(4B), param2(4B)]` | Reads key binding at given layer and position |
| `0x11` | `CMD_SET_KEY` | Host -> Dev | `[layer(1B), key_idx(1B), beh_type(1B), param1(4B), param2(4B)]` -> `[status(1B)]` | Overrides key binding in RAM |
| `0x12` | `CMD_SAVE_KEYMAP` | Host -> Dev | None -> `[status(1B)]` | Commits pending keymap overrides to Flash NVS |
| `0x13` | `CMD_DISCARD_KEYMAP` | Host -> Dev | None -> `[status(1B)]` | Reverts uncommitted keymap changes in RAM |

*Behavior Types*:
- `0x01`: `&kp` (Standard keycode, param1 = keycode)
- `0x02`: `&mo` (Momentary layer, param1 = layer index)
- `0x03`: `&to` (Switch layer, param1 = layer index)
- `0x04`: `&trans` (Transparent)
- `0x05`: `&none` (None)
- `0x06`: `&bt` (Bluetooth action, param1 = command, param2 = slot)
- `0x07`: `&out` (Output toggle/USB/BLE, param1 = command)
- `0x08`: `&studio_unlock` (Security unlock binding)
- `0x09`: `&sys_reset` / `&bootloader` (System command)

### 3.3 Rotary Encoder (Secured)
| CMD | Name | Direction | Payload (Req -> Resp) | Description |
|---|---|---|---|---|
| `0x20` | `CMD_GET_KNOB` | Host -> Dev | `[layer(1B)]` -> `[layer, cw_beh(1B), cw_param(4B), ccw_beh(1B), ccw_param(4B), pulses_per_detent(1B)]` | Reads knob actions for specified layer |
| `0x21` | `CMD_SET_KNOB` | Host -> Dev | `[layer(1B), cw_beh(1B), cw_param(4B), ccw_beh(1B), ccw_param(4B), pulses_per_detent(1B)]` -> `[status(1B)]` | Configures knob actions and detent sensitivity |

### 3.4 Dynamic Macros (Secured)
| CMD | Name | Direction | Payload (Req -> Resp) | Description |
|---|---|---|---|---|
| `0x30` | `CMD_GET_MACRO` | Host -> Dev | `[slot_num(1B)]` -> `[slot_num, step_count(2B), text_len(1B), text_or_steps[...]]` | Reads recorded macro slot contents |
| `0x31` | `CMD_SET_MACRO` | Host -> Dev | `[slot_num(1B), text_len(1B), ascii_text[...]]` -> `[status(1B)]` | Injects text directly into macro slot in NVS |
| `0x32` | `CMD_PLAY_MACRO` | Host -> Dev | `[slot_num(1B)]` -> `[status(1B)]` | Triggers playback of specified macro slot |

### 3.5 Password Generator (Secured)
| CMD | Name | Direction | Payload (Req -> Resp) | Description |
|---|---|---|---|---|
| `0x40` | `CMD_GET_PW_CONFIG` | Host -> Dev | None -> `[default_len(1B), typing_interval_ms(1B), specials_len(1B), specials_str[32]]` | Reads password generator settings |
| `0x41` | `CMD_SET_PW_CONFIG` | Host -> Dev | `[default_len(1B), typing_interval_ms(1B), specials_len(1B), specials_str[32]]` -> `[status(1B)]` | Updates password generator settings in NVS |

### 3.6 Mouse & Smooth Scrolling (Secured)
| CMD | Name | Direction | Payload (Req -> Resp) | Description |
|---|---|---|---|---|
| `0x50` | `CMD_GET_MOUSE_CFG`| Host -> Dev | None -> `[mmv_time_ms(2B), mmv_exp(1B), msc_time_ms(2B), msc_exp(1B), msc_step(1B)]` | Reads mouse acceleration parameters |
| `0x51` | `CMD_SET_MOUSE_CFG`| Host -> Dev | `[mmv_time_ms(2B), mmv_exp(1B), msc_time_ms(2B), msc_exp(1B), msc_step(1B)]` -> `[status(1B)]` | Updates mouse acceleration parameters |

### 3.7 Piezo Audio System (Secured)
| CMD | Name | Direction | Payload (Req -> Resp) | Description |
|---|---|---|---|---|
| `0x60` | `CMD_GET_AUDIO_CFG`| Host -> Dev | None -> `[master_en(1B), clicky_en(1B), freq_hz(2B), dur_ms(1B)]` | Reads piezo audio settings |
| `0x61` | `CMD_SET_AUDIO_CFG`| Host -> Dev | `[master_en(1B), clicky_en(1B), freq_hz(2B), dur_ms(1B)]` -> `[status(1B)]` | Updates piezo audio settings in NVS |
| `0x62` | `CMD_TEST_PIEZO`   | Host -> Dev | `[freq_hz(2B), dur_ms(2B)]` -> `[status(1B)]` | Plays instant preview tone on buzzer |

### 3.8 Asynchronous Event Notifications
| EVT | Name | Direction | Payload | Description |
|---|---|---|---|---|
| `0xFE` | `EVT_UNLOCKED` | Dev -> Host | `[unlocked_by(1B)]` | Pushed immediately when user presses `Fn + Z` on physical keyboard |
| `0xFD` | `EVT_LOCKED` | Dev -> Host | `[reason(1B)]` | Pushed when 5-min timeout or disconnect relocks studio |

---

## 4. Physical Security Lock Architecture

To ensure zero security risk from untrusted web pages, malicious browser tabs, or background scripts attempting to snoop on stored macros (which may contain passwords) or rebind keys into malicious keyloggers:

1. **Default State**:
   - On USB connection, system boot, or after 5 minutes of inactivity, `studio_locked = true`.
2. **Access Control**:
   - While `studio_locked == true`, all read queries for sensitive macro contents and all mutating commands (`CMD_SET_*`, `CMD_SAVE_*`) return `ERR_LOCKED` (`0xEE`).
   - Unsecured informational commands (`CMD_PING`, `CMD_HANDSHAKE`, `CMD_LOCK_STATUS`, `CMD_GET_STATUS`) return normal responses.
3. **Physical Unlock Procedure**:
   - The user presses `Fn + Z` (Physical matrix position: Key Index 40 in `func_layer` / `tri_layer`).
   - The firmware verifies physical hardware key press event.
   - The state machine toggles `studio_locked = false`.
   - The piezo buzzer plays a pleasant two-tone unlock chime (ascending `2000Hz` -> `3000Hz`).
   - The butterfly wing LEDs double-flash amber (`RGB: 200, 100, 0`) for visual confirmation.
   - An asynchronous notification `EVT_UNLOCKED` (`0xFE`) is sent to the Web GUI, which automatically transitions the UI from the locked overlay to the full editor interface.
4. **Auto-Relock Policies**:
   - Inactivity Timer: 300 seconds (5 minutes) without receiving a command resets `studio_locked = true`.
   - Transport Disconnect: DTR signal loss or USB disconnect immediately resets `studio_locked = true`.
   - Manual Lock: User clicks "Lock Keyboard" button in Web GUI (`CMD_LOCK` `0x04`).

---

## 5. Web GUI Architecture (`preonic-studio.html`)

### 5.1 Technology & File Structure
- **Format**: Single-file HTML5/CSS3/JavaScript (`web/preonic-studio.html`).
- **Dependencies**: Pure native Web APIs (Web Serial API, Canvas API, SVG, standard CSS Flexbox/Grid). Zero external CDN dependencies, zero npm build step, zero Node.js runtime required.
- **Color Palette & Theme**: Professional dark-mode aesthetic matching the Preonic industrial design:
  - Background: `#121316`
  - Cards & Panels: `#1a1c23`
  - Accent Brand: `#3b82f6` (Primary Blue) & `#10b981` (Success Green)
  - Keycap Colors: Alphanumeric `#2d3139`, Modifiers `#20232a`, Function/Layer `#374151`, Active `#3b82f6`
  - Warning/Alert: `#ef4444`

### 5.2 Application Modules & Views
1. **Top Header**:
   - Connection Status Badge: Disconnected / Connecting / Connected
   - Lock State Badge: 🔒 Locked (Click to view unlock hint) / 🔓 Unlocked
   - Battery Gauge: Dynamic battery icon with live percentage and voltage tooltip
   - Connect / Disconnect Button (triggers `navigator.serial.requestPort()`)
2. **Navigation Tabs**:
   - ⌨️ **Keymap**: Visual 5x12 MIT keyboard grid with Layer 0..4 switcher and keycode picker.
   - 📜 **Macros**: Slots 1..3 with live character count, text editor, PC file export/import, and instant trigger.
   - 🎛️ **Rotary Knob**: Per-layer CW / CCW binding selector and pulses-per-detent sensitivity slider.
   - 🔑 **Password Generator**: Default length selector, custom special characters pool editor, typing interval slider.
   - 🖱️ **Mouse & Scroll**: Acceleration curve toggles, speed sliders, and interactive smooth-scroll test sandbox.
   - 🔊 **Audio & Status**: Master sound toggle, clicky frequency slider with "Test Tone" button, live battery voltage and BLE status.
3. **Lock Overlay**:
   - If the keyboard is locked, the editing panels display an animated pulsing lock shield with clear instructions:
     *"Physical authorization required: Press Fn + Z on your Preonic keyboard to enable editing."*

---

## 6. Verification and Testing Criteria

1. **Clean-Room License Verification**:
   - Verify that all newly created C code in `src/preonic_studio.c` and `web/preonic-studio.html` contains the MIT copyright header with zero GPL code snippets.
2. **Firmware Compilation Verification**:
   - Compile firmware via GitHub Actions workflow and confirm successful build of `keyboardio_preonic__zmk.uf2`.
3. **Serial Protocol & Packet Verification**:
   - Verify packet serialization, checksum calculation, and command dispatch in browser console.
4. **Physical Unlock Security Verification**:
   - Confirm write commands return `0xEE` before unlock.
   - Confirm pressing `Fn + Z` unlocks the interface and plays the chime.
5. **Dynamic Flash Persistence Verification**:
   - Remap a key, save keymap, disconnect and reconnect USB, verify keymap remains intact from Flash.
