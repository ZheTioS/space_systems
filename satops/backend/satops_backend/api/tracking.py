from datetime import datetime

from fastapi import APIRouter, HTTPException

from satops_backend.db import get_db
from satops_backend.services import tracking

router = APIRouter(prefix="/tracking", tags=["tracking"])


@router.get("/satellites")
async def list_satellites() -> list[dict]:
    """List configured satellites from the database."""
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM satellite")
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        await db.close()


@router.get("/position/{norad_id}")
async def get_position(norad_id: int) -> dict:
    """Get current position of a satellite."""
    pos = tracking.compute_position(norad_id)
    if pos is None:
        raise HTTPException(status_code=404, detail=f"Satellite {norad_id} not found in TLE data")
    return pos


@router.get("/passes/{norad_id}")
async def get_passes(norad_id: int, hours: float = 24.0) -> list[dict]:
    """Get upcoming passes for a satellite."""
    return tracking.find_passes(norad_id, hours_ahead=hours)


@router.get("/doppler/{norad_id}")
async def get_doppler_curve(
    norad_id: int,
    aos: datetime,
    los: datetime,
    frequency_hz: int,
) -> list[dict]:
    """Get predicted Doppler curve for a pass."""
    return tracking.compute_doppler_curve(norad_id, aos, los, frequency_hz)


@router.post("/tle/refresh")
async def refresh_tles() -> dict:
    """Force refresh TLE data from CelesTrak."""
    sats = await tracking.load_tles()
    return {"loaded": len(sats)}
