"""
Glove serial packet protocol.

Every packet is exactly 13 bytes:

  Byte  0    : 0xAA  (magic)
  Byte  1    : 0xBB  (magic)
  Bytes 2-11 : 5 x uint16 big-endian ADC values (thumb → pinky)
  Byte  12   : XOR checksum of bytes 2-11

At 50 Hz and 115200 baud the bus is ~7% utilised, leaving plenty of
headroom for future additions (IMU, battery voltage, etc.).
"""

MAGIC = b"\xaa\xbb"
PACKET_SIZE = 13  # bytes
NUM_CHANNELS = 5


def encode(channels: list) -> bytes:
    buf = bytearray(PACKET_SIZE)
    buf[0], buf[1] = 0xAA, 0xBB
    checksum = 0
    for i, val in enumerate(channels[:NUM_CHANNELS]):
        val = max(0, min(4095, int(val)))
        buf[2 + i * 2] = (val >> 8) & 0xFF
        buf[3 + i * 2] = val & 0xFF
        checksum ^= buf[2 + i * 2]
        checksum ^= buf[3 + i * 2]
    buf[12] = checksum
    return bytes(buf)


def decode(buf: bytes):
    if len(buf) != PACKET_SIZE:
        return None
    if buf[0] != 0xAA or buf[1] != 0xBB:
        return None
    checksum = 0
    for b in buf[2:12]:
        checksum ^= b
    if checksum != buf[12]:
        return None
    channels = [
        (buf[2 + i * 2] << 8) | buf[3 + i * 2]
        for i in range(NUM_CHANNELS)
    ]
    return channels
