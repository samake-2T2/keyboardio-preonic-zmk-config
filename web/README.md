# Preonic Studio: Web GUI Configurator

**Preonic Studio** (`preonic-studio.html`) is a standalone, single-file Web application for configuring your Keyboardio Preonic MIT keyboard in real-time over USB CDC ACM serial without requiring any software installation, drivers, or npm dependencies.

100% clean-room MIT license, zero external CDN dependencies.

---

## 1. Quick Start

### 1.1 Requirements
- Any browser supporting the native **Web Serial API**:
  - Google Chrome (Desktop / Android)
  - Microsoft Edge
  - Brave Browser
  - Opera
- Keyboardio Preonic running firmware with Preonic Studio enabled (`CONFIG_KEYBOARDIO_PREONIC_STUDIO=y`).

### 1.2 Opening the App
Simply open `web/preonic-studio.html` directly in your browser:
- Double-click `preonic-studio.html`, or
- Press `Ctrl + O` in Chrome/Edge and select `preonic-studio.html`, or
- Run a local static file server if desired:
  ```bash
  python3 -m http.server 8000 --directory web/
  ```
  Then open `http://localhost:8000/preonic-studio.html`.

### 1.3 Linux Permissions (udev)
On Linux systems, ensure your user account belongs to the `dialout` or `uucp` group to access CDC ACM USB serial ports without root permissions:
```bash
sudo usermod -aG dialout $USER
```
*(Log out and log back in for group changes to take effect).*

---

## 2. Connecting to Your Keyboard

1. Plug your Preonic keyboard into your computer via USB.
2. Click **🔌 Connect USB** in the top-right corner of Preonic Studio.
3. A browser prompt will appear showing available serial ports. Select **Keyboardio Preonic** (USB Vendor ID: `0x3496`, Product ID: `0x00A1`) and click **Connect**.
4. The status badge will turn green: `Connected: Preonic`.

> **Tip:** You can also explore all features without physical hardware by clicking **🎮 Demo Mode**.

---

## 3. Physical Security Lock (`Fn + Z`)

To protect your stored macros (which may contain passwords or tokens) and prevent malicious websites from silently altering your keybindings, Preonic Studio enforces a **physical presence lock**:

1. **Default State**: Whenever the keyboard boots, connects over USB, or remains inactive for 5 minutes (300 seconds), it automatically locks.
2. **Unlocking**:
   - Hold the **Fn** key (Top-right key, Key #1).
   - Press the **Z** key (Row 4, Column 2, Key #40).
   - The on-board piezo buzzer plays an ascending unlock chime (`2000Hz` &rarr; `3000Hz`).
   - The 4 butterfly wing LEDs double-blink warm amber.
   - The Web GUI immediately receives an asynchronous `EVT_UNLOCKED` event and unlocks all editing controls in real-time.
3. **Manual Locking**: Click the **🔒 Lock Keyboard** button in the top bar at any time to re-lock immediately.

---

## 4. Tab Views & Features

### ⌨️ Tab 1: Keymap Editor
- **MIT Layout Representation**: Visual 5x12 ortholinear key grid + 3 top keys (PrtSc, Fn, Mute) + centered 2u Spacebar.
- **Layer Selector**: Switch between 5 layers:
  - `0: Base` (Standard typing layout)
  - `1: Lower` (Numpad, Navigation, F1–F12)
  - `2: Raise` (Mouse keys, Brackets, Symbols)
  - `3: Function` (Bluetooth, Output, Studio Unlock, Reset)
  - `4: TriFunction` (Activated when Lower + Raise are held together)
- **Click-to-Edit**: Click any keycap to open the categorized Keycode Picker modal:
  - Letters (A–Z)
  - Numbers & Symbols
  - Navigation & Editing
  - Modifiers (Shift, Ctrl, Alt, GUI)
  - Media & Volume
  - Layer operations (`&mo`, `&to`)
  - Special commands (`&trans`, `&none`, `&bt`, `&out`, `&bootloader`, `&sys_reset`, `&studio_unlock`)
- **Save to Flash**: Click **💾 Save to Flash** (`CMD_SAVE_KEYMAP`) to commit pending changes into Zephyr NVS flash memory so they persist across reboots and reconnections.
- **Revert Changes**: Click **↩ Revert Changes** (`CMD_DISCARD_KEYMAP`) to discard uncommitted RAM changes.

### 📜 Tab 2: Macro Manager
- **Slots 1, 2, 3**: Live step counter (up to 128 steps) and character length meter.
- **Direct Text Input**: Type or paste any string (up to 32 characters, uppercase and symbols supported) and click **💾 Write Text to Slot** (`CMD_SET_MACRO`).
- **Trigger Playback**: Click **▶ Play Macro on Keyboard** (`CMD_PLAY_MACRO`) to immediately execute the macro directly on the physical keyboard.
- **Backup & Restore**:
  - **📥 Backup Macros (.json)**: Download all 3 slots into a timestamped JSON file on your computer.
  - **📤 Restore Macros (.json)**: Upload a JSON backup file to restore your macros.

### 🎛️ Tab 3: Rotary Knob
- **Per-Layer Behavior**: Configure Clockwise (CW) and Counter-Clockwise (CCW) actions for each layer (Volume Up/Down, Scrolling, Page Up/Down, Track skipping).
- **Detent Sensitivity Slider**: Adjust the pulses-per-detent divider (2..16, default 2 for standard EC11 encoders).
- Click **💾 Apply Knob Settings** (`CMD_SET_KNOB`) to apply and store to NVS.

### 🔑 Tab 4: Password Generator
- **Length**: Quick buttons for 12, 16, 20, 24 characters or custom number input.
- **Custom Specials**: Edit the special character pool string (default `!@#$%*?_-.@`).
- **Typing Interval**: Adjust keystroke typing delay slider (5ms to 50ms, default 12ms).
- **Algorithm Preview**: Test simulated password generation with real-time entropy calculation and strength meter.
- Click **💾 Save Password Config** (`CMD_SET_PW_CONFIG`) to persist.

### 🖱️ Tab 5: Mouse & Smooth Scrolling
- **Mouse Movement (MMV)**: Time-to-max speed slider (100ms..2000ms) and acceleration curve exponent (0: Constant, 1: Linear, 2: Accelerated).
- **Mouse Scrolling (MSC)**: Acceleration curve exponent, time-to-max speed slider (100ms..2000ms), and scroll step size slider.
- **Interactive Sandbox**: Smooth scrolling sandbox area with test cards to test pointer and scroll feel in real-time.
- Click **💾 Save Mouse Config** (`CMD_SET_MOUSE_CFG`) to apply.

### 🔊 Tab 6: Audio & Hardware Telemetry
- **Piezo Buzzer Controls**:
  - Master audio sound toggle.
  - Mechanical clicky key sound toggle.
  - Frequency slider (1000 Hz to 6000 Hz, default 3000 Hz).
  - Duration slider (1ms to 20ms, default 5ms).
  - **🔔 Play Test Tone on Keyboard** (`CMD_TEST_PIEZO`): Hear the tone on the keyboard buzzer immediately!
- **Live Telemetry**: Real-time MAX17048 battery gauge (mV and SoC %), active BLE profile, and USB endpoint status.

---

## 5. Protocol Specification

Preonic Studio communicates over USB CDC ACM using a framed binary packet protocol:

```
+----------+----------+----------+----------+------------------+----------+----------+
|   SOF    |   CMD    |   SEQ    |   LEN    |     PAYLOAD      |  CHKSUM  |   EOF    |
|  (0xAB)  |  (1 Byte)|  (1 Byte)|  (1 Byte)|   (0..64 Bytes)  |  (1 Byte)|  (0xAD)  |
+----------+----------+----------+----------+------------------+----------+----------+
```

- **Checksum**: `(CMD + SEQ + LEN + sum(PAYLOAD)) & 0xFF`
- **Asynchronous Events**:
  - `0xFE`: `EVT_UNLOCKED` (Pushed when `Fn + Z` is pressed on hardware)
  - `0xFD`: `EVT_LOCKED` (Pushed on 300s inactivity or host disconnect)

---

## 6. License
Clean-room MIT License. Zero GPL code. Compatible with ZMK Firmware and Zephyr RTOS.
