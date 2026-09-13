# Keyboardio Preonic 피에조 사운드 시스템 설계 사양서
(Super Mario Coin Boot Greeting & Audio Clicky)

- **작성일자**: 2026-09-14
- **대상 하드웨어**: Keyboardio Preonic (Nordic nRF52840 기반 무선 오쏘리니어 키보드)
- **대상 펌웨어**: ZMK Firmware (Repository: `samake-preonic-config`)

---

## 1. 개요 및 배경

Keyboardio Preonic은 nRF52840 마이크로컨트롤러의 **`P0.22` (D18 / `PIN_SPEAKER`)** 핀에 패시브 피에조 부저(Passive Piezo Transducer)가 실장되어 있습니다. 현재 `samake-preonic-config` 환경에서는 나비 LED 상태 표시기 및 로터리 인코더 등이 구축되어 있으나, 피에조 부저는 하드웨어적으로 연결만 되어 있고 펌웨어 단에서 비활성화되어 있습니다.

본 사양서는 nRF52840 하드웨어 PWM0 컨트롤러와 ZMK 이벤트 매니저를 연동하여 다음 핵심 기능을 구현하는 사운드 서브시스템 아키텍처를 정의합니다.
1. **슈퍼마리오 코인 부팅 사운드**: 전원 인가(콜드 부팅) 시 1회 레트로 코인 획득 멜로디 재생
2. **초저지연 오디오 클릭키(Audio Clicky)**: 키 입력 시 5ms 미세 틱(Tick) 음 발생
3. **`Fn + C` 클릭키 토글**: 사무실/도서관 등 조용한 환경을 고려한 온/오프 토글 및 톤 피드백
4. **무선 절전 최적화**: 미사용 시 및 딥슬립(Deep Sleep) 시 PWM 완전 차단으로 배터리 전류 누설 0 방지

---

## 2. 사용자 요구사항 및 동작 명세

### 2.1 슈퍼마리오 코인 부팅 사운드 (Boot Greeting)
- **트리거 시점**: 전원 스위치 ON 또는 펌웨어 리셋 후 시스템 초기화가 완료된 시점에 1회 재생
- **절전 모드 정책**: 15분 미사용 후 진입하는 딥슬립(Deep Sleep)에서 아무 키나 눌러 깨어날 때는 조용히 복귀 (재생하지 않음)
- **음정 및 지속시간**:
  - 1음: **B5** (`988 Hz`), 지속시간 `65 ms` (듀티비 50%)
  - 2음: **E6** (`1,319 Hz`), 지속시간 `350 ms` (듀티비 50%)
- **비동기 처리**: 사운드 재생 중에도 키 입력 및 블루투스 연결이 차단되지 않도록 Zephyr `k_work_delayable` 기반 상태 머신으로 비동기 실행

### 2.2 오디오 클릭키 (Audio Clicky)
- **트리거 시점**: ZMK의 키 누름 이벤트(`zmk_position_state_changed`에서 `state == true`) 수신 시 즉각 반응
- **음향 특성**:
  - 주파수: **`3,000 Hz`** (단조로운 비프음 대신 기계식 타자기 틱 감을 주는 고음역대 펄스)
  - 지속시간: **`5 ms`** (키 입력 지연감이 전혀 없는 초단타 펄스)
- **무지연 보장**:
  - 키 스캔 스레드나 인터럽트 루틴을 차단(busy-wait)하지 않고, PWM 설정 후 초소형 타이머 워크를 통해 PWM 자동 정지

### 2.3 `Fn + C` 토글 및 청각 피드백
- **키 매핑**: `func_layer`의 `C` 위치 (Row 4, Col 3)에 클릭키 토글 기능 배치
- **동작**: 누를 때마다 Audio Clicky 활성/비활성 상태 반전
- **피드백 톤**:
  - **활성화 (ON)**: 높은 확인음 (`2,400 Hz`, `50 ms`) ♬ 띡!
  - **비활성화 (OFF)**: 낮은 확인음 (`1,200 Hz`, `50 ms`) ♬ 뚝!
- **기본 상태**: 부팅 시 기본값 `Enabled`

### 2.4 전력 및 배터리 관리
- 소리가 나지 않을 때는 PWM 듀티비를 0으로 설정하고 클럭 게이팅을 적용하여 배터리 소모를 원천 차단
- `ZMK_ACTIVITY_SLEEP` 이벤트 수신 시 PWM 드라이버를 완전히 디스에이블하고 핀을 Sleep 상태로 전환

---

## 3. 시스템 아키텍처 및 세부 컴포넌트

### 3.1 하드웨어 장치 트리 (Devicetree)
- **파일**: `boards/keyboardio/keyboardio_preonic/keyboardio_preonic_nrf52840_zmk.dts`
- **pinctrl 노드**:
  ```dts
  &pinctrl {
      pwm0_default: pwm0_default {
          group1 {
              psels = <NRF_PSEL(PWM_OUT0, 0, 22)>;
              nordic,invert;
          };
      };
      pwm0_sleep: pwm0_sleep {
          group1 {
              psels = <NRF_PSEL(PWM_OUT0, 0, 22)>;
              low-power-enable;
          };
      };
  };

  &pwm0 {
      status = "okay";
      pinctrl-0 = <&pwm0_default>;
      pinctrl-1 = <&pwm0_sleep>;
      pinctrl-names = "default", "sleep";
  };
  ```

### 3.2 Kconfig 및 CMake 빌드 구성
- **`boards/keyboardio/keyboardio_preonic/keyboardio_preonic_nrf52840_zmk_defconfig`**:
  ```text
  CONFIG_PWM=y
  CONFIG_PWM_NRFX=y
  ```
- **`Kconfig`**:
  ```kconfig
  menuconfig KEYBOARDIO_PREONIC_SOUND
      bool "Keyboardio Preonic Piezo Sound Subsystem"
      default y
      depends on PWM
      help
        Enables piezo buzzer sound effects including boot greeting chime and audio clicky.
  ```
- **`CMakeLists.txt`**:
  ```cmake
  if(CONFIG_KEYBOARDIO_PREONIC_SOUND)
      target_sources(app PRIVATE src/preonic_sound.c)
  endif()
  ```
- **`config/keyboardio_preonic.conf`**:
  ```text
  CONFIG_KEYBOARDIO_PREONIC_SOUND=y
  ```

### 3.3 사운드 엔진 모듈 (`include/preonic_sound.h`, `src/preonic_sound.c`)
- **주요 함수 및 인터페이스**:
  - `preonic_sound_play_tone(uint32_t freq_hz, uint32_t duration_ms)`: 단일 톤 재생
  - `preonic_sound_play_coin(void)`: 슈퍼마리오 코인 시퀀스 재생
  - `preonic_sound_play_click(void)`: 오디오 클릭키 초단타 펄스 재생
  - `preonic_sound_toggle_clicky(void)`: 클릭키 On/Off 전환 및 확인음 출력
- **이벤트 리스너**:
  - `zmk_position_state_changed`: 키 입력 감지 (토글 키 감지 및 일반 키 클릭키 재생)
  - `zmk_activity_state_changed`: 절전 진입 시 사운드 중단 및 PWM 전력 차단

### 3.4 키맵 수정 (`config/keyboardio_preonic.keymap`)
- `func_layer` 및 `tri_layer`의 C 키 위치에 커스텀 토글 바인딩 매핑

---

## 4. 예외 및 에러 핸들링
1. **PWM 드라이버 준비 실패 시**: `device_is_ready(pwm_dev)`가 false일 경우, 사운드 기능만 조용히 비활성화하고 키보드의 일반 타이핑 및 블루투스 기능은 정상 작동 유지
2. **동시 소리 재생 요청 시**: 코인 재생 중에는 일반 클릭음이 끼어들어 왜곡되지 않도록 사운드 상태 락(Lock) 적용
3. **슬립 복귀 시**: 딥슬립에서 깨어날 때 부팅음이 다시 울리지 않도록 콜드 부팅 플래그 관리

---

## 5. 검증 계획
1. **빌드 검증**: 로컬 및 CI 환경에서 Zephyr DTS, PWM 드라이버, C 소스 컴파일 무결성 검증
2. **사운드 품질 검증**:
   - 부팅 시 정확한 B5(988Hz) 및 E6(1319Hz) 음계 출력 확인
   - 키 연타 시 키 씹힘이나 무선 끊김 없는 3000Hz/5ms 틱 음 확인
   - `Fn + C` 입력 시 높은 톤/낮은 톤 피드백 및 클릭키 온/오프 상태 전환 확인
3. **전력 소모 검증**: 사운드 미재생 시 PWM 레지스터 정지 및 슬립 모드 전류 누설 없음 확인
