from datetime import datetime

from pydantic import BaseModel

# --- Satellite ---


class SatelliteBase(BaseModel):
    name: str
    norad_id: int
    frequency_hz: int


class Satellite(SatelliteBase):
    id: int


# --- Pass ---


class PassBase(BaseModel):
    satellite_id: int
    aos: datetime
    los: datetime
    max_elevation: float


class Pass(PassBase):
    id: int


# --- Observation ---


class ObservationBase(BaseModel):
    pass_id: int
    start_time: datetime
    end_time: datetime
    peak_signal: float | None = None
    avg_snr: float | None = None
    notes: str | None = None


class Observation(ObservationBase):
    id: int


# --- WebSocket events ---


class SignalUpdate(BaseModel):
    type: str = "signal_update"
    timestamp: datetime
    satellite: str
    frequency_hz: int
    doppler_hz: float
    azimuth_deg: float
    elevation_deg: float
    range_km: float
    snr_db: float | None = None


class SpectrumUpdate(BaseModel):
    type: str = "spectrum_update"
    timestamp: datetime
    center_frequency_hz: int
    bandwidth_hz: float
    magnitudes_db: list[float]


class TrackingUpdate(BaseModel):
    type: str = "tracking_update"
    timestamp: datetime
    satellite: str
    azimuth_deg: float
    elevation_deg: float
    range_km: float
    velocity_km_s: float
    doppler_hz: float


class LinkBudgetResult(BaseModel):
    type: str = "link_budget"
    timestamp: datetime
    fspl_db: float
    received_power_dbm: float
    noise_power_dbm: float
    snr_db: float


# --- SDR Status ---


class SdrStatus(BaseModel):
    connected: bool
    mode: str = "synthetic"  # "hardware" | "synthetic"
    driver: str | None = None
    frequency_hz: int | None = None
    sample_rate: int | None = None
    gain: float | None = None
