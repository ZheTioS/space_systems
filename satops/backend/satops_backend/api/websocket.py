"""WebSocket endpoint — single multiplexed connection for all live data."""

import asyncio
import json
import logging
from datetime import UTC, datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from satops_backend.config import settings
from satops_backend.db import get_db
from satops_backend.services import tracking
from satops_backend.services.link_budget import LinkBudgetInput, compute_link_budget
from satops_backend.services.pass_tracker import pass_tracker
from satops_backend.services.sdr import sdr_service

logger = logging.getLogger(__name__)

router = APIRouter()


async def _get_satellite(norad_id: int | None = None) -> dict | None:
    """Get a satellite from DB by norad_id, or the first one as default."""
    db = await get_db()
    try:
        if norad_id:
            cursor = await db.execute("SELECT * FROM satellite WHERE norad_id = ?", (norad_id,))
        else:
            cursor = await db.execute("SELECT * FROM satellite LIMIT 1")
        row = await cursor.fetchone()
        return dict(row) if row else None
    finally:
        await db.close()


@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket) -> None:
    await ws.accept()
    logger.info("WebSocket client connected")

    satellite = await _get_satellite()
    if not satellite:
        await ws.close()
        return

    async def listen_for_commands() -> None:
        """Listen for client messages to switch satellite."""
        nonlocal satellite
        while True:
            try:
                raw = await ws.receive_text()
                msg = json.loads(raw)
                if msg.get("type") == "select_satellite":
                    new_sat = await _get_satellite(msg["norad_id"])
                    if new_sat:
                        satellite = new_sat
                        logger.info("Switched to satellite: %s", new_sat["name"])
            except (WebSocketDisconnect, RuntimeError):
                break

    async def stream_updates() -> None:
        """Push tracking, spectrum, and link budget updates."""
        while True:
            norad_id = satellite["norad_id"]
            frequency_hz = satellite["frequency_hz"]
            name = satellite["name"]
            now = datetime.now(UTC)

            # Tracking update
            pos = tracking.compute_position(norad_id)
            subpoint = tracking.compute_subsatellite_point(norad_id)
            snr_db = None
            if pos and pos["elevation_deg"] > settings.tracking_elevation_threshold_deg:
                doppler = tracking.compute_doppler(pos["velocity_km_s"], frequency_hz)

                msg = {
                    "type": "tracking_update",
                    "timestamp": now.isoformat(),
                    "satellite": name,
                    "azimuth_deg": round(pos["azimuth_deg"], 2),
                    "elevation_deg": round(pos["elevation_deg"], 2),
                    "range_km": round(pos["range_km"], 2),
                    "velocity_km_s": round(pos["velocity_km_s"], 4),
                    "doppler_hz": round(doppler, 1),
                }
                if subpoint:
                    msg["lat"] = round(subpoint["lat"], 4)
                    msg["lon"] = round(subpoint["lon"], 4)
                await ws.send_json(msg)

                # Link budget (only when satellite is above horizon)
                if pos["elevation_deg"] > 0:
                    lb = compute_link_budget(
                        LinkBudgetInput(
                            frequency_hz=frequency_hz,
                            range_km=pos["range_km"],
                        )
                    )
                    snr_db = lb.snr_db
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

            # Pass tracking — auto-log observations on AOS/LOS
            if pos:
                await pass_tracker.update(
                    norad_id=norad_id,
                    satellite_name=name,
                    elevation_deg=pos["elevation_deg"],
                    signal_db=lb.received_power_dbm if snr_db is not None else None,
                    snr_db=snr_db,
                )
                active = pass_tracker.active_passes.get(norad_id)
                if active:
                    await ws.send_json(
                        {
                            "type": "active_pass",
                            "timestamp": now.isoformat(),
                            "satellite": name,
                            "aos": active.aos.isoformat(),
                            "max_elevation": round(active.max_elevation, 1),
                            "peak_signal": round(active.peak_signal, 1) if active.peak_signal > -999 else None,
                            "samples": len(active.snr_samples),
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

    try:
        await asyncio.gather(listen_for_commands(), stream_updates())
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception:
        logger.exception("WebSocket error")
