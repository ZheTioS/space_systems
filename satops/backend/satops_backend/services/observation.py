"""Observation logging service."""

from satops_backend.db import get_db
from satops_backend.schemas import Observation, ObservationBase


async def create_observation(obs: ObservationBase) -> Observation:
    db = await get_db()
    try:
        cursor = await db.execute(
            """INSERT INTO observation (pass_id, start_time, end_time, peak_signal, avg_snr, notes)
            VALUES (?, ?, ?, ?, ?, ?)""",
            (
                obs.pass_id,
                obs.start_time.isoformat(),
                obs.end_time.isoformat(),
                obs.peak_signal,
                obs.avg_snr,
                obs.notes,
            ),
        )
        await db.commit()
        return Observation(id=cursor.lastrowid, **obs.model_dump())
    finally:
        await db.close()


async def get_observations(limit: int = 50) -> list[Observation]:
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM observation ORDER BY start_time DESC LIMIT ?", (limit,))
        rows = await cursor.fetchall()
        return [Observation(**dict(row)) for row in rows]
    finally:
        await db.close()


async def get_observation(observation_id: int) -> Observation | None:
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM observation WHERE id = ?", (observation_id,))
        row = await cursor.fetchone()
        return Observation(**dict(row)) if row else None
    finally:
        await db.close()
