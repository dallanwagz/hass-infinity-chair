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
# manual techniques only take effect while the chair is already running. Zero gravity, power and
# the pad-move commands work even while idle.
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
    "zero_gravity": 112,
}

# Active-program identity, decoded from status byte 13 (program number = b13 >> 2).
_PROGRAM_NAMES: dict[int, str] = {
    0x05: "recover",
    0x09: "stretch",
    0x0D: "relax",
    0x11: "pain_recovery",
    0x15: "upper_body",
    0x19: "lower_body",
    0x1C: "manual",
    0x1D: "manual",
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

    Fields below were validated byte-by-byte against hardware. The remaining bytes of the 17-byte
    frame (roller position, program timer, technique sub-params) aren't surfaced yet; ``raw`` carries
    the full frame as hex for diagnostics and further reverse-engineering.

    Byte map (frame = F0 b1..b15 F1):
      b1  bit 0x40 -> powered
      b2  bit 0x40 -> heat on
      b3  low bits (& 0x07) -> airbag strength (0 off, 1..5); bit 0x40 -> ionizer on
      b7           -> run state (0 off, non-zero running)
      b12 bits     -> airbag zones: 0x10 arm&shoulder, 0x08 back&waist, 0x04 leg&foot, 0x20 buttock
                      (0x40 = back/roller massage active, not an airbag zone)
      b13          -> active program (see _PROGRAM_NAMES; program # = b13 >> 2)
      b14          -> 3D strength level (1..5; set by the 3D button or the menu "strength")
    """

    powered: bool
    running: bool
    program: str | None
    heat: bool
    ionizer: bool
    strength: int
    airbag_strength: int
    airbag_arm_shoulder: bool
    airbag_back_waist: bool
    airbag_leg_foot: bool
    airbag_buttock: bool
    raw: str


def parse_status(data: bytes) -> ChairState | None:
    """Parse a status notification frame, or None if it isn't a valid 17-byte F0..F1 frame."""
    if len(data) != 17 or data[0] != _SOI or data[-1] != _EOI:
        return None
    airbag = data[12]
    return ChairState(
        powered=bool(data[1] & 0x40),
        running=data[7] != 0,
        program=_PROGRAM_NAMES.get(data[13]),
        heat=bool(data[2] & 0x40),
        ionizer=bool(data[3] & 0x40),
        strength=data[14],
        airbag_strength=data[3] & 0x07,
        airbag_arm_shoulder=bool(airbag & 0x10),
        airbag_back_waist=bool(airbag & 0x08),
        airbag_leg_foot=bool(airbag & 0x04),
        airbag_buttock=bool(airbag & 0x20),
        raw=data.hex(),
    )
