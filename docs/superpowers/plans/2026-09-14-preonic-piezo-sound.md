# Keyboardio Preonic 피에조 사운드 시스템 구현 계획서
(Super Mario Coin Boot Greeting & Audio Clicky)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Keyboardio Preonic의 P0.22 핀에 연결된 피에조 부저를 하드웨어 PWM0로 제어하여 슈퍼마리오 코인 부팅 멜로디 및 Fn+C로 토글 가능한 오디오 클릭키(Audio Clicky) 기능을 구현하고 원격 저장소에 푸시합니다.

**Architecture:** Nordic nRF52840의 하드웨어 PWM0 컨트롤러를 P0.22 핀에 매핑하고, Zephyr 논블로킹 워크큐(`k_work_delayable`) 기반의 독립 사운드 엔진(`src/preonic_sound.c`)을 통해 CPU 지연 없이 8비트 코인 멜로디 및 5ms 초저지연 키 클릭음을 재생합니다.

**Tech Stack:** Zephyr RTOS, ZMK Firmware, nRF52840 Hardware PWM (`nrfx_pwm`), C, Devicetree (DTS), Kconfig, CMake

**Spec:** [`docs/superpowers/specs/2026-09-14-preonic-piezo-sound-design.md`](file:///root/samake-preonic-config/docs/superpowers/specs/2026-09-14-preonic-piezo-sound-design.md)

## Global Constraints

- 하드웨어 핀: nRF52840 `P0.22` (스피커 전용 핀)
- 키 스캔 및 블루투스 성능 보장: 사운드 출력 중 CPU busy-wait 루프 절대 금지 (논블로킹 타이머/워크큐 활용)
- 절전 보존: 소리가 나지 않을 때는 PWM 듀티비 0 및 딥슬립 시 PWM 전원 차단
- ZMK Studio / Keymap Editor 호환성 유지: 비표준 커스텀 키코드 난립 방지, 표준 이벤트 핸들러 방식 사용

---

### Task 1: Hardware Devicetree & Defconfig Setup (DTS PWM0 on P0.22)

**Files:**
- Modify: `boards/keyboardio/keyboardio_preonic/keyboardio_preonic_nrf52840_zmk.dts`
- Modify: `boards/keyboardio/keyboardio_preonic/keyboardio_preonic_nrf52840_zmk_defconfig`

**Interfaces:**
- Produces: `&pwm0` hardware device node mapped to `P0.22` with `pwm0_default` and `pwm0_sleep` pinctrl states
- Consumes: Nordic nRF52840 pinctrl macros `NRF_PSEL(PWM_OUT0, 0, 22)`

- [ ] **Step 1: DTS 파일에 pwm0 pinctrl 및 pwm0 노드 추가**
  `keyboardio_preonic_nrf52840_zmk.dts`에 `pwm0_default`, `pwm0_sleep` 및 `&pwm0` 노드 정의
- [ ] **Step 2: defconfig 파일에 PWM 드라이버 활성화 옵션 추가**
  `keyboardio_preonic_nrf52840_zmk_defconfig`에 `CONFIG_PWM=y`, `CONFIG_PWM_NRFX=y` 추가
- [ ] **Step 3: DTS 구문 검증**
  DTS 문법 오류가 없는지 파싱 확인
- [ ] **Step 4: 커밋**
  `git commit -m "feat(dts): enable pwm0 on P0.22 for piezo speaker"`

---

### Task 2: Kconfig and CMakeLists Configuration

**Files:**
- Modify: `Kconfig`
- Modify: `CMakeLists.txt`
- Modify: `config/keyboardio_preonic.conf`

**Interfaces:**
- Produces: `CONFIG_KEYBOARDIO_PREONIC_SOUND`, `CONFIG_PREONIC_SOUND_CLICKY_DEFAULT`, `CONFIG_PREONIC_SOUND_COIN_BOOT`
- Consumes: `CONFIG_PWM`

- [ ] **Step 1: Kconfig에 사운드 모듈 메뉴 및 옵션 정의**
  `KEYBOARDIO_PREONIC_SOUND` 및 클릭키 기본값, 코인 부팅음 활성화 옵션 추가
- [ ] **Step 2: CMakeLists.txt에 `preonic_sound.c` 빌드 대상 등록**
  `CONFIG_KEYBOARDIO_PREONIC_SOUND` 활성화 시 C 소스 컴파일되도록 등록
- [ ] **Step 3: config/keyboardio_preonic.conf에 설정 추가**
  `CONFIG_KEYBOARDIO_PREONIC_SOUND=y` 명시
- [ ] **Step 4: 커밋**
  `git commit -m "feat(kconfig): add piezo sound subsystem build options"`

---

### Task 3: Sound Engine Subsystem Implementation (`include/preonic_sound.h`, `src/preonic_sound.c`)

**Files:**
- Create: `include/preonic_sound.h`
- Create: `src/preonic_sound.c`

**Interfaces:**
- Produces: 
  - `void preonic_sound_play_tone(uint32_t freq_hz, uint32_t duration_ms)`
  - `void preonic_sound_play_coin(void)`
  - `void preonic_sound_play_click(void)`
  - `void preonic_sound_toggle_clicky(void)`
- Consumes:
  - `<zephyr/drivers/pwm.h>` (`pwm_set_dt` / `pwm_set_cycles` / `pwm_set`)
  - `<zmk/events/position_state_changed.h>`
  - `<zmk/events/activity_state_changed.h>`

- [ ] **Step 1: include/preonic_sound.h 헤더 정의**
  사운드 서브시스템 공개 함수 원형 선언
- [ ] **Step 2: src/preonic_sound.c 구현**
  - PWM 하드웨어 초기화 및 안전성 검증 (`device_is_ready`)
  - 비동기 워크큐 기반 슈퍼마리오 코인 시퀀스 (B5 988Hz 65ms -> E6 1319Hz 350ms)
  - 3,000Hz 5ms 초저지연 오디오 클릭키 펄스 재생
  - Fn+C 입력 감지 시 토글 및 2400Hz(ON) / 1200Hz(OFF) 피드백 톤 재생
  - 딥슬립 진입 시 사운드 강제 중단 및 PWM 전력 차단
- [ ] **Step 3: C 소스 구문 및 타입 무결성 검증**
  컴파일 에러 및 경고 가능성 정적 분석
- [ ] **Step 4: 커밋**
  `git commit -m "feat(sound): implement mario coin greeting and audio clicky engine"`

---

### Task 4: Keymap Integration & Documentation

**Files:**
- Modify: `config/keyboardio_preonic.keymap`
- Modify: `README.md`

**Interfaces:**
- Consumes: Function Layer (L_FN) key event on position 42 (C key)

- [ ] **Step 1: README.md에 사운드 기능 및 Fn+C 단축키 설명 추가**
  영문 및 한국어 설명에 피에조 사운드, 슈퍼마리오 부팅음, 오디오 클릭키 토글 안내 반영
- [ ] **Step 2: 커밋**
  `git commit -m "docs: document piezo sound features and Fn+C toggle in README"`

---

### Task 5: Verification & Push to Remote Repository

**Files:**
- Workspace: `/root/samake-preonic-config`

- [ ] **Step 1: Git 저장소 변경사항 전수 확인**
  `git diff`, `git status` 확인
- [ ] **Step 2: 원격 저장소 푸시 (`git push origin master`)**
  GitHub 원격 저장소에 커밋 푸시
- [ ] **Step 3: GitHub Actions 자동 빌드 트리거 확인**
  빌드 상태 및 워크플로우 확인
