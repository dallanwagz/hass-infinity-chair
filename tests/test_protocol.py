"""Unit tests for the chair wire protocol (no Home Assistant needed)."""

import pathlib
import sys

sys.path.insert(
    0, str(pathlib.Path(__file__).resolve().parent.parent / "custom_components" / "infinity_chair")
)

import protocol  # noqa: E402


def test_build_frame_power():
    # F0 83 01 7B F1 — checksum = (~(0x83+1)) & 0x7F
    assert protocol.build_frame(1) == bytes.fromhex("f083017bf1")


def test_build_frame_shiatsu():
    # F0 83 22 5A F1 (messageId 34)
    assert protocol.build_frame(34) == bytes.fromhex("f083225af1")


def test_build_frame_out_of_range():
    for bad in (-1, 256):
        try:
            protocol.build_frame(bad)
        except ValueError:
            continue
        raise AssertionError(f"expected ValueError for {bad}")


def test_parse_idle():
    state = protocol.parse_status(bytes.fromhex("f0050300093000002b0000000300050bf1"))
    assert state is not None
    assert state.powered is False
    assert state.running is False
    assert state.program == 0x03


def test_parse_powered():
    state = protocol.parse_status(bytes.fromhex("f0450300000000022b00000003000502f1"))
    assert state is not None
    assert state.powered is True
    assert state.running is True
    assert state.program == 0x03


def test_parse_shiatsu_running():
    state = protocol.parse_status(bytes.fromhex("f0451b002e0700032b400000031c0558f1"))
    assert state is not None
    assert state.powered is True
    assert state.running is True
    assert state.program == 0x1B


def test_parse_rejects_bad_frames():
    assert protocol.parse_status(b"\x00\x01\x02") is None  # too short
    assert protocol.parse_status(bytes(17)) is None  # no F0/F1 markers
