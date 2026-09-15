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

if __name__ == "__main__":
    unittest.main()
