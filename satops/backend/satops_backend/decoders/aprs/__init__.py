"""APRS (Automatic Packet Reporting System) decoder.

Implements the receive chain for 1200 baud AFSK packet radio (Bell 202) as used
by the ISS APRS digipeater and terrestrial APRS networks: AFSK demod, NRZI,
HDLC bit-destuff, CRC-16-CCITT, AX.25 frame parse, APRS info parse.

CLI: ``python -m satops_backend.decoders.aprs path/to/audio.wav``
"""

from satops_backend.decoders.aprs.aprs import parse_info
from satops_backend.decoders.aprs.audio import demodulate, modulate, read_wav, write_wav
from satops_backend.decoders.aprs.ax25 import Address, Ax25Frame
from satops_backend.decoders.aprs.hdlc import crc16_ccitt, hdlc_decode, hdlc_encode

__all__ = [
    "Address",
    "Ax25Frame",
    "crc16_ccitt",
    "demodulate",
    "hdlc_decode",
    "hdlc_encode",
    "modulate",
    "parse_info",
    "read_wav",
    "write_wav",
]
