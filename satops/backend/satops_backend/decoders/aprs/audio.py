"""AFSK 1200 (Bell 202) modem + WAV I/O.

Modulator: phase-continuous mark (1200 Hz) / space (2200 Hz) tones at one
symbol per bit. Demodulator: I/Q correlation against both tones, integrate
over one bit period, then a single-pass phase-offset search picks the symbol
clock alignment that maximises decision margin.

The static clock-offset works for short clean recordings (synthetic demos,
TNC-quality captures). Real off-air recordings with drift would need a digital
PLL or Mueller-Müller TED — out of scope here.
"""

import wave
from collections.abc import Iterable
from pathlib import Path

import numpy as np

MARK_HZ = 1200.0
SPACE_HZ = 2200.0
BAUD = 1200.0


def modulate(bits: Iterable[int], sample_rate: int = 48000, amplitude: float = 0.6) -> np.ndarray:
    """Generate phase-continuous AFSK 1200 samples for the given line bits."""
    bit_list = list(bits)
    if not bit_list:
        return np.zeros(0, dtype=np.float32)

    samples_per_bit = sample_rate / BAUD
    total = int(round(samples_per_bit * len(bit_list)))
    out = np.empty(total, dtype=np.float32)

    phase = 0.0
    cursor = 0
    for i, b in enumerate(bit_list):
        end = int(round((i + 1) * samples_per_bit))
        f = MARK_HZ if b == 1 else SPACE_HZ
        dphi = 2.0 * np.pi * f / sample_rate
        for k in range(cursor, end):
            out[k] = amplitude * np.sin(phase)
            phase += dphi
        cursor = end
        # Keep phase bounded to preserve float precision over long streams.
        phase = phase % (2.0 * np.pi)

    return out[:cursor]


def write_wav(path: str | Path, samples: np.ndarray, sample_rate: int = 48000) -> None:
    pcm = np.clip(samples, -1.0, 1.0)
    pcm = (pcm * 32767.0).astype(np.int16)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(pcm.tobytes())


def read_wav(path: str | Path) -> tuple[np.ndarray, int]:
    """Read a mono or multi-channel 16-bit PCM WAV. Multi-channel is averaged to mono."""
    with wave.open(str(path), "rb") as w:
        sr = w.getframerate()
        nch = w.getnchannels()
        sw = w.getsampwidth()
        frames = w.readframes(w.getnframes())
    if sw != 2:
        raise ValueError(f"Only 16-bit PCM WAV supported (got {sw * 8}-bit)")
    samples = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
    if nch > 1:
        samples = samples.reshape(-1, nch).mean(axis=1)
    return samples, sr


def demodulate(samples: np.ndarray, sample_rate: int) -> list[int]:
    """Return the recovered line bits (mark=1, space=0) — feed into nrzi_decode."""
    if len(samples) == 0:
        return []

    n = len(samples)
    samples_per_bit = sample_rate / BAUD
    if n < int(samples_per_bit) * 2:
        return []

    t = np.arange(n, dtype=np.float64) / sample_rate

    mark_i = samples * np.cos(2 * np.pi * MARK_HZ * t)
    mark_q = samples * np.sin(2 * np.pi * MARK_HZ * t)
    space_i = samples * np.cos(2 * np.pi * SPACE_HZ * t)
    space_q = samples * np.sin(2 * np.pi * SPACE_HZ * t)

    win = max(1, int(round(samples_per_bit)))
    kernel = np.ones(win, dtype=np.float64) / win
    mark_mag = np.sqrt(np.convolve(mark_i, kernel, "same") ** 2 + np.convolve(mark_q, kernel, "same") ** 2)
    space_mag = np.sqrt(np.convolve(space_i, kernel, "same") ** 2 + np.convolve(space_q, kernel, "same") ** 2)
    diff = mark_mag - space_mag  # > 0 => mark, < 0 => space

    # Sweep static symbol-clock offsets; pick the one with the largest decision margin.
    sweep = max(2, int(round(samples_per_bit)))
    best_offset, best_score = 0, -np.inf
    for offset in range(sweep):
        idx = np.arange(offset, n, samples_per_bit).astype(int)
        idx = idx[idx < n]
        if len(idx) < 2:
            continue
        score = float(np.abs(diff[idx]).mean())
        if score > best_score:
            best_score, best_offset = score, offset

    idx = np.arange(best_offset, n, samples_per_bit).astype(int)
    idx = idx[idx < n]
    return [1 if v > 0 else 0 for v in diff[idx]]
