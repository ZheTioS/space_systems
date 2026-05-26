"""Pass session tracker — detects AOS/LOS and auto-logs observations."""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime

from satops_backend.config import settings
from satops_backend.db import get_db

logger = logging.getLogger(__name__)


@dataclass
class ActivePass:
    satellite_id: int
    norad_id: int
    satellite_name: str
    aos: datetime
    max_elevation: float = 0.0
    peak_signal: float = -999.0
    snr_samples: list[float] = field(default_factory=list)
    pass_db_id: int | None = None


class PassTracker:
    def __init__(self) -> None:
        self._active: dict[int, ActivePass] = {}  # norad_id -> ActivePass
        self._lock = asyncio.Lock()

    @property
    def active_passes(self) -> dict[int, ActivePass]:
        return self._active

    async def update(
        self,
        norad_id: int,
        satellite_name: str,
        elevation_deg: float,
        signal_db: float | None = None,
        snr_db: float | None = None,
    ) -> None:
        """Call on every tracking update. Handles AOS/LOS transitions."""
        # AOS threshold matches find_passes' min_pass_elevation_deg so the
        # predicted upcoming-passes list and auto-logged observations agree.
        is_visible = elevation_deg > settings.min_pass_elevation_deg

        async with self._lock:
            if is_visible and norad_id not in self._active:
                await self._start_pass(norad_id, satellite_name, elevation_deg)

            if norad_id in self._active:
                ap = self._active[norad_id]
                ap.max_elevation = max(ap.max_elevation, elevation_deg)
                if signal_db is not None:
                    ap.peak_signal = max(ap.peak_signal, signal_db)
                if snr_db is not None:
                    ap.snr_samples.append(snr_db)

            if not is_visible and norad_id in self._active:
                await self._end_pass(norad_id)

    async def _start_pass(self, norad_id: int, name: str, elevation: float) -> None:
        """Record AOS — insert pass row into DB."""
        now = datetime.now(UTC)
        db = await get_db()
        try:
            # Look up satellite DB id from norad_id
            cursor = await db.execute("SELECT id FROM satellite WHERE norad_id = ?", (norad_id,))
            row = await cursor.fetchone()
            if not row:
                return
            sat_db_id = row["id"]

            # Insert pass with placeholder LOS (updated on end)
            cursor = await db.execute(
                "INSERT INTO pass (satellite_id, aos, los, max_elevation) VALUES (?, ?, ?, ?)",
                (sat_db_id, now.isoformat(), now.isoformat(), elevation),
            )
            await db.commit()
            pass_id = cursor.lastrowid
        finally:
            await db.close()

        self._active[norad_id] = ActivePass(
            satellite_id=sat_db_id,
            norad_id=norad_id,
            satellite_name=name,
            aos=now,
            max_elevation=elevation,
            pass_db_id=pass_id,
        )
        logger.info("AOS: %s (pass #%d)", name, pass_id)

    async def _end_pass(self, norad_id: int) -> None:
        """Record LOS — update pass row and create observation."""
        ap = self._active.pop(norad_id)
        now = datetime.now(UTC)
        avg_snr = sum(ap.snr_samples) / len(ap.snr_samples) if ap.snr_samples else None
        peak = ap.peak_signal if ap.peak_signal > -999.0 else None

        db = await get_db()
        try:
            # Update pass with actual LOS and max elevation
            await db.execute(
                "UPDATE pass SET los = ?, max_elevation = ? WHERE id = ?",
                (now.isoformat(), ap.max_elevation, ap.pass_db_id),
            )

            # Create observation
            await db.execute(
                """INSERT INTO observation (pass_id, start_time, end_time, peak_signal, avg_snr, notes)
                VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    ap.pass_db_id,
                    ap.aos.isoformat(),
                    now.isoformat(),
                    peak,
                    round(avg_snr, 2) if avg_snr is not None else None,
                    f"Auto-logged {ap.satellite_name}",
                ),
            )
            await db.commit()
        finally:
            await db.close()

        duration = (now - ap.aos).total_seconds()
        logger.info(
            "LOS: %s (pass #%d, %.0fs, max el %.1f°, peak %.1f dB, avg SNR %s dB)",
            ap.satellite_name,
            ap.pass_db_id,
            duration,
            ap.max_elevation,
            peak if peak is not None else 0,
            f"{avg_snr:.1f}" if avg_snr is not None else "N/A",
        )


# Singleton
pass_tracker = PassTracker()
