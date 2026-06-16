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


def test_parse_powered_running():
    s = protocol.parse_status(frame("f0 45 03 00 00 00 00 02 2b 00 00 00 03 00 05 02 f1"))
    assert s.powered is True
    assert s.running is True


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


def test_parse_rejects_bad_frames():
    assert protocol.parse_status(b"\x00\x01\x02") is None  # too short
    assert protocol.parse_status(bytes(17)) is None  # no F0/F1 markers
