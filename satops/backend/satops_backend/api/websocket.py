"""WebSocket endpoint — single multiplexed connection for all live data."""

import asyncio
import logging
from datetime import UTC, datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from satops_backend.config import settings
from satops_backend.db import get_db
from satops_backend.services import tracking
from satops_backend.services.link_budget import LinkBudgetInput, compute_link_budget
from satops_backend.services.sdr import sdr_service

logger = logging.getLogger(__name__)

router = APIRouter()


async def _get_active_satellite() -> dict | None:
    """Get the first satellite from DB as default active satellite."""
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM satellite LIMIT 1")
        row = await cursor.fetchone()
        return dict(row) if row else None
    finally:
        await db.close()


async def _stream_updates(ws: WebSocket) -> None:
    """Push tracking, spectrum, and link budget updates to the client."""
    satellite = await _get_active_satellite()
    if not satellite:
        return

    norad_id = satellite["norad_id"]
    frequency_hz = satellite["frequency_hz"]
    name = satellite["name"]

    while True:
        now = datetime.now(UTC)

        # Tracking update
        pos = tracking.compute_position(norad_id)
        if pos and pos["elevation_deg"] > settings.tracking_elevation_threshold_deg:
            doppler = tracking.compute_doppler(pos["velocity_km_s"], frequency_hz)

            await ws.send_json(
                {
                    "type": "tracking_update",
                    "timestamp": now.isoformat(),
                    "satellite": name,
                    "azimuth_deg": round(pos["azimuth_deg"], 2),
                    "elevation_deg": round(pos["elevation_deg"], 2),
                    "range_km": round(pos["range_km"], 2),
                    "velocity_km_s": round(pos["velocity_km_s"], 4),
                    "doppler_hz": round(doppler, 1),
                }
            )

            # Link budget (only when satellite is above horizon)
            if pos["elevation_deg"] > 0:
                lb = compute_link_budget(
                    LinkBudgetInput(
                        frequency_hz=frequency_hz,
                        range_km=pos["range_km"],
                    )
                )
                await ws.send_json(
                    {
                        "type": "link_budget",
                        "timestamp": now.isoformat(),
                        "fspl_db": lb.fspl_db,
                        "received_power_dbm": lb.received_power_dbm,
                        "noise_power_dbm": lb.noise_power_dbm,
                        "snr_db": lb.snr_db,
                    }
                )

        # Spectrum update
        spectrum = await sdr_service.get_spectrum()
        if spectrum is not None:
            await ws.send_json(
                {
                    "type": "spectrum_update",
                    "timestamp": now.isoformat(),
                    "center_frequency_hz": frequency_hz,
                    "bandwidth_hz": sdr_service._sample_rate,
                    "magnitudes_db": spectrum.tolist(),
                }
            )

        await asyncio.sleep(settings.ws_update_interval_s)


@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket) -> None:
    await ws.accept()
    logger.info("WebSocket client connected")
    try:
        await _stream_updates(ws)
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception:
        logger.exception("WebSocket error")
