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
        self._loop: asyncio.AbstractEventLoop | None = None
        self._fft_size = settings.sdr_fft_size

    @property
    def status(self) -> SdrStatus:
        return SdrStatus(
            connected=self._connected,
            driver=settings.sdr_driver if self._connected else None,
            frequency_hz=self._frequency_hz if self._connected else None,
            sample_rate=self._sample_rate if self._connected else None,
            gain=self._gain if self._connected else None,
        )

    async def connect(self) -> bool:
        """Connect to SDR hardware, or start synthetic mode."""
        if HAS_SOAPY:
            try:
                # SoapySDR Python bindings require SoapySDRKwargs, not plain dicts.
                # Use enumerate() result to get the right type.
                devices = _SoapySDR.Device.enumerate({"driver": settings.sdr_driver})
                if not devices:
                    logger.warning("No SDR devices found for driver=%s, using synthetic mode", settings.sdr_driver)
                    self._connected = True
                    return self._connected
                self._device = _SoapySDR.Device(devices[0])
                self._device.setSampleRate(_SoapySDR.SOAPY_SDR_RX, 0, self._sample_rate)
                self._device.setFrequency(_SoapySDR.SOAPY_SDR_RX, 0, self._frequency_hz)
                self._device.setGain(_SoapySDR.SOAPY_SDR_RX, 0, self._gain)
                self._connected = True
                self._use_hardware = True
                logger.info("Connected to SDR: %s", settings.sdr_driver)
            except Exception:
                logger.exception("Failed to connect to SDR hardware, falling back to synthetic mode")
                self._connected = True
        else:
            self._connected = True  # Synthetic mode

        return self._connected

    async def disconnect(self) -> None:
        """Stop streaming and disconnect."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        if self._device and self._use_hardware:
            if self._stream:
                self._device.deactivateStream(self._stream)
                self._device.closeStream(self._stream)
                self._stream = None
            self._device = None
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
        """Background thread: read IQ samples, compute FFT, push to queue."""
        while self._running:
            if self._use_hardware and self._device:
                self._read_hardware()
            else:
                self._generate_synthetic()
            time.sleep(1.0 / settings.sdr_update_rate_hz)

    def _read_hardware(self) -> None:
        """Read IQ samples from real SDR hardware, compute FFT."""
        if not self._stream:
            self._stream = self._device.setupStream(_SoapySDR.SOAPY_SDR_RX, _SoapySDR.SOAPY_SDR_CS8)
            self._device.activateStream(self._stream)

        buff = np.array([0] * self._fft_size * 2, np.int8)
        sr = self._device.readStream(self._stream, [buff], self._fft_size)

        if sr.ret > 0:
            # Convert interleaved I/Q int8 to complex float
            iq = buff[: sr.ret * 2].astype(np.float32).view(np.complex64)
            # Compute FFT magnitude in dB
            fft_vals = np.fft.fftshift(np.fft.fft(iq, self._fft_size))
            magnitude = 20 * np.log10(np.abs(fft_vals) + 1e-10)
            if self._loop and not self._queue.full():
                self._loop.call_soon_threadsafe(self._queue.put_nowait, magnitude)

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

    async def set_frequency(self, frequency_hz: int) -> None:
        self._frequency_hz = frequency_hz
        if self._use_hardware and self._device:
            self._device.setFrequency(_SoapySDR.SOAPY_SDR_RX, 0, frequency_hz)

    async def set_gain(self, gain: float) -> None:
        self._gain = gain
        if self._use_hardware and self._device:
            self._device.setGain(_SoapySDR.SOAPY_SDR_RX, 0, gain)


# Singleton
sdr_service = SdrService()
