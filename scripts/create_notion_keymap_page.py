import os
import json
import urllib.request
import urllib.error

NOTION_API_TOKEN = os.environ.get("NOTION_API_TOKEN")
PARENT_PAGE_ID = "3d696981-2b85-802f-931b-cddb91fe1cea"
NOTION_VERSION = "2025-09-03"

GITHUB_IMG_BASE = "https://raw.githubusercontent.com/samake-2T2/keyboardio-preonic-zmk-config/master/docs/images"

def notion_request(url, method="GET", data=None):
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
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode("utf-8")
        print(f"HTTPError {e.code}: {err_msg}")
        raise

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

def create_keymap_page():
    print("Creating Notion page...")
    initial_blocks = [
        callout_block([
            rt("본 문서는 ", bold=True),
            rt("Keyboardio Preonic (nRF52840)", bold=True, color="blue"),
            rt(" 무선 기계식 키보드의 공식 ZMK 커스텀 키맵 가이드입니다.\n\n"),
            rt("특징 요약:\n", bold=True),
            rt("• 레이아웃: ", bold=True),
            rt("5x12 직교(Ortholinear) 배열 + "),
            rt("중앙 2U 스페이스바", bold=True, color="orange"),
            rt(" (MIT 레이아웃)\n"),
            rt("• 상단 보조 키: ", bold=True),
            rt("PrtSc 화면 캡처, 독립 Fn 키, "),
            rt("로터리 인코더(음량/음소거)", bold=True, color="green"),
            rt("\n• 배터리 모니터링: ", bold=True),
            rt("비프음 오디오 게이지(구간별 음계 + 15% 저배터리 자동 경고음) & 텍스트 백분율 자동 타이퍼(XX%)\n"),
            rt("• 피드백 및 편의: ", bold=True),
            rt("키 클릭음 토글(&clicky_toggle), 마우스 커서/클릭 에뮬레이션, 다이렉트 부트로더 진입\n\n"),
            rt("🔗 GitHub 펌웨어 저장소 바로가기", bold=True, link="https://github.com/samake-2T2/keyboardio-preonic-zmk-config")
        ], emoji="⌨️", color="blue_background"),
        divider_block()
    ]

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
                "QWERTY 알파벳, 한/영 전환, 중앙 2U 스페이스, 로터리 볼륨 노브"
            ]),
            table_row_block([
                [rt("Layer 1: Lower", bold=True, color="brown")],
                "바텀열 Lower 키 누른 상태 유지 (Hold)",
                "오른손 3x3 텐키패드(Numpad) + 2U '0' 키, 좌측 문서 네비게이션"
            ]),
            table_row_block([
                [rt("Layer 2: Raise", bold=True, color="green")],
                "바텀열 Raise 키 누른 상태 유지 (Hold)",
                "Shift 특수문자 및 기호류 완비, 오른손 마우스 커서/클릭/휠 제어"
            ]),
            table_row_block([
                [rt("Layer 3: Function & Tri", bold=True, color="purple")],
                "상단 Fn 키 누름 OR Lower + Raise 동시 입력",
                "BLE 프로필(1~3), 배터리 비프음/타이퍼, 클릭 사운드 토글, 부트로더 진입"
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
            rt("Row 3 좌측은 Esc/Caps, Row 4 좌측 LShift, Row 5 좌측 LCtrl, LGui, LAlt 순으로 직관적으로 배치되어 있습니다.")
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
            rt("   - 사칙연산 키(/, *, -, +) 및 소수점(.), Numpad Enter 완비\n"),
            rt("• 왼손 문서 편집 및 방향키 네비게이션:\n", bold=True, color="green"),
            rt("   - Row 2~3: Home, End, Page Up, Page Down, Delete\n"),
            rt("   - 왼손 영역에도 상/하/좌/우 커서 방향키가 매핑되어 있어 오른손 마우스 조작 중 왼손만으로 방향 이동 가능\n"),
            rt("• 상단 숫자열: ", bold=True),
            rt("숫자열 전체에 Shift 기호(~, !, @, #, $, %, ^, &, *, (, ))와 Delete 매핑")
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
            rt("• 코딩 및 문서용 특수 기호 완비:\n", bold=True, color="blue"),
            rt("   - 중괄호 및 대괄호: {, }, [, ]\n"),
            rt("   - 연산 및 구분 기호: +, -, =, _, |, ~, `, Backslash\n"),
            rt("   - 상단 전체에 특수문자 (!, @, #, $, %, ^, &, *, (, )) 배치\n"),
            rt("• 오른손 정밀 마우스 에뮬레이션 (ZMK Mouse Keys):\n", bold=True, color="purple"),
            rt("   - 커서 이동: ", bold=True),
            rt("I (상), J (좌), K (하), L (우) - 부드러운 가속 곡선 적용\n"),
            rt("   - 마우스 클릭: ", bold=True),
            rt("U (좌클릭 LMB), O (우클릭 RMB), H (휠클릭 MMB)\n"),
            rt("   - 마우스 휠 스크롤: ", bold=True),
            rt("[ (스크롤 업), ; (스크롤 다운)")
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
            rt("됩니다. 키보드의 하드웨어 설정, 배터리 진단, 무선 연결 및 펌웨어 복구를 제어합니다.")
        ]),
        image_block(
            f"{GITHUB_IMG_BASE}/layer3_func.png",
            caption_text="Layer 3: Function & Tri-Layer (System, Battery, BLE, Audio Control)"
        ),
        callout_block([
            rt("🔋 배터리 상태 확인 시스템 (듀얼 모니터링):\n", bold=True, color="green"),
            rt("1. 나비 LED & 오디오 비프음 게이지 (Fn + B):\n", bold=True),
            rt("   • "),
            rt("누르고 있는 동안만 표시(Hold)", bold=True, color="orange"),
            rt(": Fn+B를 누르고 있는 동안 나비 날개 LED에 배터리 잔량 단계가 표시되며, 손을 떼면 즉시 원래 상태(USB 화이트/BLE 블루)로 복귀합니다.\n"),
            rt("   • LED 날개 표시: ≥75% 4개(초록) / 50~74% 3개(라임) / 25~49% 2개(주황) / <25% 1개(빨강)\n"),
            rt("   • ≤15%: 저음 경고음 3회 연속 (15% 진입 시 1회 자동 경고 비프음 발생)\n", color="red"),
            rt("   • 16% ~ 39%: 단음 1회 (도) / 40% ~ 69%: 2중음 (도 - 미) / 70% ~ 89%: 3중음 / ≥90%: 4중음 아르페지오\n\n"),
            rt("2. 텍스트 백분율 자동 타이퍼 (Fn + P):\n", bold=True),
            rt("   • 현재 배터리 잔량을 화면 커서 위치에 ", bold=True),
            rt("XX%", bold=True, color="orange"),
            rt(" 형식으로 즉시 타이핑합니다.\n"),
            rt("   • 한/영 입력기 상태에 구애받지 않는 안전한 다이렉트 숫자/퍼센트 전송 기술이 적용되어 있습니다.")
        ], emoji="🔋", color="gray_background"),
        callout_block([
            rt("🔊 오디오 클릭 사운드 토글 (Fn + C):\n", bold=True, color="blue"),
            rt("• 내장 피에조 부저를 이용한 기계식 타건 클릭음(&clicky_toggle)을 On/Off 전환합니다.\n"),
            rt("• On 전환 시 상승 알림음, Off 전환 시 하강 알림음이 울립니다.")
        ], emoji="🔊", color="gray_background"),
        callout_block([
            rt("📡 블루투스(BLE) 및 USB 유무선 제어:\n", bold=True, color="blue"),
            rt("• Fn + Q / W / E: ", bold=True), rt("BLE 프로필 1, 2, 3번 즉시 전환\n"),
            rt("• Fn + T: ", bold=True), rt("현재 활성화된 프로필의 BLE 페어링 정보 초기화 (&bt BT_CLR)\n"),
            rt("• Fn + Y: ", bold=True), rt("USB 유선 출력과 블루투스 무선 출력 모드 수동 토글 (&out OUT_TOG)\n"),
            rt("• 나비 LED 색상: USB 모드는 화이트(White), BLE 모드는 블루(Cyan/Blue)로 점등되어 배터리 게이지와 확실히 구별됩니다.")
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
                [rt("배터리 청각/시각 확인", bold=True)],
                [rt("Fn + B (Hold)", code=True)],
                "누르고 있는 동안 나비 날개 LED에 잔량 표시 및 비프음 재생"
            ]),
            table_row_block([
                [rt("배터리 화면 출력", bold=True)],
                [rt("Fn + P", code=True)],
                "커서 위치에 'XX%' 형식으로 배터리 잔량 자동 타이핑"
            ]),
            table_row_block([
                [rt("타건 클릭음 토글", bold=True)],
                [rt("Fn + C", code=True)],
                "키 입력 부저 사운드 On/Off 전환"
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
                [rt("Fn + Q / W / E", code=True)],
                "블루투스 페어링 슬롯 1, 2, 3 선택"
            ]),
            table_row_block([
                [rt("BLE 페어링 삭제", bold=True)],
                [rt("Fn + T", code=True)],
                "현재 프로필 페어링 정보 클리어"
            ]),
            table_row_block([
                [rt("USB / BLE 전환", bold=True)],
                [rt("Fn + Y", code=True)],
                "유선 연결과 무선 연결 모드 강제 토글"
            ]),
            table_row_block([
                [rt("음소거 / 볼륨", bold=True)],
                [rt("노브 클릭 / 회전", code=True)],
                "누름: 음소거, 시계 방향: Vol+, 반시계: Vol-"
            ]),
            table_row_block([
                [rt("마우스 커서 이동", bold=True)],
                [rt("Raise + I / J / K / L", code=True)],
                "I(상), J(좌), K(하), L(우) 방향 마우스 이동"
            ]),
            table_row_block([
                [rt("마우스 클릭/휠", bold=True)],
                [rt("Raise + U / O / H / [ / ;", code=True)],
                "U(좌클릭), O(우클릭), H(휠클릭), [(휠위), ;(휠아래)"
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

    print("All sections successfully created and appended!")
    return page_id, page_url

if __name__ == "__main__":
    page_id, page_url = create_keymap_page()
    print(f"DONE! Notion Page URL: {page_url}")
