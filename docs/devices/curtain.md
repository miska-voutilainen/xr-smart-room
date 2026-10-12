# Curtain - Aqara Curtain Driver E1

A battery-powered motor on the wall-mounted curtain rail. It is paired over Zigbee to the lab's Aqara Hub M3, which passes it on to [Home Assistant](home-assistant.md).

| | |
|---|---|
| Path | Curtain -> Zigbee -> Aqara Hub M3 -> Home Assistant -> bridge |
| Entity | `cover.curtain_2` ("Curtain") |
| Battery | `sensor.curtain_battery` (100% when tested) |
| Bridge name | `curtain1` |
| Position | 0 = closed, 100 = open |

## Two Entities, One Curtain

Home Assistant lists the curtain twice. Only one of them moves it.

| Entity | Behaviour |
|---|---|
| `cover.curtain_2` | Moves the real curtain. A full move takes 6-25 seconds. Use this one |
| `cover.aqara_curtain_driver_e1` | Goes from "opening" to "open" in 2-3 seconds without moving anything. Its state does not match the real curtain |

We found this in the Home Assistant logbook and confirmed it by opening the curtain through `cover.curtain_2`.

## Testing

```
python bridge/lab.py curtain status
python bridge/lab.py curtain open          # also: close, stop, position 40
python bridge/lab.py curtain watch         # live position until Ctrl+C
```

After a movement command the script prints the position until the curtain stops. While the curtain moves, the hub sometimes reports a brief wrong state (for example "closed" while opening). The script therefore waits for four identical readings before it treats the curtain as stopped.

## Bridge Server

| Sends to XR | Accepts from XR |
|---|---|
| `position` (0-100), `state` (open, closed, opening, closing), `status` | `open`, `close`, `stop`, `set_position` (0-100) |

## Stop

`cover.curtain_2` only supports open, close and set position. Home Assistant rejects `cover.stop_cover` for it with error 500.

The stop command therefore reads the curtain's current position and sends the curtain to that position, which halts the motor. Curtains that do support stop get a normal `stop_cover`. The code is `curtain_stop()` in `bridge/lab.py`, used by both `lab.py` and `server.py`.

The reported position lags slightly behind the motor, so the curtain may stop a little past the point where stop was pressed.

## Notes

- **Movement updates.** The motor runs on a battery and reports its position while moving and when it stops, not continuously.
- **Shared device.** Other people control the curtain from the Aqara app and Home Assistant too. It moved on its own during our tests.
- **Second shade.** A similar device, the Aqara Roller Shade Driver E1, is `cover.aqara_roller_shade_driver_e1` (battery 65%). It can be tested with `--entity cover.aqara_roller_shade_driver_e1`.

## Test Results

| Test | Result |
|---|---|
| Read position and state | Works |
| Open through `cover.curtain_2` (0 -> 100) | Works, the real curtain moved |
| Close, set position | Not tested yet. Same Home Assistant call as open |
| `stop_cover` | Rejected by Home Assistant (error 500) |
| Stop by holding the current position | Not tested yet. The PC left the lab network before the test |

## In XR

- **UC2:** the user grabs the virtual curtain to open or close it. Send `set_position` once when the grab is released, not every frame.
- **UC3:** the curtains close on a temperature alarm. Not yet wired to the real curtain.
- **Two-way sync:** the virtual curtain should move from the reported `position`, so changes made in the app or on the wall also show in XR.
