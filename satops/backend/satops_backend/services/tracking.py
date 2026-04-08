"""Orbit tracking service using Skyfield and TLE data."""

import logging
from datetime import UTC, datetime, timedelta

import httpx
from skyfield.api import EarthSatellite, load, wgs84
from skyfield.toposlib import GeographicPosition

from satops_backend.config import settings

logger = logging.getLogger(__name__)

ts = load.timescale()

# In-memory TLE store: norad_id -> EarthSatellite
_satellites: dict[int, EarthSatellite] = {}
_observer: GeographicPosition | None = None


def get_observer() -> GeographicPosition:
    global _observer
    if _observer is None:
        _observer = wgs84.latlon(settings.observer_lat, settings.observer_lon, settings.observer_elev_m)
    return _observer


async def load_tles() -> dict[int, EarthSatellite]:
    """Fetch TLE data from CelesTrak and parse into Skyfield satellites."""
    global _satellites
    _satellites.clear()

    async with httpx.AsyncClient() as client:
        for url in settings.tle_urls:
            try:
                resp = await client.get(url, timeout=settings.tle_timeout_s)
                resp.raise_for_status()
                _parse_tle_text(resp.text)
            except Exception:
                logger.exception("Failed to fetch TLEs from %s", url)

    logger.info("Loaded %d TLEs", len(_satellites))
    return _satellites


def _parse_tle_text(text: str) -> None:
    """Parse 3-line TLE format and add to the satellite store."""
    lines = text.strip().splitlines()
    for i in range(0, len(lines) - 2, 3):
        name = lines[i].strip()
        line1 = lines[i + 1].strip()
        line2 = lines[i + 2].strip()
        sat = EarthSatellite(line1, line2, name, ts)
        norad_id = int(line2.split()[1])
        _satellites[norad_id] = sat


def get_satellite(norad_id: int) -> EarthSatellite | None:
    return _satellites.get(norad_id)


def compute_position(norad_id: int, at_time: datetime | None = None) -> dict | None:
    """Compute satellite position relative to observer.

    Returns dict with azimuth, elevation, range, velocity, doppler.
    """
    sat = get_satellite(norad_id)
    if sat is None:
        return None

    observer = get_observer()
    t = ts.from_datetime(at_time) if at_time else ts.now()

    difference = sat - observer
    topocentric = difference.at(t)
    alt, az, distance = topocentric.altaz()

    # Compute velocity for Doppler
    t2 = ts.tt_jd(t.tt + 1.0 / 86400)  # 1 second later
    topo2 = difference.at(t2)
    _, _, distance2 = topo2.altaz()
    velocity_km_s = distance2.km - distance.km  # range rate in km/s

    return {
        "azimuth_deg": az.degrees,
        "elevation_deg": alt.degrees,
        "range_km": distance.km,
        "velocity_km_s": velocity_km_s,
    }


def compute_subsatellite_point(norad_id: int, at_time: datetime | None = None) -> dict | None:
    """Compute the sub-satellite point (lat/lon) for a satellite."""
    sat = get_satellite(norad_id)
    if sat is None:
        return None

    t = ts.from_datetime(at_time) if at_time else ts.now()
    geocentric = sat.at(t)
    subpoint = wgs84.subpoint(geocentric)

    return {
        "lat": subpoint.latitude.degrees,
        "lon": subpoint.longitude.degrees,
        "altitude_km": subpoint.elevation.km,
    }


def compute_ground_track(
    norad_id: int,
    minutes_behind: float = 45.0,
    minutes_ahead: float = 45.0,
    num_points: int = 180,
) -> list[dict]:
    """Compute ground track as a series of lat/lon points."""
    sat = get_satellite(norad_id)
    if sat is None:
        return []

    t_now = ts.now()
    total_minutes = minutes_behind + minutes_ahead
    step_minutes = total_minutes / num_points

    points = []
    for i in range(num_points + 1):
        offset_minutes = -minutes_behind + i * step_minutes
        t = ts.tt_jd(t_now.tt + offset_minutes / 1440.0)
        geocentric = sat.at(t)
        subpoint = wgs84.subpoint(geocentric)
        points.append(
            {
                "lat": subpoint.latitude.degrees,
                "lon": subpoint.longitude.degrees,
                "time_offset_min": round(offset_minutes, 1),
            }
        )

    return points


def compute_doppler(velocity_km_s: float, frequency_hz: int) -> float:
    """Compute Doppler shift given range rate and carrier frequency."""
    c = 299_792.458  # km/s
    return -frequency_hz * velocity_km_s / c


def find_passes(
    norad_id: int,
    hours_ahead: float = 24.0,
    min_elevation: float = settings.min_pass_elevation_deg,
) -> list[dict]:
    """Find upcoming passes for a satellite above minimum elevation."""
    sat = get_satellite(norad_id)
    if sat is None:
        return []

    observer = get_observer()
    t0 = ts.now()
    t1 = ts.tt_jd(t0.tt + hours_ahead / 24.0)

    t_events, events = sat.find_events(observer, t0, t1, altitude_degrees=min_elevation)

    passes = []
    current_pass: dict = {}

    for ti, event in zip(t_events, events):
        dt = ti.utc_datetime()
        if event == 0:  # AOS
            current_pass = {"aos": dt, "satellite_id": norad_id}
        elif event == 1:  # Max elevation
            if current_pass:
                pos = compute_position(norad_id, dt)
                current_pass["max_elevation"] = pos["elevation_deg"] if pos else 0.0
        elif event == 2:  # LOS
            if current_pass:
                current_pass["los"] = dt
                passes.append(current_pass)
                current_pass = {}

    return passes


def compute_doppler_curve(
    norad_id: int,
    aos: datetime,
    los: datetime,
    frequency_hz: int,
    num_points: int = 60,
) -> list[dict]:
    """Compute predicted Doppler shift over a pass."""
    sat = get_satellite(norad_id)
    if sat is None:
        return []

    observer = get_observer()
    duration = (los - aos).total_seconds()
    step = duration / num_points

    curve = []
    for i in range(num_points + 1):
        dt = aos + timedelta(seconds=i * step)
        t = ts.from_datetime(dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt)

        t2 = ts.tt_jd(t.tt + 1.0 / 86400)
        diff = sat - observer
        _, _, d1 = diff.at(t).altaz()
        _, _, d2 = diff.at(t2).altaz()

        velocity = d2.km - d1.km
        doppler = compute_doppler(velocity, frequency_hz)
        curve.append({"time": dt.isoformat(), "doppler_hz": doppler})

    return curve
