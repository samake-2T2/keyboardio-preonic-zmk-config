import unittest

SOF = 0xAB
EOF = 0xAD

CMD_PING = 0x01
CMD_HANDSHAKE = 0x02
CMD_GET_LOCK_STATUS = 0x03
CMD_LOCK = 0x04
CMD_GET_STATUS = 0x05
CMD_GET_KEY = 0x10
CMD_SET_KEY = 0x11
CMD_SAVE_KEYMAP = 0x12
CMD_DISCARD_KEYMAP = 0x13
CMD_GET_KNOB = 0x20
CMD_SET_KNOB = 0x21
CMD_GET_MACRO = 0x30
CMD_SET_MACRO = 0x31
CMD_PLAY_MACRO = 0x32
CMD_GET_PW_CONFIG = 0x40
CMD_SET_PW_CONFIG = 0x41
CMD_GET_MOUSE_CFG = 0x50
CMD_SET_MOUSE_CFG = 0x51
CMD_GET_AUDIO_CFG = 0x60
CMD_SET_AUDIO_CFG = 0x61
CMD_TEST_PIEZO = 0x62
EVT_UNLOCKED = 0xFE
EVT_LOCKED = 0xFD

ERR_OK = 0x00
ERR_INVALID = 0x01
ERR_LOCKED = 0xEE

# HID usage keycodes
HID_KEY_A = 0x04
HID_KEY_B = 0x05
HID_KEY_C = 0x06
HID_KEY_D = 0x07
HID_KEY_E = 0x08
HID_KEY_F = 0x09
HID_KEY_G = 0x0A
HID_KEY_H = 0x0B
HID_KEY_I = 0x0C
HID_KEY_J = 0x0D
HID_KEY_K = 0x0E
HID_KEY_L = 0x0F
HID_KEY_M = 0x10
HID_KEY_N = 0x11
HID_KEY_O = 0x12
HID_KEY_P = 0x13
HID_KEY_Q = 0x14
HID_KEY_R = 0x15
HID_KEY_S = 0x16
HID_KEY_T = 0x17
HID_KEY_U = 0x18
HID_KEY_V = 0x19
HID_KEY_W = 0x1A
HID_KEY_X = 0x1B
HID_KEY_Y = 0x1C
HID_KEY_Z = 0x1D

HID_KEY_1 = 0x1E
HID_KEY_2 = 0x1F
HID_KEY_3 = 0x20
HID_KEY_4 = 0x21
HID_KEY_5 = 0x22
HID_KEY_6 = 0x23
HID_KEY_7 = 0x24
HID_KEY_8 = 0x25
HID_KEY_9 = 0x26
HID_KEY_0 = 0x27

HID_KEY_ENTER = 0x28
HID_KEY_TAB = 0x2B
HID_KEY_SPACE = 0x2C
HID_KEY_MINUS = 0x2D
HID_KEY_EQUAL = 0x2E
HID_KEY_LEFTBRACE = 0x2F
HID_KEY_RIGHTBRACE = 0x30
HID_KEY_BACKSLASH = 0x31
HID_KEY_SEMICOLON = 0x33
HID_KEY_APOSTROPHE = 0x34
HID_KEY_GRAVE = 0x35
HID_KEY_COMMA = 0x36
HID_KEY_DOT = 0x37
HID_KEY_SLASH = 0x38
HID_KEY_LEFTSHIFT = 0xE1

SHIFTED_SYMBOLS = {
    '!': HID_KEY_1,
    '@': HID_KEY_2,
    '#': HID_KEY_3,
    '$': HID_KEY_4,
    '%': HID_KEY_5,
    '^': HID_KEY_6,
    '&': HID_KEY_7,
    '*': HID_KEY_8,
    '(': HID_KEY_9,
    ')': HID_KEY_0,
    '_': HID_KEY_MINUS,
    '+': HID_KEY_EQUAL,
    '{': HID_KEY_LEFTBRACE,
    '}': HID_KEY_RIGHTBRACE,
    '|': HID_KEY_BACKSLASH,
    ':': HID_KEY_SEMICOLON,
    '"': HID_KEY_APOSTROPHE,
    '<': HID_KEY_COMMA,
    '>': HID_KEY_DOT,
    '?': HID_KEY_SLASH,
    '~': HID_KEY_GRAVE,
}

UNSHIFTED_SYMBOLS = {
    ' ': HID_KEY_SPACE,
    '\n': HID_KEY_ENTER,
    '\r': HID_KEY_ENTER,
    '\t': HID_KEY_TAB,
    '-': HID_KEY_MINUS,
    '=': HID_KEY_EQUAL,
    '[': HID_KEY_LEFTBRACE,
    ']': HID_KEY_RIGHTBRACE,
    '\\': HID_KEY_BACKSLASH,
    ';': HID_KEY_SEMICOLON,
    "'": HID_KEY_APOSTROPHE,
    ',': HID_KEY_COMMA,
    '.': HID_KEY_DOT,
    '/': HID_KEY_SLASH,
    '`': HID_KEY_GRAVE,
}

DYN_MACRO_MAX_STEPS = 128

def ascii_to_macro_steps(text, max_steps=DYN_MACRO_MAX_STEPS):
    """
    Converts an ASCII text string to a list of (keycode, pressed) steps.
    Returns (steps, err_code).
    0 = success, -22 = EINVAL, -28 = ENOSPC.
    """
    if text is None:
        return [], -22

    # Pre-calculate steps
    total_steps = 0
    i = 0
    while i < len(text):
        if text[i] == '\r' and i + 1 < len(text) and text[i + 1] == '\n':
            i += 1
            continue
        ch = text[i]
        if 'A' <= ch <= 'Z' or ch in SHIFTED_SYMBOLS:
            total_steps += 4
        elif 'a' <= ch <= 'z' or '0' <= ch <= '9' or ch in UNSHIFTED_SYMBOLS:
            total_steps += 2
        i += 1

    if total_steps > max_steps:
        return [], -28

    steps = []
    i = 0
    while i < len(text):
        if text[i] == '\r' and i + 1 < len(text) and text[i + 1] == '\n':
            i += 1
            continue
        ch = text[i]
        if 'A' <= ch <= 'Z':
            kc = HID_KEY_A + (ord(ch) - ord('A'))
            steps.append((HID_KEY_LEFTSHIFT, 1))
            steps.append((kc, 1))
            steps.append((kc, 0))
            steps.append((HID_KEY_LEFTSHIFT, 0))
        elif ch in SHIFTED_SYMBOLS:
            kc = SHIFTED_SYMBOLS[ch]
            steps.append((HID_KEY_LEFTSHIFT, 1))
            steps.append((kc, 1))
            steps.append((kc, 0))
            steps.append((HID_KEY_LEFTSHIFT, 0))
        elif 'a' <= ch <= 'z':
            kc = HID_KEY_A + (ord(ch) - ord('a'))
            steps.append((kc, 1))
            steps.append((kc, 0))
        elif '0' <= ch <= '9':
            kc = HID_KEY_0 if ch == '0' else HID_KEY_1 + (ord(ch) - ord('1'))
            steps.append((kc, 1))
            steps.append((kc, 0))
        elif ch in UNSHIFTED_SYMBOLS:
            kc = UNSHIFTED_SYMBOLS[ch]
            steps.append((kc, 1))
            steps.append((kc, 0))
        i += 1

    return steps, 0

def calc_checksum(cmd, seq, length, data):
    total = cmd + seq + length + sum(data)
    return total & 0xFF

def encode_packet(cmd, seq, data=b""):
    length = len(data)
    chk = calc_checksum(cmd, seq, length, data)
    return bytes([SOF, cmd, seq, length]) + data + bytes([chk, EOF])

def decode_packet(buf):
    if len(buf) < 6:
        return None
    if buf[0] != SOF or buf[-1] != EOF:
        return None
    cmd = buf[1]
    seq = buf[2]
    length = buf[3]
    if len(buf) != 6 + length:
        return None
    data = buf[4:4+length]
    chk = buf[4+length]
    if chk != calc_checksum(cmd, seq, length, data):
        return None
    return {"cmd": cmd, "seq": seq, "data": data}

class TestPreonicStudioProtocol(unittest.TestCase):
    def test_packet_encode_decode(self):
        pkt = encode_packet(CMD_PING, 1, b"")
        self.assertEqual(len(pkt), 6)
        decoded = decode_packet(pkt)
        self.assertIsNotNone(decoded)
        self.assertEqual(decoded["cmd"], CMD_PING)
        self.assertEqual(decoded["seq"], 1)
        self.assertEqual(decoded["data"], b"")

    def test_packet_with_data(self):
        data = bytes([0x01, 0x02, 0x03, 0x04])
        pkt = encode_packet(CMD_SET_KEY, 42, data)
        self.assertEqual(len(pkt), 6 + 4)
        decoded = decode_packet(pkt)
        self.assertIsNotNone(decoded)
        self.assertEqual(decoded["cmd"], CMD_SET_KEY)
        self.assertEqual(decoded["seq"], 42)
        self.assertEqual(decoded["data"], data)

    def test_corrupted_checksum(self):
        pkt = bytearray(encode_packet(CMD_PING, 1, b""))
        pkt[-2] ^= 0xFF # corrupt checksum
        self.assertIsNone(decode_packet(pkt))

    def test_ascii_uppercase(self):
        steps, err = ascii_to_macro_steps("A")
        self.assertEqual(err, 0)
        expected = [
            (HID_KEY_LEFTSHIFT, 1),
            (HID_KEY_A, 1),
            (HID_KEY_A, 0),
            (HID_KEY_LEFTSHIFT, 0)
        ]
        self.assertEqual(steps, expected)

    def test_ascii_lowercase(self):
        steps, err = ascii_to_macro_steps("z")
        self.assertEqual(err, 0)
        expected = [
            (HID_KEY_Z, 1),
            (HID_KEY_Z, 0)
        ]
        self.assertEqual(steps, expected)

    def test_ascii_number(self):
        steps, err = ascii_to_macro_steps("1")
        self.assertEqual(err, 0)
        expected = [
            (HID_KEY_1, 1),
            (HID_KEY_1, 0)
        ]
        self.assertEqual(steps, expected)

    def test_ascii_shifted_symbols(self):
        steps, err = ascii_to_macro_steps("!")
        self.assertEqual(err, 0)
        expected = [
            (HID_KEY_LEFTSHIFT, 1),
            (HID_KEY_1, 1),
            (HID_KEY_1, 0),
            (HID_KEY_LEFTSHIFT, 0)
        ]
        self.assertEqual(steps, expected)

        steps_at, err = ascii_to_macro_steps("@")
        self.assertEqual(err, 0)
        expected_at = [
            (HID_KEY_LEFTSHIFT, 1),
            (HID_KEY_2, 1),
            (HID_KEY_2, 0),
            (HID_KEY_LEFTSHIFT, 0)
        ]
        self.assertEqual(steps_at, expected_at)

    def test_ascii_unshifted_symbols(self):
        steps, err = ascii_to_macro_steps(" -=[ \t\n")
        self.assertEqual(err, 0)
        self.assertEqual(len(steps), 14) # 7 unshifted chars * 2

    def test_ascii_crlf_handling(self):
        steps, err = ascii_to_macro_steps("\r\n")
        self.assertEqual(err, 0)
        expected = [
            (HID_KEY_ENTER, 1),
            (HID_KEY_ENTER, 0)
        ]
        self.assertEqual(steps, expected)

    def test_ascii_mixed_string(self):
        steps, err = ascii_to_macro_steps("Hello, 2026!")
        self.assertEqual(err, 0)
        # 'H': 4, 'e': 2, 'l': 2, 'l': 2, 'o': 2, ',': 2, ' ': 2, '2': 2, '0': 2, '2': 2, '6': 2, '!': 4
        # Total = 4 + 2*10 + 4 = 28 steps
        self.assertEqual(len(steps), 28)

    def test_ascii_overflow_guard(self):
        # 33 uppercase letters require 33 * 4 = 132 steps > 128
        long_text = "A" * 33
        steps, err = ascii_to_macro_steps(long_text)
        self.assertEqual(err, -28)
        self.assertEqual(len(steps), 0)

        # 32 uppercase letters = 128 steps, fits exactly
        exact_text = "A" * 32
        steps, err = ascii_to_macro_steps(exact_text)
        self.assertEqual(err, 0)
        self.assertEqual(len(steps), 128)

    def test_password_config_protocol_payload(self):
        default_len = 16
        interval_ms = 12
        specials = b"!@#$%*?_-.@"
        payload = bytes([default_len, interval_ms, len(specials)]) + specials.ljust(32, b"\x00")
        pkt = encode_packet(CMD_SET_PW_CONFIG, 10, payload)
        decoded = decode_packet(pkt)
        self.assertIsNotNone(decoded)
        self.assertEqual(decoded["cmd"], CMD_SET_PW_CONFIG)
        self.assertEqual(decoded["seq"], 10)
        self.assertEqual(decoded["data"][0], 16)
        self.assertEqual(decoded["data"][1], 12)
        self.assertEqual(decoded["data"][2], 11)
        self.assertEqual(decoded["data"][3:14], b"!@#$%*?_-.@")

if __name__ == "__main__":
    unittest.main()

