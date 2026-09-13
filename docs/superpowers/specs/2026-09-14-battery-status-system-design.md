# Keyboardio Preonic 배터리 상태 모니터링 시스템 설계 사양서
(Butterfly LED 4-Level Gauge, Low Battery Alert & Auto Text Typer)

- **작성일자**: 2026-09-14
- **대상 하드웨어**: Keyboardio Preonic (nRF52840, MAX17048 배터리 잔량계, 4구 나비 LED, 피에조 부저)
- **대상 펌웨어**: ZMK Firmware (`samake-preonic-config`)

---

## 1. 개요 및 배경

Keyboardio Preonic은 디스플레이가 없는 오쏘리니어 무선 키보드로, 배터리 잔량을 시각적·청각적·텍스트 방식으로 다채롭게 확인할 수 있는 통합 시스템이 필요합니다.
본 사양서는 기존 나비 LED 인디케이터(`butterfly_status.c`)와 피에조 사운드 엔진(`preonic_sound.c`), 그리고 ZMK HID 키코드 이벤트를 연동하여 다음 3가지 배터리 모니터링 기능을 구현합니다.

1. **`Fn + B` 나비 LED 4단계 게이지**: 3초간 4개의 날개 LED 색상과 개수로 배터리 잔량을 시각화
2. **저배터리(15% 이하) 스마트 경고음**: 최초 15% 진입 시 자동 1회 경고음 출력, 이후에는 `Fn + B` 수동 확인 시에만 경고음 출력 (20% 이상 충전 시 자동 리셋)
3. **`Fn + P` 배터리 잔량 자동 타이핑**: 메모장, 검색창 등에 현재 잔량을 `"Battery: XX%"` 형태로 매끄럽게 자동 타이핑

---

## 2. 사용자 요구사항 및 상세 동작 명세

### 2.1 `Fn + B` 나비 날개 4단계 LED 게이지
- **트리거**: Function 레이어에서 `B` 키 (Row 4, Col 5 / index 44) 누름
- **동작 방식**: 3,000ms 동안 나비 LED가 배터리 잔량 게이지 모드로 전환되며, 시간 경과 후 원래의 블루투스/USB 프로필 인디케이터로 복귀
- **배터리 구간별 LED 색상 및 날개 점등 개수**:
  - `75% ~ 100%`: 4개 날개 모두 **초록색** (`RGB: 0, 150, 0`)
  - `50% ~ 74%`: 3개 날개 **연두색** (`RGB: 60, 150, 0`) (날개 0, 1, 2 점등, 날개 3 소등)
  - `25% ~ 49%`: 2개 날개 **주황색** (`RGB: 160, 50, 0`) (날개 0, 1 점등, 날개 2, 3 소등)
  - `0% ~ 24%`: 1개 날개 **빨간색** (`RGB: 160, 0, 0`) (날개 0 점등, 날개 1, 2, 3 소등)
- **15% 이하 수동 경고음 연동**:
  - `Fn + B`를 눌렀을 때 잔량이 15% 이하이면, 1번 날개 빨간색 점등과 동시에 피에조 부저에서 `1500Hz` 경고음(150ms)을 함께 출력하여 충전 필요성을 즉시 전달

### 2.2 저배터리(15% 이하) 스마트 비프음 정책
- **최초 15% 진입 시 자동 경고**:
  - 배터리 잔량 변경 이벤트(`zmk_battery_state_changed`) 또는 주기적 검사에서 배터리가 최초로 `15% 이하`로 떨어지면, **더블 비프음(`1500Hz` 100ms → 100ms 쉼 → `1500Hz` 100ms)**을 1회 자동 재생
- **반복 비프 억제**:
  - 이후에는 자동 알림을 울리지 않고, 사용자가 `Fn + B`를 눌러 수동 확인할 때만 경고음 발생 (도서관, 회의실 등 조용한 환경 방해 금지)
- **재충전 리셋(Hysteresis)**:
  - 충전기를 연결하여 배터리가 `20% 이상`으로 올라가면 경고 플래그가 초기화되어, 다음 방전 주기 때 다시 최초 1회 자동 경고 작동

### 2.3 `Fn + P` 배터리 잔량 자동 타이핑 (이스터에그 매크로)
- **트리거**: Function 레이어에서 `P` 키 (Row 2, Col 10 / index 24) 누름
- **출력 형식**: `"Battery: XX%"` (예: 배터리가 82%인 경우 `Battery: 82%`)
- **타이핑 엔진 구현**:
  - `raise_zmk_keycode_state_changed_from_encoded`를 이용해 문자열의 각 문자에 해당하는 키코드를 순차 전송
  - 글자 사이에 `12ms`의 인터벌을 부여하여 OS 입력 버퍼 오버플로우나 글자 씹힘 없이 매끄럽게 타이핑
  - 비동기 워크큐(`k_work_delayable`)로 동작하여 키보드 스캔 및 블루투스 성능 저하 제로

---

## 3. 시스템 아키텍처 및 세부 컴포넌트

### 3.1 파일 및 모듈 구성
1. **`src/butterfly_status.c` / `include/butterfly_status.h`**:
   - `void butterfly_show_battery(void)` 함수 구현
   - 배터리 게이지 타이머 상태 머신(`is_battery_gauge_active`, `battery_gauge_end_time`) 추가
   - `<zmk/battery.h>`의 `zmk_battery_state_of_charge()` 연동
   - `ZMK_SUBSCRIPTION(butterfly_status, zmk_battery_state_changed)` 추가하여 15% 최초 진입 감지

2. **`src/preonic_sound.c` / `include/preonic_sound.h`**:
   - `void preonic_sound_play_low_battery_warning(void)` 함수 구현
   - 1500Hz 더블 비프음 시퀀스 상태 머신 추가

3. **`src/battery_typer.c` / `include/battery_typer.h`** (또는 `preonic_sound.c` 내 타이퍼):
   - 문자열 키코드 인코딩 테이블 및 비동기 워크큐 타이핑 엔진
   - `void preonic_type_battery_status(void)` 함수 구현

4. **`config/keyboardio_preonic.keymap`**:
   - `func_layer` 및 `tri_layer`에서:
     - `P` (Row 2, Col 10, index 24): `&none` 설정
     - `B` (Row 4, Col 5, index 44): `&none` 설정
   - 키 누름 감지 시 기본 영문 자모 입력 방지 및 C 모듈 핸들러 인터셉트

---

## 4. 예외 및 에러 핸들링
1. **타이핑 중 인터럽트**: `Fn + P`로 배터리 타이핑 중 다른 키를 누르더라도 워크큐가 안전하게 완료되거나 취소되도록 보호
2. **슬립 모드**: 딥슬립 진입 시 배터리 게이지 및 타이퍼 워크큐 즉시 취소
3. **충전 상태 감지**: USB 연결(`ZMK_TRANSPORT_USB`) 중에는 충전 전압으로 인해 잔량이 상승하므로 안전하게 리셋 처리

---

## 5. 검증 계획
1. **`Fn + B` 시각 게이지 검증**: 75% 이상(4칸 초록), 50~74%(3칸 연두), 25~49%(2칸 주황), 25% 미만(1칸 빨강) 3초 표시 후 복귀 확인
2. **저배터리 비프음 검증**: 15% 이하 시 `Fn + B` 입력 시 1500Hz 비프음 출력 확인
3. **`Fn + P` 타이핑 검증**: 메모장/브라우저 주소창에서 `Battery: XX%` 텍스트가 깨짐 없이 온전히 출력되는지 확인
4. **빌드 무결성**: GitHub Actions 파이프라인에서 에러 없이 펌웨어 `.uf2` 빌드 성공 확인
