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
EVT_LAYER_CHANGED = 0xFC
EVT_KEY_TEST = 0xFB

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

class PreonicStudioDispatcher:
    def __init__(self):
        self.locked = True
        self.keymap = {}
        self.knobs = {i: {"cw_beh": 1, "cw_param": 0xE9, "ccw_beh": 1, "ccw_param": 0xEA, "ppd": 2} for i in range(8)}
        self.macros = {1: "", 2: "", 3: ""}
        self.pw_config = {"len": 16, "interval": 12, "specials": "!@#$%*?_-.@"}
        self.mouse_cfg = {"mmv_time": 500, "mmv_exp": 1, "msc_time": 300, "msc_exp": 1, "msc_step": 10}
        self.audio_cfg = {"master": 0, "clicky": 1, "freq": 3000, "dur": 5}
        self.auto_lock_remaining = 300
        self.outbox = []

        self.state = "WAIT_SOF"
        self.cmd = 0
        self.seq = 0
        self.length = 0
        self.data = bytearray()
        self.chksum = 0

    def is_locked(self):
        return self.locked

    def unlock(self):
        self.locked = False
        self.auto_lock_remaining = 300

    def lock(self):
        self.locked = True
        self.auto_lock_remaining = 0

    def physical_unlock(self):
        self.unlock()
        self.send_packet(EVT_UNLOCKED, 0, bytes([0x01]))

    def auto_lock_timeout(self):
        if not self.locked:
            self.lock()
            self.send_packet(EVT_LOCKED, 0, bytes([0x01]))

    def disconnect(self):
        if not self.locked:
            self.lock()
            self.send_packet(EVT_LOCKED, 0, bytes([0x02]))

    def send_packet(self, cmd, seq, data=b""):
        pkt = encode_packet(cmd, seq, data)
        self.outbox.append(pkt)

    def process_byte(self, byte):
        if self.state == "WAIT_SOF":
            if byte == SOF:
                self.state = "CMD"
        elif self.state == "CMD":
            self.cmd = byte
            self.state = "SEQ"
        elif self.state == "SEQ":
            self.seq = byte
            self.state = "LEN"
        elif self.state == "LEN":
            self.length = byte
            self.data = bytearray()
            if self.length > 64:
                self.state = "WAIT_SOF"
            elif self.length == 0:
                self.state = "CHKSUM"
            else:
                self.state = "DATA"
        elif self.state == "DATA":
            self.data.append(byte)
            if len(self.data) >= self.length:
                self.state = "CHKSUM"
        elif self.state == "CHKSUM":
            self.chksum = byte
            self.state = "EOF"
        elif self.state == "EOF":
            if byte == EOF:
                calc_chk = calc_checksum(self.cmd, self.seq, self.length, self.data)
                if calc_chk == self.chksum:
                    self.dispatch_command(self.cmd, self.seq, bytes(self.data))
            self.state = "WAIT_SOF"

    def process_bytes(self, stream):
        for b in stream:
            self.process_byte(b)

    def dispatch_command(self, cmd, seq, data):
        if not self.locked:
            self.auto_lock_remaining = 300

        mutating_or_private = (
            cmd in [CMD_SET_KEY, CMD_SAVE_KEYMAP, CMD_DISCARD_KEYMAP,
                    CMD_SET_KNOB, CMD_GET_MACRO, CMD_SET_MACRO, CMD_PLAY_MACRO,
                    CMD_SET_PW_CONFIG, CMD_SET_MOUSE_CFG, CMD_SET_AUDIO_CFG, CMD_TEST_PIEZO]
        )
        if self.locked and mutating_or_private:
            self.send_packet(cmd, seq, bytes([ERR_LOCKED]))
            return

        if cmd == CMD_PING:
            self.send_packet(CMD_PING, seq, bytes([ERR_OK]))
        elif cmd == CMD_HANDSHAKE:
            name_bytes = b"Preonic".ljust(16, b"\x00")
            resp = bytes([2, 0, 0, 1 if self.locked else 0, 8, 5, 12]) + name_bytes
            self.send_packet(CMD_HANDSHAKE, seq, resp)
        elif cmd == CMD_GET_LOCK_STATUS:
            rem = self.auto_lock_remaining if not self.locked else 0
            resp = bytes([1 if self.locked else 0, rem & 0xFF, (rem >> 8) & 0xFF])
            self.send_packet(CMD_GET_LOCK_STATUS, seq, resp)
        elif cmd == CMD_LOCK:
            self.lock()
            self.send_packet(CMD_LOCK, seq, bytes([ERR_OK]))
        elif cmd == CMD_GET_STATUS:
            mv = 3300 + 82 * 9
            resp = bytes([mv & 0xFF, (mv >> 8) & 0xFF, 82, 0, 1, self.audio_cfg["master"], self.audio_cfg["clicky"]])
            self.send_packet(CMD_GET_STATUS, seq, resp)
        elif cmd == CMD_GET_KEY:
            if len(data) < 2:
                self.send_packet(cmd, seq, bytes([ERR_INVALID]))
                return
            layer, key_idx = data[0], data[1]
            entry = self.keymap.get((layer, key_idx), (0x01, 0, 0))
            beh_type, p1, p2 = entry
            resp = bytes([layer, key_idx, beh_type,
                          p1 & 0xFF, (p1 >> 8) & 0xFF, (p1 >> 16) & 0xFF, (p1 >> 24) & 0xFF,
                          p2 & 0xFF, (p2 >> 8) & 0xFF, (p2 >> 16) & 0xFF, (p2 >> 24) & 0xFF])
            self.send_packet(CMD_GET_KEY, seq, resp)
        elif cmd == CMD_SET_KEY:
            if len(data) < 11:
                self.send_packet(cmd, seq, bytes([ERR_INVALID]))
                return
            layer, key_idx, beh = data[0], data[1], data[2]
            p1 = int.from_bytes(data[3:7], "little")
            p2 = int.from_bytes(data[7:11], "little")
            self.keymap[(layer, key_idx)] = (beh, p1, p2)
            self.send_packet(CMD_SET_KEY, seq, bytes([ERR_OK]))
        elif cmd == CMD_SAVE_KEYMAP or cmd == CMD_DISCARD_KEYMAP:
            self.send_packet(cmd, seq, bytes([ERR_OK]))
        elif cmd == CMD_GET_KNOB:
            if len(data) < 1:
                self.send_packet(cmd, seq, bytes([ERR_INVALID]))
                return
            layer = data[0]
            k = self.knobs.get(layer, {"cw_beh": 1, "cw_param": 0xE9, "ccw_beh": 1, "ccw_param": 0xEA, "ppd": 2})
            resp = bytes([layer, k["cw_beh"]]) + k["cw_param"].to_bytes(4, "little") + bytes([k["ccw_beh"]]) + k["ccw_param"].to_bytes(4, "little") + bytes([k["ppd"]])
            self.send_packet(CMD_GET_KNOB, seq, resp)
        elif cmd == CMD_SET_KNOB:
            if len(data) < 12:
                self.send_packet(cmd, seq, bytes([ERR_INVALID]))
                return
            layer = data[0]
            cw_beh = data[1]
            cw_param = int.from_bytes(data[2:6], "little")
            ccw_beh = data[6]
            ccw_param = int.from_bytes(data[7:11], "little")
            ppd = data[11]
            self.knobs[layer] = {"cw_beh": cw_beh, "cw_param": cw_param, "ccw_beh": ccw_beh, "ccw_param": ccw_param, "ppd": ppd}
            self.send_packet(CMD_SET_KNOB, seq, bytes([ERR_OK]))
        elif cmd == CMD_GET_MACRO:
            if len(data) < 1:
                self.send_packet(cmd, seq, bytes([ERR_INVALID]))
                return
            slot = data[0]
            text = self.macros.get(slot, "")
            text_bytes = text.encode("ascii")
            resp = bytes([slot, len(text_bytes) * 2, 0, len(text_bytes)]) + text_bytes
            self.send_packet(CMD_GET_MACRO, seq, resp)
        elif cmd == CMD_SET_MACRO:
            if len(data) < 2:
                self.send_packet(cmd, seq, bytes([ERR_INVALID]))
                return
            slot = data[0]
            text_len = data[1]
            text = data[2:2+text_len].decode("ascii", errors="ignore")
            self.macros[slot] = text
            self.send_packet(CMD_SET_MACRO, seq, bytes([ERR_OK]))
        elif cmd == CMD_PLAY_MACRO:
            self.send_packet(CMD_PLAY_MACRO, seq, bytes([ERR_OK]))
        elif cmd == CMD_GET_PW_CONFIG:
            specials = self.pw_config["specials"].encode("ascii")
            resp = bytes([self.pw_config["len"], self.pw_config["interval"], len(specials)]) + specials.ljust(32, b"\x00")
            self.send_packet(CMD_GET_PW_CONFIG, seq, resp)
        elif cmd == CMD_SET_PW_CONFIG:
            if len(data) < 3:
                self.send_packet(cmd, seq, bytes([ERR_INVALID]))
                return
            self.pw_config["len"] = data[0]
            self.pw_config["interval"] = data[1]
            spec_len = data[2]
            self.pw_config["specials"] = data[3:3+spec_len].decode("ascii", errors="ignore")
            self.send_packet(CMD_SET_PW_CONFIG, seq, bytes([ERR_OK]))
        elif cmd == CMD_GET_MOUSE_CFG:
            resp = (self.mouse_cfg["mmv_time"].to_bytes(2, "little") +
                    bytes([self.mouse_cfg["mmv_exp"]]) +
                    self.mouse_cfg["msc_time"].to_bytes(2, "little") +
                    bytes([self.mouse_cfg["msc_exp"], self.mouse_cfg["msc_step"]]))
            self.send_packet(CMD_GET_MOUSE_CFG, seq, resp)
        elif cmd == CMD_SET_MOUSE_CFG:
            if len(data) < 7:
                self.send_packet(cmd, seq, bytes([ERR_INVALID]))
                return
            self.mouse_cfg["mmv_time"] = int.from_bytes(data[0:2], "little")
            self.mouse_cfg["mmv_exp"] = data[2]
            self.mouse_cfg["msc_time"] = int.from_bytes(data[3:5], "little")
            self.mouse_cfg["msc_exp"] = data[5]
            self.mouse_cfg["msc_step"] = data[6]
            self.send_packet(CMD_SET_MOUSE_CFG, seq, bytes([ERR_OK]))
        elif cmd == CMD_GET_AUDIO_CFG:
            resp = bytes([self.audio_cfg["master"], self.audio_cfg["clicky"]]) + self.audio_cfg["freq"].to_bytes(2, "little") + bytes([self.audio_cfg["dur"]])
            self.send_packet(CMD_GET_AUDIO_CFG, seq, resp)
        elif cmd == CMD_SET_AUDIO_CFG:
            if len(data) < 5:
                self.send_packet(cmd, seq, bytes([ERR_INVALID]))
                return
            self.audio_cfg["master"] = data[0]
            self.audio_cfg["clicky"] = data[1]
            self.audio_cfg["freq"] = int.from_bytes(data[2:4], "little")
            self.audio_cfg["dur"] = data[4]
            self.send_packet(CMD_SET_AUDIO_CFG, seq, bytes([ERR_OK]))
        elif cmd == CMD_TEST_PIEZO:
            self.send_packet(CMD_TEST_PIEZO, seq, bytes([ERR_OK]))
        else:
            self.send_packet(cmd, seq, bytes([ERR_INVALID]))

class TestPreonicStudioDispatcher(unittest.TestCase):
    def setUp(self):
        self.disp = PreonicStudioDispatcher()

    def test_handshake(self):
        pkt = encode_packet(CMD_HANDSHAKE, 1, bytes([1, 0]))
        self.disp.process_bytes(pkt)
        self.assertEqual(len(self.disp.outbox), 1)
        resp = decode_packet(self.disp.outbox[-1])
        self.assertIsNotNone(resp)
        self.assertEqual(resp["cmd"], CMD_HANDSHAKE)
        self.assertEqual(resp["seq"], 1)
        data = resp["data"]
        self.assertEqual(data[0], 2) # major v2
        self.assertEqual(data[1], 0) # minor v0
        self.assertEqual(data[2], 0) # patch v0
        self.assertEqual(data[3], 1) # locked by default
        self.assertEqual(data[4], 8) # 8 layers
        self.assertEqual(data[5], 5) # rows
        self.assertEqual(data[6], 12) # cols
        self.assertTrue(data[7:].startswith(b"Preonic"))

    def test_layer_changed_and_key_test_events(self):
        layer_pkt = encode_packet(EVT_LAYER_CHANGED, 0, bytes([5])) # switched to layer 5
        decoded_layer = decode_packet(layer_pkt)
        self.assertEqual(decoded_layer["cmd"], EVT_LAYER_CHANGED)
        self.assertEqual(decoded_layer["data"][0], 5)

        key_pkt = encode_packet(EVT_KEY_TEST, 0, bytes([40, 1])) # key 40 pressed
        decoded_key = decode_packet(key_pkt)
        self.assertEqual(decoded_key["cmd"], EVT_KEY_TEST)
        self.assertEqual(decoded_key["data"][0], 40)
        self.assertEqual(decoded_key["data"][1], 1)

    def test_lock_status(self):
        pkt = encode_packet(CMD_GET_LOCK_STATUS, 2)
        self.disp.process_bytes(pkt)
        resp = decode_packet(self.disp.outbox[-1])
        self.assertEqual(resp["cmd"], CMD_GET_LOCK_STATUS)
        self.assertEqual(resp["data"][0], 1) # locked

    def test_lock_rejection_for_mutating_and_private_commands(self):
        mutating_commands = [
            (CMD_SET_KEY, bytes([0, 0, 1, 4, 0, 0, 0, 0, 0, 0, 0])),
            (CMD_SAVE_KEYMAP, b""),
            (CMD_DISCARD_KEYMAP, b""),
            (CMD_SET_KNOB, bytes([0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 2])),
            (CMD_GET_MACRO, bytes([1])),
            (CMD_SET_MACRO, bytes([1, 5]) + b"hello"),
            (CMD_PLAY_MACRO, bytes([1])),
            (CMD_SET_PW_CONFIG, bytes([16, 12, 0]) + b"\x00" * 32),
            (CMD_SET_MOUSE_CFG, bytes([0, 0, 1, 0, 0, 1, 10])),
            (CMD_SET_AUDIO_CFG, bytes([1, 1, 0, 0, 5])),
            (CMD_TEST_PIEZO, bytes([0, 0, 0, 0])),
        ]
        seq = 10
        for cmd, payload in mutating_commands:
            pkt = encode_packet(cmd, seq, payload)
            self.disp.process_bytes(pkt)
            resp = decode_packet(self.disp.outbox[-1])
            self.assertEqual(resp["cmd"], cmd)
            self.assertEqual(resp["data"], bytes([ERR_LOCKED]), f"Command 0x{cmd:02X} should be rejected when locked")
            seq += 1

    def test_physical_unlock_and_unlocked_operations(self):
        self.assertTrue(self.disp.is_locked())
        self.disp.physical_unlock()
        self.assertFalse(self.disp.is_locked())

        # Check outbox has EVT_UNLOCKED
        evt = decode_packet(self.disp.outbox[-1])
        self.assertEqual(evt["cmd"], EVT_UNLOCKED)
        self.assertEqual(evt["data"], bytes([0x01]))

        # Now SET_KEY should succeed
        payload_key = bytes([0, 10, 1, 4, 0, 0, 0, 0, 0, 0, 0])
        self.disp.process_bytes(encode_packet(CMD_SET_KEY, 20, payload_key))
        resp = decode_packet(self.disp.outbox[-1])
        self.assertEqual(resp["cmd"], CMD_SET_KEY)
        self.assertEqual(resp["data"], bytes([ERR_OK]))

        # GET_KEY should return the set key
        self.disp.process_bytes(encode_packet(CMD_GET_KEY, 21, bytes([0, 10])))
        resp = decode_packet(self.disp.outbox[-1])
        self.assertEqual(resp["cmd"], CMD_GET_KEY)
        self.assertEqual(resp["data"][0], 0) # layer
        self.assertEqual(resp["data"][1], 10) # idx
        self.assertEqual(resp["data"][2], 1) # beh_type &kp
        self.assertEqual(resp["data"][3], 4) # param1 HID_KEY_A

        # SET_MACRO should succeed
        macro_text = b"Secret123"
        payload_macro = bytes([1, len(macro_text)]) + macro_text
        self.disp.process_bytes(encode_packet(CMD_SET_MACRO, 22, payload_macro))
        resp = decode_packet(self.disp.outbox[-1])
        self.assertEqual(resp["cmd"], CMD_SET_MACRO)
        self.assertEqual(resp["data"], bytes([ERR_OK]))

        # GET_MACRO should return the text
        self.disp.process_bytes(encode_packet(CMD_GET_MACRO, 23, bytes([1])))
        resp = decode_packet(self.disp.outbox[-1])
        self.assertEqual(resp["cmd"], CMD_GET_MACRO)
        self.assertEqual(resp["data"][0], 1) # slot 1
        self.assertEqual(resp["data"][3], len(macro_text))
        self.assertEqual(resp["data"][4:4+len(macro_text)], macro_text)

    def test_manual_lock(self):
        self.disp.unlock()
        self.assertFalse(self.disp.is_locked())

        self.disp.process_bytes(encode_packet(CMD_LOCK, 30))
        resp = decode_packet(self.disp.outbox[-1])
        self.assertEqual(resp["cmd"], CMD_LOCK)
        self.assertEqual(resp["data"], bytes([ERR_OK]))
        self.assertTrue(self.disp.is_locked())

    def test_inactivity_auto_lock(self):
        self.disp.unlock()
        self.assertFalse(self.disp.is_locked())

        self.disp.auto_lock_timeout()
        self.assertTrue(self.disp.is_locked())
        evt = decode_packet(self.disp.outbox[-1])
        self.assertEqual(evt["cmd"], EVT_LOCKED)
        self.assertEqual(evt["data"], bytes([0x01])) # 1 = timeout

    def test_disconnect_auto_lock(self):
        self.disp.unlock()
        self.assertFalse(self.disp.is_locked())

        self.disp.disconnect()
        self.assertTrue(self.disp.is_locked())
        evt = decode_packet(self.disp.outbox[-1])
        self.assertEqual(evt["cmd"], EVT_LOCKED)
        self.assertEqual(evt["data"], bytes([0x02])) # 2 = disconnect

    def test_stream_fragmented_byte_simulation(self):
        self.disp.unlock()
        pkt = encode_packet(CMD_PING, 99)
        # Feed one byte at a time
        for b in pkt:
            self.disp.process_byte(b)
        resp = decode_packet(self.disp.outbox[-1])
        self.assertEqual(resp["cmd"], CMD_PING)
        self.assertEqual(resp["seq"], 99)
        self.assertEqual(resp["data"], bytes([ERR_OK]))

if __name__ == "__main__":
    unittest.main()

