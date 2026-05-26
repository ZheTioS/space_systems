"""Unit + integration tests for the APRS decoder.

The end-to-end test (``test_audio_roundtrip``) builds a known frame, modulates
to AFSK samples, demodulates, decodes, and asserts byte-for-byte equality with
the original. That single test exercises every layer in the pipeline.
"""

import numpy as np
import pytest

from satops_backend.decoders.aprs.aprs import parse_info
from satops_backend.decoders.aprs.audio import demodulate, modulate
from satops_backend.decoders.aprs.ax25 import Address, Ax25Frame
from satops_backend.decoders.aprs.hdlc import (
    bit_stuff,
    bit_unstuff,
    crc16_ccitt,
    hdlc_decode,
    hdlc_encode,
    nrzi_decode,
    nrzi_encode,
)


def test_crc16_ccitt_known_vector():
    # Test vector: CRC of '123456789' under reflected X.25 conventions = 0x906E.
    assert crc16_ccitt(b"123456789") == 0x906E


def test_crc16_ccitt_empty():
    # CRC over empty payload: 0xFFFF init, no updates, final XOR -> 0x0000.
    assert crc16_ccitt(b"") == 0x0000


def test_bit_stuff_roundtrip():
    for payload in [b"\x00", b"\xff", b"hello", bytes(range(256))]:
        bits = [(byte >> i) & 1 for byte in payload for i in range(8)]
        assert bit_unstuff(bit_stuff(bits)) == bits


def test_bit_stuff_inserts_zero_after_five_ones():
    assert bit_stuff([1, 1, 1, 1, 1, 1]) == [1, 1, 1, 1, 1, 0, 1]


def test_nrzi_roundtrip():
    for bits in [[0], [1], [1, 0, 1, 0], [0, 0, 0, 0], [1, 1, 1, 1]]:
        assert nrzi_decode(nrzi_encode(bits)) == bits


def test_ax25_address_roundtrip():
    a = Address("NA1SS", ssid=0, has_been_repeated=True)
    encoded = a.encode(end_of_field=False)
    decoded, end = Address.decode(encoded)
    assert decoded.callsign == "NA1SS"
    assert decoded.ssid == 0
    assert decoded.has_been_repeated is True
    assert end is False


def test_ax25_frame_roundtrip():
    frame = Ax25Frame(
        destination=Address("APRS"),
        source=Address("N0CALL", ssid=3),
        path=[Address("ARISS", has_been_repeated=True), Address("WIDE2", ssid=1)],
        info=b"=5231.30N/01324.30E>hello",
    )
    decoded = Ax25Frame.decode(frame.encode())
    assert str(decoded.source) == "N0CALL-3"
    assert str(decoded.destination) == "APRS"
    assert [str(p) for p in decoded.path] == ["ARISS*", "WIDE2-1"]
    assert decoded.info == frame.info


def test_aprs_parse_position():
    out = parse_info(b"=5231.30N/01324.30E>SatOps demo")
    assert out["type"] == "position"
    assert out["latitude_deg"] == pytest.approx(52 + 31.30 / 60.0)
    assert out["longitude_deg"] == pytest.approx(13 + 24.30 / 60.0)
    assert out["symbol_table"] == "/"
    assert out["symbol_code"] == ">"
    assert out["comment"] == "SatOps demo"


def test_aprs_parse_position_south_west():
    out = parse_info(b"!3357.40S/15112.10W#test")
    assert out["latitude_deg"] == pytest.approx(-(33 + 57.40 / 60.0))
    assert out["longitude_deg"] == pytest.approx(-(151 + 12.10 / 60.0))


def test_aprs_parse_status_and_message():
    assert parse_info(b">Hello world") == {"type": "status", "text": "Hello world"}
    msg = parse_info(b":N0CALL   :ack42")
    assert msg["type"] == "message"
    assert msg["addressee"] == "N0CALL"
    assert msg["text"] == "ack42"


def test_hdlc_roundtrip_single_frame():
    payload = b"the quick brown fox jumps over the lazy dog"
    line_bits = hdlc_encode(payload, preamble_flags=2, trailing_flags=2)
    frames = hdlc_decode(line_bits)
    assert frames == [payload]


def test_hdlc_roundtrip_payload_with_five_ones_pattern():
    # Pick payload bytes that force bit stuffing
    payload = b"\xff\xff\xff" + b"AX.25 test " + b"\x7e\xff\x00"
    line_bits = hdlc_encode(payload)
    assert hdlc_decode(line_bits) == [payload]


def test_hdlc_corrupted_frame_dropped():
    payload = b"hello"
    line_bits = hdlc_encode(payload)
    # Flip a bit in the middle of the payload (well past the preamble flags).
    mid = len(line_bits) // 2
    line_bits[mid] ^= 1
    # CRC must fail; nothing should be returned.
    assert hdlc_decode(line_bits) == []


def test_audio_roundtrip():
    """End-to-end: real frame → AX.25 → HDLC → AFSK → demod → HDLC decode → AX.25 → match."""
    original = Ax25Frame(
        destination=Address("APRS"),
        source=Address("NA1SS"),
        path=[Address("ARISS", has_been_repeated=True), Address("WIDE2", ssid=1)],
        info=b"!5231.30N/01324.30E>SatOps APRS demo packet",
    )
    payload = original.encode()
    line_bits = hdlc_encode(payload, preamble_flags=24, trailing_flags=8)

    sample_rate = 48000
    samples = modulate(line_bits, sample_rate=sample_rate)
    assert samples.dtype == np.float32

    recovered_bits = demodulate(samples, sample_rate)
    frames = hdlc_decode(recovered_bits)
    assert len(frames) == 1, f"expected exactly one frame, got {len(frames)}"
    assert frames[0] == payload

    decoded = Ax25Frame.decode(frames[0])
    assert decoded.info == original.info
    assert str(decoded.source) == "NA1SS"


def test_audio_roundtrip_survives_mild_noise():
    """Decoder should still recover the frame with -25 dB additive Gaussian noise."""
    payload = (
        Ax25Frame(
            destination=Address("APRS"),
            source=Address("NA1SS"),
            info=b"=5231.30N/01324.30E>noise robustness",
        )
    ).encode()
    line_bits = hdlc_encode(payload, preamble_flags=24, trailing_flags=8)

    sample_rate = 48000
    samples = modulate(line_bits, sample_rate=sample_rate)
    rng = np.random.default_rng(0)
    noise = rng.normal(scale=0.06, size=samples.shape).astype(np.float32)
    noisy = samples + noise

    bits = demodulate(noisy, sample_rate)
    frames = hdlc_decode(bits)
    assert frames == [payload]
