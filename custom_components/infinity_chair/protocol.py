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
    "session_10min": 80,
    "session_20min": 81,
    "session_30min": 82,
}

# Run state, decoded from status byte 7.
_RUN_STATES: dict[int, str] = {
    0: "idle",
    1: "resetting",
    2: "ready",
    3: "running",
}

# Manual technique/MODE, decoded from b1 bits 3..5: (b1 >> 3) & 0x07.
_TECHNIQUES: dict[int, str] = {
    1: "kneading",
    2: "knocking",
    3: "sync",
    4: "tapping",
    5: "shiatsu",
}

# Manual roller width (b2 & 0x03) and massage part/scope (b4 >> 5).
_WIDTHS: dict[int, str] = {1: "narrow", 2: "medium", 3: "wide"}
_PARTS: dict[int, str] = {1: "whole", 2: "partial", 3: "point"}

# Roller vertical position (byte 8): measured travel from waist to neck.
_ROLLER_MIN = 0x20  # bottom / lower back (waist)
_ROLLER_MAX = 0x2C  # top / neck

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
    0x2D: "3d",  # any 3D preset (3D-1/2/3 are not individually distinguished in the status)
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
      b1  bit 0x40 -> powered; bits 3..5 ((b1>>3)&7) -> technique/MODE (see _TECHNIQUES)
      b2  bit 0x40 -> heat; bits 2..4 -> manual speed (1..6); bits 0..1 -> roller width
      b3  low bits (& 0x07) -> airbag strength (0 off, 1..5); bit 0x40 -> ionizer on
      b4  high bits (>> 5) -> massage part/scope (1 whole, 2 partial, 3 point)
      b4/b5 -> time remaining: ((b4 & 0x1F) << 7) | (b5 & 0x7f) seconds (only meaningful while running)
      b6  high bits (>> 5) -> foot-roller level (0 off, 1..3)
      b7           -> run state (0 idle, 1 resetting, 2 ready, 3 running)
      b8           -> roller vertical position (0x20 waist .. 0x2c neck)
      b10 bit 0x40 -> zero gravity engaged
      b12 bits     -> airbag zones: 0x10 arm&shoulder, 0x08 back&waist, 0x04 leg&foot, 0x20 buttock
                      (0x40 = back/roller massage active, not an airbag zone)
      b13          -> active program (see _PROGRAM_NAMES; program # = b13 >> 2)
      b14          -> 3D strength level (1..5; set by the 3D button or the menu "strength")

    NOTE: manual technique (MODE) is not reported — kneading/tapping produce identical frames.
    The roller-position / speed / width fields are live readings (they reflect motion in some
    techniques), so they're only surfaced while a program is running.
    """

    powered: bool
    running: bool
    run_state: str | None
    program: str | None
    technique: str | None
    heat: bool
    ionizer: bool
    strength: int
    airbag_strength: int
    time_remaining: int | None
    roller_position: int | None
    speed: int | None
    width: str | None
    foot_roller: int
    part: str | None
    zero_gravity: bool
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
    run = data[7]
    running = run == 3
    # These live in bytes that hold defaults/garbage while idle, so only surface them while running.
    time_remaining = (((data[4] & 0x1F) << 7) | (data[5] & 0x7F)) if running else None
    speed = ((data[2] >> 2) & 0x07) if running else None
    width = _WIDTHS.get(data[2] & 0x03) if running else None
    if running:
        span = _ROLLER_MAX - _ROLLER_MIN
        roller_position = max(0, min(100, round((data[8] - _ROLLER_MIN) * 100 / span)))
    else:
        roller_position = None
    return ChairState(
        powered=bool(data[1] & 0x40),
        running=running,
        run_state=_RUN_STATES.get(run),
        program=_PROGRAM_NAMES.get(data[13]),
        technique=_TECHNIQUES.get((data[1] >> 3) & 0x07),
        heat=bool(data[2] & 0x40),
        ionizer=bool(data[3] & 0x40),
        strength=data[14],
        airbag_strength=data[3] & 0x07,
        time_remaining=time_remaining,
        roller_position=roller_position,
        speed=speed,
        width=width,
        foot_roller=data[6] >> 5,
        part=_PARTS.get(data[4] >> 5),
        zero_gravity=bool(data[10] & 0x40),
        airbag_arm_shoulder=bool(airbag & 0x10),
        airbag_back_waist=bool(airbag & 0x08),
        airbag_leg_foot=bool(airbag & 0x04),
        airbag_buttock=bool(airbag & 0x20),
        raw=data.hex(),
    )
