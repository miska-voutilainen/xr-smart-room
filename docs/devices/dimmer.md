# Light Dimmer - Aqara Dimmer Switch H2

A wall dimmer switch controlling a real lamp. It has a built-in power meter and reaches [Home Assistant](home-assistant.md) through the Aqara Hub M3.

| | |
|---|---|
| Path | Dimmer -> Aqara Hub M3 -> Home Assistant -> bridge |
| Entity | `light.aqara_dimmer_switch_h2` |
| Power | `sensor.aqara_dimmer_switch_h2_power` (W). Energy and current sensors also exist |
| Bridge name | `dimmer1` |
| Level | 0-100%. Home Assistant uses brightness 0-255, and the bridge converts |

## Entities

| Entity | Purpose |
|---|---|
| `light.aqara_dimmer_switch_h2` | On/off and brightness. Used by the bridge |
| `light.switch` | Second entry for the same dimmer. It followed every change in our tests |
| `event.aqara_dimmer_switch_h2_button` | Presses of the physical button |
| `number.aqara_dimmer_switch_h2_on_level` | Level used when switched on |
| `number.aqara_dimmer_switch_h2_power_on_level` | Level after a power loss |
| `select.aqara_dimmer_switch_h2_power_on_behaviour_on_startup` | Behaviour after a power loss (currently "previous") |

## Testing

```
python bridge/lab.py dimmer status         # on/off, level and power
python bridge/lab.py dimmer level 40       # also: on, off, toggle; level 0 turns it off
python bridge/lab.py dimmer watch
```

Each command prints the power two seconds later. A changing power value shows that the real lamp reacted.

## Bridge Server

| Sends to XR | Accepts from XR |
|---|---|
| `on`, `level` (0-100), `power` (W), `status` | `on`, `off`, `toggle`, `set_level` (0-100, 0 = off) |

## Test Results

| Test | Result |
|---|---|
| Level 50% | Works, the lamp drew 3.16 W |
| Level 30%, then off, through `server.py` | Works, power back to 0 W |
| Level 1% | Works, about 1.4 W |
| `light.switch` follows changes | Works |

## Notes

- **Shared device.** The dimmer was on at 1% before our tests. Put it back the way you found it.
- **Power delay.** The power value updates a second or two after the level changes.

## In XR

- **UC2:** a virtual slider dims the lamp and a button toggles it. Send `set_level` at most a few times per second; the dimmer cannot keep up with a command every frame.
- **Two-way sync:** the virtual lamp should take its brightness from the reported `on` and `level`, so the wall switch also updates XR.
- **Information panel:** shows `power`.
- **UC1:** motion switches only the virtual room light, not this dimmer.
