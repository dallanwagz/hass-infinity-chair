"""Wire protocol for Infinity / Rongtai massage chairs (BLE GATT).

Pure logic, no Home Assistant or BLE-stack dependencies, so it can be unit-tested standalone.

GATT layout (vendor service 0xFFF0):
  command  -> write to 0xFFF1:  F0 83 <messageId> <checksum> F1
  checksum =  (~(0x83 + messageId)) & 0x7F
  status   <- notify on 0734594a-a8e7-4b1a-a6b1-cd5243059a57:  17-byte  F0 <...> F1  frames
"""

from __future__ import annotations

from dataclasses import dataclass

# Characteristic UUIDs (full 128-bit form, as bleak expects).
COMMAND_CHAR_UUID = "0000fff1-0000-1000-8000-00805f9b34fb"
STATUS_CHAR_UUID = "0734594a-a8e7-4b1a-a6b1-cd5243059a57"

# Frame markers.
_SOI = 0xF0  # start of frame
_EOI = 0xF1  # end of frame
_VOI = 0x83  # command type byte

# Command catalog: friendly name -> messageId. Power is a toggle (also stops a running program);
# manual techniques only take effect while the chair is already running.
COMMANDS: dict[str, int] = {
    "power": 1,
    "auto_recover": 16,
    "auto_stretch": 17,
    "auto_relax": 18,
    "auto_pain_recovery": 19,
    "auto_upper_body": 20,
    "auto_lower_body": 21,
    "knead": 32,
    "knock": 33,
    "shiatsu": 34,
    "tap": 35,
    "knead_knock": 36,
    "heat": 39,
    "airbag_auto": 68,
}


def build_frame(message_id: int) -> bytes:
    """Build the 5-byte command frame for a messageId."""
    if not 0 <= message_id <= 0xFF:
        raise ValueError(f"message_id out of range: {message_id}")
    checksum = (~(_VOI + message_id)) & 0x7F
    return bytes([_SOI, _VOI, message_id, checksum, _EOI])


@dataclass(frozen=True)
class ChairState:
    """Decoded chair status.

    Only the fields validated against hardware are exposed; the remaining bytes of the 17-byte
    status frame map to the vendor app's status struct and are not yet decoded. ``raw`` carries the
    full frame as hex for diagnostics and further reverse-engineering.
    """

    powered: bool
    running: bool
    program: int
    raw: str


def parse_status(data: bytes) -> ChairState | None:
    """Parse a status notification frame, or None if it isn't a valid 17-byte F0..F1 frame."""
    if len(data) != 17 or data[0] != _SOI or data[-1] != _EOI:
        return None
    return ChairState(
        powered=bool(data[1] & 0x40),
        running=data[7] != 0,
        program=data[2],
        raw=data.hex(),
    )
