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
                self._device = _SoapySDR.Device({"driver": settings.sdr_driver})
                self._device.setSampleRate(_SoapySDR.SOAPY_SDR_RX, 0, self._sample_rate)
                self._device.setFrequency(_SoapySDR.SOAPY_SDR_RX, 0, self._frequency_hz)
                self._device.setGain(_SoapySDR.SOAPY_SDR_RX, 0, self._gain)
                self._connected = True
                logger.info("Connected to SDR: %s", settings.sdr_driver)
            except Exception:
                logger.exception("Failed to connect to SDR hardware")
                self._connected = True  # Synthetic fallback
        else:
            self._connected = True  # Synthetic mode

        return self._connected

    async def disconnect(self) -> None:
        """Stop streaming and disconnect."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        if self._device and HAS_SOAPY:
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
            if HAS_SOAPY and self._device:
                self._read_hardware()
            else:
                self._generate_synthetic()
            time.sleep(1.0 / settings.sdr_update_rate_hz)

    def _read_hardware(self) -> None:
        """Read from real SDR hardware."""
        # TODO: implement real SoapySDR readStream
        self._generate_synthetic()

    def _generate_synthetic(self) -> None:
        """Generate synthetic spectrum data for development."""
        noise = np.random.normal(-80, 5, self._fft_size)
        # Add a signal peak near center
        center = self._fft_size // 2
        signal = np.zeros(self._fft_size)
        signal[center - 5 : center + 5] = np.random.normal(-40, 3, 10)
        spectrum = noise + signal

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
        if HAS_SOAPY and self._device:
            self._device.setFrequency(_SoapySDR.SOAPY_SDR_RX, 0, frequency_hz)

    async def set_gain(self, gain: float) -> None:
        self._gain = gain
        if HAS_SOAPY and self._device:
            self._device.setGain(_SoapySDR.SOAPY_SDR_RX, 0, gain)


# Singleton
sdr_service = SdrService()
