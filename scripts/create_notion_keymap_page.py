import os
import time
import json
import urllib.request
import urllib.error

NOTION_API_TOKEN = os.environ.get("NOTION_API_TOKEN")
TARGET_PAGE_ID = os.environ.get("NOTION_PAGE_ID", "3db96981-2b85-817b-adc0-c8a46d3ddfee")
PARENT_PAGE_ID = os.environ.get("NOTION_PARENT_PAGE_ID", "3d696981-2b85-802f-931b-cddb91fe1cea")
NOTION_VERSION = "2025-09-03"

GITHUB_IMG_BASE = "https://raw.githubusercontent.com/samake-2T2/keyboardio-preonic-zmk-config/v1.7.0/docs/images"

def notion_request(url, method="GET", data=None, retries=5):
    headers = {
        "Authorization": f"Bearer {NOTION_API_TOKEN}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json"
    }
    req = urllib.request.Request(
        url,
        headers=headers,
        method=method,
        data=json.dumps(data).encode("utf-8") if data else None
    )
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req) as resp:
                res_body = resp.read().decode("utf-8")
                return json.loads(res_body) if res_body else {}
        except urllib.error.HTTPError as e:
            if e.code == 429:
                retry_after = int(e.headers.get("Retry-After", 1))
                print(f"Rate limited (429), retrying after {retry_after}s...")
                time.sleep(retry_after)
                continue
            err_msg = e.read().decode("utf-8")
            print(f"HTTPError {e.code}: {err_msg}")
            raise

def clear_page_children(page_id):
    print(f"Clearing existing child blocks for page {page_id}...")
    deleted_count = 0
    while True:
        resp = notion_request(f"https://api.notion.com/v1/blocks/{page_id}/children?page_size=100")
        results = resp.get("results", [])
        if not results:
            break
        print(f"Found {len(results)} blocks to delete...")
        for b in results:
            bid = b["id"]
            notion_request(f"https://api.notion.com/v1/blocks/{bid}", method="DELETE")
            deleted_count += 1
            time.sleep(0.15)
        if not resp.get("has_more"):
            break
    print(f"Successfully deleted {deleted_count} old blocks.")

def rt(content, bold=False, italic=False, code=False, color="default", link=None):
    return {
        "type": "text",
        "text": {"content": content, "link": {"url": link} if link else None},
        "annotations": {
            "bold": bold,
            "italic": italic,
            "strikethrough": False,
            "underline": False,
            "code": code,
            "color": color
        }
    }

def p_block(rich_texts):
    return {
        "object": "block",
        "type": "paragraph",
        "paragraph": {"rich_text": rich_texts}
    }

def h2_block(title):
    return {
        "object": "block",
        "type": "heading_2",
        "heading_2": {
            "rich_text": [rt(title, bold=True)],
            "color": "default",
            "is_toggleable": False
        }
    }

def h3_block(title):
    return {
        "object": "block",
        "type": "heading_3",
        "heading_3": {
            "rich_text": [rt(title, bold=True)],
            "color": "default",
            "is_toggleable": False
        }
    }

def callout_block(rich_texts, emoji="💡", color="gray_background"):
    return {
        "object": "block",
        "type": "callout",
        "callout": {
            "rich_text": rich_texts,
            "icon": {"type": "emoji", "emoji": emoji},
            "color": color
        }
    }

def bullet_block(rich_texts):
    return {
        "object": "block",
        "type": "bulleted_list_item",
        "bulleted_list_item": {"rich_text": rich_texts}
    }

def divider_block():
    return {
        "object": "block",
        "type": "divider",
        "divider": {}
    }

def image_block(url, caption_text=None):
    caption = [rt(caption_text)] if caption_text else []
    return {
        "object": "block",
        "type": "image",
        "image": {
            "type": "external",
            "external": {"url": url},
            "caption": caption
        }
    }

def table_row_block(cells):
    row_cells = []
    for c in cells:
        if isinstance(c, str):
            row_cells.append([rt(c)])
        elif isinstance(c, list):
            row_cells.append(c)
        else:
            row_cells.append([c])
    return {
        "object": "block",
        "type": "table_row",
        "table_row": {"cells": row_cells}
    }

def table_block(rows, table_width=3, has_column_header=True):
    return {
        "object": "block",
        "type": "table",
        "table": {
            "table_width": table_width,
            "has_column_header": has_column_header,
            "has_row_header": False,
            "children": rows
        }
    }

def update_or_create_keymap_page():
    initial_blocks = [
        callout_block([
            rt("본 문서는 ", bold=True),
            rt("Keyboardio Preonic (nRF52840)", bold=True, color="blue"),
            rt(" 무선 기계식 키보드의 공식 ZMK 커스텀 키맵 가이드 (v1.8.0)입니다.\n\n"),
            rt("특징 요약:\n", bold=True),
            rt("• 레이아웃: ", bold=True),
            rt("5x12 직교(Ortholinear) 배열 + "),
            rt("중앙 2U 스페이스바", bold=True, color="orange"),
            rt(" (MIT 레이아웃, 총 62키)\n"),
            rt("• 상단 보조 키: ", bold=True),
            rt("PrtSc 화면 캡처, 독립 Fn 키, "),
            rt("로터리 인코더(음량 조절 / 클릭 시 음소거)", bold=True, color="green"),
            rt("\n• 하드웨어 TRNG 패스워드 생성기: ", bold=True),
            rt("Nordic nRF52840 진성 하드웨어 난수 기반, DB/환경설정/URI 안전 Zero-Escape 특수문자(_,-), Fn+노브 회전으로 자리수 선택(12/16/20/24자, 2클릭 1스텝 감도 조절, 나비 골드 게이지 & 도/미/솔/도 음계 피드백, NVS 영구 저장), 하이브리드 제어(Fn+노브 1회 클릭 또는 Fn+D: DB Safe, Fn+노브 더블 클릭 또는 Fn+W: Web Extended, Fn+노브 0.4초 롱 클릭 또는 Fn+A: Alphanumeric), 12ms 비동기 자동 타이핑 및 모디파이어 자동 마스킹\n"),
            rt("• 스마트 하이브리드 USB/BLE 자동 전환: ", bold=True),
            rt("USB 케이블 분리 또는 배터리 전원 인가 시 마지막 활성 BLE 프로필(0~3번)로 자동 복귀, NVS 플래시 안전 보존, PC 유선 연결 시 USB 자동 전환(순백색 점등), 충전기 연결 시 무선 BLE 유지\n"),
            rt("• 피에조 사운드 시스템: ", bold=True),
            rt("마스터 사운드 On/Off 토글(기본값 OFF 무음, Fn + S, NVS 플래시 영구 보존으로 전원 차단/재부팅 후에도 설정 유지), 절전모드 복귀 부팅음 차단, 타건 클릭음(Fn + C), 부팅 슈퍼마리오 코인 차임\n"),
            rt("• QMK 호환 다이나믹 매크로: ", bold=True),
            rt("키보드 단독 실시간 매크로 녹화/재생, NVS 플래시 영구 보존(재부팅/방전 후 보존), 3개 독립 슬롯(슬롯1: Fn+5 녹화/Fn+6 재생, 슬롯2: Fn+7 녹화/Fn+8 재생, 슬롯3: Fn+9 녹화/Fn+0 재생), 녹화 시 슬롯별 LED 숨쉬기(슬롯1 빨강, 슬롯2 보라, 슬롯3 골드), 재생 시 점등 피드백, 12ms BLE 안전 딜레이, 마스터 사운드 연동 비프음\n"),
            rt("• 배터리 모니터링: ", bold=True),
            rt("4단계 나비 날개 LED & 오디오 비프음 게이지(Fn + B 누르고 있는 동안 Hold), 스마트 저배터리 자동 경고(15% 이하 시 1회 더블 비프음), 텍스트 백분율 자동 타이퍼(Fn + P로 'XX%' 자동 입력)\n"),
            rt("• 무선 연결 및 시스템 제어: ", bold=True),
            rt("4-Device 블루투스 멀티페어링(Fn + 1/2/3/4, 나비 날개 1:1 매핑), USB/BLE 출력 모드 토글(Fn + ~), 좌손 마우스 에뮬레이션, 다이렉트 부트로더 진입(Fn + LCtrl), ZMK Studio 잠금 해제(Fn + Z)\n\n"),
            rt("🔗 GitHub 펌웨어 저장소 바로가기", bold=True, link="https://github.com/samake-2T2/keyboardio-preonic-zmk-config")
        ], emoji="⌨️", color="blue_background"),
        divider_block()
    ]

    if TARGET_PAGE_ID:
        page_id = TARGET_PAGE_ID
        page_url = f"https://notion.so/{TARGET_PAGE_ID.replace('-', '')}"
        print(f"Targeting existing Notion page: {page_id}")
        # Clear existing old blocks before re-populating with latest content
        clear_page_children(page_id)
        print("Appending initial overview blocks...")
        notion_request(f"https://api.notion.com/v1/blocks/{page_id}/children", method="PATCH", data={"children": initial_blocks})
    else:
        print("Creating new Notion page...")
        page_payload = {
            "parent": {"page_id": PARENT_PAGE_ID},
            "icon": {"type": "emoji", "emoji": "⌨️"},
            "properties": {
                "title": {
                    "title": [{"type": "text", "text": {"content": "⌨️ Keyboardio Preonic 레이어별 키맵 가이드 (MIT Layout)"}}]
                }
            },
            "children": initial_blocks
        }
        page = notion_request("https://api.notion.com/v1/pages", method="POST", data=page_payload)
        page_id = page["id"]
        page_url = page["url"]
        print(f"Page created: {page_id} -> {page_url}")

    # Section 1: Overview & Table of Contents
    sec1_blocks = [
        h2_block("레이어 구조 개요 (Layer Hierarchy)"),
        p_block([
            rt("Keyboardio Preonic은 콤팩트한 5x12 직교 배열이지만, 강력한 "),
            rt("4단계 레이어 시스템", bold=True),
            rt("과 "),
            rt("Tri-Layer", bold=True, color="orange"),
            rt(" 기능을 결합하여 풀사이즈 108키 키보드 이상의 모든 기능과 마우스 제어까지 지원합니다.")
        ]),
        table_block([
            table_row_block([
                [rt("레이어 번호 / 명칭", bold=True)],
                [rt("진입 방법 (Activation)", bold=True)],
                [rt("주요 역할 및 기능", bold=True)]
            ]),
            table_row_block([
                [rt("Layer 0: Base", bold=True, color="blue")],
                "기본 활성화 (Default)",
                "QWERTY 알파벳, 한/영 전환(RAlt), 중앙 2U 스페이스바, 상단 PrtSc/Fn/로터리 볼륨 노브"
            ]),
            table_row_block([
                [rt("Layer 1: Lower", bold=True, color="brown")],
                "바텀열 Lower 키 누른 상태 유지 (Hold)",
                "오른손 3x3 텐키패드(Numpad) + 중앙 2U '0' 키, 좌측 문서 편집 및 네비게이션, 상단 F1~F12"
            ]),
            table_row_block([
                [rt("Layer 2: Raise", bold=True, color="green")],
                "바텀열 Raise 키 누른 상태 유지 (Hold)",
                "오른손 코딩 특수문자 및 기호류 완비, 좌측 정밀 마우스 커서/클릭/휠 제어, 상단 F1~F12"
            ]),
            table_row_block([
                [rt("Layer 3: Function & Tri", bold=True, color="purple")],
                "상단 Fn 키 누름 OR Lower + Raise 동시 입력",
                "하드웨어 TRNG 패스워드 생성기(Fn+노브 회전 12/16/20/24자, 노브 1회/더블/롱클릭 및 Fn+D/W/A 직관키), 다이나믹 매크로(Fn+5~0 녹화/재생), BLE 프로필(1~4), 마스터 사운드 토글(기본 OFF), 클릭 사운드 토글, 배터리 게이지/타이퍼, 부트로더 진입, ZMK Studio 잠금 해제"
            ])
        ], table_width=3, has_column_header=True),
        divider_block()
    ]

    print("Appending Section 1...")
    notion_request(f"https://api.notion.com/v1/blocks/{page_id}/children", method="PATCH", data={"children": sec1_blocks})

    # Section 2: Layer 0 Base
    sec2_blocks = [
        h2_block("1. Layer 0: Base Layer (기본 영문 자판)"),
        p_block([
            rt("표준 QWERTY 배열을 바탕으로 한국어 입력과 편리한 엄지 키 조합을 최적화한 기본 레이어입니다.")
        ]),
        image_block(
            f"{GITHUB_IMG_BASE}/layer0_base.png",
            caption_text="Layer 0: Base Layer (5x12 MIT Layout with Centered 2U Spacebar)"
        ),
        callout_block([
            rt("핵심 레이아웃 특징:\n", bold=True),
            rt("• 중앙 2U 스페이스바: ", bold=True, color="orange"),
            rt("바텀열 5번째/6번째 컬럼에 넓은 2U 스페이스바를 탑재하여 양손 엄지 모두 편안하게 스페이스 입력이 가능합니다.\n"),
            rt("• RAlt / 한영 전환 키: ", bold=True, color="blue"),
            rt("스페이스바 바로 좌측에 RAlt(한영) 키를 배치하여 Windows, macOS, Linux 환경에서 엄지손가락으로 손쉽게 한/영 전환을 수행합니다.\n"),
            rt("• 상단 독립 보조 키열 (Row 0):\n", bold=True),
            rt("   - Col 9 (PrtSc): ", bold=True), rt("한 번의 터치로 화면 스크린샷 캡처\n"),
            rt("   - Col 10 (Fn): ", bold=True), rt("누르고 있는 동안 Function 레이어(Layer 3) 즉시 활성화\n"),
            rt("   - Col 11 (Rotary Encoder): ", bold=True), rt("노브 클릭 시 음소거(Mute), 시계/반시계 회전 시 볼륨 Up / Down\n"),
            rt("• 모디파이어 키 배치: ", bold=True),
            rt("Row 3 좌측은 Esc, Row 4 좌측 LShift, Row 5 좌측 LCtrl, LGui, LAlt, 우측 방향키(←, ↓, ↑, →) 순으로 직관적으로 배치되어 있습니다.")
        ], emoji="⌨️", color="gray_background"),
        divider_block()
    ]

    print("Appending Section 2...")
    notion_request(f"https://api.notion.com/v1/blocks/{page_id}/children", method="PATCH", data={"children": sec2_blocks})

    # Section 3: Layer 1 Lower
    sec3_blocks = [
        h2_block("2. Layer 1: Lower Layer (숫자 패드 & 편집 네비게이션)"),
        p_block([
            rt("바텀열의 "),
            rt("Lower 키", bold=True, color="brown"),
            rt("를 누르고 있는 동안 활성화되며, 우측의 집중식 텐키패드와 좌측의 문서 편집 네비게이션을 제공합니다.")
        ]),
        image_block(
            f"{GITHUB_IMG_BASE}/layer1_lower.png",
            caption_text="Layer 1: Lower Layer (Numpad + Navigation)"
        ),
        callout_block([
            rt("주요 기능 상세:\n", bold=True),
            rt("• 오른손 풀사이즈 텐키패드 (Numpad):\n", bold=True, color="blue"),
            rt("   - 오른손 홈포지션에 3x3 정규 숫자 키패드 (7, 8, 9 / 4, 5, 6 / 1, 2, 3) 집중 배치\n"),
            rt("   - 바텀열 중앙 2U 스페이스바 위치가 "),
            rt("대형 2U '0' 키", bold=True, color="orange"),
            rt("로 변환되어 일반 텐키패드와 완전히 동일한 편안한 숫자 입력 지원\n"),
            rt("   - Col 10에 NumLock, 우측에 추가 0 키 완비\n"),
            rt("• 왼손 문서 편집 및 방향키 네비게이션:\n", bold=True, color="green"),
            rt("   - Row 2~3: Home, End, Page Up, Page Down, Insert, Delete, Caps Lock\n"),
            rt("   - 왼손 영역에도 상/하/좌/우 커서 방향키가 매핑되어 있어 오른손 마우스 조작 중 왼손만으로 방향 이동 가능\n"),
            rt("• 상단 펑션열: ", bold=True),
            rt("숫자열 전체에 F1 ~ F12 펑션키 완비 (F1~F11 상단열, F12 우측 매핑)")
        ], emoji="🔢", color="gray_background"),
        divider_block()
    ]

    print("Appending Section 3...")
    notion_request(f"https://api.notion.com/v1/blocks/{page_id}/children", method="PATCH", data={"children": sec3_blocks})

    # Section 4: Layer 2 Raise
    sec4_blocks = [
        h2_block("3. Layer 2: Raise Layer (특수 기호 & 마우스 제어)"),
        p_block([
            rt("바텀열의 "),
            rt("Raise 키", bold=True, color="green"),
            rt("를 누르고 있는 동안 활성화되며, 프로그래밍에 필수적인 모든 특수 기호와 키보드 마우스 에뮬레이션을 제공합니다.")
        ]),
        image_block(
            f"{GITHUB_IMG_BASE}/layer2_raise.png",
            caption_text="Layer 2: Raise Layer (Special Characters & Mouse Emulation)"
        ),
        callout_block([
            rt("주요 기능 상세:\n", bold=True),
            rt("• 왼손 정밀 마우스 에뮬레이션 (ZMK Mouse Keys & Pointer):\n", bold=True, color="purple"),
            rt("   - 커서 이동: ", bold=True),
            rt("E (상), S (좌), D (하), F (우) - 직관적인 1차 선형 가속(Linear) 적용\n"),
            rt("   - 마우스 클릭: ", bold=True),
            rt("W (좌클릭 LMB), R (우클릭 RMB), C (휠클릭 MMB)\n"),
            rt("   - 마우스 휠 스크롤: ", bold=True),
            rt("Q (휠 위), A (휠 아래), X (휠 좌측), V (휠 우측)\n"),
            rt("   - 웹 탐색 버튼: ", bold=True),
            rt("T (앞으로 가기 MB5), G (뒤로 가기 MB4)\n"),
            rt("• 오른손 코딩 및 문서용 특수 기호 완비:\n", bold=True, color="blue"),
            rt("   - 대괄호 및 중괄호: [ { (Col 9), ] } (Col 10), { (Row 3 Col 9), } (Row 3 Col 10)\n"),
            rt("   - 소괄호: ( (Row 4 Col 9), ) (Row 4 Col 10)\n"),
            rt("   - 연산 및 구분 기호: - _ (Col 7), = + (Col 8), _ (Row 3 Col 7), + (Row 3 Col 8)\n"),
            rt("• 상단 펑션열: ", bold=True),
            rt("숫자열 전체에 F1 ~ F12 펑션키 완비")
        ], emoji="🖱️", color="gray_background"),
        divider_block()
    ]

    print("Appending Section 4...")
    notion_request(f"https://api.notion.com/v1/blocks/{page_id}/children", method="PATCH", data={"children": sec4_blocks})

    # Section 5: Layer 3 Function & Tri
    sec5_blocks = [
        h2_block("4. Layer 3: Function & Tri-Layer (시스템 & 배터리 & 오디오)"),
        p_block([
            rt("상단 Row 0의 "),
            rt("Fn 키", bold=True),
            rt("를 누르거나, 바텀열의 "),
            rt("Lower + Raise 키를 동시에 누르면 Tri-Layer에 의해 자동으로 활성화", bold=True, color="purple"),
            rt("됩니다. 키보드의 하드웨어 설정, 다이나믹 매크로, 배터리 진단, 무선 연결 및 펌웨어 복구를 제어합니다.")
        ]),
        image_block(
            f"{GITHUB_IMG_BASE}/layer3_func.png",
            caption_text="Layer 3: Function & Tri-Layer (Dynamic Macros, BLE, Sound, Battery, Bootloader)"
        ),
        callout_block([
            rt("🔑 하드웨어 TRNG 랜덤 패스워드 생성기 (Fn + 로터리 노브 & 직관 단축키):\n", bold=True, color="purple"),
            rt("• "),
            rt("진정한 암호학적 하드웨어 엔트로피", bold=True, color="orange"),
            rt(": Nordic nRF52840 SoC 내부 하드웨어 난수 생성기(TRNG)의 물리적 열 잡음(Thermal Noise) 엔트로피를 직접 사용하여 소프트웨어 의사 난수와 차원이 다른 안전한 패스워드를 생성합니다.\n"),
            rt("• "),
            rt("노브 회전으로 자리수 변경 (12 / 16 / 20 / 24자리)", bold=True),
            rt(": Fn(또는 Tri) 레이어에서 노브를 돌리면 자리수가 즉시 순환 변경됩니다 (2클릭 1스텝 둔감화로 정밀 조작). 나비 날개 1~4개가 따뜻한 골드/앰버(Gold) 색상으로 2초간 게이지 형태로 점등되며, 마스터 사운드 ON 시 도(C5) / 미(E5) / 솔(G5) / 높은도(C6) 음악 피치 톤이 제공됩니다. 설정값은 "),
            rt("NVS 플래시에 영구 저장", bold=True, color="blue"),
            rt("되어 재부팅 후에도 유지됩니다.\n"),
            rt("• "),
            rt("DB & Config Safe 모드 (Fn + 노브 1회 클릭 또는 Fn + D)", bold=True, color="green"),
            rt(": "),
            rt("Zero-Escape 안전 문자", bold=True),
            rt("(`A-Z`, `a-z`, `0-9`, `_`, `-`)로만 구성된 패스워드를 생성합니다. PostgreSQL, MySQL, Redis 등 DB 접속 URI(`postgres://user:pass@host/db`) 파싱 오류나 Docker `.env`, YAML, XML 파싱 시 특수문자 충돌/이스케이프 문제를 원천 차단합니다. (노브 클릭 대기 없이 Fn + D로 즉시 생성 가능)\n"),
            rt("• "),
            rt("웹 확장(Web Extended) 모드 (Fn + 노브 더블 클릭 또는 Fn + W)", bold=True),
            rt(": 특수문자 필수 사이트를 위해 `@`, `.` 기호를 포함하여 생성합니다. (노브 250ms 내 더블 클릭 또는 Fn + W 직관키)\n"),
            rt("• "),
            rt("순수 영숫자(Alphanumeric) 모드 (Fn + 노브 롱 클릭(0.4초) 또는 Fn + A)", bold=True),
            rt(": 특수문자 사용이 금지된 레거시 시스템을 위해 영문 대소문자 및 숫자(`A-Z, a-z, 0-9`)만으로 생성합니다. (노브를 0.4초 누르면 880Hz 확인음과 함께 생성되거나 Fn + A 직관키로 즉시 생성)\n"),
            rt("• "),
            rt("비동기 12ms 타이핑 & 모디파이어 자동 마스킹", bold=True),
            rt(": 키보드가 패스워드를 타이핑하는 동안 사용자가 누르고 있는 Fn 물리 모디파이어를 펌웨어 단에서 일시 마스킹하여 키 입력 왜곡 없이 완벽하게 자동 타이핑하고 완료 시 에메랄드/골드 축하 점멸 효과를 표시합니다.")
        ], emoji="🔑", color="gray_background"),
        callout_block([
            rt("🎬 QMK 호환 다이나믹 매크로 시스템 (Fn + 5 / 6 / 7 / 8 / 9 / 0):\n", bold=True, color="purple"),
            rt("• 별도 소프트웨어나 재빌드 없이 키보드에서 실시간으로 키 입력을 녹화하고 즉시 재생하는 시스템입니다.\n"),
            rt("• "),
            rt("NVS 플래시 메모리 영구 보존", bold=True, color="orange"),
            rt(": 녹화 완료 시 Zephyr NVS 파티션에 자동 저장되어 전원 차단, 방전, 재부팅 후에도 매크로가 영구 유지됩니다.\n"),
            rt("• "),
            rt("3개 독립 슬롯 & 즉시 덮어쓰기", bold=True),
            rt(": 슬롯 1(Fn+5/6), 슬롯 2(Fn+7/8), 슬롯 3(Fn+9/0)이 완전히 독립적(각 최대 128키)으로 작동하며, 새로운 녹화를 시작하면 기존 매크로를 즉시 삭제하고 그 자리에 새로 생성합니다.\n"),
            rt("• "),
            rt("슬롯별 독립 LED 색상 피드백", bold=True, color="blue"),
            rt(":\n"),
            rt("   - 슬롯 1 (Fn+5/6): 녹화 중 "), rt("빨간색 숨쉬기(Red Pulse)", bold=True, color="red"), rt(", 재생 시 "), rt("빨간색 점등(Solid Red)", bold=True, color="red"), rt("\n"),
            rt("   - 슬롯 2 (Fn+7/8): 녹화 중 "), rt("보라색 숨쉬기(Purple Pulse)", bold=True, color="purple"), rt(", 재생 시 "), rt("보라색 점등(Solid Purple)", bold=True, color="purple"), rt("\n"),
            rt("   - 슬롯 3 (Fn+9/0): 녹화 중 "), rt("골드 숨쉬기(Gold Pulse)", bold=True, color="orange"), rt(", 재생 시 "), rt("골드 점등(Solid Gold)", bold=True, color="orange"), rt("\n"),
            rt("• "),
            rt("마스터 사운드 연동 오디오 피드백", bold=True),
            rt(": 마스터 사운드(Fn+S)가 ON일 때만 사운드가 출력되며, OFF 시 완벽히 무음으로 동작합니다 (녹화 시작: 상승 2음, 녹화 종료: 더블 비프, 재생: 틱음, 용량 초과: 저음 버저).\n"),
            rt("• "),
            rt("12ms BLE 안전 딜레이", bold=True),
            rt(": 블루투스 무선 연결 시 키 누락(키 씹힘)을 완벽 방지하는 12ms 고정 딜레이 인터벌 적용.")
        ], emoji="🎬", color="gray_background"),
        callout_block([
            rt("🔇 마스터 사운드 On/Off 토글 (Fn + S):\n", bold=True, color="blue"),
            rt("• 내장 피에조 부저의 모든 사운드(부팅음, 클릭키, 배터리 경고음, 매크로 효과음)를 총괄하는 마스터 스위치입니다.\n"),
            rt("• "),
            rt("기본값 무음(OFF)", bold=True, color="orange"),
            rt(": 펌웨어 기본값은 OFF 상태로 설정되어 있어 사용자가 직접 켜기 전까지 완벽히 무음으로 동작합니다.\n"),
            rt("• "),
            rt("NVS 플래시 영구 저장", bold=True),
            rt(": 변경된 사운드 상태는 비휘발성 NVS 플래시에 즉시 영구 저장되어 USB 케이블 분리, 전원 스위치 OFF/ON, 배터리 방전 후에도 설정이 그대로 유지됩니다 (사운드 ON 시 재연결 부팅음 정상 출력).\n"),
            rt("• "),
            rt("절전모드 복귀 부팅음 차단", bold=True),
            rt(": 절전모드에서 깨어날 때는 부팅 차임이 울리지 않도록 하드웨어 리셋 원인 필터링이 적용되어 있습니다.\n"),
            rt("• 토글 피드백: On 전환 시 2200Hz 높은 확인음, Off 전환 시 1000Hz 낮은 확인음이 울립니다.")
        ], emoji="🔇", color="gray_background"),
        callout_block([
            rt("🔋 배터리 상태 확인 시스템 (듀얼 모니터링):\n", bold=True, color="green"),
            rt("1. 나비 LED & 오디오 비프음 게이지 (Fn + B):\n", bold=True),
            rt("   • "),
            rt("누르고 있는 동안만 표시(Hold)", bold=True, color="orange"),
            rt(": Fn+B를 누르고 있는 동안 나비 날개 LED에 배터리 잔량 단계가 표시되며, 손을 떼면 즉시 원래 상태(USB 화이트/BLE 블루)로 복귀합니다.\n"),
            rt("   • LED 날개 표시: ≥75% 4개(초록) / 50~74% 3개(연두) / 25~49% 2개(주황) / <25% 1개(빨강)\n"),
            rt("   • ≤15%: 저음 경고음 3회 연속 (마스터 사운드 On 시)\n", color="red"),
            rt("2. 스마트 저배터리 자동 경고:\n", bold=True),
            rt("   • 사용 중 배터리가 최초 15% 이하로 떨어지면 1500Hz 더블 비프음으로 1회 자동 경고합니다.\n"),
            rt("   • 이후 반복 비프를 억제하여 불편함을 방지하며, 20% 이상 충전 시 알림 상태가 자동 리셋됩니다.\n"),
            rt("3. 텍스트 백분율 자동 타이퍼 (Fn + P):\n", bold=True),
            rt("   • 현재 배터리 잔량을 화면 커서 위치에 ", bold=True),
            rt("XX%", bold=True, color="orange"),
            rt(" 형식으로 즉시 타이핑합니다.\n"),
            rt("   • 한/영 입력기 상태에 구애받지 않는 안전한 다이렉트 숫자/퍼센트 전송 기술이 적용되어 있습니다.")
        ], emoji="🔋", color="gray_background"),
        callout_block([
            rt("🔊 오디오 클릭 사운드 토글 (Fn + C):\n", bold=True, color="blue"),
            rt("• 내장 피에조 부저를 이용한 기계식 타건 클릭음(&clicky_toggle)을 On/Off 전환합니다.\n"),
            rt("• On 전환 시 상승 알림음, Off 전환 시 하강 알림음이 울립니다 (마스터 사운드가 On인 경우에만 출력).")
        ], emoji="🔊", color="gray_background"),
        callout_block([
            rt("📡 스마트 하이브리드 USB/BLE 제어 & 나비 LED 인디케이터:\n", bold=True, color="blue"),
            rt("1. 스마트 자동 출력 전환 & NVS 플래시 보존:\n", bold=True),
            rt("   • 케이블 분리 & 배터리 부팅: ", bold=True, color="orange"),
            rt("USB 케이블을 뽑거나 외부 전원 스위치를 켤 때 자동으로 마지막 사용 BLE 슬롯(0~3번)으로 즉시 전환되며, 플래시에 안전하게 보존됩니다.\n"),
            rt("   • PC USB 연결 시: ", bold=True, color="green"),
            rt("PC와 HID 통신이 연결되면 자동으로 USB 유선 출력 모드로 전환되며 나비 로고가 순백색(Clean White)으로 점등됩니다.\n"),
            rt("   • 충전기/보조배터리 연결 시: ", bold=True, color="blue"),
            rt("전원 공급 전용(Power-only) 연결을 감지하여 블루투스 무선 입력을 가로채지 않고 BLE 모드를 유지합니다.\n"),
            rt("2. 프로필 선택 및 수동 제어:\n", bold=True),
            rt("   • Fn + 1 / 2 / 3 / 4: ", bold=True), rt("BLE 프로필 0, 1, 2, 3번 즉시 전환 (최대 4대 기기 멀티페어링)\n"),
            rt("   • 나비 로고 LED 1:1 매핑: ", bold=True), rt("4개의 날개 조각이 4개 프로필에 1:1 대응 (대기: 하늘색 깜빡임, 연결: 사파이어 블루 점등 후 감광, PC USB 유선: 순백색 Clean White)\n"),
            rt("   • Fn + ~ (Grave): ", bold=True), rt("USB 유선 출력과 블루투스 무선 출력 모드 수동 토글 (&out OUT_TOG)\n"),
            rt("   • Fn + → (하단 가장 우측 키): ", bold=True), rt("현재 활성화된 프로필의 BLE 페어링 정보 초기화 (&bt BT_CLR)")
        ], emoji="📡", color="gray_background"),
        callout_block([
            rt("🛠️ 부트로더 진입 (Fn + LCtrl):\n", bold=True, color="orange"),
            rt("• 하단 좌측의 LCtrl 키 위치를 누르면 즉시 "),
            rt("UF2 펌웨어 드라이브 모드로 재기동", bold=True, color="orange"),
            rt("합니다.\n"),
            rt("• 블루투스 설정 보존: 부트로더 모드 진입 시 기존 블루투스 페어링/설정은 전혀 초기화되지 않고 안전하게 보존됩니다.\n"),
            rt("• 실수 진입 시 복귀 방법: 키보드 뒷면 리셋 버튼 1회 클릭, 또는 USB 케이블 재연결 / PC 탐색기에서 '꺼내기(Eject)'를 누르면 일반 키보드 모드로 즉시 정상 복귀합니다.")
        ], emoji="🛠️", color="orange_background"),
        callout_block([
            rt("🔓 ZMK Studio 잠금 해제 (Fn + Z):\n", bold=True, color="blue"),
            rt("• ZMK Studio 웹 앱에서 실시간으로 키맵을 편집할 수 있도록 키보드 보안 잠금을 해제(&studio_unlock)합니다.\n"),
            rt("• 레이어 키(Lower)와의 중복 간섭을 방지하기 위해 Z 키 위치에 안전하게 독립 배치되었습니다.")
        ], emoji="🔓", color="gray_background"),
        divider_block()
    ]

    print("Appending Section 5...")
    notion_request(f"https://api.notion.com/v1/blocks/{page_id}/children", method="PATCH", data={"children": sec5_blocks})

    # Section 6: Quick Reference Table
    sec6_blocks = [
        h2_block("단축키 빠른 참조표 (Quick Reference)"),
        table_block([
            table_row_block([
                [rt("기능 분류", bold=True)],
                [rt("단축키 조합 (Key Combo)", bold=True)],
                [rt("동작 설명", bold=True)]
            ]),
            table_row_block([
                [rt("패스워드 길이 조절", bold=True)],
                [rt("Fn + 노브 회전", code=True)],
                "자리수 12, 16, 20, 24자 순환 (2클릭 1스텝 둔감화, 나비 골드 게이지 1~4개, 도/미/솔/도 음계, NVS 영구 저장)"
            ]),
            table_row_block([
                [rt("DB 안전 패스워드 생성", bold=True)],
                [rt("Fn + 노브 1회 클릭\n또는 Fn + D", code=True)],
                "Zero-Escape DB & Config Safe 패스워드 자동 타이핑 (A-Z, a-z, 0-9, _, -)"
            ]),
            table_row_block([
                [rt("웹 확장 패스워드 생성", bold=True)],
                [rt("Fn + 노브 더블 클릭\n또는 Fn + W", code=True)],
                "특수문자 필수 사이트용 패스워드 자동 타이핑 (A-Z, a-z, 0-9, _, -, @, .)"
            ]),
            table_row_block([
                [rt("영숫자 패스워드 생성", bold=True)],
                [rt("Fn + 노브 롱 클릭 (0.4초)\n또는 Fn + A", code=True)],
                "순수 영문/숫자 패스워드 자동 타이핑 (A-Z, a-z, 0-9)"
            ]),
            table_row_block([
                [rt("매크로 1 녹화/종료", bold=True)],
                [rt("Fn + 5", code=True)],
                "슬롯 1 매크로 녹화 시작/종료 토글 (빨간색 숨쉬기 LED, 새 녹화 시 덮어쓰기)"
            ]),
            table_row_block([
                [rt("매크로 1 재생", bold=True)],
                [rt("Fn + 6", code=True)],
                "슬롯 1 매크로 12ms 안전 딜레이로 재생 (빨간색 점등 LED)"
            ]),
            table_row_block([
                [rt("매크로 2 녹화/종료", bold=True)],
                [rt("Fn + 7", code=True)],
                "슬롯 2 매크로 녹화 시작/종료 토글 (보라색 숨쉬기 LED, 새 녹화 시 덮어쓰기)"
            ]),
            table_row_block([
                [rt("매크로 2 재생", bold=True)],
                [rt("Fn + 8", code=True)],
                "슬롯 2 매크로 12ms 안전 딜레이로 재생 (보라색 점등 LED)"
            ]),
            table_row_block([
                [rt("매크로 3 녹화/종료", bold=True)],
                [rt("Fn + 9", code=True)],
                "슬롯 3 매크로 녹화 시작/종료 토글 (골드 숨쉬기 LED, 새 녹화 시 덮어쓰기)"
            ]),
            table_row_block([
                [rt("매크로 3 재생", bold=True)],
                [rt("Fn + 0", code=True)],
                "슬롯 3 매크로 12ms 안전 딜레이로 재생 (골드 점등 LED)"
            ]),
            table_row_block([
                [rt("마스터 사운드 토글", bold=True)],
                [rt("Fn + S", code=True)],
                "전체 피에조 사운드 On/Off (기본 OFF 무음, 딥슬립 설정 유지)"
            ]),
            table_row_block([
                [rt("배터리 청각/시각 확인", bold=True)],
                [rt("Fn + B (Hold)", code=True)],
                "누르고 있는 동안 나비 날개 LED에 잔량 표시 및 비프음 재생 (<=15% 경고음)"
            ]),
            table_row_block([
                [rt("배터리 화면 출력", bold=True)],
                [rt("Fn + P", code=True)],
                "커서 위치에 'XX%' 형식으로 배터리 잔량 자동 타이핑"
            ]),
            table_row_block([
                [rt("타건 클릭음 토글", bold=True)],
                [rt("Fn + C", code=True)],
                "키 입력 부저 사운드 On/Off 전환 (마스터 사운드 On 시)"
            ]),
            table_row_block([
                [rt("부트로더 모드", bold=True)],
                [rt("Fn + LCtrl", code=True)],
                "펌웨어 업데이트용 UF2 드라이브 진입 (블루투스 설정 보존)"
            ]),
            table_row_block([
                [rt("ZMK Studio 잠금 해제", bold=True)],
                [rt("Fn + Z", code=True)],
                "실시간 키맵 수정 웹 앱 보안 잠금 해제"
            ]),
            table_row_block([
                [rt("BLE 프로필 전환", bold=True)],
                [rt("Fn + 1 / 2 / 3 / 4", code=True)],
                "블루투스 페어링 슬롯 1, 2, 3, 4 선택 (나비 날개 1:1 대응)"
            ]),
            table_row_block([
                [rt("BLE 페어링 삭제", bold=True)],
                [rt("Fn + → (오른쪽 화살표)", code=True)],
                "현재 프로필 페어링 정보 클리어"
            ]),
            table_row_block([
                [rt("USB / BLE 전환", bold=True)],
                [rt("Fn + ~ (Grave)", code=True)],
                "유무선 출력 수동 토글 (케이블 분리/전원 인가 시 BLE 자동 전환 & NVS 플래시 보존)"
            ]),
            table_row_block([
                [rt("음소거 / 볼륨", bold=True)],
                [rt("노브 클릭 / 회전", code=True)],
                "누름: 음소거, 시계 방향: Vol+, 반시계: Vol-"
            ]),
            table_row_block([
                [rt("마우스 커서 이동", bold=True)],
                [rt("Raise + E / S / D / F", code=True)],
                "E(상), S(좌), D(하), F(우) 방향 마우스 커서 이동"
            ]),
            table_row_block([
                [rt("마우스 클릭/휠", bold=True)],
                [rt("Raise + W / R / C / Q / A", code=True)],
                "W(좌클릭), R(우클릭), C(휠클릭), Q(휠위), A(휠아래)"
            ]),
            table_row_block([
                [rt("마우스 휠 좌/우", bold=True)],
                [rt("Raise + X / V", code=True)],
                "X(휠좌), V(휠우)"
            ]),
            table_row_block([
                [rt("웹 앞/뒤로가기", bold=True)],
                [rt("Raise + T / G", code=True)],
                "T(앞으로 가기 MB5), G(뒤로 가기 MB4)"
            ]),
            table_row_block([
                [rt("Tri-Layer 진입", bold=True)],
                [rt("Lower + Raise 동시 누름", code=True)],
                "Function 레이어(Layer 3) 자동 활성화"
            ])
        ], table_width=3, has_column_header=True)
    ]

    print("Appending Section 6...")
    notion_request(f"https://api.notion.com/v1/blocks/{page_id}/children", method="PATCH", data={"children": sec6_blocks})

    print("All sections successfully updated and appended!")
    return page_id, page_url

if __name__ == "__main__":
    page_id, page_url = update_or_create_keymap_page()
    print(f"DONE! Notion Page URL: {page_url}")
