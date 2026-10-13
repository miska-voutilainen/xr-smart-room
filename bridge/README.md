# Bridge - Data-Exchange Layer

This folder is the data-exchange layer from [concept.md](../concept.md). It talks to the real devices in the lab and gives the XR application one simple message format.

- `lab.py`: test any lab device from the command line. Also holds the lab configuration and the clients that `server.py` uses.
- `server.py`: the bridge server the XR app connects to.

Status on 13.10.2026: all devices can be read, the curtain, dimmer and speaker can also be controlled, and the server has been tested against the real lab. `lab.py` can also switch and dim the DALI lamps, but on 13.10.2026 only commands to all lamps reached them (see open issue 1). Unity is still a concept; section 5 describes how it will connect.

Device details (addresses, entities, test results) are in [docs/](../docs/README.md).

## 1. Setup

1. Install Python 3.10 or newer (tested with 3.14), then run `pip install -r bridge/requirements.txt`. This installs `websockets` for the server and `xknx` for the KNX commands; everything else is in the standard library.
2. Create `bridge/.env` with the Home Assistant token. The file is git-ignored:
   ```
   HA_TOKEN=<long-lived access token>
   ```
   See [home-assistant.md](../docs/devices/home-assistant.md) for how to create the token.
3. Connect to the lab Wi-Fi. When Windows Firewall asks, allow Python on private networks. The server listens on ports 8765 and 8000, and BACnet replies arrive on UDP 47808.

## 2. Testing Devices - lab.py

Run from the project root. `check` reads every device once and changes nothing:

```
python bridge/lab.py check
```

| Device | Commands | Page |
|---|---|---|
| `curtain` | `status`, `watch`, `open`, `close`, `stop`, `position 0-100` | [curtain.md](../docs/devices/curtain.md) |
| `dimmer` | `status`, `watch`, `on`, `off`, `toggle`, `level 0-100` | [dimmer.md](../docs/devices/dimmer.md) |
| `speaker` | `status`, `play <file or URL> [--volume N]`, `pause`, `resume`, `stop`, `volume up/down/0-100`, `restore` | [speaker.md](../docs/devices/speaker.md) |
| `camera` | `status`, `snapshot [file.jpg]`, `watch` | [camera.md](../docs/devices/camera.md) |
| `sensor` | no argument, or `watch [--alarm 25]` | [room-sensor.md](../docs/devices/room-sensor.md) |
| `bacnet` | `discover`, `objects [--json file]` | [room-sensor.md](../docs/devices/room-sensor.md) |
| `dali` | no argument (`status`), `watch`, `info`, `on`/`off`/`up`/`down <target> [steps]`, `level <target> 0-100`, `kelvin <target> K`, `scene <target> 0-15`, `[--fade S]`; target is a short address 0-63, `g0`-`g15` or `all` | [dali.md](../docs/devices/dali.md) |
| `knx` | `monitor`, `read <ga>`, `scan <first> <last>`, `write <ga> <value> [--type switch/percent/byte]` | [knx.md](../docs/devices/knx.md) |
| `list` | `curtain`, `dimmer`, `speaker` | [home-assistant.md](../docs/devices/home-assistant.md) |

Examples:

```
python bridge/lab.py dimmer level 40
python bridge/lab.py speaker play song.mp3 --volume 15
python bridge/lab.py knx monitor
```

- **Other devices.** `curtain`, `dimmer` and `speaker` take `--entity` to use another Home Assistant entity. `sensor`, `bacnet`, `dali` and `knx` take `--ip`.
- **What changes things.** Only the curtain, dimmer and speaker actions (everything except `status` and `watch`), the `dali` actions other than `status`, `watch` and `info`, and `knx write`. All other commands only read.

## 3. Bridge Server - server.py

The server polls all devices, keeps their latest state and sends every change to connected clients over WebSocket. Clients send commands back on the same connection.

```
python bridge/server.py              # real lab devices
python bridge/server.py --simulate   # fake devices, no lab or token needed
```

| Option | Default | Meaning |
|---|---|---|
| `--port` | 8765 | WebSocket port |
| `--http-port` | 8000 | HTTP port for camera frames and songs |
| `--temp-alarm` | 26 | Temperature alarm threshold in °C |
| `--hold` | 30 | Seconds without a person before the room counts as empty |
| `--min-score` | 0.5 | Ignore person detections below this score |
| `--presence` | `camera` | What switches the virtual light: `camera`, `motion` (Aqara motion sensor) or `any` |
| `--alarm-actions` | off | When the alarm starts, close the curtain and play `--alarm-sound` on the speaker |
| `--alarm-sound` | `alarm.mp3` | Sound file in `bridge/` for `--alarm-actions` |

```
              +----------------------- server.py -----------------------+
XR app <-WS-> | latest state, broadcast, rules                          |
       <-HTTP-|  Home Assistant, every 1 s -> curtain1, dimmer1,        |
              |                               speaker1, motion1         |
              |  Frigate, every 1 s        -> camera1                   |
              |  BACnet, every 5 s         -> room_sensor1              |
              |  DALI panel, every 2 s     -> dali1                     |
              |  HTTP: /camera.jpg, /media/<song>                       |
              +---------------------------------------------------------+
```

### Messages from the Server

One JSON object per message. A new client first receives the full current state, then only changes:

```json
{ "device": "dimmer1", "property": "level", "value": 60, "source": "real", "timestamp": "2026-10-12T11:48:50+00:00" }
```

`source` is `real` or `simulated`. `status` is `online`, `offline` or `simulated`, and gives the connection status for the information panels in the concept.

| Device | Properties |
|---|---|
| `curtain1` | `position` (0-100, 0 = closed), `state`, `status` |
| `dimmer1` | `on`, `level` (0-100), `power` (W), `status` |
| `speaker1` | `state`, `volume` (0-100), `title`, `status` |
| `camera1` | `occupied`, `status` |
| `motion1` | `motion`, `illuminance` (lx), `status` |
| `room_sensor1` | `temperature`, `humidity`, `co2`, `air_quality`, `battery_low`, `alarm`, `status` |
| `dali1` | `lamp<N>_on`, `lamp<N>_failure` for DALI short address N = 0-9; `group<N>_on`, `group<N>_level` (0-100), `group<N>_kelvin` for DALI group N = 0-2; `status` |
| `virtual_light` | `on` |
| any | `error`, sent only to the client whose command failed |

### Commands to the Server

```json
{ "device": "curtain1", "command": "set_position", "value": 40 }
```

| Device | Commands |
|---|---|
| `curtain1` | `open`, `close`, `stop`, `set_position` (0-100) |
| `dimmer1` | `on`, `off`, `toggle`, `set_level` (0-100, 0 = off) |
| `speaker1` | `play` (file name in `bridge/`), `pause`, `resume`, `stop`, `volume_up`, `volume_down`, `set_volume` (0-100), `restore` |

- **Errors.** An unknown device, command or file is answered with an `error` message.
- **Curtain stop.** The real curtain has no stop function in Home Assistant, so `stop` holds the current position instead. See [curtain.md](../docs/devices/curtain.md).
- **Speaker.** The server saves the Sonos state before the first song and restores it when the song ends.

### HTTP

- `GET /camera.jpg` returns the current camera frame from Frigate, or 503 if the camera is unavailable.
- `GET /media/<file>` returns the song that is playing, for the speaker to download. All other paths return 404.

### Rules

- **UC1.** The room's presence switches `virtual_light.on`. `--presence` picks the source: `camera1.occupied` (default), `motion1.motion`, or `any` of them. Only the virtual light is switched, not the real dimmer.
- **UC3.** `room_sensor1.alarm` is true while the temperature is above `--temp-alarm`. With `--alarm-actions`, each time the alarm starts the server closes the curtain and plays `--alarm-sound` on the speaker, through the same commands Unity uses. It is off by default, because it moves real devices. If the sound file is missing, the server warns at startup and only closes the curtain. If the temperature is already above the limit when the server starts, the actions run straight away.

### Simulation Mode

With `--simulate`:
- **Curtain:** moves 10% every half second.
- **Dimmer:** reports a made-up power value.
- **Speaker:** changes state without making sound.
- **Camera:** switches between occupied and empty every 15 seconds.
- **Motion sensor:** reports motion for 10 seconds every 40 seconds.
- **Room sensor:** the temperature moves between 22 and 28 °C every two minutes, which triggers the UC3 alarm.
- **DALI:** all lamps and groups are on. Lamp 5 reports a lamp failure for 10 seconds every minute.

### Test Results

| Test | Result |
|---|---|
| Simulation, all commands | Works. Bad commands, files and JSON get an `error` back |
| Real lab, state from all five devices | Works |
| `dimmer1 set_level 30`, then `off` | Works, the real lamp followed |
| `/camera.jpg` | Works |
| Curtain and speaker commands through the server | Not tested yet (the devices were in use). The same calls were tested with `lab.py` |
| Simulation run-through on 12.10.2026: UC1 with each `--presence`, UC2 commands, UC3 with and without `--alarm-actions`, errors, reconnect | Works |
| Real mode without the lab network | Works, every device reports `offline` |
| Motion sensor and `--alarm-actions` on the real devices | Not tested yet |
| `dali1` on 13.10.2026, real panel and simulation | Works: 10 lamps and 3 groups. Commands are rejected with an `error` |
| `lab.py dali` control on 13.10.2026 | The panel accepts every command. Only `all` changes the lamps; single lamps and groups do nothing, also from the panel's own screen |

## 4. Use Cases

| Use case | Real data | Bridge | XR |
|---|---|---|---|
| UC1 Motion -> light | Frigate person detection works; motion sensor not tested | `camera1` or `motion1` -> `virtual_light.on` works in simulation | Concept |
| UC2 XR control of light and curtains | Dimmer and curtain work | Commands and two-way state work | Concept |
| UC3 Temperature alarm | BACnet room sensor works | `room_sensor1.alarm` works; `--alarm-actions` works in simulation | Concept |
| Extension: live camera panel | Frigate frames work | `/camera.jpg` works | Concept |
| Extension: DALI lamps and lamp failure | Lunatone panel REST API works (read) | `dali1` works, read-only | Concept |

## 5. Planned Unity Integration

As in the concept, Unity never talks to the devices directly, only to `server.py`.

**Connection**
- **WebSocket.** Unity opens one WebSocket to `ws://<bridge PC IP>:8765`. Check the IP with `ipconfig`, because Wi-Fi addresses can change.
- **Library.** It needs a WebSocket library that works on Quest. NativeWebSocket is the candidate.
- **Quest builds.** They need Internet Access set to Require in Player Settings.

**Components**, one per device. Each listens to its device's messages and sends its commands:

| Component | Shows | Interaction -> command |
|---|---|---|
| Bridge client | Connection state, reconnects | Parses messages, sends commands |
| Room lights (UC1) | Fades the virtual lights on `virtual_light.on` | - |
| Curtain | Moves the curtain mesh to `position` | Grab and release -> `set_position`; buttons -> `open`, `close`, `stop` |
| Dimmer | Lamp brightness from `on` and `level`, power on the information panel | Slider -> `set_level`; button -> `toggle` |
| Speaker | State, title and volume | Play/pause -> `play`, `pause`, `resume`; knob -> `set_volume` |
| Camera | Panel loading `http://<bridge PC>:8000/camera.jpg` 2-5 times a second, occupied badge | Point at the camera to show or hide the panel |
| DALI lamps | One fixture per short address, on/off from `lamp<N>_on`, flashing red on `lamp<N>_failure` | - (control later) |
| Room sensor (UC3) | Temperature label or thermometer, CO2, humidity, room tint, warning panel on `alarm` | - |
| Information panel | Name, value, last update (`timestamp`), connection (`status`, `source`) | Point and select a device |

**Guidelines**
- **Visuals follow the bridge.** Update visuals from the bridge's messages, not from the user's input. Then the wall switches and the Aqara app also update XR, which gives two-way sync.
- **Send sparingly.** Send continuous input rarely: a curtain grab once on release, sliders a few times per second at most.
- **Offline devices.** Use `status` to grey out offline devices. Use simulation mode when away from the lab.

## 6. Open Issues

1. **DALI addressing.** The Lunatone DALI-2 Display at .120 reaches the lamps only with commands to all lamps. None of the stored short addresses 0-9 answer the panel's status queries, so the lamps probably need to be addressed again by the lab staff. Until then `lamp<N>_on` is `false` for every lamp, and `dali1` stays read-only. Also find out which lamps "Task light 1" and "Task light 2" are. See [dali.md](../docs/devices/dali.md).
2. **UC3 reactions.** `--alarm-actions` is implemented but off by default. Agree with the lab staff whether the alarm may close the real curtain and play an alert on the real speaker before using it in the lab. It needs an alarm sound in `bridge/`. `*.mp3` is git-ignored, so copy the file there by hand.
3. **UC1 demo.** Someone is almost always in view of the camera, so the room rarely counts as empty. `--presence motion` uses the Aqara motion sensor instead, which can be pointed away from people. A Frigate zone (ask the lab staff) or a shorter `--hold` are other options.
4. **Curtain stop.** Holding the current position has not been tested on the real curtain yet.
5. **Writing to BACnet or KNX.** Not implemented on purpose. Only write to objects the lab staff approve.
6. **Security.** The server has no authentication, so only run it on the lab network. Revoke the Home Assistant token after the project.
