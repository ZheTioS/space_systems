from fastapi import APIRouter

from satops_backend.schemas import SdrStatus
from satops_backend.services.sdr import sdr_service

router = APIRouter(prefix="/sdr", tags=["sdr"])


@router.get("/status")
async def get_status() -> SdrStatus:
    return sdr_service.status


@router.post("/connect")
async def connect() -> SdrStatus:
    await sdr_service.connect()
    await sdr_service.start_streaming()
    return sdr_service.status


@router.post("/disconnect")
async def disconnect() -> SdrStatus:
    await sdr_service.disconnect()
    return sdr_service.status


@router.post("/frequency")
async def set_frequency(frequency_hz: int) -> SdrStatus:
    await sdr_service.set_frequency(frequency_hz)
    return sdr_service.status


@router.post("/gain")
async def set_gain(gain: float) -> SdrStatus:
    await sdr_service.set_gain(gain)
    return sdr_service.status
