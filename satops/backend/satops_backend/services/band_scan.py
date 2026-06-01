"""Band scanner — hop the SDR across a frequency band and detect signal peaks.

Each hop tunes the SDR, drains any stale frames, then averages a handful of
fresh spectrum frames. Peaks above ``threshold_db`` over the median noise floor
are clustered, rounded to the band's channel grid (100 kHz for FM broadcast),
and returned with their strongest power.

The scan briefly interrupts audio and live spectrum streaming because every
hop calls ``sdr_service.set_frequency`` — callers should restore the previous
tune via ``sdr_service.set_frequency(original_hz)`` after the scan.
"""

import asyncio
import logging
from dataclasses import dataclass

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class Station:
    frequency_hz: int
    power_db: float
    snr_db: float


async def scan_band(
    sdr_service,
    start_hz: int,
    end_hz: int,
    *,
    channel_step_hz: int = 100_000,
    threshold_db: float = 15.0,
    frames_per_hop: int = 5,
) -> list[Station]:
    """Sweep the SDR across [start_hz, end_hz] and return detected stations."""
    sample_rate = sdr_service._sample_rate  # noqa: SLF001 — service-internal field
    # 75 % of bandwidth per hop so adjacent hops overlap and edge stations don't
    # get clipped by the anti-aliasing rolloff of one window alone.
    hop_step = int(sample_rate * 0.75)
    if hop_step <= 0:
        return []

    original_hz = sdr_service._frequency_hz  # noqa: SLF001

    all_stations: dict[int, Station] = {}
    center = start_hz + sample_rate // 2
    try:
        while center - sample_rate // 2 < end_hz:
            await sdr_service.set_frequency(center)
            # Let the tuner settle before reading the spectrum — librtlsdr
            # returns a few transitional frames after a retune.
            await asyncio.sleep(0.1)

            # Drain stale frames that were already in the queue from the
            # previous hop's frequency.
            while not sdr_service._queue.empty():  # noqa: SLF001
                try:
                    sdr_service._queue.get_nowait()  # noqa: SLF001
                except asyncio.QueueEmpty:
                    break

            frames = []
            for _ in range(frames_per_hop):
                frame = await sdr_service.get_spectrum()
                if frame is not None:
                    frames.append(frame)
            if not frames:
                center += hop_step
                continue

            avg = np.mean(np.array(frames), axis=0)
            n_bins = len(avg)
            bin_width_hz = sample_rate / n_bins
            median = float(np.median(avg))

            # Skip the central ±10 bins — the SDR's DC-offset spike isn't a station.
            dc_mask = np.ones(n_bins, dtype=bool)
            dc_mask[n_bins // 2 - 10 : n_bins // 2 + 10] = False

            candidates = np.where((avg > median + threshold_db) & dc_mask)[0]
            for cluster in _cluster_adjacent(candidates, max_gap=5):
                peak_bin = int(cluster[np.argmax(avg[cluster])])
                peak_hz = int(center + (peak_bin - n_bins / 2) * bin_width_hz)
                if not (start_hz <= peak_hz <= end_hz):
                    continue
                snapped = int(round(peak_hz / channel_step_hz) * channel_step_hz)
                # Keep the strongest measurement per snapped channel.
                power = float(avg[peak_bin])
                snr = power - median
                prev = all_stations.get(snapped)
                if prev is None or power > prev.power_db:
                    all_stations[snapped] = Station(frequency_hz=snapped, power_db=power, snr_db=snr)

            center += hop_step
    finally:
        try:
            await sdr_service.set_frequency(original_hz)
        except Exception:
            logger.exception("failed to restore original frequency after scan")

    return sorted(all_stations.values(), key=lambda s: s.frequency_hz)


def _cluster_adjacent(indices: np.ndarray, *, max_gap: int) -> list[np.ndarray]:
    """Group sorted indices into runs where successive entries differ by ≤ max_gap."""
    if indices.size == 0:
        return []
    breaks = np.where(np.diff(indices) > max_gap)[0]
    return np.split(indices, breaks + 1)
