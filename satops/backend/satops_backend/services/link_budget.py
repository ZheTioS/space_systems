"""Link budget computation service."""

import math
from dataclasses import dataclass

from satops_backend.config import settings


@dataclass
class LinkBudgetInput:
    frequency_hz: float
    range_km: float
    tx_power_dbm: float = settings.tx_power_dbm
    tx_gain_dbi: float = settings.tx_gain_dbi
    rx_gain_dbi: float = settings.rx_gain_dbi
    system_losses_db: float = settings.system_losses_db
    noise_figure_db: float = settings.noise_figure_db
    bandwidth_hz: float = settings.bandwidth_hz


@dataclass
class LinkBudgetOutput:
    fspl_db: float
    received_power_dbm: float
    noise_power_dbm: float
    snr_db: float


def compute_fspl(distance_km: float, frequency_hz: float) -> float:
    """Free-space path loss in dB.

    FSPL = 20*log10(d_km) + 20*log10(f_GHz) + 92.45
    """
    frequency_ghz = frequency_hz / 1e9
    return 20 * math.log10(distance_km) + 20 * math.log10(frequency_ghz) + 92.45


def compute_noise_power(noise_figure_db: float, bandwidth_hz: float) -> float:
    """Noise power in dBm.

    N = -174 + 10*log10(BW) + NF
    """
    return -174.0 + 10 * math.log10(bandwidth_hz) + noise_figure_db


def compute_link_budget(params: LinkBudgetInput) -> LinkBudgetOutput:
    """Compute full link budget."""
    fspl = compute_fspl(params.range_km, params.frequency_hz)

    received_power = params.tx_power_dbm + params.tx_gain_dbi + params.rx_gain_dbi - fspl - params.system_losses_db

    noise_power = compute_noise_power(params.noise_figure_db, params.bandwidth_hz)
    snr = received_power - noise_power

    return LinkBudgetOutput(
        fspl_db=round(fspl, 2),
        received_power_dbm=round(received_power, 2),
        noise_power_dbm=round(noise_power, 2),
        snr_db=round(snr, 2),
    )
