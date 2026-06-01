import asyncio

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect

from satops_backend.schemas import SdrStatus
from satops_backend.services.audio_demod import AUDIO_RATE
from satops_backend.services.band_scan import scan_band
from satops_backend.services.sdr import AUDIO_MODES, sdr_service

# FM broadcast band, IARU Region 1 / ITU.
_FM_BAND_START_HZ = 87_500_000
_FM_BAND_END_HZ = 108_000_000

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


@router.post("/scan")
async def scan(
    start_hz: int = _FM_BAND_START_HZ,
    end_hz: int = _FM_BAND_END_HZ,
    threshold_db: float = 15.0,
) -> dict:
    """Sweep the SDR through ``[start_hz, end_hz]`` and return signal peaks.

    Defaults scan the FM broadcast band. Briefly interrupts live audio because
    the scan retunes the radio at each hop; the previous tune is restored
    before the response is returned.
    """
    stations = await scan_band(
        sdr_service,
        start_hz=start_hz,
        end_hz=end_hz,
        threshold_db=threshold_db,
    )
    return {
        "start_hz": start_hz,
        "end_hz": end_hz,
        "threshold_db": threshold_db,
        "stations": [{"frequency_hz": s.frequency_hz, "power_db": s.power_db, "snr_db": s.snr_db} for s in stations],
    }


@router.post("/audio_mode")
async def set_audio_mode(mode: str) -> dict:
    """Set the FM demodulator mode: off | wfm | nfm."""
    if mode not in AUDIO_MODES:
        raise HTTPException(status_code=400, detail=f"mode must be one of {AUDIO_MODES}")
    sdr_service.set_audio_mode(mode)
    return {"mode": mode, "audio_rate_hz": AUDIO_RATE}


@router.get("/audio_mode")
async def get_audio_mode() -> dict:
    return {"mode": sdr_service.audio_mode, "audio_rate_hz": AUDIO_RATE}


@router.websocket("/audio")
async def audio_stream(ws: WebSocket) -> None:
    """Stream demodulated PCM audio as binary WebSocket frames.

    First message (text) is a JSON header with ``sample_rate`` and ``channels``
    so the browser can configure its AudioContext. Subsequent messages are
    binary frames of little-endian Float32 mono samples at ``sample_rate``.
    Client should ignore frames silently when ``audio_mode`` is "off".
    """
    await ws.accept()
    try:
        await ws.send_json({"type": "audio_header", "sample_rate": AUDIO_RATE, "channels": 1, "format": "float32"})
        while True:
            chunk = await sdr_service.get_audio(timeout=1.0)
            if chunk is None:
                # No audio (mode off, or producer stalled); keep the connection
                # alive by sleeping briefly rather than spamming the WS.
                await asyncio.sleep(0.1)
                continue
            # Binary frame: raw little-endian float32 samples (Web Audio compatible).
            await ws.send_bytes(chunk.astype("<f4").tobytes())
    except WebSocketDisconnect:
        return
    except Exception:  # noqa: BLE001 — log and close cleanly
        import logging

        logging.getLogger(__name__).exception("audio stream error")
        await ws.close()
