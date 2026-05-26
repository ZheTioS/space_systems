"""AX.25 v2.2 frame: address field, control, PID, info.

Each address byte in the address field is shifted left by 1 bit; the LSB of
each byte carries control flags (the last address byte's LSB marks end-of-field).
"""

from dataclasses import dataclass, field

UI_CONTROL = 0x03
NO_LAYER3_PID = 0xF0


@dataclass
class Address:
    callsign: str  # 1..6 chars, A-Z 0-9
    ssid: int = 0  # 0..15
    has_been_repeated: bool = False
    command_or_response: bool = False  # C bit (dest) / H bit semantics vary by position

    def encode(self, end_of_field: bool = False) -> bytes:
        call = self.callsign.upper().ljust(6, " ")
        if len(call) != 6:
            raise ValueError(f"Callsign must be ≤6 chars: {self.callsign!r}")
        out = bytearray(c << 1 for c in call.encode("ascii"))
        ssid_byte = 0b01100000 | ((self.ssid & 0x0F) << 1)
        if self.has_been_repeated:
            ssid_byte |= 0x80
        if self.command_or_response:
            ssid_byte |= 0x80
        if end_of_field:
            ssid_byte |= 0x01
        out.append(ssid_byte)
        return bytes(out)

    @classmethod
    def decode(cls, b: bytes) -> tuple["Address", bool]:
        """Return (address, is_end_of_field)."""
        if len(b) != 7:
            raise ValueError("Address must be 7 bytes")
        call = "".join(chr(c >> 1) for c in b[:6]).rstrip(" ")
        ssid_byte = b[6]
        return (
            cls(
                callsign=call,
                ssid=(ssid_byte >> 1) & 0x0F,
                has_been_repeated=bool(ssid_byte & 0x80),
            ),
            bool(ssid_byte & 0x01),
        )

    def __str__(self) -> str:
        s = f"{self.callsign}-{self.ssid}" if self.ssid else self.callsign
        return s + ("*" if self.has_been_repeated else "")


@dataclass
class Ax25Frame:
    destination: Address
    source: Address
    path: list[Address] = field(default_factory=list)
    control: int = UI_CONTROL
    pid: int | None = NO_LAYER3_PID
    info: bytes = b""

    def encode(self) -> bytes:
        addrs = [self.destination, self.source, *self.path]
        out = bytearray()
        for i, a in enumerate(addrs):
            out += a.encode(end_of_field=(i == len(addrs) - 1))
        out.append(self.control)
        if self.pid is not None:
            out.append(self.pid)
        out += self.info
        return bytes(out)

    @classmethod
    def decode(cls, frame: bytes) -> "Ax25Frame":
        if len(frame) < 15:
            raise ValueError(f"AX.25 frame too short: {len(frame)} bytes")

        dest, end = Address.decode(frame[0:7])
        if end:
            raise ValueError("Destination address marked as end-of-field")
        src, end = Address.decode(frame[7:14])

        path: list[Address] = []
        i = 14
        while not end:
            if i + 7 > len(frame):
                raise ValueError("Truncated digipeater path")
            addr, end = Address.decode(frame[i : i + 7])
            path.append(addr)
            i += 7

        if i >= len(frame):
            raise ValueError("Missing control byte")
        control = frame[i]
        i += 1

        pid: int | None = None
        if control == UI_CONTROL:
            if i >= len(frame):
                raise ValueError("UI frame missing PID byte")
            pid = frame[i]
            i += 1

        return cls(
            destination=dest,
            source=src,
            path=path,
            control=control,
            pid=pid,
            info=frame[i:],
        )

    def header_str(self) -> str:
        """Standard TNC-2 monitor format: SRC>DEST[,PATH]."""
        parts = [str(self.source), ">", str(self.destination)]
        for p in self.path:
            parts.append(",")
            parts.append(str(p))
        return "".join(parts)
