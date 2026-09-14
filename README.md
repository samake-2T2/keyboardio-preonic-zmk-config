# Keyboardio Preonic - ZMK Firmware Configuration

<p align="center">
  <a href="https://github.com/samake-2T2/keyboardio-preonic-zmk-config/releases/tag/v1.7.1"><img src="https://img.shields.io/badge/Release-v1.7.1-blue.svg?style=for-the-badge" alt="Latest Release v1.7.1"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-green.svg?style=for-the-badge" alt="MIT License"></a>
</p>

<p align="center">
  <a href="#english">English</a> | <a href="#한국어">한국어</a>
</p>

---

<a name="english"></a>
## English

Custom ZMK firmware configuration specifically developed for the **Keyboardio Preonic**, manufactured by [Keyboardio](https://keyboard.io).

> [!TIP]
> **Latest Release v1.7.1**: **Smart Hybrid Output Auto-Switching** (auto-defaults to last-active BLE profile when unplugged or cold-booted on battery switch, auto-engages USB when plugged into PC, maintains BLE on wall charger, zero-delay NVS Flash commit) & **3-Slot QMK-Compatible Dynamic Macro System** (`Fn + 5/6` Slot 1, `Fn + 7/8` Slot 2, `Fn + 9/0` Slot 3).

> [!IMPORTANT]
> **Hardware Compatibility Note**:
> This repository is exclusively configured for the **Keyboardio Preonic** (designed by Keyboardio), featuring an onboard nRF52840 BLE controller, EC11 rotary encoder, 2 dedicated auxiliary top keys, and central butterfly logo RGB underglow.
> **It is NOT compatible with standard Drop / OLKB Preonic boards**, which use completely different controllers, matrix wiring, and lack wireless/rotary hardware.

### ✨ Features

* **5×12 Ortholinear (MIT Layout)**: 62 keys total (including 2 top buttons, 1 rotary encoder push switch, and a centered 2U spacebar).
* **Rotary Encoder (EC11)**: Smooth volume control (`Volume Up / Down`) with click-to-mute (`C_MUTE`).
* **Enhanced Wireless Connection**: Bluetooth Low Energy (BLE) with 4 profile slots and **+8 dBm** transmit power for maximum stability.
* **Low-Latency Debouncing**: Optimized debouncing (1 ms press / 5 ms release) for rapid response and debounce error prevention.
* **Full NKRO**: N-Key Rollover enabled for simultaneous keypress accuracy.
* **RGB Underglow**: Keyboardio butterfly logo illuminated on startup with signature cyan breathing effect (`HSV: 195, 100, 100`).
* **Piezo Sound System**: Hardware PWM-driven onboard piezo buzzer with master sound control (`Fn + S`, default OFF for silence). When manually enabled, features a signature Super Mario coin chime on cold boot and crisp 5ms audio clicky feedback on keystrokes (`Fn + C`).
* **Battery Monitoring System**:
  * **`Fn + B` 4-Level Butterfly Gauge**: Displays battery level across the 4 butterfly wing LEDs for 3 seconds (75-100%: 4 Green, 50-74%: 3 Lime Green, 25-49%: 2 Orange, 0-24%: 1 Red). If battery is <= 15%, simultaneously emits a warning beep.
  * **Smart Low-Battery Alert**: Automatically sounds a 1500Hz double-beep warning once when battery first drops to <= 15% during use. Suppresses repeated alerts (only beeps on manual `Fn + B` afterwards) and resets once recharged to >= 20%.
  * **`Fn + P` Async Battery Typer**: Types out current battery status smoothly (e.g. `"82%"`) via asynchronous HID keystrokes without blocking key scanning or dropping characters, fully immune to Korean/English IME conversion issues.
* **Dynamic Macro System (QMK-Compatible)**:
  * **On-the-Fly Recording & Replay**: Record and play back keystrokes instantly without reflashing or software.
  * **NVS Flash Persistence**: Recorded macros are automatically saved to non-volatile flash memory (NVS) and preserved across power loss or reboot.
  * **Triple Independent Slots**: Slot 1 (`Fn + 5` Rec, `Fn + 6` Play), Slot 2 (`Fn + 7` Rec, `Fn + 8` Play), and Slot 3 (`Fn + 9` Rec, `Fn + 0` Play) up to 128 keystrokes each. Starting a new recording instantly clears and overwrites the previous macro.
  * **Visual & Audio Feedback**: Slot 1 breathes Red while recording and flashes Red on play. Slot 2 breathes Purple while recording and flashes Purple on play. Slot 3 breathes Gold while recording and flashes Gold on play. When Master Sound is enabled, provides distinct audio cues (rising chime on rec start, double-beep on rec stop, click on playback, warning buzz on buffer full).
  * **Safe 12ms Typing Interval**: Fixed 12ms step delay ensures reliable wireless transmission over Bluetooth Low Energy without dropped keystrokes.
* **Smart Hybrid Output Auto-Switching (Zero-Delay NVS Flash Retention)**:
  * **Unplug USB / Power Switch ON on Battery**: Instantly defaults to Bluetooth Low Energy (BLE) mode on the last-active profile (0..3), saving to NVS Flash without debounce delay to prevent connection drops on abrupt power cuts.
  * **PC USB Connection**: Automatically switches to USB mode as soon as USB HID communication is ready.
  * **Wall Charger / Power Bank**: Intelligently identifies charge-only power connections (`CONN_POWERED`) and maintains active BLE wireless typing.
  * **Manual Override**: `Fn + ~` (`OUT_TOG`) remains available at all times for manual USB/BLE toggling.
* **Mouse Emulation (ZMK Pointing)**: Integrated mouse cursor movement, clicking, and scrolling on the Raise layer.
* **Decoupled Tri-Layer & Dedicated Fn**: Enter the Function layer either via the dedicated top-middle `Fn` key (`&mo L_FN`) or by holding `Lower` and `Raise` simultaneously without conflict.
* **GUI Configurator Compatibility**:
  * **Keymap Editor**: Pre-configured layout metadata (`config/keyboardio_preonic.json` & `config/info.json`) with `row` and `col` properties for clean devicetree formatting.
  * **ZMK Studio**: Real-time keymap and layer adjustments over USB via ZMK Studio.

---

### 🗺️ Layer Map

#### 1. Base Layer
![Base Layer](https://raw.githubusercontent.com/samake-2T2/keyboardio-preonic-zmk-config/v1.7.0/docs/images/layer0_base.png)
* **Top Row (Right)**: `PrintScreen` | `Fn (L_FN)` | `Knob Click (Mute)`
* **Main Grid**: Standard Preonic ortholinear alpha layout with 2U Spacebar.
* **Thumbs**: `LCTRL`, `LGUI`, `LALT`, `RALT`, `Lower`, `Space`, `Raise`, Arrow keys (`Left`, `Down`, `Up`, `Right`).

#### 2. Lower Layer (Numpad & Navigation)
![Lower Layer](https://raw.githubusercontent.com/samake-2T2/keyboardio-preonic-zmk-config/v1.7.0/docs/images/layer1_lower.png)
* **Right Hand**: Dedicated 10-key numeric keypad (`KP_N0` ~ `KP_N9`, `.`, `Enter`).
* **Left Hand**: `F1` ~ `F11`, `Home`, `End`, `Page Up`, `Page Down`, `Insert`, `Delete`.

#### 3. Raise Layer (Symbols & Mouse Keys)
![Raise Layer](https://raw.githubusercontent.com/samake-2T2/keyboardio-preonic-zmk-config/v1.7.0/docs/images/layer2_raise.png)
* **Symbols**: Brackets, braces, parentheses, mathematical operators.
* **Mouse Emulation**: Cursor movement (`MOVE_UP`, `MOVE_DOWN`, etc.), buttons (`LCLK`, `RCLK`, `MCLK`, `MB4`, `MB5`), and wheel scrolling (`SCRL_UP`, `SCRL_DOWN`, etc.).

#### 4. Function Layer (Official Keyboardio Preonic Layout)
![Function Layer](https://raw.githubusercontent.com/samake-2T2/keyboardio-preonic-zmk-config/v1.7.0/docs/images/layer3_func.png)
* **Number Row**:
  * `Grave` position: `&out OUT_TOG` (Manual toggle between USB and BLE output; auto-switches to BLE on unplug/battery boot)
  * `1` ~ `4`: `&bt BT_SEL 0` ~ `&bt BT_SEL 3` (Select Bluetooth profiles 0 to 3, max 4 devices)
  * `5`: **Macro 1 Record / Stop** (`Fn + 5` toggle record start/stop; Red breathing LED)
  * `6`: **Macro 1 Playback** (`Fn + 6` replay macro 1; Red flash)
  * `7`: **Macro 2 Record / Stop** (`Fn + 7` toggle record start/stop; Purple breathing LED)
  * `8`: **Macro 2 Playback** (`Fn + 8` replay macro 2; Purple flash)
  * `9`: **Macro 3 Record / Stop** (`Fn + 9` toggle record start/stop; Gold breathing LED)
  * `0`: **Macro 3 Playback** (`Fn + 0` replay macro 3; Gold flash)
* **Alphabet Rows**:
  * `S` position: **Master Sound Toggle** (`Fn + S` toggles all piezo sound on/off; defaults to OFF, state persisted to NVS Flash across reboots/power cycles)
  * `Z` position: `&studio_unlock` (Unlock ZMK Studio)
  * `C` position: **Audio Clicky Toggle** (`Fn + C` toggles typing click sound on/off; high tone for ON, low tone for OFF)
  * `B` position: **Butterfly Battery Gauge** (`Fn + B` shows 4-level LED battery gauge while held; beeps if <= 15%)
  * `P` position: **Battery Status Typer** (`Fn + P` types out `"XX%"`)
* **Bottom Row**:
  * `LCTRL` position: `&bootloader` (Enter DFU bootloader mode)
  * `Right` position: `&bt BT_CLR` (Clear current Bluetooth bonding)

---

### 🦋 Butterfly Logo Bluetooth Status Indicator

The Keyboardio Preonic features a distinctive butterfly logo illuminated by 4 addressable RGB LEDs (SK6812/WS2812). Our custom driver replicates the factory Kaleidoscope firmware behavior by assigning each wing piece 1:1 to a Bluetooth profile:

| Wing Piece | Bluetooth Profile | Behavior: Pairing / Advertising | Behavior: Connected |
|:---:|:---:|:---:|:---:|
| **Wing 0** | Profile 0 (`BT_SEL 0`) | Blinks Azure/Cyan (400ms interval) | Solid Sapphire Blue (dims after 5s) |
| **Wing 1** | Profile 1 (`BT_SEL 1`) | Blinks Azure/Cyan (400ms interval) | Solid Sapphire Blue (dims after 5s) |
| **Wing 2** | Profile 2 (`BT_SEL 2`) | Blinks Azure/Cyan (400ms interval) | Solid Sapphire Blue (dims after 5s) |
| **Wing 3** | Profile 3 (`BT_SEL 3`) | Blinks Azure/Cyan (400ms interval) | Solid Sapphire Blue (dims after 5s) |

* **USB Mode**: All 4 wings illuminate in Emerald Green (when connected to PC USB host).
* **Smart Auto-Switching**: Unplugging the USB cable or turning on the external battery switch immediately restores the last active Bluetooth profile and wing indicator. Plugging into a wall charger keeps BLE active while charging.
* **Battery Saver**: Automatically dims to ambient brightness after 5s of connection, and shuts off completely in deep sleep.

---

### 📥 Flashing Firmware

1. **Build**: Every push to `master` triggers a GitHub Actions build producing a firmware `.uf2` artifact.
2. **Enter Bootloader Mode**:
   * **Via Keyboard**: Hold `Fn` and tap the bottom-left key (`LCTRL` position).
   * **Via Hardware**: Double-press the physical reset button on the board.
3. **Flash**: Drag and drop the downloaded `keyboardio_preonic__zmk.uf2` into the mounted USB mass-storage drive (`PREONIC`). The device will reboot automatically once finished.

---

### 🛠️ Web GUI Customization

* **[Keymap Editor](https://nickcoutsos.github.io/keymap-editor/)**: Connect your GitHub repository to visually customize bindings, combos, and rotary encoder actions.
* **[ZMK Studio](https://zmk.dev/docs/features/studio)**: Connect via WebUSB for instant on-the-fly key reassignment without rebuilding firmware.

---
---

<a name="한국어"></a>
## 한국어

[Keyboardio(키보디오)](https://keyboard.io) 사에서 개발 및 제조한 **Keyboardio Preonic** 기계식 키보드 전용 ZMK 펌웨어 설정 저장소입니다.

> [!TIP]
> **최신 릴리즈 v1.7.1**: **스마트 하이브리드 USB/BLE 자동 전환 & 무지연 NVS 플래시 보존** (USB 케이블 분리 또는 배터리 전원 인가 시 마지막 사용 BLE 슬롯으로 자동 전환, 돌발 전원 차단 방지 Zero-Delay NVS 영구 저장, PC 유선 연결 시 USB 자동 전환, 충전기/보조배터리 연결 시 무선 BLE 유지) 및 **3슬롯 QMK 호환 다이나믹 매크로 시스템** 탑재 (`Fn + 5/6` 슬롯1, `Fn + 7/8` 슬롯2, `Fn + 9/0` 슬롯3).

> [!IMPORTANT]
> **하드웨어 호환성 안내**:
> 본 저장소는 **Keyboardio사의 Preonic 모델 전용**으로 구성되어 있습니다. nRF52840 무선 BLE SoC, 상단 2개 보조 버튼(PrintScreen, Fn), EC11 로터리 인코더 노브, 중앙 나비 로고 RGB 언더글로우를 포함한 Keyboardio 고유의 기판/핀맵 사양을 지원합니다.
> **일반 Drop / OLKB Preonic 키보드와는 호환되지 않습니다** (컨트롤러, 매트릭스 핀 배치 및 무선/인코더 지원 여부가 완전히 다릅니다).

### ✨ 주요 기능

* **5×12 직교 배열 (MIT Layout)**: 중앙 2U 스페이스바, 상단 2개 보조 키 및 로터리 인코더 푸시 스위치 포함 총 62개 키 지원.
* **로터리 인코더 (EC11)**: 부드러운 볼륨 조절(`Volume Up / Down`) 및 클릭 시 음소거(`C_MUTE`) 동작.
* **안정적인 무선 연결**: 블루투스 저전력(BLE) 4개 프로필 슬롯 및 **+8 dBm 최대 송신 출력** 설정으로 연결 끊김 최소화.
* **초저지연 디바운스**: 1ms 누름 / 5ms 릴리즈 설정으로 키 입력 반응성 극대화 및 채터링 방지.
* **NKRO 완벽 지원**: 무한 동시 입력(N-Key Rollover) 지원.
* **Keyboardio 나비 로고 RGB 언더글로우**: 부팅 시 시그니처 스카이블루 숨쉬기(Cyan Breathing, `HSV: 195, 100, 100`) 효과 자동 점등.
* **피에조 사운드 시스템 (Piezo Sound)**: 하드웨어 PWM0 기반 피에조 부저 시스템으로, 마스터 사운드가 **기본 OFF(무음)**로 설정되어 있습니다. 사용자가 `Fn + S`로 수동 활성화한 경우에만 콜드 부팅 슈퍼마리오 코인 차임 및 5ms 기계식 오디오 클릭키(`Fn + C`), 배터리 경고음이 출력됩니다.
* **배터리 상태 모니터링 시스템**:
  * **`Fn + B` 나비 날개 4단계 LED 게이지**: 3초간 4개 나비 날개 LED로 배터리 잔량을 시각화 표시 (75~100%: 4개 초록, 50~74%: 3개 연두, 25~49%: 2개 주황, 0~24%: 1개 빨강). 잔량이 15% 이하인 경우 1500Hz 경고 비프음 동시 출력.
  * **스마트 저배터리 경고음**: 사용 중 배터리가 최초 15% 이하로 떨어지면 1500Hz 더블 비프음으로 1회 자동 경고. 이후 반복 비프를 억제하고 수동(`Fn + B`) 확인 시에만 경고음을 울리며, 충전하여 20% 이상 도달 시 플래그 자동 리셋.
  * **`Fn + P` 배터리 잔량 비동기 자동 타이핑**: 현재 배터리 상태(예: `"82%"`)를 비동기 HID 키 입력으로 매끄럽게 자동 타이핑 (한/영 IME 변환 영향 없이 순수 숫자 및 `%`만 출력).
* **QMK 호환 다이나믹 매크로 시스템 (Dynamic Macro)**:
  * **실시간 온더플라이 녹화 및 재생**: 별도 소프트웨어나 재빌드 없이 키보드에서 즉시 키 입력을 녹화하고 반복 실행.
  * **NVS 플래시 메모리 영구 보존**: 녹화 완료 시 Zephyr NVS(Non-Volatile Storage) 플래시에 자동 저장되어 전원 차단이나 방전, 재부팅 후에도 매크로 영구 유지.
  * **3개 독립 슬롯 지원**: 슬롯 1 (`Fn + 5` 녹화 토글, `Fn + 6` 재생), 슬롯 2 (`Fn + 7` 녹화 토글, `Fn + 8` 재생), 슬롯 3 (`Fn + 9` 녹화 토글, `Fn + 0` 재생) 각 최대 128키 저장. 새 녹화 시작 시 기존 매크로를 즉시 삭제하고 덮어쓰기.
  * **슬롯별 독립 LED 색상 및 사운드 피드백**: 슬롯 1 녹화 중 **빨간색 숨쉬기**, 재생 시 **빨간색 점등**. 슬롯 2 녹화 중 **보라색 숨쉬기**, 재생 시 **보라색 점등**. 슬롯 3 녹화 중 **골드 숨쉬기**, 재생 시 **골드 점등**. 마스터 사운드 ON 상태일 때 시작 상승음, 종료 더블 비프, 재생 클릭음, 버퍼 초과 경고음 출력.
  * **12ms 무선 안정 고정 딜레이**: BLE 무선 통신 시 키 누락(키 씹힘)을 완벽 방지하는 12ms 안전 딜레이 인터벌 적용.
* **스마트 하이브리드 USB/BLE 자동 전환 (Zero-Delay NVS Flash 보존)**:
  * **USB 분리 & 배터리 전원 스위치 ON**: USB 케이블을 뽑거나 외부 전원 스위치를 켤 때 자동으로 마지막으로 활성화되었던 블루투스(BLE) 슬롯(0~3번)으로 즉시 전환됩니다.
  * **돌발 전원 차단 방지 무지연 NVS 플래시 저장**: ZMK 기본 1초 디바운스 대기를 건너뛰고 `settings_save_one`으로 플래시에 즉시 커밋하여, 전환 직후 전원을 꺼도 설정이 유실되지 않습니다.
  * **PC USB 연결 시 자동 전환**: PC에 케이블을 연결하여 HID 통신이 준비되면 즉시 USB 유선 모드로 자동 전환됩니다.
  * **충전기/보조배터리 연결 시 BLE 유지**: 단순 충전기(Power-only)에 연결된 경우 블루투스 모드를 가로채지 않고 무선 타이핑 상태를 그대로 유지합니다.
  * **수동 강제 토글**: 언제든 `Fn + ~` (`OUT_TOG`) 조합으로 유/무선 출력을 수동 토글할 수 있습니다.
* **마우스 에뮬레이션 (ZMK Pointing)**: Raise 레이어에서 마우스 커서 이동, 클릭, 휠 스크롤 지원.
* **트라이 레이어 및 독립 Fn 동시 지원 (디커플링)**: 상단 중앙 독립 `Fn` 키(`&mo L_FN`) 진입과 `Lower` + `Raise` 동시 입력을 통한 트라이 레이어 진입을 충돌 없이 완벽히 지원.
* **웹 GUI 도구 완벽 호환**:
  * **Keymap Editor**: 전용 레이아웃 메타데이터(`row`, `col` 포함)를 완비하여 소스코드 가독성 경고 해결 및 깔끔한 코드 정렬 지원.
  * **ZMK Studio**: 펌웨어 재빌드 없이 실시간으로 키 매핑을 수정할 수 있는 ZMK Studio 지원.

---

### 🗺️ 레이어 구성

#### 1. 기본 레이어 (Base Layer)
![기본 레이어](https://raw.githubusercontent.com/samake-2T2/keyboardio-preonic-zmk-config/v1.7.0/docs/images/layer0_base.png)
* **상단 우측 3키**: `PrintScreen` (화면 캡처) | `Fn (L_FN)` (펑션 레이어 진입) | `노브 클릭` (음소거)
* **알파벳 열**: 표준 Preonic 직교 영문 자판 및 중앙 2U 스페이스바.
* **하단 열**: `LCTRL`, `LGUI`, `LALT`, `RALT`, `Lower`, `Space`, `Raise`, 방향키 (`Left`, `Down`, `Up`, `Right`).

#### 2. 로워 레이어 (Lower Layer - 숫자 패드 & 내비게이션)
![로워 레이어](https://raw.githubusercontent.com/samake-2T2/keyboardio-preonic-zmk-config/v1.7.0/docs/images/layer1_lower.png)
* **우측 손**: 텐키리스 숫자 키패드(`KP_N0` ~ `KP_N9`, `.`, `Enter`).
* **좌측 손**: `F1` ~ `F11`, `Home`, `End`, `Page Up`, `Page Down`, `Insert`, `Delete`.

#### 3. 레이즈 레이어 (Raise Layer - 특수기호 & 마우스)
![레이즈 레이어](https://raw.githubusercontent.com/samake-2T2/keyboardio-preonic-zmk-config/v1.7.0/docs/images/layer2_raise.png)
* **특수 기호**: 괄호(`[]`, `{}`, `()`), 연산 기호 등 프로그래밍에 유용한 기호 배치.
* **마우스 제어**: 커서 이동(`MOVE_UP`, `MOVE_DOWN` 등), 클릭(`좌클릭`, `우클릭`, `휠클릭`, `앞/뒤로가기`), 휠 스크롤.

#### 4. 펑션 레이어 (Function Layer - 공식 순정 키맵 규격)
![펑션 레이어](https://raw.githubusercontent.com/samake-2T2/keyboardio-preonic-zmk-config/v1.7.0/docs/images/layer3_func.png)
* **숫자 행**:
  * `Grave` 자리: **`&out OUT_TOG`** (USB 유선 / 블루투스 무선 출력 모드 수동 토글; USB 분리 및 배터리 부팅 시 BLE 자동 전환)
  * `1 ~ 4` 자리: **`&bt BT_SEL 0 ~ 3`** (블루투스 기기 프로필 0번 ~ 3번, 총 4대 선택)
  * `5` 자리: **매크로 1 녹화 시작 / 종료 토글** (`Fn + 5` 입력 시 슬롯 1 녹화/종료, 녹화 중 나비 빨간색 숨쉬기)
  * `6` 자리: **매크로 1 재생** (`Fn + 6` 슬롯 1 매크로 실행, 나비 빨간색 점등)
  * `7` 자리: **매크로 2 녹화 시작 / 종료 토글** (`Fn + 7` 입력 시 슬롯 2 녹화/종료, 녹화 중 나비 보라색 숨쉬기)
  * `8` 자리: **매크로 2 재생** (`Fn + 8` 슬롯 2 매크로 실행, 나비 보라색 점등)
  * `9` 자리: **매크로 3 녹화 시작 / 종료 토글** (`Fn + 9` 입력 시 슬롯 3 녹화/종료, 녹화 중 나비 골드 숨쉬기)
  * `0` 자리: **매크로 3 재생** (`Fn + 0` 슬롯 3 매크로 실행, 나비 골드 점등)
* **알파벳 행**:
  * `S` 자리: **키보드 전체 사운드 On/Off 마스터 토글** (`Fn + S` 입력 시 모든 피에조 사운드 마스터 활성화/비활성화, 기본값 OFF, NVS 플래시 영구 저장으로 전원 차단/재부팅 후에도 설정 유지)
  * `Z` 자리: **`&studio_unlock`** (ZMK Studio 잠금 해제)
  * `C` 자리: **오디오 클릭키 On/Off 토글** (`Fn + C` 입력 시 타이핑 클릭 소리를 켜고 끄며, 켤 때 높은 톤 / 끌 때 낮은 톤 확인음 제공)
  * `B` 자리: **나비 배터리 게이지** (`Fn + B` 누르고 있는 동안 4단계 나비 LED 잔량 게이지 표시, 15% 이하 시 경고 비프음 출력)
  * `P` 자리: **배터리 잔량 자동 타이핑** (`Fn + P` 입력 시 `"XX%"` 텍스트 자동 타이핑)
* **하단 행**:
  * `LCTRL` 자리: **`&bootloader`** (USB 외장 드라이브 부트로더 모드 진입)
  * `Right` 자리: **`&bt BT_CLR`** (현재 연결된 블루투스 페어링 정보 삭제)

---

### 🦋 나비 로고 블루투스 상태 표시기 (1:1 매핑)

Keyboardio Preonic 상단 중앙의 나비 로고에는 4개의 어드레서블 RGB LED(SK6812/WS2812)가 내장되어 있습니다. 본 설정의 커스텀 드라이버는 공장 순정 Kaleidoscope 펌웨어의 동작 방식을 완벽히 재현하여 4개의 날개 조각을 블루투스 프로필 0~3번에 1:1로 매핑합니다:

| 날개 조각 위치 | 할당 프로필 | 페어링 대기 / 탐색 중 동작 | 연결 완료(Connected) 동작 |
|:---:|:---:|:---:|:---:|
| **날개 0번 (Wing 0)** | 0번 슬롯 (`BT_SEL 0`) | 하늘색/청록색 깜빡임 (400ms 주기) | 사파이어 블루 점등 (5초 후 은은한 밝기로 전환) |
| **날개 1번 (Wing 1)** | 1번 슬롯 (`BT_SEL 1`) | 하늘색/청록색 깜빡임 (400ms 주기) | 사파이어 블루 점등 (5초 후 은은한 밝기로 전환) |
| **날개 2번 (Wing 2)** | 2번 슬롯 (`BT_SEL 2`) | 하늘색/청록색 깜빡임 (400ms 주기) | 사파이어 블루 점등 (5초 후 은은한 밝기로 전환) |
| **날개 3번 (Wing 3)** | 3번 슬롯 (`BT_SEL 3`) | 하늘색/청록색 깜빡임 (400ms 주기) | 사파이어 블루 점등 (5초 후 은은한 밝기로 전환) |

* **USB 유선 모드**: PC에 유선 연결 시 4개 날개 전체가 에메랄드 그린(Green)으로 점등.
* **스마트 자동 전환**: 케이블 분리나 배터리 스위치 ON 시 마지막 사용된 블루투스 슬롯으로 즉시 복귀하며, 충전기 연결 중에도 블루투스 무선 모드가 유지됩니다.
* **사용자 선택 우선순위**: USB 유선 케이블이 연결되어 있어도 블루투스 슬롯을 선택하면 날개 LED가 해당 블루투스 상태를 즉시 표시합니다.
* **스마트 배터리 절전**: 연결 완료 5초 후 저전력 은은한 밝기로 자동 감광되며, 키보드가 딥슬립(Deep Sleep)에 진입하면 모든 LED가 완전히 꺼져 배터리 소모를 0으로 유지합니다.

---

### 📥 펌웨어 빌드 및 설치 방법

1. **자동 빌드**: `master` 브랜치에 코드를 푸시하면 GitHub Actions 파이프라인이 자동으로 펌웨어를 빌드하여 릴리스/아티팩트로 생성합니다.
2. **부트로더 진입 방법**:
   * **키 조합**: `Fn` 키(또는 Lower + Raise)를 누른 상태에서 하단 가장 왼쪽 키(`LCTRL` 자리)를 입력합니다.
   * **물리 버튼**: 키보드 기판의 리셋 버튼을 빠르게 2회 클릭합니다.
3. **설치**: PC에 `PREONIC`이라는 이름의 외장 드라이브가 인식되면, 다운로드한 `keyboardio_preonic__zmk.uf2` 파일을 드래그 앤 드롭(또는 복사)합니다. 복사가 완료되면 자동으로 키보드가 재부팅되며 새 펌웨어가 적용됩니다.

---

### 🛠️ 웹 GUI 설정 도구 활용

* **[Keymap Editor](https://nickcoutsos.github.io/keymap-editor/)**: GitHub 계정을 연결하여 웹 브라우저에서 직관적으로 키맵, 콤보, 인코더 바인딩을 수정할 수 있습니다.
* **[ZMK Studio](https://zmk.dev/docs/features/studio)**: WebUSB를 지원하는 브라우저(Chrome, Edge 등)에서 키보드를 연결하면 펌웨어 플래시 없이 즉시 키를 바꿀 수 있습니다.

---

### 📂 저장소 구조

```text
├── .github/workflows/build.yml   # GitHub Actions 빌드 자동화 워크플로우
├── CMakeLists.txt                # Zephyr 빌드 타겟 및 소스 등록
├── Kconfig                       # 나비 인디케이터 Kconfig 메뉴 및 옵션 정의
├── include/                      # C 헤더 파일 (butterfly_status, preonic_sound, battery_typer, dynamic_macro)
├── src/                          # C 소스 파일 (butterfly_status, preonic_sound, battery_typer, dynamic_macro)
├── boards/keyboardio/            # Keyboardio Preonic 보드 및 DTS 정의
├── config/
│   ├── keyboardio_preonic.keymap # 5단계 레이어 키 매핑 정의 (Base, Lower, Raise, Function, Tri)
│   ├── keyboardio_preonic.conf   # 블루투스, 나비 인디케이터, NKRO 설정
│   ├── keyboardio_preonic.json   # Keymap Editor용 레이아웃 메타데이터
│   ├── info.json                 # GUI 도구 호환용 표준 메타데이터
│   └── west.yml                  # ZMK 빌드 매니페스트
├── zephyr/                       # Zephyr 모듈 매니페스트 (module.yml)
├── build.yaml                    # 빌드 타겟 보드 및 스니펫 지정
└── LICENSE                       # MIT License
```

---

### 📄 License

This project is open source and available under the [MIT License](LICENSE).
Copyright (c) 2026 samake-2T2.

