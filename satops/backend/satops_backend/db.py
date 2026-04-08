import aiosqlite

from satops_backend.config import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS satellite (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    norad_id INTEGER NOT NULL UNIQUE,
    frequency_hz INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS pass (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    satellite_id INTEGER NOT NULL REFERENCES satellite(id),
    aos TEXT NOT NULL,
    los TEXT NOT NULL,
    max_elevation REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS observation (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pass_id INTEGER NOT NULL REFERENCES pass(id),
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    peak_signal REAL,
    avg_snr REAL,
    notes TEXT
);
"""

DEFAULT_SATELLITES = [
    ("NOAA 18", 28654, 137_912_500),
    ("NOAA 19", 33591, 137_100_000),
    ("METEOR-M2 3", 57166, 137_900_000),
    ("METEOR-M2 4", 59051, 137_100_000),
    ("FUNCUBE-1", 39444, 145_935_000),
]


async def get_db() -> aiosqlite.Connection:
    db = await aiosqlite.connect(settings.db_path)
    db.row_factory = aiosqlite.Row
    return db


async def init_db() -> None:
    db = await get_db()
    try:
        await db.executescript(SCHEMA)
        for name, norad_id, freq in DEFAULT_SATELLITES:
            await db.execute(
                "INSERT OR IGNORE INTO satellite (name, norad_id, frequency_hz) VALUES (?, ?, ?)",
                (name, norad_id, freq),
            )
        await db.commit()
    finally:
        await db.close()
