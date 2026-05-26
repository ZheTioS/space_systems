"""CLI: decode an AFSK-1200 / AX.25 / APRS recording.

Usage:
    python -m satops_backend.decoders.aprs <file.wav>
    python -m satops_backend.decoders.aprs --synthesize out.wav
        (writes a sample WAV containing one synthetic APRS position frame)

The synthesise path also runs the decoder on what it just wrote, so a single
``--synthesize`` invocation acts as an end-to-end smoke test.
"""

import argparse
import sys
from pathlib import Path

from satops_backend.decoders.aprs.aprs import parse_info
from satops_backend.decoders.aprs.audio import (
    BAUD,
    demodulate,
    modulate,
    read_wav,
    write_wav,
)
from satops_backend.decoders.aprs.ax25 import Address, Ax25Frame
from satops_backend.decoders.aprs.hdlc import hdlc_decode, hdlc_encode


def _print_frame(payload: bytes) -> None:
    try:
        frame = Ax25Frame.decode(payload)
    except ValueError as exc:
        print(f"[malformed AX.25] {exc}")
        return
    header = frame.header_str()
    info_repr = frame.info.decode("ascii", errors="replace")
    print(f"{header}: {info_repr}")
    parsed = parse_info(frame.info)
    if parsed and parsed.get("type") == "position":
        print(
            f"  POS: {parsed['latitude_deg']:.4f}, {parsed['longitude_deg']:.4f}"
            f"  symbol={parsed['symbol_table']}{parsed['symbol_code']}"
            f"  comment={parsed['comment']!r}"
        )
    elif parsed and parsed.get("type") == "status":
        print(f"  STATUS: {parsed['text']!r}")
    elif parsed and parsed.get("type") == "message":
        print(f"  MSG to {parsed['addressee']!r}: {parsed['text']!r}")
    elif parsed:
        print(f"  {parsed}")


def _synthesize(out_path: Path, sample_rate: int = 48000) -> None:
    frame = Ax25Frame(
        destination=Address("APRS"),
        source=Address("NA1SS"),
        path=[Address("ARISS", has_been_repeated=True), Address("WIDE2", ssid=1)],
        info=b"!5231.30N/01324.30E>SatOps APRS demo packet",
    )
    payload = frame.encode()
    line_bits = hdlc_encode(payload, preamble_flags=24, trailing_flags=8)
    samples = modulate(line_bits, sample_rate=sample_rate)
    write_wav(out_path, samples, sample_rate=sample_rate)
    print(f"Wrote {len(samples)} samples ({len(samples) / sample_rate:.2f}s @ {sample_rate} Hz) to {out_path}")
    print(f"  Encoded frame: {frame.header_str()}: {frame.info.decode('ascii')}")
    print(f"  HDLC bits: {len(line_bits)} ({len(line_bits) / BAUD:.2f}s of air time)")


def _decode_file(path: Path) -> int:
    samples, sr = read_wav(path)
    line_bits = demodulate(samples, sr)
    frames = hdlc_decode(line_bits)
    if not frames:
        print(f"No frames decoded from {path}", file=sys.stderr)
        return 1
    print(f"{len(frames)} frame(s) decoded from {path}:")
    for f in frames:
        _print_frame(f)
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m satops_backend.decoders.aprs")
    p.add_argument("path", help="input WAV file (or output path when --synthesize)")
    p.add_argument(
        "--synthesize",
        action="store_true",
        help="Write a synthetic demo WAV instead of decoding, then decode it.",
    )
    args = p.parse_args(argv)
    path = Path(args.path)

    if args.synthesize:
        _synthesize(path)
        print("\nDecoding what we just wrote:")
        return _decode_file(path)

    return _decode_file(path)


if __name__ == "__main__":
    raise SystemExit(main())
