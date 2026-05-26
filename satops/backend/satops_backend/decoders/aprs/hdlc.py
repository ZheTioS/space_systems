"""HDLC bit-level framing: NRZI, bit stuffing, flag detection, CRC-16-CCITT.

AX.25 uses HDLC on the wire — frames are bracketed by 0x7E flag bytes, a 0 is
stuffed after every five consecutive 1s in the payload (to keep the flag
pattern unambiguous), data is NRZI-line-encoded, and the trailing FCS is the
CRC-16-CCITT computed over the unstuffed payload bytes.
"""

from collections.abc import Iterable

FLAG_BYTE = 0x7E
_FLAG_BITS = (0, 1, 1, 1, 1, 1, 1, 0)  # 0x7E serialized LSB-first


def crc16_ccitt(data: bytes) -> int:
    """CRC-16-CCITT (X.25 / AX.25 FCS): poly 0x1021, init 0xFFFF, reflected, final XOR 0xFFFF."""
    crc = 0xFFFF
    for byte in data:
        for i in range(8):
            bit = (byte >> i) & 1
            lsb = crc & 1
            crc >>= 1
            if bit ^ lsb:
                crc ^= 0x8408
    return crc ^ 0xFFFF


def bytes_to_bits_lsb(data: bytes) -> list[int]:
    """LSB-first serialization (AX.25 wire order)."""
    return [(byte >> i) & 1 for byte in data for i in range(8)]


def bits_to_bytes_lsb(bits: Iterable[int]) -> bytes:
    bits = list(bits)
    out = bytearray()
    for i in range(0, (len(bits) // 8) * 8, 8):
        byte = 0
        for k in range(8):
            byte |= (bits[i + k] & 1) << k
        out.append(byte)
    return bytes(out)


def bit_stuff(bits: Iterable[int]) -> list[int]:
    """Insert a 0 after every run of five 1s."""
    out: list[int] = []
    ones = 0
    for b in bits:
        out.append(b)
        if b == 1:
            ones += 1
            if ones == 5:
                out.append(0)
                ones = 0
        else:
            ones = 0
    return out


def bit_unstuff(bits: Iterable[int]) -> list[int]:
    out: list[int] = []
    ones = 0
    for b in bits:
        if ones == 5 and b == 0:
            ones = 0
            continue
        out.append(b)
        ones = ones + 1 if b == 1 else 0
    return out


def nrzi_encode(bits: Iterable[int]) -> list[int]:
    """AX.25 NRZI: a data 0 toggles the line; a data 1 holds. Initial line state 1."""
    line: list[int] = []
    state = 1
    for b in bits:
        if b == 0:
            state ^= 1
        line.append(state)
    return line


def nrzi_decode(line: Iterable[int]) -> list[int]:
    bits: list[int] = []
    prev = 1
    for s in line:
        bits.append(1 if s == prev else 0)
        prev = s
    return bits


def hdlc_encode(payload: bytes, preamble_flags: int = 16, trailing_flags: int = 4) -> list[int]:
    """Wrap a payload with CRC + bit-stuffing + HDLC flags, then NRZI-encode."""
    crc = crc16_ccitt(payload)
    framed = payload + bytes([crc & 0xFF, (crc >> 8) & 0xFF])
    data_bits = bytes_to_bits_lsb(framed)
    stuffed = bit_stuff(data_bits)
    flag = list(_FLAG_BITS)
    bits = flag * preamble_flags + stuffed + flag * trailing_flags
    return nrzi_encode(bits)


def hdlc_decode(line_bits: Iterable[int]) -> list[bytes]:
    """NRZI-decode, split on flag boundaries, unstuff, verify CRC.

    Returns the list of CRC-verified payloads (FCS stripped). Frames that fail
    CRC are dropped silently.
    """
    bits = nrzi_decode(line_bits)
    n = len(bits)
    if n < 8:
        return []

    flag_positions: list[int] = []
    i = 0
    while i <= n - 8:
        if tuple(bits[i : i + 8]) == _FLAG_BITS:
            flag_positions.append(i)
            i += 8
        else:
            i += 1

    frames: list[bytes] = []
    for j in range(len(flag_positions) - 1):
        start = flag_positions[j] + 8
        end = flag_positions[j + 1]
        if start == end:
            continue
        unstuffed = bit_unstuff(bits[start:end])
        data = bits_to_bytes_lsb(unstuffed)
        # Minimum AX.25 UI frame: 7 dest + 7 src + 1 ctrl + 0 PID + 0 info + 2 FCS = 17
        if len(data) < 17:
            continue
        payload, fcs = data[:-2], data[-2:]
        expected = fcs[0] | (fcs[1] << 8)
        if crc16_ccitt(payload) == expected:
            frames.append(payload)
    return frames
