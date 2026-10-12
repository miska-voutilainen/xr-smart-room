# Bridge: lab devices ↔ XR Smart Room

This folder is the **data-exchange layer** from [concept.md](../concept.md). It talks to the real devices in the Virumaa College lab and provides one simple message protocol for the XR application.

**Status (12.10.2026):** every lab device below can be read, and all except the DALI panel can be controlled, from Python on the lab network. A single bridge server (`server.py`) streams all device states and accepts commands, and has been tested against the real lab. **Unity is still only a concept.** Section 7 describes how it's meant to connect.

---

## 1. Lab network map

All devices are on the lab Wi-Fi, `192.168.15.0/24`.

| What | Address | How we reach it | Found with |
|---|---|---|---|
| Home Assistant | `192.168.15.249:8123` | REST API with a long-lived access token | `homeassistant.local` lookup |
| Aqara Hub M3 | (behind Home Assistant) | Its Zigbee devices appear as Home Assistant entities | Home Assistant entity list |
| Frigate (camera software) | `192.168.15.249:5000` | HTTP API, no login | Port check |
| Aqara camera (G5) | `192.168.15.144`, RTSP `8554` | Through Frigate (direct RTSP needs a login we don't have) | Home Assistant + Frigate |
| Sonos "Office" (Roam) | `192.168.15.183` | Home Assistant `media_player.roam_2_2` | Home Assistant |
| Google Nest speakers | – | Home Assistant `media_player.googlehome6580` ("Dali stand WhiteNest"), `media_player.famnest2` | Home Assistant |
| BACnet gateway, Siemens **OCT200.KNBA** | `192.168.15.132:47808`, device instance `1223` | BACnet/IP ReadProperty | `lab.py bacnet discover` |
| KNX/IP interface **KNX IP BAOS 777** | `192.168.15.191`, KNX address `1.5.1` | KNXnet/IP (port 3671 UDP), web UI on 80/443, BAOS protocol on 12004 | KNX search request |
| MQTT broker (Mosquitto) | `192.168.15.249:1883` | Login works but **nothing is published there**, so it's not used | – |

Home Assistant itself is connected to KNX through a tunnel (Home Assistant's KNX address `1.5.248`), but it exposes no KNX lights or DALI devices to our token.

## 2. Devices

| Device (bridge name) | Real device | Source | Read | Control | Tested |
|---|---|---|---|---|---|
| `curtain1` | Aqara Curtain Driver E1 | Home Assistant `cover.curtain_2` | position, state | open, close, stop, position | ✅ |
| `dimmer1` | Aqara Dimmer Switch H2 + lamp | Home Assistant `light.aqara_dimmer_switch_h2` (+ power sensor) | on, level, watts | on, off, toggle, level | ✅ |
| `speaker1` | Sonos "Office" | Home Assistant `media_player.roam_2_2` | state, volume, title | play file, pause, resume, stop, volume, restore | ✅ (CLI) |
| `camera1` | Aqara camera via Frigate | Frigate person events | occupied (person seen) | – | ✅ |
| `room_sensor1` | KNX room sensor via BACnet gateway | BACnet objects AI 0/2/3, MSV 0, BV 0 | temperature, humidity, CO₂, air quality, battery low | – (read-only) | ✅ |
| DALI panel | – | Not reachable yet, see section 8 | – | – | ❌ |

**Things that will catch you out:**
- **Two curtain entries.** `cover.aqara_curtain_driver_e1` reports "open" within 2–3 s but **does not move the curtain**. Use `cover.curtain_2`, which moves the real one in 6–25 s.
- **Two dimmer entries.** `light.switch` mirrors the same dimmer. Either works; we use `light.aqara_dimmer_switch_h2` because it has a power sensor.
- **Shared devices.** Other people use these devices. The dimmer was at 1% and the Sonos was playing someone's phone over Bluetooth when we tested. Put things back the way you found them.
- **Sensor values.** The BACnet air-quality value is **CO₂ in ppm** (BACnet unit 96). The air-quality levels are `1 unknown, 2 poor, 3 okay, 4 good`.

## 3. Setup

1. Python 3.10+ (tested on 3.14), then `pip install -r bridge/requirements.txt` (`websockets` for the server, `xknx` for the KNX commands; everything else uses the standard library).
2. Create `bridge/.env` with one line:
   ```
   HA_TOKEN=<Home Assistant long-lived access token>
   ```
   Make a token in Home Assistant under Profile → Security → Long-lived access tokens. `.env` is git-ignored. Never put the token in code or commits.
3. Be on the lab Wi-Fi. When Windows Firewall asks, allow Python on **private** networks. The server must accept connections on 8765/8000, and BACnet replies arrive on UDP 47808.

## 4. Testing devices: `lab.py`

One script tests every device. Run it from the project root:

```
python bridge/lab.py check            # read-only test of all devices, one line each
```

| Device | Commands | Notes |
|---|---|---|
| `curtain` | `status`, `watch`, `open`, `close`, `stop`, `position 0-100` | Waits and prints until the curtain stops moving. |
| `dimmer` | `status`, `watch`, `on`, `off`, `toggle`, `level 0-100` | Also prints the lamp's power draw, which proves the real lamp reacted. |
| `speaker` | `status`, `play <file or URL> [--volume N]`, `pause`, `resume`, `stop`, `volume up/down/0-100`, `restore` | See below. |
| `camera` | `status`, `snapshot [file.jpg]`, `watch` | Frame rates, a saved frame, or each person detection. |
| `sensor` | (none), `watch [--alarm 25]` | Room sensor over BACnet; `--alarm` warns above that temperature. |
| `bacnet` | `discover`, `objects [--json file]` | Who-Is broadcast (like YABE), or every object of the gateway with its value. |
| `knx` | `monitor`, `read <ga>`, `scan <first> <last>`, `write <ga> <value> [--type switch/percent/byte]` | KNX bus through the BAOS 777, for finding the DALI lamps. See section 8. |
| `list` | `curtain`, `dimmer`, `speaker` | Home Assistant entities of that kind. |

Examples: `python bridge/lab.py dimmer level 40`, `python bridge/lab.py speaker play 11044ab7fe_villian-madk1d-dinastija.mp3 --volume 15`, `python bridge/lab.py knx monitor`.

- **Other devices:** `curtain`, `dimmer` and `speaker` accept `--entity` to target another Home Assistant entity. `sensor`, `bacnet` and `knx` accept `--ip`.
- **What changes things:** only curtain, dimmer and speaker actions (anything but `status` and `watch`) and `knx write`. Everything else only reads.
- **Server code:** `lab.py` also holds the shared code `server.py` uses: the lab configuration (addresses, entity IDs), the Home Assistant client, the BACnet client and the room-sensor reader.

**How `speaker play` works:**
1. If the song is a local file (looked up in the current folder, then in `bridge/`), the script serves **only that file** over HTTP on port 8000. The speaker downloads it from the PC.
2. On a Sonos, it first saves the speaker's current state with `sonos.snapshot`.
3. It sets `--volume` if given, then plays the song.
4. When the song ends, or on Ctrl+C, it restores the previous state with `sonos.restore`: same source and volume. This was tested: the speaker went back to the Bluetooth phone at 48%.
5. If the script is killed, `lab.py speaker restore` does the same by hand.
6. **Google Nest speakers can't restore** what was playing before, and Bluetooth playback on a Nest is invisible to Home Assistant.

**Camera:** Frigate already pulls the camera stream and runs person detection at 1280×720 and about 5 fps, so we use its open API on port 5000 rather than the camera itself. The Frigate config we were given has RTSP credentials, but the camera rejects them, so direct RTSP doesn't work. The camera films people: don't commit snapshots (`*.jpg` is git-ignored).

### BACnet room sensor

The gateway exposes one room sensor:

| Object | Name | Meaning | Example |
|---|---|---|---|
| analog-input 0 | `1_/p/rts/temproom` | Room temperature | 22.2 °C |
| analog-input 2 | `1_/p/rrhs/humrelroom` | Relative humidity | 46 % |
| analog-input 3 | `1_/p/raqs/aqroom` | Air quality (CO₂) | 930 ppm |
| multi-state-value 0 | `1_/p/raqs/aqroomind` | Air quality level | 4 = good |
| binary-value 0 | `1_/p/sdev/batterylow` | Sensor battery low | false |

The BACnet commands are **read-only**. Writing to the gateway is deliberately not implemented.

## 5. The bridge server (`server.py`)

`server.py` is the piece the XR app will use. It polls all devices, keeps the latest state, and pushes every change to connected clients over WebSocket. It also accepts commands from those clients.

```
python bridge/server.py               # real lab devices
python bridge/server.py --simulate    # fake devices: works anywhere, no lab needed
```

Options:
- `--port 8765`: WebSocket
- `--http-port 8000`: camera frames and songs
- `--temp-alarm 26`: °C threshold for the room-sensor alarm
- `--hold 30`: seconds without a person before the room counts as empty
- `--min-score 0.5`: ignore person detections below this score

```
                ┌──────────────── server.py ────────────────┐
 Unity ◄─ WS ──►│ Hub: latest state, broadcast, rules       │
 (planned)      │   Home Assistant poll 1 s ─► curtain1, dimmer1, speaker1
       ◄─ HTTP ─│   Frigate poll 1 s ───────► camera1 (occupied)
   camera.jpg   │   BACnet poll 5 s ────────► room_sensor1
                │ HTTP: /camera.jpg, /media/<song>          │
                └───────────────────────────────────────────┘
```

### Messages: server → client

One JSON object per WebSocket message. A new client first gets the full current state, then only changes.

```json
{ "device": "dimmer1", "property": "level", "value": 60, "source": "real", "timestamp": "2026-10-12T11:48:50+00:00" }
```

`source` is `real` or `simulated`.

| Device | Properties |
|---|---|
| `curtain1` | `position` 0–100 (0 = closed), `state` (open/closed/opening/closing), `status` |
| `dimmer1` | `on` bool, `level` 0–100, `power` W, `status` |
| `speaker1` | `state` (playing/paused/idle/…), `volume` 0–100, `title`, `status` |
| `camera1` | `occupied` bool, `status` |
| `room_sensor1` | `temperature` °C, `humidity` %, `co2` ppm, `air_quality`, `battery_low`, `alarm` bool, `status` |
| `virtual_light` | `on` bool |
| any | `error` text, sent only to the client whose command failed |

`status` is `online`, `offline` (the device or service isn't answering) or `simulated`. This is the connection status shown in the information panels described in concept.md.

### Commands: client → server

```json
{ "device": "curtain1", "command": "set_position", "value": 40 }
```

| Device | Commands |
|---|---|
| `curtain1` | `open`, `close`, `stop`, `set_position` (0–100) |
| `dimmer1` | `on`, `off`, `toggle`, `set_level` (0–100, 0 = off) |
| `speaker1` | `play` (file name in `bridge/`), `pause`, `resume`, `stop`, `volume_up`, `volume_down`, `set_volume` (0–100), `restore` |

Unknown devices, commands or files are answered with an `error` message. `play` only accepts audio files that sit directly in `bridge/`. The server snapshots the Sonos before the first song and restores it automatically when the song ends.

### HTTP

- `GET /camera.jpg` returns the latest camera frame (proxied from Frigate), or 503 if the camera is unavailable.
- `GET /media/<file>` is the song currently being played; the speaker downloads it from here. Every other path returns 404.

### Rules, built into the server

- **UC1:** `camera1.occupied` → `virtual_light.on`. This only switches the **virtual** light, as agreed. The real dimmer is not switched automatically.
- **UC3:** `room_sensor1.temperature > --temp-alarm` → `room_sensor1.alarm = true`. This is only a signal. The planned reactions (speaker alert, closing curtains) are **not** wired to real devices yet; see section 8.

### Simulation mode

`--simulate` needs no lab and no token:
- The curtain moves 10% every half second.
- The dimmer reports a fake power draw.
- The speaker changes state without making sound.
- The camera alternates occupied/empty every 15 s.
- The temperature swings between 22 and 28 °C every 2 minutes, so the UC3 alarm triggers on its own.

### Test results (12.10.2026)

- **Simulation:** all commands and properties work, and bad commands, bad files and bad JSON each get an `error` back.
- **Real lab:** all five devices reported live state. `dimmer1 set_level 30` → the real lamp went to 30%, then `off`. `/camera.jpg` served a live frame.
- **Not yet tested through the server:** curtain and speaker commands (they were in use by others). Both were tested with the device scripts, which make the same Home Assistant calls (now `lab.py curtain` / `lab.py speaker`).

## 6. Use cases: where they stand

| Use case | Real data | Bridge | XR |
|---|---|---|---|
| UC1 Motion → light | Frigate person detection ✅ | `camera1.occupied` → `virtual_light.on` ✅ | concept |
| UC2 XR control of light and curtains | Dimmer ✅, curtain ✅ | Commands + two-way state ✅ | concept |
| UC3 Temperature alarm | BACnet room sensor ✅ | `room_sensor1.alarm` ✅; speaker/curtain reactions open | concept |
| Extension: live camera panel | Frigate frames ✅ | `/camera.jpg` ✅ | concept |
| DALI panel | ❌ not reachable yet | – | concept |

## 7. Planned Unity integration (concept)

Rule from the concept: **Unity never talks to devices directly**, only to `server.py`.

**Connection**
- Unity opens one WebSocket to `ws://<bridge-PC-IP>:8765`. Find the IP with `ipconfig`; Wi-Fi addresses can change.
- A WebSocket library that works on Quest is needed. [NativeWebSocket](https://github.com/endel/NativeWebSocket) is the candidate.
- Quest builds need *Internet Access: Require* in Player Settings.

**Planned components**, one per device. Each listens to its device's messages and sends commands:

| Component | Shows | XR interaction → command |
|---|---|---|
| Bridge client | Connection state; reconnects | Parses `device`/`property`, sends commands |
| Room lights (UC1) | Fades virtual lights on `virtual_light.on` | – |
| Curtain | Moves the curtain mesh to `position` | Grab and release → `set_position`; buttons → `open`/`close`/`stop` |
| Dimmer | Lamp intensity from `on` + `level`; power on the info panel | Slider → `set_level` (sent at most ~3×/s); button → `toggle` |
| Speaker | State, title, volume | Play/pause button → `play`/`pause`/`resume`; volume knob → `set_volume` |
| Camera | Live panel loading `http://<bridge-PC>:8000/camera.jpg` 2–5×/s; "occupied" badge | Point at the camera → show/hide the panel |
| Room sensor (UC3) | Temperature label/thermometer, CO₂, humidity, room tint; warning panel on `alarm` | – |
| Info panel (all devices) | Name, value, last update (`timestamp`), connection (`status` + `source`) | Point and select a device |

**Design rules for the XR side**
- **Update visuals from the bridge's state messages, not from the user's input.** The XR object moves when the real device reports it moved. That gives two-way sync for free: wall switches and the Aqara app update XR too.
- **Send continuous inputs sparingly.** Send a curtain grab once on release, and send sliders at most a few times per second. Real motors and dimmers can't keep up with per-frame commands.
- **Use `status` to grey out offline devices,** and use simulation mode for development away from the lab.

## 8. Open issues and next steps

1. **DALI panel.**
   - There's no IP device for DALI. It most likely sits on the KNX bus behind a KNX–DALI gateway, reachable through the **KNX IP BAOS 777** (`192.168.15.191`).
   - Done so far: `lab.py knx` connects to the bus through the BAOS 777 (tested). In 60 s of `monitor` the bus was silent. `scan 0/0/1 0/0/40` got no answers. The BAOS object server (TCP 12004) didn't answer either.
   - Next: run `python bridge/lab.py knx monitor` while someone operates the DALI panel. The group addresses of the lamps appear as telegrams. Then try `knx read <ga>` and `knx write <ga> on` / `40%`.
   - Alternatively, get the **ETS project or the group address list** from the lab staff, or the BAOS 777 web login. A wider `knx scan` also works but sends many read requests, so keep `--delay` and ask the staff first.
   - Once the addresses are known, add a `dali1` device to `server.py`. Don't guess passwords.
2. **UC3 reactions.** Decide with the lab staff whether the alarm may close the real curtain and play an alert on a real speaker. If so, add those actions to `Hub.apply_rules` behind a flag. The Nest on the DALI stand (`media_player.googlehome6580`) is a candidate for the alert sound.
3. **UC1 demo.** People are always in view, so the room rarely counts as "empty". Options:
   - Ask the lab staff for a Frigate **zone**, e.g. in front of stand 1, and trigger on that.
   - Use a shorter `--hold`.
   - Use the Aqara motion sensor (`binary_sensor.aqara_motion_sensor`) as a second trigger.
4. **Direct camera RTSP** needs the current RTSP login, set in the Aqara Home app under RTSP LAN preview. It isn't needed while Frigate works.
5. **SoundCloud** was looked at, not built. API access is hard to get and streams are often in a format the speakers don't play reliably. Local MP3s work.
6. **Writing to BACnet/KNX** is not implemented on purpose. Only write to objects the lab staff approve, with a low BACnet priority.
7. **Security.**
   - The Home Assistant token was shared in chat. Revoke it after the project.
   - The server has no authentication: run it only on the lab network.
