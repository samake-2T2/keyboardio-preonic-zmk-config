import os
from PIL import Image, ImageDraw, ImageFont

# Canvas dimensions
PAD_X = 60
PAD_Y = 110
U_W = 86
U_H = 76
GAP = 10
TOTAL_W = PAD_X * 2 + 12 * U_W + 11 * GAP
TOTAL_H = PAD_Y + 6 * (U_H + GAP) + 45

# Color Palette
BG_COLOR = (18, 18, 22)         # Deep slate dark
BORDER_KEY = (60, 62, 74)       # Key outline
SHADOW_COLOR = (10, 10, 14)     # Key shadow
TEXT_WHITE = (248, 248, 252)
TEXT_MUTED = (180, 182, 195)
TEXT_DIM = (95, 95, 110)

# Role Colors
COLOR_ALPHA = (48, 50, 60)         # Alphanumeric keys
COLOR_MOD = (34, 36, 44)           # Modifiers (Ctrl, Alt, Shift, Enter, etc)
COLOR_LAYER_LOWER = (29, 78, 216)  # Blue (Lower)
COLOR_LAYER_RAISE = (126, 34, 206) # Purple (Raise)
COLOR_LAYER_FN = (5, 150, 105)     # Emerald Green (Fn)
COLOR_NUMPAD = (217, 119, 6)       # Amber (Numpad)
COLOR_MOUSE = (13, 148, 136)       # Teal (Mouse & Wheel)
COLOR_SYM = (79, 70, 229)          # Indigo (Symbols)
COLOR_FEATURE = (225, 29, 72)      # Rose (Special features: Clicky, Battery, Typer)
COLOR_BLE = (2, 132, 199)          # Sky Blue (Bluetooth & Output)
COLOR_DANGER = (220, 38, 38)       # Red (Bootloader, BT Clear)
COLOR_TRANS = (26, 27, 32)         # Transparent / unused on layer

FONT_PATH = "/usr/share/fonts/google-noto-sans-cjk-vf-fonts/NotoSansCJK-VF.ttc"

def get_font(size, weight="Bold"):
    f = ImageFont.truetype(FONT_PATH, size, index=1)
    if hasattr(f, "set_variation_by_name"):
        try:
            f.set_variation_by_name(weight)
        except Exception:
            pass
    return f

FONT_TITLE = get_font(28, "Bold")
FONT_SUBTITLE = get_font(16, "Medium")
FONT_MAIN = get_font(20, "Bold")
FONT_SUB = get_font(12, "Medium")
FONT_TAG = get_font(11, "Bold")

def draw_key(draw, x, y, w, h, main_text, sub_text="", bg_color=COLOR_ALPHA, text_color=TEXT_WHITE, radius=8, is_knob=False, tag=""):
    # Shadow
    draw.rounded_rectangle([x + 2, y + 4, x + w + 2, y + h + 4], radius=radius, fill=SHADOW_COLOR)
    # Key face
    draw.rounded_rectangle([x, y, x + w, y + h], radius=radius, fill=bg_color, outline=BORDER_KEY, width=1)
    
    if is_knob:
        cx, cy = x + w / 2, y + h / 2 - 4
        r = min(w, h) / 2 - 8
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(55, 58, 70), outline=(14, 165, 233), width=2)
        inner_r = r - 7
        draw.ellipse([cx - inner_r, cy - inner_r, cx + inner_r, cy + inner_r], fill=(30, 32, 40))
        draw.ellipse([cx - 3, cy - 3, cx + 3, cy + 3], fill=(14, 165, 233))
    
    if tag:
        t_bbox = draw.textbbox((0, 0), tag, font=FONT_TAG)
        tw = t_bbox[2] - t_bbox[0]
        draw.rounded_rectangle([x + w - tw - 9, y + 4, x + w - 4, y + 18], radius=3, fill=(10, 10, 15, 210))
        draw.text((x + w - tw - 6, y + 4), tag, fill=(210, 230, 255), font=FONT_TAG)
        
    if sub_text:
        bbox1 = draw.textbbox((0, 0), main_text, font=FONT_MAIN)
        w1, h1 = bbox1[2] - bbox1[0], bbox1[3] - bbox1[1]
        draw.text((x + (w - w1) / 2, y + (h / 2) - h1 - 2), main_text, fill=text_color, font=FONT_MAIN)
        
        bbox2 = draw.textbbox((0, 0), sub_text, font=FONT_SUB)
        w2, h2 = bbox2[2] - bbox2[0], bbox2[3] - bbox2[1]
        draw.text((x + (w - w2) / 2, y + (h / 2) + 4), sub_text, fill=TEXT_MUTED if text_color == TEXT_WHITE else text_color, font=FONT_SUB)
    else:
        bbox = draw.textbbox((0, 0), main_text, font=FONT_MAIN)
        w1, h1 = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text((x + (w - w1) / 2, y + (h - h1) / 2 - 2), main_text, fill=text_color, font=FONT_MAIN)

def render_layer(title, subtitle, keys, out_file):
    img = Image.new("RGBA", (TOTAL_W, TOTAL_H), BG_COLOR)
    draw = ImageDraw.Draw(img)
    
    # Title
    draw.text((PAD_X, 30), title, fill=TEXT_WHITE, font=FONT_TITLE)
    draw.text((PAD_X, 68), subtitle, fill=TEXT_MUTED, font=FONT_SUBTITLE)
    
    # Keyboard Case Outline
    draw.rounded_rectangle(
        [PAD_X - 16, PAD_Y - 16, TOTAL_W - PAD_X + 16, TOTAL_H - 24],
        radius=18, fill=(24, 25, 30), outline=(50, 52, 60), width=2
    )
    
    # Top Logo Plate Area (Columns 0..8 of Row 0)
    logo_w = 9 * U_W + 8 * GAP
    draw.rounded_rectangle(
        [PAD_X, PAD_Y, PAD_X + logo_w, PAD_Y + U_H],
        radius=10, fill=(30, 31, 38), outline=(48, 50, 60), width=1
    )
    logo_text = "Keyboardio Butterfly Logo (4-Wing RGB BLE Profile & Battery Gauge LEDs)"
    lb = draw.textbbox((0, 0), logo_text, font=FONT_SUB)
    draw.text((PAD_X + (logo_w - (lb[2] - lb[0])) / 2, PAD_Y + (U_H - (lb[3] - lb[1])) / 2), logo_text, fill=(140, 160, 190), font=FONT_SUB)
    
    for k in keys:
        col, row = k["col"], k["row"]
        span = k.get("span", 1.0)
        x = PAD_X + col * (U_W + GAP)
        y = PAD_Y + row * (U_H + GAP)
        w = int(span * U_W + (span - 1) * GAP)
        h = U_H
        draw_key(
            draw, x, y, w, h,
            main_text=k.get("main", ""),
            sub_text=k.get("sub", ""),
            bg_color=k.get("bg", COLOR_ALPHA),
            text_color=k.get("fg", TEXT_WHITE),
            radius=8,
            is_knob=k.get("is_knob", False),
            tag=k.get("tag", "")
        )
        
    img.save(out_file, "PNG")
    print(f"Generated: {out_file}")

# ----------------------------------------------------
# 1. BASE LAYER (Layer 0)
# ----------------------------------------------------
base_keys = [
    # Top row
    {"col": 9, "row": 0, "main": "PrtSc", "sub": "Screen", "bg": COLOR_MOD},
    {"col": 10, "row": 0, "main": "Fn", "sub": "Layer 3", "bg": COLOR_LAYER_FN},
    {"col": 11, "row": 0, "main": "Mute", "sub": "Vol Up/Dn", "bg": COLOR_MOD, "is_knob": True},
    # Row 1 (Numbers)
    {"col": 0, "row": 1, "main": "` ~", "bg": COLOR_MOD},
    {"col": 1, "row": 1, "main": "1", "sub": "!"},
    {"col": 2, "row": 1, "main": "2", "sub": "@"},
    {"col": 3, "row": 1, "main": "3", "sub": "#"},
    {"col": 4, "row": 1, "main": "4", "sub": "$"},
    {"col": 5, "row": 1, "main": "5", "sub": "%"},
    {"col": 6, "row": 1, "main": "6", "sub": "^"},
    {"col": 7, "row": 1, "main": "7", "sub": "&"},
    {"col": 8, "row": 1, "main": "8", "sub": "*"},
    {"col": 9, "row": 1, "main": "9", "sub": "("},
    {"col": 10, "row": 1, "main": "0", "sub": ")"},
    {"col": 11, "row": 1, "main": "Bksp", "bg": COLOR_MOD},
    # Row 2
    {"col": 0, "row": 2, "main": "Tab", "bg": COLOR_MOD},
    {"col": 1, "row": 2, "main": "Q"},
    {"col": 2, "row": 2, "main": "W"},
    {"col": 3, "row": 2, "main": "E"},
    {"col": 4, "row": 2, "main": "R"},
    {"col": 5, "row": 2, "main": "T"},
    {"col": 6, "row": 2, "main": "Y"},
    {"col": 7, "row": 2, "main": "U"},
    {"col": 8, "row": 2, "main": "I"},
    {"col": 9, "row": 2, "main": "O"},
    {"col": 10, "row": 2, "main": "P"},
    {"col": 11, "row": 2, "main": "\\ |", "bg": COLOR_MOD},
    # Row 3
    {"col": 0, "row": 3, "main": "Esc", "bg": COLOR_MOD},
    {"col": 1, "row": 3, "main": "A"},
    {"col": 2, "row": 3, "main": "S"},
    {"col": 3, "row": 3, "main": "D"},
    {"col": 4, "row": 3, "main": "F"},
    {"col": 5, "row": 3, "main": "G"},
    {"col": 6, "row": 3, "main": "H"},
    {"col": 7, "row": 3, "main": "J"},
    {"col": 8, "row": 3, "main": "K"},
    {"col": 9, "row": 3, "main": "L"},
    {"col": 10, "row": 3, "main": "; :"},
    {"col": 11, "row": 3, "main": "' \"", "bg": COLOR_MOD},
    # Row 4
    {"col": 0, "row": 4, "main": "Shift", "bg": COLOR_MOD},
    {"col": 1, "row": 4, "main": "Z"},
    {"col": 2, "row": 4, "main": "X"},
    {"col": 3, "row": 4, "main": "C"},
    {"col": 4, "row": 4, "main": "V"},
    {"col": 5, "row": 4, "main": "B"},
    {"col": 6, "row": 4, "main": "N"},
    {"col": 7, "row": 4, "main": "M"},
    {"col": 8, "row": 4, "main": ", <"},
    {"col": 9, "row": 4, "main": ". >"},
    {"col": 10, "row": 4, "main": "/ ?"},
    {"col": 11, "row": 4, "main": "Enter", "bg": COLOR_MOD},
    # Row 5 (Thumbs & 2U Space)
    {"col": 0, "row": 5, "main": "Ctrl", "bg": COLOR_MOD},
    {"col": 1, "row": 5, "main": "Gui", "sub": "Win/Cmd", "bg": COLOR_MOD},
    {"col": 2, "row": 5, "main": "Alt", "bg": COLOR_MOD},
    {"col": 3, "row": 5, "main": "RAlt", "sub": "한/영", "bg": COLOR_MOD},
    {"col": 4, "row": 5, "main": "Lower", "sub": "Layer 1", "bg": COLOR_LAYER_LOWER},
    {"col": 5, "row": 5, "span": 2.0, "main": "Space", "sub": "Centered 2U Spacebar", "bg": COLOR_ALPHA, "tag": "2U"},
    {"col": 7, "row": 5, "main": "Raise", "sub": "Layer 2", "bg": COLOR_LAYER_RAISE},
    {"col": 8, "row": 5, "main": "←", "sub": "Left", "bg": COLOR_MOD},
    {"col": 9, "row": 5, "main": "↓", "sub": "Down", "bg": COLOR_MOD},
    {"col": 10, "row": 5, "main": "↑", "sub": "Up", "bg": COLOR_MOD},
    {"col": 11, "row": 5, "main": "→", "sub": "Right", "bg": COLOR_MOD},
]

# ----------------------------------------------------
# 2. LOWER LAYER (Layer 1: Numpad & Navigation)
# ----------------------------------------------------
lower_keys = [
    # Top row
    {"col": 9, "row": 0, "main": "▽", "bg": COLOR_TRANS, "fg": TEXT_DIM},
    {"col": 10, "row": 0, "main": "▽", "bg": COLOR_TRANS, "fg": TEXT_DIM},
    {"col": 11, "row": 0, "main": "Mute", "sub": "Vol Up/Dn", "bg": COLOR_MOD, "is_knob": True},
    # Row 1 (F-Keys)
    {"col": 0, "row": 1, "main": "▽", "bg": COLOR_TRANS, "fg": TEXT_DIM},
    {"col": 1, "row": 1, "main": "F1", "bg": COLOR_MOD},
    {"col": 2, "row": 1, "main": "F2", "bg": COLOR_MOD},
    {"col": 3, "row": 1, "main": "F3", "bg": COLOR_MOD},
    {"col": 4, "row": 1, "main": "F4", "bg": COLOR_MOD},
    {"col": 5, "row": 1, "main": "F5", "bg": COLOR_MOD},
    {"col": 6, "row": 1, "main": "F6", "bg": COLOR_MOD},
    {"col": 7, "row": 1, "main": "F7", "bg": COLOR_MOD},
    {"col": 8, "row": 1, "main": "F8", "bg": COLOR_MOD},
    {"col": 9, "row": 1, "main": "F9", "bg": COLOR_MOD},
    {"col": 10, "row": 1, "main": "F10", "bg": COLOR_MOD},
    {"col": 11, "row": 1, "main": "F11", "bg": COLOR_MOD},
    # Row 2 (Nav & Numpad Top)
    {"col": 0, "row": 2, "main": "▽", "bg": COLOR_TRANS, "fg": TEXT_DIM},
    {"col": 1, "row": 2, "main": "PgUp", "bg": COLOR_MOD},
    {"col": 2, "row": 2, "main": "Home", "bg": COLOR_MOD},
    {"col": 3, "row": 2, "main": "Up", "sub": "↑", "bg": COLOR_MOD},
    {"col": 4, "row": 2, "main": "End", "bg": COLOR_MOD},
    {"col": 5, "row": 2, "main": "Insert", "bg": COLOR_MOD},
    {"col": 6, "row": 2, "main": "▽", "bg": COLOR_TRANS, "fg": TEXT_DIM},
    {"col": 7, "row": 2, "main": "7", "bg": COLOR_NUMPAD},
    {"col": 8, "row": 2, "main": "8", "bg": COLOR_NUMPAD},
    {"col": 9, "row": 2, "main": "9", "bg": COLOR_NUMPAD},
    {"col": 10, "row": 2, "main": "NumLk", "sub": "Keypad", "bg": COLOR_NUMPAD},
    {"col": 11, "row": 2, "main": "F12", "bg": COLOR_MOD},
    # Row 3 (Nav & Numpad Mid)
    {"col": 0, "row": 3, "main": "Caps", "bg": COLOR_MOD},
    {"col": 1, "row": 3, "main": "PgDn", "bg": COLOR_MOD},
    {"col": 2, "row": 3, "main": "Left", "sub": "←", "bg": COLOR_MOD},
    {"col": 3, "row": 3, "main": "Down", "sub": "↓", "bg": COLOR_MOD},
    {"col": 4, "row": 3, "main": "Right", "sub": "→", "bg": COLOR_MOD},
    {"col": 5, "row": 3, "main": "Del", "bg": COLOR_MOD},
    {"col": 6, "row": 3, "main": "▽", "bg": COLOR_TRANS, "fg": TEXT_DIM},
    {"col": 7, "row": 3, "main": "4", "bg": COLOR_NUMPAD},
    {"col": 8, "row": 3, "main": "5", "bg": COLOR_NUMPAD},
    {"col": 9, "row": 3, "main": "6", "bg": COLOR_NUMPAD},
    {"col": 10, "row": 3, "main": "▽", "bg": COLOR_TRANS, "fg": TEXT_DIM},
    {"col": 11, "row": 3, "main": "▽", "bg": COLOR_TRANS, "fg": TEXT_DIM},
    # Row 4 (Numpad Bot)
    {"col": 0, "row": 4, "main": "▽", "bg": COLOR_TRANS, "fg": TEXT_DIM},
    {"col": 1, "row": 4, "main": "▽", "bg": COLOR_TRANS, "fg": TEXT_DIM},
    {"col": 2, "row": 4, "main": "▽", "bg": COLOR_TRANS, "fg": TEXT_DIM},
    {"col": 3, "row": 4, "main": "▽", "bg": COLOR_TRANS, "fg": TEXT_DIM},
    {"col": 4, "row": 4, "main": "▽", "bg": COLOR_TRANS, "fg": TEXT_DIM},
    {"col": 5, "row": 4, "main": "▽", "bg": COLOR_TRANS, "fg": TEXT_DIM},
    {"col": 6, "row": 4, "main": "▽", "bg": COLOR_TRANS, "fg": TEXT_DIM},
    {"col": 7, "row": 4, "main": "1", "bg": COLOR_NUMPAD},
    {"col": 8, "row": 4, "main": "2", "bg": COLOR_NUMPAD},
    {"col": 9, "row": 4, "main": "3", "bg": COLOR_NUMPAD},
    {"col": 10, "row": 4, "main": "▽", "bg": COLOR_TRANS, "fg": TEXT_DIM},
    {"col": 11, "row": 4, "main": "▽", "bg": COLOR_TRANS, "fg": TEXT_DIM},
    # Row 5 (Thumbs & 2U 0)
    {"col": 0, "row": 5, "main": "▽", "bg": COLOR_TRANS, "fg": TEXT_DIM},
    {"col": 1, "row": 5, "main": "▽", "bg": COLOR_TRANS, "fg": TEXT_DIM},
    {"col": 2, "row": 5, "main": "▽", "bg": COLOR_TRANS, "fg": TEXT_DIM},
    {"col": 3, "row": 5, "main": "RCtrl", "bg": COLOR_MOD},
    {"col": 4, "row": 5, "main": "HOLD", "sub": "Lower", "bg": COLOR_LAYER_LOWER},
    {"col": 5, "row": 5, "span": 2.0, "main": "0", "sub": "Keypad 2U Zero", "bg": COLOR_NUMPAD, "tag": "2U"},
    {"col": 7, "row": 5, "main": "Tri-Fn", "sub": "+Raise", "bg": COLOR_LAYER_FN},
    {"col": 8, "row": 5, "main": "0", "sub": "KP 0", "bg": COLOR_NUMPAD},
    {"col": 9, "row": 5, "main": "0", "sub": "KP 0", "bg": COLOR_NUMPAD},
    {"col": 10, "row": 5, "main": "▽", "bg": COLOR_TRANS, "fg": TEXT_DIM},
    {"col": 11, "row": 5, "main": "▽", "bg": COLOR_TRANS, "fg": TEXT_DIM},
]

# ----------------------------------------------------
# 3. RAISE LAYER (Layer 2: Symbols & Mouse Keys)
# ----------------------------------------------------
raise_keys = [
    # Top row
    {"col": 9, "row": 0, "main": "▽", "bg": COLOR_TRANS, "fg": TEXT_DIM},
    {"col": 10, "row": 0, "main": "▽", "bg": COLOR_TRANS, "fg": TEXT_DIM},
    {"col": 11, "row": 0, "main": "Mute", "sub": "Vol Up/Dn", "bg": COLOR_MOD, "is_knob": True},
    # Row 1 (F-Keys)
    {"col": 0, "row": 1, "main": "▽", "bg": COLOR_TRANS, "fg": TEXT_DIM},
    {"col": 1, "row": 1, "main": "F1", "bg": COLOR_MOD},
    {"col": 2, "row": 1, "main": "F2", "bg": COLOR_MOD},
    {"col": 3, "row": 1, "main": "F3", "bg": COLOR_MOD},
    {"col": 4, "row": 1, "main": "F4", "bg": COLOR_MOD},
    {"col": 5, "row": 1, "main": "F5", "bg": COLOR_MOD},
    {"col": 6, "row": 1, "main": "F6", "bg": COLOR_MOD},
    {"col": 7, "row": 1, "main": "F7", "bg": COLOR_MOD},
    {"col": 8, "row": 1, "main": "F8", "bg": COLOR_MOD},
    {"col": 9, "row": 1, "main": "F9", "bg": COLOR_MOD},
    {"col": 10, "row": 1, "main": "F10", "bg": COLOR_MOD},
    {"col": 11, "row": 1, "main": "F11", "bg": COLOR_MOD},
    # Row 2 (Mouse & Symbols)
    {"col": 0, "row": 2, "main": "▽", "bg": COLOR_TRANS, "fg": TEXT_DIM},
    {"col": 1, "row": 2, "main": "ScrlUp", "sub": "Wheel ↑", "bg": COLOR_MOUSE},
    {"col": 2, "row": 2, "main": "L-Click", "sub": "Mouse L", "bg": COLOR_MOUSE},
    {"col": 3, "row": 2, "main": "Cur Up", "sub": "Cursor ↑", "bg": COLOR_MOUSE},
    {"col": 4, "row": 2, "main": "R-Click", "sub": "Mouse R", "bg": COLOR_MOUSE},
    {"col": 5, "row": 2, "main": "Fwd", "sub": "Mouse 5", "bg": COLOR_MOUSE},
    {"col": 6, "row": 2, "main": "▽", "bg": COLOR_TRANS, "fg": TEXT_DIM},
    {"col": 7, "row": 2, "main": "- _", "sub": "Minus", "bg": COLOR_SYM},
    {"col": 8, "row": 2, "main": "= +", "sub": "Equal", "bg": COLOR_SYM},
    {"col": 9, "row": 2, "main": "[ {", "sub": "L-Brkt", "bg": COLOR_SYM},
    {"col": 10, "row": 2, "main": "] }", "sub": "R-Brkt", "bg": COLOR_SYM},
    {"col": 11, "row": 2, "main": "F12", "bg": COLOR_MOD},
    # Row 3 (Mouse & Symbols)
    {"col": 0, "row": 3, "main": "Caps", "bg": COLOR_MOD},
    {"col": 1, "row": 3, "main": "ScrlDn", "sub": "Wheel ↓", "bg": COLOR_MOUSE},
    {"col": 2, "row": 3, "main": "Cur Left", "sub": "Cursor ←", "bg": COLOR_MOUSE},
    {"col": 3, "row": 3, "main": "Cur Down", "sub": "Cursor ↓", "bg": COLOR_MOUSE},
    {"col": 4, "row": 3, "main": "Cur Right", "sub": "Cursor →", "bg": COLOR_MOUSE},
    {"col": 5, "row": 3, "main": "Back", "sub": "Mouse 4", "bg": COLOR_MOUSE},
    {"col": 6, "row": 3, "main": "▽", "bg": COLOR_TRANS, "fg": TEXT_DIM},
    {"col": 7, "row": 3, "main": "_", "sub": "Under", "bg": COLOR_SYM},
    {"col": 8, "row": 3, "main": "+", "sub": "Plus", "bg": COLOR_SYM},
    {"col": 9, "row": 3, "main": "{", "sub": "L-Brace", "bg": COLOR_SYM},
    {"col": 10, "row": 3, "main": "}", "sub": "R-Brace", "bg": COLOR_SYM},
    {"col": 11, "row": 3, "main": "▽", "bg": COLOR_TRANS, "fg": TEXT_DIM},
    # Row 4 (Mouse Wheel H & Parens)
    {"col": 0, "row": 4, "main": "▽", "bg": COLOR_TRANS, "fg": TEXT_DIM},
    {"col": 1, "row": 4, "main": "▽", "bg": COLOR_TRANS, "fg": TEXT_DIM},
    {"col": 2, "row": 4, "main": "ScrlL", "sub": "Wheel ←", "bg": COLOR_MOUSE},
    {"col": 3, "row": 4, "main": "M-Click", "sub": "Wheel Mid", "bg": COLOR_MOUSE},
    {"col": 4, "row": 4, "main": "ScrlR", "sub": "Wheel →", "bg": COLOR_MOUSE},
    {"col": 5, "row": 4, "main": "▽", "bg": COLOR_TRANS, "fg": TEXT_DIM},
    {"col": 6, "row": 4, "main": "▽", "bg": COLOR_TRANS, "fg": TEXT_DIM},
    {"col": 7, "row": 4, "main": "▽", "bg": COLOR_TRANS, "fg": TEXT_DIM},
    {"col": 8, "row": 4, "main": "▽", "bg": COLOR_TRANS, "fg": TEXT_DIM},
    {"col": 9, "row": 4, "main": "(", "sub": "L-Paren", "bg": COLOR_SYM},
    {"col": 10, "row": 4, "main": ")", "sub": "R-Paren", "bg": COLOR_SYM},
    {"col": 11, "row": 4, "main": "▽", "bg": COLOR_TRANS, "fg": TEXT_DIM},
    # Row 5 (Thumbs & 2U Space)
    {"col": 0, "row": 5, "main": "▽", "bg": COLOR_TRANS, "fg": TEXT_DIM},
    {"col": 1, "row": 5, "main": "▽", "bg": COLOR_TRANS, "fg": TEXT_DIM},
    {"col": 2, "row": 5, "main": "▽", "bg": COLOR_TRANS, "fg": TEXT_DIM},
    {"col": 3, "row": 5, "main": "▽", "bg": COLOR_TRANS, "fg": TEXT_DIM},
    {"col": 4, "row": 5, "main": "Tri-Fn", "sub": "+Lower", "bg": COLOR_LAYER_FN},
    {"col": 5, "row": 5, "span": 2.0, "main": "Space", "sub": "Centered 2U Spacebar", "bg": COLOR_ALPHA, "tag": "2U"},
    {"col": 7, "row": 5, "main": "HOLD", "sub": "Raise", "bg": COLOR_LAYER_RAISE},
    {"col": 8, "row": 5, "main": "▽", "bg": COLOR_TRANS, "fg": TEXT_DIM},
    {"col": 9, "row": 5, "main": "▽", "bg": COLOR_TRANS, "fg": TEXT_DIM},
    {"col": 10, "row": 5, "main": "▽", "bg": COLOR_TRANS, "fg": TEXT_DIM},
    {"col": 11, "row": 5, "main": "▽", "bg": COLOR_TRANS, "fg": TEXT_DIM},
]

# ----------------------------------------------------
# 4. FUNCTION & TRI-LAYER (Layer 3 & 4: BLE, Sound, Battery, Bootloader)
# ----------------------------------------------------
func_keys = [
    # Top row
    {"col": 9, "row": 0, "main": "▽", "bg": COLOR_TRANS, "fg": TEXT_DIM},
    {"col": 10, "row": 0, "main": "HOLD", "sub": "Fn Active", "bg": COLOR_LAYER_FN},
    {"col": 11, "row": 0, "main": "Mute", "sub": "Vol Up/Dn", "bg": COLOR_MOD, "is_knob": True},
    # Row 1 (Output & Bluetooth Profiles)
    {"col": 0, "row": 1, "main": "OUT TOG", "sub": "USB ↔ BLE", "bg": COLOR_BLE},
    {"col": 1, "row": 1, "main": "BT 0", "sub": "Wing 0", "bg": COLOR_BLE},
    {"col": 2, "row": 1, "main": "BT 1", "sub": "Wing 1", "bg": COLOR_BLE},
    {"col": 3, "row": 1, "main": "BT 2", "sub": "Wing 2", "bg": COLOR_BLE},
    {"col": 4, "row": 1, "main": "BT 3", "sub": "Wing 3", "bg": COLOR_BLE},
    {"col": 5, "row": 1, "main": "▽", "bg": COLOR_TRANS, "fg": TEXT_DIM},
    {"col": 6, "row": 1, "main": "▽", "bg": COLOR_TRANS, "fg": TEXT_DIM},
    {"col": 7, "row": 1, "main": "▽", "bg": COLOR_TRANS, "fg": TEXT_DIM},
    {"col": 8, "row": 1, "main": "▽", "bg": COLOR_TRANS, "fg": TEXT_DIM},
    {"col": 9, "row": 1, "main": "▽", "bg": COLOR_TRANS, "fg": TEXT_DIM},
    {"col": 10, "row": 1, "main": "▽", "bg": COLOR_TRANS, "fg": TEXT_DIM},
    {"col": 11, "row": 1, "main": "▽", "bg": COLOR_TRANS, "fg": TEXT_DIM},
    # Row 2 (Battery Typer on P)
    {"col": 0, "row": 2, "main": "▽", "bg": COLOR_TRANS, "fg": TEXT_DIM},
    {"col": 1, "row": 2, "main": "▽", "bg": COLOR_TRANS, "fg": TEXT_DIM},
    {"col": 2, "row": 2, "main": "▽", "bg": COLOR_TRANS, "fg": TEXT_DIM},
    {"col": 3, "row": 2, "main": "▽", "bg": COLOR_TRANS, "fg": TEXT_DIM},
    {"col": 4, "row": 2, "main": "▽", "bg": COLOR_TRANS, "fg": TEXT_DIM},
    {"col": 5, "row": 2, "main": "▽", "bg": COLOR_TRANS, "fg": TEXT_DIM},
    {"col": 6, "row": 2, "main": "▽", "bg": COLOR_TRANS, "fg": TEXT_DIM},
    {"col": 7, "row": 2, "main": "▽", "bg": COLOR_TRANS, "fg": TEXT_DIM},
    {"col": 8, "row": 2, "main": "▽", "bg": COLOR_TRANS, "fg": TEXT_DIM},
    {"col": 9, "row": 2, "main": "▽", "bg": COLOR_TRANS, "fg": TEXT_DIM},
    {"col": 10, "row": 2, "main": "Type %", "sub": "Auto \"XX%\"", "bg": COLOR_FEATURE, "tag": "Fn+P"},
    {"col": 11, "row": 2, "main": "▽", "bg": COLOR_TRANS, "fg": TEXT_DIM},
    # Row 3
    {"col": 0, "row": 3, "main": "▽", "bg": COLOR_TRANS, "fg": TEXT_DIM},
    {"col": 1, "row": 3, "main": "▽", "bg": COLOR_TRANS, "fg": TEXT_DIM},
    {"col": 2, "row": 3, "main": "▽", "bg": COLOR_TRANS, "fg": TEXT_DIM},
    {"col": 3, "row": 3, "main": "▽", "bg": COLOR_TRANS, "fg": TEXT_DIM},
    {"col": 4, "row": 3, "main": "▽", "bg": COLOR_TRANS, "fg": TEXT_DIM},
    {"col": 5, "row": 3, "main": "▽", "bg": COLOR_TRANS, "fg": TEXT_DIM},
    {"col": 6, "row": 3, "main": "▽", "bg": COLOR_TRANS, "fg": TEXT_DIM},
    {"col": 7, "row": 3, "main": "▽", "bg": COLOR_TRANS, "fg": TEXT_DIM},
    {"col": 8, "row": 3, "main": "▽", "bg": COLOR_TRANS, "fg": TEXT_DIM},
    {"col": 9, "row": 3, "main": "▽", "bg": COLOR_TRANS, "fg": TEXT_DIM},
    {"col": 10, "row": 3, "main": "▽", "bg": COLOR_TRANS, "fg": TEXT_DIM},
    {"col": 11, "row": 3, "main": "▽", "bg": COLOR_TRANS, "fg": TEXT_DIM},
    # Row 4 (Studio Unlock on Z, Clicky on C, Gauge on B)
    {"col": 0, "row": 4, "main": "▽", "bg": COLOR_TRANS, "fg": TEXT_DIM},
    {"col": 1, "row": 4, "main": "Unlock", "sub": "ZMK Studio", "bg": COLOR_BLE, "tag": "Fn+Z"},
    {"col": 2, "row": 4, "main": "▽", "bg": COLOR_TRANS, "fg": TEXT_DIM},
    {"col": 3, "row": 4, "main": "Clicky", "sub": "Audio On/Off", "bg": COLOR_FEATURE, "tag": "Fn+C"},
    {"col": 4, "row": 4, "main": "▽", "bg": COLOR_TRANS, "fg": TEXT_DIM},
    {"col": 5, "row": 4, "main": "Gauge", "sub": "Batt LED (Hold)", "bg": COLOR_FEATURE, "tag": "Fn+B"},
    {"col": 6, "row": 4, "main": "▽", "bg": COLOR_TRANS, "fg": TEXT_DIM},
    {"col": 7, "row": 4, "main": "▽", "bg": COLOR_TRANS, "fg": TEXT_DIM},
    {"col": 8, "row": 4, "main": "▽", "bg": COLOR_TRANS, "fg": TEXT_DIM},
    {"col": 9, "row": 4, "main": "▽", "bg": COLOR_TRANS, "fg": TEXT_DIM},
    {"col": 10, "row": 4, "main": "▽", "bg": COLOR_TRANS, "fg": TEXT_DIM},
    {"col": 11, "row": 4, "main": "▽", "bg": COLOR_TRANS, "fg": TEXT_DIM},
    # Row 5 (Bootloader, BT Clear)
    {"col": 0, "row": 5, "main": "Bootloader", "sub": "UF2 DFU Mode", "bg": COLOR_DANGER, "tag": "Fn+Ctrl"},
    {"col": 1, "row": 5, "main": "▽", "bg": COLOR_TRANS, "fg": TEXT_DIM},
    {"col": 2, "row": 5, "main": "▽", "bg": COLOR_TRANS, "fg": TEXT_DIM},
    {"col": 3, "row": 5, "main": "▽", "bg": COLOR_TRANS, "fg": TEXT_DIM},
    {"col": 4, "row": 5, "main": "▽", "bg": COLOR_TRANS, "fg": TEXT_DIM},
    {"col": 5, "row": 5, "span": 2.0, "main": "Space (2U)", "sub": "Centered 2U Spacebar", "bg": COLOR_TRANS, "tag": "2U", "fg": TEXT_DIM},
    {"col": 7, "row": 5, "main": "▽", "bg": COLOR_TRANS, "fg": TEXT_DIM},
    {"col": 8, "row": 5, "main": "▽", "bg": COLOR_TRANS, "fg": TEXT_DIM},
    {"col": 9, "row": 5, "main": "▽", "bg": COLOR_TRANS, "fg": TEXT_DIM},
    {"col": 10, "row": 5, "main": "▽", "bg": COLOR_TRANS, "fg": TEXT_DIM},
    {"col": 11, "row": 5, "main": "BT Clear", "sub": "Clear Profile", "bg": COLOR_DANGER},
]

out_dir = "/root/samake-preonic-config/docs/images"
os.makedirs(out_dir, exist_ok=True)

render_layer("Keyboardio Preonic — Layer 0: Base Layer (기본 레이어)", "Standard 5x12 MIT Layout (Alphanumerics, Centered 2U Spacebar, Top Fn & Media Knob)", base_keys, f"{out_dir}/layer0_base.png")
render_layer("Keyboardio Preonic — Layer 1: Lower Layer (로워 레이어)", "Numeric Keypad (Tenkeyless Numpad on Right Hand) & Navigation Keys (Home, End, PgUp, PgDn)", lower_keys, f"{out_dir}/layer1_lower.png")
render_layer("Keyboardio Preonic — Layer 2: Raise Layer (레이즈 레이어)", "Programming Symbols & Full Mouse Emulation (Move, Click, Wheel Scroll)", raise_keys, f"{out_dir}/layer2_raise.png")
render_layer("Keyboardio Preonic — Layer 3: Function & Tri Layer (펑션 레이어)", "Hardware Controls: Bluetooth Profiles, Audio Clicky (Fn+C), Battery Gauge (Fn+B), Typer (Fn+P), Bootloader", func_keys, f"{out_dir}/layer3_func.png")

print("All 4 layer images successfully re-generated with NotoSansCJK Bold!")
