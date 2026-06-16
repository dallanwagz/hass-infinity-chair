# Infinity / Rongtai Massage Chair — Home Assistant integration

Control Infinity / Rongtai massage chairs (BLE name `EVOLUTION-0xxxxx`) from Home Assistant over
Bluetooth LE — using your **existing ESPHome / Shelly Bluetooth proxies**. No dedicated hardware
next to the chair.

Home Assistant connects to the chair through whichever Bluetooth proxy is in range (active
connections), sends the vendor's command frames, and reads the chair's status notifications.

## Features

- **Command buttons**: Power, the four Auto programs and two body-zone programs, and the manual
  techniques (Knead, Knock, Shiatsu, Tap, Knead+Knock, Heat, Airbag auto).
- **Decoded status sensors**: **Running**, **Heat**, **Intensity** (1–5), and an airbag binary
  sensor per zone (**arm & shoulder**, **back & waist**, **leg & foot**, **buttock**).
- **Connected** diagnostic sensor, plus **Program code** / **Raw status** diagnostics.
- Bluetooth auto-discovery — the chair shows up to be added once a proxy sees it.

## Requirements

- Home Assistant 2024.12+.
- At least one Bluetooth proxy (ESPHome `bluetooth_proxy` with active connections — the default —
  or a built-in adapter) within range of the chair.
- The vendor app **disconnected** from the chair: these chairs accept only one BLE central at a
  time, so the iOS/Android app will fight Home Assistant for the connection if left connected.

## Installation (HACS)

1. HACS → Integrations → ⋮ → Custom repositories → add this repo as an **Integration**.
2. Install "Infinity Massage Chair" and restart Home Assistant.
3. Settings → Devices & Services. The chair should appear as a discovered Bluetooth device — click
   **Add**. (Or add it manually via **+ Add Integration → Infinity Massage Chair**.)

## How it works

The vendor's iOS app controls the chair over BLE GATT (the Android app's Bluetooth Classic SPP path
does not work on the hardware tested). The wire protocol:

```
command  -> write to 0xFFF1:                 F0 83 <messageId> <checksum> F1
checksum =  (~(0x83 + messageId)) & 0x7F
status   <- notify on 0734594a-...:          17-byte  F0 <...> F1  frames
```

Power is a toggle (also stops a running program). Manual techniques (Knead, Shiatsu, …) only take
effect once the chair is running — press **Power** first if it's idle.

### Status decoding

The 17-byte status frame (`F0 b1..b15 F1`), reverse-engineered byte-by-byte against hardware:

| Byte | Meaning |
|---|---|
| 1 | bit `0x40` = powered on |
| 2 | bit `0x40` = heat on (low nibble cycles with roller phase) |
| 7 | run state (0 = idle, non-zero = running) |
| 12 | airbag-zone bitmask: `0x10` arm&shoulder, `0x08` back&waist, `0x04` leg&foot, `0x20` buttock (`0x40` = back/roller massage active) |
| 14 | intensity / strength level (1–5) |
| 15 | checksum |

Still unmapped: roller position (b8), program timer (b4:b5), 3D depth, specific auto-program
identity, and bytes b6/b10/b11/b13. The **Raw status** diagnostic sensor exposes the full frame for
anyone extending the decode. Note: seat/back/legrest **positions are command-only** — the chair
moves on command but does not report the resulting angle.

## Development

The wire protocol lives in `protocol.py` with no Home Assistant dependencies and is unit-tested:

```bash
pytest tests/
```

## License

MIT — see [LICENSE](LICENSE).
