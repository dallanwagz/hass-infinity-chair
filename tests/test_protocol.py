"""Unit tests for the chair wire protocol (no Home Assistant needed).

Status frames below are real captures from hardware (see the RE notes / remote catalog).
"""

import pathlib
import sys

sys.path.insert(
    0, str(pathlib.Path(__file__).resolve().parent.parent / "custom_components" / "infinity_chair")
)

import protocol  # noqa: E402


def frame(spaced_hex: str) -> bytes:
    return bytes.fromhex(spaced_hex.replace(" ", ""))


# --- command framing -------------------------------------------------------------------

def test_build_frame_power():
    assert protocol.build_frame(1) == frame("f0 83 01 7b f1")


def test_build_frame_shiatsu():
    assert protocol.build_frame(34) == frame("f0 83 22 5a f1")


def test_build_frame_out_of_range():
    for bad in (-1, 256):
        try:
            protocol.build_frame(bad)
        except ValueError:
            continue
        raise AssertionError(f"expected ValueError for {bad}")


# --- status parsing --------------------------------------------------------------------

def test_parse_idle():
    s = protocol.parse_status(frame("f0 05 03 00 09 30 00 00 2b 00 00 00 03 00 05 0b f1"))
    assert s is not None
    assert s.powered is False
    assert s.running is False


def test_parse_run_states():
    ready = protocol.parse_status(frame("f0 45 03 00 00 00 00 02 2b 00 00 00 03 00 05 02 f1"))
    running = protocol.parse_status(frame("f0 45 27 02 44 57 00 03 2b 00 20 00 41 15 03 4f f1"))
    resetting = protocol.parse_status(frame("f0 6d 05 00 40 00 00 01 28 00 00 00 01 1c 05 02 f1"))
    idle = protocol.parse_status(frame("f0 05 03 00 09 30 00 00 2b 00 00 00 03 00 05 0b f1"))
    assert (ready.run_state, ready.running, ready.powered) == ("ready", False, True)
    assert (running.run_state, running.running) == ("running", True)
    assert resetting.run_state == "resetting"
    assert idle.run_state == "idle"


def test_parse_time_remaining():
    # ((b4 & 0x1F) << 7) | (b5 & 0x7f) while running; high b4 bits are flags
    start = protocol.parse_status(frame("f0 45 27 02 44 57 00 03 2b 00 20 00 41 15 03 4f f1"))
    assert start.time_remaining == 599  # ~10:00 at session start
    # only valid while running -> None when idle/resetting
    idle = protocol.parse_status(frame("f0 05 03 00 09 30 00 00 2b 00 00 00 03 00 05 0b f1"))
    assert idle.time_remaining is None


def test_parse_strength():
    low = protocol.parse_status(frame("f0 4d 0b 00 26 54 00 03 26 00 00 00 03 1c 01 64 f1"))
    high = protocol.parse_status(frame("f0 4d 0a 00 26 30 00 03 20 00 00 00 03 1c 05 0b f1"))
    assert low.strength == 1
    assert high.strength == 5


def test_parse_program():
    # auto programs identified by byte 13 (program # = b13 >> 2)
    recover = protocol.parse_status(frame("f0 4d 29 02 2d 6f 10 03 2b 00 09 00 43 05 03 59 f1"))
    lower = protocol.parse_status(frame("f0 4d 25 02 4d 70 10 03 21 00 00 00 43 19 01 3d f1"))
    idle = protocol.parse_status(frame("f0 05 03 00 09 30 00 00 2b 00 00 00 03 00 05 0b f1"))
    assert recover.program == "recover"
    assert lower.program == "lower_body"
    assert idle.program is None  # b13 = 00 -> no active program


def test_zero_gravity_command():
    assert protocol.COMMANDS["zero_gravity"] == 112
    assert protocol.build_frame(112) == frame("f0 83 70 0c f1")


def test_session_length_commands():
    assert protocol.COMMANDS["session_10min"] == 80
    assert protocol.COMMANDS["session_20min"] == 81
    assert protocol.COMMANDS["session_30min"] == 82


def test_parse_airbag_strength():
    # byte 3 low bits = airbag strength (0 off, 1-5)
    f1 = protocol.parse_status(frame("f0 4d 09 01 26 44 00 03 29 00 00 00 23 1c 01 52 f1"))
    f5 = protocol.parse_status(frame("f0 4d 0b 05 26 18 04 03 28 00 00 00 23 1c 01 75 f1"))
    off = protocol.parse_status(frame("f0 4d 0a 00 25 5a 00 03 26 00 00 00 03 1c 01 60 f1"))
    assert f1.airbag_strength == 1
    assert f5.airbag_strength == 5
    assert off.airbag_strength == 0


def test_parse_ionizer():
    # byte 3 bit 0x40 = ionizer; low bits stay = airbag strength
    on = protocol.parse_status(frame("f0 55 35 42 48 4a 63 03 20 00 00 00 43 19 01 3e f1"))
    off = protocol.parse_status(frame("f0 55 29 02 48 6d 03 23 22 00 00 00 43 19 01 25 f1"))
    assert on.ionizer is True
    assert off.ionizer is False
    assert on.airbag_strength == 2  # ionizer bit doesn't corrupt the strength read


def test_parse_heat():
    on = protocol.parse_status(frame("f0 45 78 02 2d 76 73 03 28 40 09 00 43 1d 01 55 f1"))
    off = protocol.parse_status(frame("f0 45 38 02 2d 72 70 03 29 40 09 00 43 1d 01 1b f1"))
    assert on.heat is True
    assert off.heat is False


def test_parse_airbag_zones():
    # one zone on at a time -> exactly one airbag flag set (byte 12 bitmask)
    arm = protocol.parse_status(frame("f0 4d 09 02 23 33 00 03 25 00 00 00 13 1c 05 75 f1"))
    back = protocol.parse_status(frame("f0 4d 0a 02 23 05 00 23 22 00 00 00 0b 1c 05 0d f1"))
    leg = protocol.parse_status(frame("f0 4d 0a 02 22 54 01 03 21 00 00 00 07 1c 05 63 f1"))
    butt = protocol.parse_status(frame("f0 4d 09 02 22 2b 04 03 23 00 00 00 23 1c 05 6c f1"))

    def zones(s):
        return (s.airbag_arm_shoulder, s.airbag_back_waist, s.airbag_leg_foot, s.airbag_buttock)

    assert zones(arm) == (True, False, False, False)
    assert zones(back) == (False, True, False, False)
    assert zones(leg) == (False, False, True, False)
    assert zones(butt) == (False, False, False, True)


def test_parse_technique():
    # MODE / manual technique lives in b1 bits 3..5: (b1 >> 3) & 0x07
    kneading = protocol.parse_status(frame("f0 4d 0d 00 63 64 00 03 21 00 00 00 03 1c 03 18 f1"))
    knocking = protocol.parse_status(frame("f0 55 0d 00 61 70 00 03 21 00 00 00 03 1c 03 06 f1"))
    sync = protocol.parse_status(frame("f0 5d 09 00 2d 12 00 03 25 00 00 00 03 1c 03 10 f1"))
    tapping = protocol.parse_status(frame("f0 65 1a 00 2c 6f 00 03 25 00 00 00 03 1c 03 1b f1"))
    shiatsu = protocol.parse_status(frame("f0 6d 0a 00 2d 58 00 03 23 00 00 00 03 1c 03 3b f1"))
    assert kneading.technique == "kneading"
    assert knocking.technique == "knocking"
    assert sync.technique == "sync"
    assert tapping.technique == "tapping"
    assert shiatsu.technique == "shiatsu"


def test_parse_3d_program():
    # 3D presets (3D-1/2/3) all report b13 = 0x2d -> "3d"
    s = protocol.parse_status(frame("f0 45 26 02 24 0d 10 03 28 00 00 00 43 2d 0d 29 f1"))
    assert s.program == "3d"


def test_parse_speed_and_width():
    s6 = protocol.parse_status(frame("f0 65 1a 00 2c 6f 00 03 25 00 00 00 03 1c 03 1b f1"))
    narrow = protocol.parse_status(frame("f0 65 0d 00 2b 3b 00 03 24 00 00 00 03 1c 03 5d f1"))
    wide = protocol.parse_status(frame("f0 65 0f 00 2a 6e 00 03 26 00 00 00 03 1c 03 28 f1"))
    assert (s6.speed, s6.width) == (6, "medium")
    assert (narrow.speed, narrow.width) == (3, "narrow")
    assert wide.width == "wide"


def test_parse_foot_roller():
    off = protocol.parse_status(frame("f0 65 1a 00 2c 6f 00 03 25 00 00 00 03 1c 03 1b f1"))
    lvl3 = protocol.parse_status(frame("f0 65 2d 00 28 24 60 03 26 00 00 00 03 1d 03 75 f1"))
    assert off.foot_roller == 0
    assert lvl3.foot_roller == 3


def test_parse_part():
    whole = protocol.parse_status(frame("f0 65 0d 00 26 29 00 03 28 00 00 00 03 1c 03 71 f1"))
    partial = protocol.parse_status(frame("f0 65 0d 00 46 09 00 03 20 00 00 00 03 1c 03 79 f1"))
    point = protocol.parse_status(frame("f0 65 0d 00 65 5a 00 03 21 00 00 00 03 1c 03 08 f1"))
    assert (whole.part, partial.part, point.part) == ("whole", "partial", "point")


def test_parse_zero_gravity():
    on = protocol.parse_status(frame("f0 65 0d 00 65 0a 00 03 21 00 40 00 03 1c 03 18 f1"))
    off = protocol.parse_status(frame("f0 65 0d 00 65 5a 00 03 21 00 00 00 03 1c 03 08 f1"))
    assert on.zero_gravity is True
    assert off.zero_gravity is False


def test_parse_roller_position():
    top = protocol.parse_status(frame("f0 4d 06 00 62 68 00 03 2c 00 00 00 01 1c 05 11 f1"))
    bottom = protocol.parse_status(frame("f0 4d 19 00 61 29 00 03 20 00 00 00 01 1c 03 4c f1"))
    assert top.roller_position == 100  # b8 = 0x2c (neck)
    assert bottom.roller_position == 0  # b8 = 0x20 (waist)
    # not surfaced while idle
    idle = protocol.parse_status(frame("f0 05 03 00 09 30 00 00 2b 00 00 00 03 00 05 0b f1"))
    assert idle.roller_position is None


def test_parse_rejects_bad_frames():
    assert protocol.parse_status(b"\x00\x01\x02") is None  # too short
    assert protocol.parse_status(bytes(17)) is None  # no F0/F1 markers
