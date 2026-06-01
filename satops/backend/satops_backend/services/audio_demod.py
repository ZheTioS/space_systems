"""FM audio demodulation for SDR baseband I/Q.

Quadrature FM demodulator: ``phase_diff = angle(x[n] * conj(x[n-1]))``,
scaled so a maximum frequency deviation maps to roughly ±1.0, then
low-pass-filtered and decimated to the requested audio sample rate. WFM also
gets a single-pole 50 µs de-emphasis (Region 1 standard).

WFM expects an FM broadcast channel (~200 kHz BW, 75 kHz max deviation).
NFM expects narrowband amateur voice (~12.5 kHz BW, 5 kHz max deviation).
"""

import numpy as np
import scipy.signal

# Audio rate is fixed so the frontend AudioContext setup stays simple.
AUDIO_RATE = 32000


def fm_demod(iq: np.ndarray, in_rate: float, *, narrowband: bool = False) -> np.ndarray:
    """Demodulate FM from baseband I/Q to mono float32 PCM at AUDIO_RATE.

    The order matters: phase-diff → decimate → DC-removal → scale → de-emphasis.
    Removing the per-chunk mean before applying the gain factor strips out the
    constant frequency offset between the LO and the actual broadcast carrier
    (which would otherwise demodulate to a strong DC level that consumes the
    entire output dynamic range and clips the program audio).

    Parameters
    ----------
    iq
        Baseband I/Q samples as complex64.
    in_rate
        Input sample rate (Hz).
    narrowband
        True for amateur NFM voice (~5 kHz deviation), False for FM broadcast
        (~75 kHz deviation).
    """
    if iq.size < 2:
        return np.zeros(0, dtype=np.float32)

    # 1. Phase difference between consecutive samples — proportional to instantaneous frequency.
    audio = np.angle(iq[1:] * np.conj(iq[:-1]))

    # 2. Decimate to audio rate while filtering out everything above audio BW.
    decim = int(round(in_rate / AUDIO_RATE))
    if decim > 1:
        audio = scipy.signal.decimate(audio, decim, ftype="fir", zero_phase=True)

    # 3. Strip DC (= constant carrier-LO offset). Per-chunk mean removal is
    #    naive vs a stateful HPF but works fine for streamed chunks of ~4 ms.
    audio = audio - audio.mean()

    # 4. Scale so a full ±max_dev deviation maps to ±1.0.
    max_dev_hz = 5_000 if narrowband else 75_000
    gain = in_rate / (2.0 * np.pi * max_dev_hz)
    audio = audio * gain

    # 5. De-emphasis for WFM (50 µs single-pole IIR, Region 1 standard).
    if not narrowband:
        tau = 50e-6
        a = float(np.exp(-1.0 / (AUDIO_RATE * tau)))
        audio = scipy.signal.lfilter([1 - a], [1.0, -a], audio)

    return np.clip(audio, -1.0, 1.0).astype(np.float32)
