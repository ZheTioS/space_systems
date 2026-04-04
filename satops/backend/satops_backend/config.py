from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_prefix": "SATOPS_"}

    # Server
    host: str = "127.0.0.1"
    port: int = 8000
    cors_origins: list[str] = ["http://localhost:5173"]

    # Database
    db_path: str = "satops.db"

    # SDR
    sdr_driver: str = "rtlsdr"
    sdr_frequency_hz: int = 137_100_000  # NOAA 19 default
    sdr_sample_rate: int = 2_048_000
    sdr_gain: float = 40.0
    sdr_fft_size: int = 1024
    sdr_update_rate_hz: float = 10.0
    sdr_queue_size: int = 10

    # TLE
    tle_url: str = "https://celestrak.org/NORAD/elements/gp.php?GROUP=weather&FORMAT=tle"
    tle_timeout_s: float = 30.0

    # Link budget defaults
    tx_power_dbm: float = 37.0  # ~5W typical NOAA
    tx_gain_dbi: float = 5.0
    rx_gain_dbi: float = 3.0
    system_losses_db: float = 2.0
    noise_figure_db: float = 3.5
    bandwidth_hz: float = 34_000.0  # NOAA APT bandwidth

    # Tracking
    min_pass_elevation_deg: float = 5.0
    tracking_elevation_threshold_deg: float = -5.0
    ws_update_interval_s: float = 0.1

    # Observer location (default: Berlin)
    observer_lat: float = 52.52
    observer_lon: float = 13.405
    observer_elev_m: float = 34.0


settings = Settings()
