"""APRS info-field parser (subset).

Implements the common DTIs (data type identifiers):
    !  =  position without timestamp
    /  @  position with timestamp
    >    status
    :    message
Anything else surfaces as ``{"type": "unknown", "dti": ..., "raw": ...}``.

Reference: APRS Protocol Reference v1.0.1 (Bob Bruninga WB4APR, 2000).
"""

from dataclasses import dataclass


@dataclass
class Position:
    latitude_deg: float
    longitude_deg: float
    symbol_table: str
    symbol_code: str
    comment: str = ""


def parse_info(info: bytes) -> dict | None:
    """Parse an APRS info field into a structured dict.

    Returns None for an empty field. Unrecognised DTIs return a generic
    ``{"type": "unknown", ...}`` payload so callers can still log them.
    """
    if not info:
        return None
    dti = chr(info[0])

    if dti in "!=":
        return _parse_position(info[1:], dti)
    if dti in "/@":
        if len(info) < 8:
            return _unknown(dti, info)
        return _parse_position(info[8:], dti, timestamp_raw=info[1:8])
    if dti == ">":
        return {"type": "status", "text": _ascii(info[1:])}
    if dti == ":":
        if len(info) < 11:
            return _unknown(dti, info)
        addressee = _ascii(info[1:10]).strip()
        text = _ascii(info[11:])
        return {"type": "message", "addressee": addressee, "text": text}

    return _unknown(dti, info)


def _parse_position(payload: bytes, dti: str, timestamp_raw: bytes | None = None) -> dict | None:
    if len(payload) < 19:
        return _unknown(dti, payload)
    try:
        lat = _parse_lat(payload[0:8].decode("ascii"))
        lon = _parse_lon(payload[9:18].decode("ascii"))
    except (ValueError, UnicodeDecodeError):
        return _unknown(dti, payload)

    result = {
        "type": "position",
        "dti": dti,
        "latitude_deg": lat,
        "longitude_deg": lon,
        "symbol_table": chr(payload[8]),
        "symbol_code": chr(payload[18]),
        "comment": _ascii(payload[19:]),
    }
    if timestamp_raw is not None:
        result["timestamp_raw"] = _ascii(timestamp_raw)
    return result


def _parse_lat(s: str) -> float:
    if len(s) != 8 or s[7] not in "NS" or s[4] != ".":
        raise ValueError(f"Bad APRS latitude: {s!r}")
    deg = int(s[0:2])
    minutes = float(s[2:7])
    val = deg + minutes / 60.0
    return -val if s[7] == "S" else val


def _parse_lon(s: str) -> float:
    if len(s) != 9 or s[8] not in "EW" or s[5] != ".":
        raise ValueError(f"Bad APRS longitude: {s!r}")
    deg = int(s[0:3])
    minutes = float(s[3:8])
    val = deg + minutes / 60.0
    return -val if s[8] == "W" else val


def _ascii(b: bytes) -> str:
    return b.decode("ascii", errors="replace")


def _unknown(dti: str, payload: bytes) -> dict:
    return {"type": "unknown", "dti": dti, "raw": _ascii(payload)}
