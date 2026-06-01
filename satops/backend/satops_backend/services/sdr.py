"""SDR service — manages connection and streaming from RTL-SDR via SoapySDR.

When SoapySDR is not available, falls back to generating synthetic spectrum data
for development and testing.
"""

import asyncio
import logging
import threading
import time

import numpy as np
from numpy.typing import NDArray

from satops_backend.config import settings
from satops_backend.schemas import SdrStatus
from satops_backend.services import audio_demod

# Larger reads than fft_size so we keep up with the SDR's 2.048 MSps stream
# (eliminates overruns) and have enough samples per cycle to FM-demodulate
# real-time audio. 8192 ≈ 4 ms at 2.048 MSps, giving ~250 Hz read iterations.
_SAMPLES_PER_READ = 8192
# Compute spectrum every Nth chunk so its update rate stays at ~10 Hz even
# though the read loop now runs ~25× faster than before.
_SPECTRUM_EVERY_N_CHUNKS = 25

AUDIO_MODES = ("off", "wfm", "nfm")

logger = logging.getLogger(__name__)

# Try to import SoapySDR, fall back to fake mode
try:
    import SoapySDR as _SoapySDR

    HAS_SOAPY = True
except ImportError:
    HAS_SOAPY = False
    logger.info("SoapySDR not available — using synthetic data mode")


class SdrService:
    def __init__(self) -> None:
        self._connected = False
        self._use_hardware = False
        self._device = None
        self._stream = None
        self._frequency_hz = settings.sdr_frequency_hz
        self._sample_rate = settings.sdr_sample_rate
        self._gain = settings.sdr_gain
        self._running = False
        self._thread: threading.Thread | None = None
        self._queue: asyncio.Queue[NDArray[np.float64]] = asyncio.Queue(maxsize=settings.sdr_queue_size)
        # Audio queue is shallow — listeners must consume in real time. Excess
        # chunks are dropped at the producer to keep latency bounded.
        self._audio_queue: asyncio.Queue[NDArray[np.float32]] = asyncio.Queue(maxsize=8)
        self._audio_mode = "off"
        self._loop: asyncio.AbstractEventLoop | None = None
        self._fft_size = settings.sdr_fft_size
        # Serialises every libSoapySDR / librtlsdr call. The read thread and the
        # asyncio set_frequency/set_gain handlers both touch the device; without
        # this, concurrent calls trigger librtlsdr "setFrequency failed" errors.
        self._device_lock = threading.Lock()

    @property
    def status(self) -> SdrStatus:
        return SdrStatus(
            connected=self._connected,
            mode="hardware" if self._use_hardware else "synthetic",
            driver=settings.sdr_driver if self._connected else None,
            frequency_hz=self._frequency_hz if self._connected else None,
            sample_rate=self._sample_rate if self._connected else None,
            gain=self._gain if self._connected else None,
        )

    async def connect(self) -> bool:
        """Connect to SDR hardware, or start synthetic mode.

        Every exit path explicitly sets ``_use_hardware`` and ``_device`` so the
        read loop's ``if self._use_hardware and self._device`` check can never
        observe inconsistent stale state — e.g. ``_use_hardware=True`` left over
        from a prior successful connect while ``_device`` is now ``None``,
        which would silently flip the service into synthetic mode with no
        error visible to callers.
        """
        if not HAS_SOAPY:
            logger.info("SoapySDR not installed — synthetic mode")
            self._use_hardware = False
            self._device = None
            self._connected = True
            return self._connected

        try:
            devices = _SoapySDR.Device.enumerate({"driver": settings.sdr_driver})
            if not devices:
                logger.warning("No SDR devices found for driver=%s — synthetic mode", settings.sdr_driver)
                self._use_hardware = False
                self._device = None
                self._connected = True
                return self._connected
            device = _SoapySDR.Device(devices[0])
            device.setSampleRate(_SoapySDR.SOAPY_SDR_RX, 0, self._sample_rate)
            device.setFrequency(_SoapySDR.SOAPY_SDR_RX, 0, self._frequency_hz)
            device.setGain(_SoapySDR.SOAPY_SDR_RX, 0, self._gain)
            # Only commit the device handle after every config call succeeds,
            # so a partial init can't leave us with a half-configured device.
            self._device = device
            self._use_hardware = True
            self._connected = True
            logger.info(
                "Connected to SDR hardware: %s @ %.3f MHz, gain %.1f dB",
                settings.sdr_driver,
                self._frequency_hz / 1e6,
                self._gain,
            )
        except Exception:
            logger.exception("SDR hardware init failed — synthetic mode")
            self._device = None
            self._use_hardware = False
            self._connected = True

        return self._connected

    async def disconnect(self) -> None:
        """Stop streaming, release hardware, and reset state."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        if self._device is not None and self._use_hardware:
            try:
                if self._stream:
                    self._device.deactivateStream(self._stream)
                    self._device.closeStream(self._stream)
            except Exception:
                logger.exception("Error releasing SDR stream during disconnect")
        self._stream = None
        self._device = None
        self._use_hardware = False
        self._connected = False

    async def start_streaming(self) -> None:
        """Start the SDR read thread."""
        if self._running:
            return
        self._running = True
        self._loop = asyncio.get_event_loop()
        self._thread = threading.Thread(target=self._read_loop, daemon=True)
        self._thread.start()

    def _read_loop(self) -> None:
        """Background thread: continuously read IQ, demod audio, push spectrum at 10 Hz.

        Reads run at the SDR's natural sample-rate cadence (~250 Hz for
        8192-sample chunks at 2.048 MSps) rather than a fixed sleep, so:
        - The librtlsdr internal buffer doesn't overrun (no `O` markers).
        - Audio gets fed every chunk → continuous PCM stream.
        - Spectrum is rate-limited to one FFT per ``_SPECTRUM_EVERY_N_CHUNKS``.
        """
        chunks_since_spectrum = 0
        while self._running:
            if not (self._use_hardware and self._device):
                self._generate_synthetic()
                time.sleep(1.0 / settings.sdr_update_rate_hz)
                continue

            try:
                iq = self._read_chunk(_SAMPLES_PER_READ)
            except Exception:
                logger.exception("SDR read failed — stopping read thread")
                return
            if iq is None or iq.size == 0:
                continue

            # Audio (every chunk while a mode is enabled — keeps the stream gapless)
            if self._audio_mode != "off":
                try:
                    audio = audio_demod.fm_demod(
                        iq,
                        in_rate=self._sample_rate,
                        narrowband=(self._audio_mode == "nfm"),
                    )
                except Exception:
                    logger.exception("FM demod failed for mode=%s", self._audio_mode)
                    audio = None
                if audio is not None and audio.size and self._loop:
                    if self._audio_queue.full():
                        # Drop oldest to keep latency bounded under slow consumers.
                        self._loop.call_soon_threadsafe(self._audio_queue.get_nowait)
                    self._loop.call_soon_threadsafe(self._audio_queue.put_nowait, audio)

            # Spectrum (rate-limited)
            chunks_since_spectrum += 1
            if chunks_since_spectrum >= _SPECTRUM_EVERY_N_CHUNKS:
                fft_input = iq[: self._fft_size] if iq.size >= self._fft_size else iq
                fft_vals = np.fft.fftshift(np.fft.fft(fft_input, self._fft_size))
                magnitude = 20 * np.log10(np.abs(fft_vals) + 1e-10)
                if self._loop and not self._queue.full():
                    self._loop.call_soon_threadsafe(self._queue.put_nowait, magnitude)
                chunks_since_spectrum = 0

    def _read_chunk(self, n_samples: int) -> NDArray[np.complex64] | None:
        """Read ``n_samples`` complex samples from the SDR; returns None if zero returned."""
        buff = np.zeros(n_samples * 2, np.int8)
        with self._device_lock:
            if not self._stream:
                self._stream = self._device.setupStream(_SoapySDR.SOAPY_SDR_RX, _SoapySDR.SOAPY_SDR_CS8)
                self._device.activateStream(self._stream)
            sr = self._device.readStream(self._stream, [buff], n_samples)
        if sr.ret <= 0:
            return None
        return buff[: sr.ret * 2].astype(np.float32).view(np.complex64)

    def _generate_synthetic(self) -> None:
        """Generate synthetic spectrum data for development."""
        spectrum = np.random.normal(-80, 5, self._fft_size)
        # Add a signal peak near center (overwrite, not add — values are in dB)
        center = self._fft_size // 2
        spectrum[center - 5 : center + 5] = np.random.normal(-40, 3, 10)

        if self._loop and not self._queue.full():
            self._loop.call_soon_threadsafe(self._queue.put_nowait, spectrum)

    async def get_spectrum(self) -> NDArray[np.float64] | None:
        """Get next spectrum frame from the queue."""
        try:
            return await asyncio.wait_for(self._queue.get(), timeout=0.5)
        except TimeoutError:
            return None

    async def get_audio(self, timeout: float = 0.5) -> NDArray[np.float32] | None:
        """Get next audio chunk (Float32 PCM at audio_demod.AUDIO_RATE)."""
        try:
            return await asyncio.wait_for(self._audio_queue.get(), timeout=timeout)
        except TimeoutError:
            return None

    def set_audio_mode(self, mode: str) -> None:
        """Switch the FM demodulator: ``off``, ``wfm`` (broadcast), ``nfm`` (amateur voice)."""
        if mode not in AUDIO_MODES:
            raise ValueError(f"audio mode must be one of {AUDIO_MODES}, got {mode!r}")
        self._audio_mode = mode
        # Flush stale chunks so consumers don't hear leftover audio from the
        # previous mode/frequency after the switch.
        while not self._audio_queue.empty():
            try:
                self._audio_queue.get_nowait()
            except asyncio.QueueEmpty:
                break

    @property
    def audio_mode(self) -> str:
        return self._audio_mode

    async def set_frequency(self, frequency_hz: int) -> None:
        # Only commit the field update once the hardware confirms the retune,
        # so ``status.frequency_hz`` never advertises a tune the radio hasn't
        # actually performed. Retry with backoff because librtlsdr occasionally
        # returns -EAGAIN when a USB transfer from a prior readStream is still
        # in flight even after the read lock is released.
        if self._use_hardware and self._device:
            await self._call_device(
                lambda: self._device.setFrequency(_SoapySDR.SOAPY_SDR_RX, 0, frequency_hz),
                what=f"setFrequency({frequency_hz})",
            )
        self._frequency_hz = frequency_hz

    async def set_gain(self, gain: float) -> None:
        if self._use_hardware and self._device:
            await self._call_device(
                lambda: self._device.setGain(_SoapySDR.SOAPY_SDR_RX, 0, gain),
                what=f"setGain({gain})",
            )
        self._gain = gain

    async def _call_device(self, fn, *, what: str, attempts: int = 3) -> None:
        """Run a librtlsdr/SoapySDR device call under the lock with retry."""
        last_exc: Exception | None = None
        for attempt in range(attempts):
            try:
                with self._device_lock:
                    fn()
                return
            except RuntimeError as exc:
                last_exc = exc
                await asyncio.sleep(0.05 * (attempt + 1))
        logger.error("%s failed after %d attempts: %s", what, attempts, last_exc)
        if last_exc is not None:
            raise last_exc


# Singleton
sdr_service = SdrService()
