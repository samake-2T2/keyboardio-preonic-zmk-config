# Keyboardio Preonic 배터리 모니터링 시스템 구현 계획서
(Butterfly LED 4-Level Gauge, Low Battery Alert & Auto Text Typer)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Keyboardio Preonic에서 `Fn + B` 입력 시 나비 날개 4단계 LED 게이지 점등(15% 이하 시 경고 비프음 동시 출력), 사용 중 최초 15% 진입 시 자동 1회 경고 비프음, `Fn + P` 입력 시 `"Battery: XX%"` 텍스트 자동 타이핑 기능을 구현하고 원격 저장소에 푸시합니다.

**Architecture:** `<zmk/battery.h>`의 `zmk_battery_state_of_charge()`를 기존 나비 LED 모듈(`src/butterfly_status.c`)과 피에조 사운드 엔진(`src/preonic_sound.c`), 그리고 비동기 텍스트 타이퍼(`src/battery_typer.c`)에 연결하고, 키맵의 `func_layer`에서 `B`(위치 44) 및 `P`(위치 24)를 인터셉트합니다.

**Tech Stack:** Zephyr RTOS, ZMK Firmware, MAX17048 Battery Fuel Gauge, WS2812 RGB LED Strip, nRF52840 PWM, ZMK HID Events, C

**Spec:** [`docs/superpowers/specs/2026-09-14-battery-status-system-design.md`](file:///root/samake-preonic-config/docs/superpowers/specs/2026-09-14-battery-status-system-design.md)

## Global Constraints

- 하드웨어 핀 및 소모 전류: MAX17048 I2C 버스, P0.24 WS2812 SPI, P0.22 PWM0
- 논블로킹 원칙: 텍스트 타이핑 및 사운드 출력 중 CPU busy-wait 절대 금지 (Zephyr 워크큐 활용)
- 절전 보존: 딥슬립(Deep Sleep) 시 모든 게이지 및 타이퍼 워크 취소
- ZMK Studio / Keymap Editor 완벽 호환: 키맵에 비표준 커스텀 키코드 선언 대신 `&none` 및 C 이벤트 리스너 인터셉트 사용

---

### Task 1: Low Battery Warning Sound in Sound Engine

**Files:**
- Modify: `include/preonic_sound.h`
- Modify: `src/preonic_sound.c`

**Interfaces:**
- Produces: `void preonic_sound_play_low_battery_warning(void)`
- Consumes: `pwm_set()` on PWM0 (1500Hz 더블 비프 시퀀스)

- [ ] **Step 1: include/preonic_sound.h에 경고음 함수 선언 추가**
  `void preonic_sound_play_low_battery_warning(void);` 추가
- [ ] **Step 2: src/preonic_sound.c에 더블 비프 상태 머신 구현**
  1500Hz 100ms → 80ms 무음 → 1500Hz 100ms 시퀀스 구현
- [ ] **Step 3: 커밋**
  `git commit -m "feat(sound): add low battery double-beep warning sequence"`

---

### Task 2: Butterfly LED 4-Level Gauge & Low Battery Detection

**Files:**
- Modify: `include/butterfly_status.h`
- Modify: `src/butterfly_status.c`

**Interfaces:**
- Produces: `void butterfly_show_battery(void)`
- Consumes: `<zmk/battery.h>` (`zmk_battery_state_of_charge()`), `preonic_sound_play_low_battery_warning()`

- [ ] **Step 1: include/butterfly_status.h에 게이지 함수 선언 추가**
  `void butterfly_show_battery(void);` 추가
- [ ] **Step 2: src/butterfly_status.c에 배터리 게이지 상태 및 색상 로직 구현**
  - 3초 지속 게이지 모드 (75% 이상: 4칸 초록, 50~74%: 3칸 연두, 25~49%: 2칸 주황, 25% 미만: 1칸 빨강)
  - 3초 경과 후 원래의 블루투스/USB 표시로 복귀
  - 수동 조회 시 15% 이하이면 `preonic_sound_play_low_battery_warning()` 호출
  - `zmk_battery_state_changed` 이벤트 구독하여 최초 15% 이하 진입 시 1회 자동 경고음 출력 (20% 이상 충전 시 리셋)
  - Fn + B (position 44) 누름 시 `butterfly_show_battery()` 인터셉트 호출
- [ ] **Step 3: 커밋**
  `git commit -m "feat(led): implement 4-level butterfly battery gauge and smart alert"`

---

### Task 3: Asynchronous Battery Text Typer

**Files:**
- Create: `include/battery_typer.h`
- Create: `src/battery_typer.c`
- Modify: `CMakeLists.txt`
- Modify: `src/butterfly_status.c` (Fn + P 이벤트 라우팅)

**Interfaces:**
- Produces: `void preonic_type_battery_status(void)`
- Consumes: `<zmk/battery.h>`, `<zmk/events/keycode_state_changed.h>`

- [ ] **Step 1: include/battery_typer.h 선언**
  `void preonic_type_battery_status(void);` 선언
- [ ] **Step 2: src/battery_typer.c 구현**
  - 현재 배터리 잔량을 읽어 `"Battery: XX%"` 문자열 생성
  - Zephyr 워크큐를 통해 글자당 12ms 간격으로 키코드 순차 전송
- [ ] **Step 3: CMakeLists.txt에 battery_typer.c 등록**
  타겟 소스에 `src/battery_typer.c` 추가
- [ ] **Step 4: butterfly_status.c의 이벤트 리스너에서 Fn + P (position 24) 감지 시 preonic_type_battery_status() 호출**
- [ ] **Step 5: 커밋**
  `git commit -m "feat(typer): implement async battery percentage text typer"`

---

### Task 4: Keymap & README Documentation

**Files:**
- Modify: `config/keyboardio_preonic.keymap`
- Modify: `README.md`

**Interfaces:**
- Consumes: `func_layer` and `tri_layer` key positions (P: 24, B: 44)

- [ ] **Step 1: keymap에서 func_layer 및 tri_layer의 P와 B 키를 &none으로 매핑**
  단축키 입력 시 기본 영문 자모 입력 방지
- [ ] **Step 2: README.md에 배터리 기능 및 Fn+B, Fn+P 가이드 추가**
  영문 및 한국어 설명에 배터리 확인법 상세 기술
- [ ] **Step 3: 커밋**
  `git commit -m "docs: document battery gauge and text typer in keymap and README"`

---

### Task 5: Build Verification & Push to Remote Repository

**Files:**
- Workspace: `/root/samake-preonic-config`

- [ ] **Step 1: Git 변경사항 및 구문 정적 검증**
- [ ] **Step 2: 원격 저장소 푸시 (`git push origin master`)**
- [ ] **Step 3: GitHub Actions 자동 빌드 모니터링 및 성공 확인**
- [ ] **Step 4: 로컬 최신 펌웨어 아티팩트 갱신 (`/root/latest_firmware/`)**
