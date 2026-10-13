# XR Smart Room

A Unity-based XR application that visualizes and controls the devices of the TalTech Virumaa College KNX laboratory. Each virtual device mirrors a real one: real state changes appear in XR, and XR interactions can control the real stand.

Built during the Erasmus+ BIP project "Development of a Practical XR Application Prototype" (Virumaa College, Tallinn University of Technology, 5-16.10.2026).

## Features

- 3D smart room with virtual devices that can be placed freely
- XR interaction: press, grab, slide and point
- Live visualization of device states and measured values
- Warnings when values exceed defined limits
- Separate data-exchange layer for KNX/IP, BACnet/IP and the camera stream
- Simulation mode for working without the lab connection

## Devices

Light dimmer, DALI panel, curtains, temperature sensor, camera, speaker and a BACnet/IP gateway.

## Core Use Cases

1. **Motion -> light:** camera detects motion, the lamp turns on in XR and on the real stand.
2. **XR control:** dim the lamp with a virtual slider and grab the curtain to open or close it, with two-way sync.
3. **Temperature alarm:** live temperature in XR; above a limit a warning appears, the speaker sounds and the curtains close.

## Architecture

```
Unity + XRI/OpenXR  <-- WebSocket (JSON) -->  Data layer (bridge/server.py)  <-->  KNX/IP, BACnet/IP, DALI, camera
```

Unity never talks to the lab protocols directly. The data layer translates between them and a simple JSON message format, and can generate simulated values instead.

Unity connects to `bridge/server.py` over WebSocket (`ws://<bridge host>:8765`, JSON messages as in [bridge/README.md](bridge/README.md) section 3) and fetches camera frames and sounds over HTTP (port 8000). An adapter will map incoming `{device, property, value}` messages onto the device controllers' public setters (the IoT library's `StateChanged` events send commands back); `--simulate` gives the same messages without the lab.

## Tech Stack

| Area | Choice |
|---|---|
| Engine | Unity 2022.3.76f1 LTS, URP 14 |
| XR framework | XR Interaction Toolkit 3.5.0 + OpenXR 1.17.1 (XR Plug-in Management 4.6.1, Input System 1.19.0). VRTK v4 was dropped: unmaintained since 2024, no URP/OpenXR support (see unity/README.md) |
| 3D model | Blender 5.2 room model, scripted, exported to FBX for Unity (`blender/`) |
| Data layer | Python (`bridge/`) |
| Messaging | WebSocket (JSON) |
| Tools | YABE, ETS, Blender |

## Repository Structure

```
concept.md     Project concept: objectives, architecture, plan, risks
use-cases.md   Use cases for each device
docs/          Lab device documentation: one page per connected device
unity/         Unity 2022.3 URP project (OpenXR + XRI 3.5), see unity/README.md
  Assets/Editor/                  OrangeRoom import rules + "OrangeRoom > Build Scene" (room, lights, XR rig, devices)
  Assets/IoTDigitalTwin_Modular/  the 9-device IoT library (moved here from the repo root, history kept)
blender/       Blender model of the lab room: build_room.py + apply_materials.py rebuild main.blend from scripts;
               unity_export/ = FBX exporter for unity/Assets, textures/ (LICENSES.md), previews/ (renders)
bridge/        Data-exchange layer: device scripts and bridge server (working, see bridge/README.md)
```

## Status

- **Data layer:** works with the real lab. Curtain, dimmer, speaker, camera, room sensor and the DALI lamps can be read through `bridge/server.py`, and the curtain, dimmer and speaker can also be controlled. `lab.py` can switch and dim the DALI lamps, but only all together until the lamps are addressed again. See [bridge/README.md](bridge/README.md).
- **Devices:** one page per connected device in [docs/](docs/README.md).
- **Unity:** project created in `unity/` (URP, OpenXR, XRI 3.5). The IoT device library now lives in `unity/Assets/IoTDigitalTwin_Modular/` (moved from the repo root, as its README allows). Run **Tools > IoT Digital Twin > Generate Prefabs and Demo** once, then **OrangeRoom > Build Scene**. See [unity/README.md](unity/README.md), [concept.md](concept.md) and [use-cases.md](use-cases.md).
- **3D room:** Blender model of the lab in `blender/` (renders in `blender/previews/`).

## Next Steps (Unity)

1. **Editor version.** `unity/ProjectSettings/ProjectVersion.txt` pins 2022.3.76f1, an Extended LTS build that only opens with a Unity Industry/Enterprise licence (a Personal licence stops at start-up with "requires either a valid Unity Industry or Unity Enterprise license"). With Personal, open the project with the newest 2022.3 that Unity Hub offers you and let it rewrite the pin.
2. **First open.** Accept the Input System prompt (Active Input Handling: Input System Package or Both; XRI 3.5 needs it, the IoT library's `IoTMouseInput` already switches on `ENABLE_INPUT_SYSTEM`). Create the URP asset, enable OpenXR, import the XRI Starter Assets (steps in `unity/README.md`), then commit the generated `ProjectSettings/*.asset` and `Packages/packages-lock.json`.
3. **Devices.** Run **Tools > IoT Digital Twin > Generate Prefabs and Demo** once, then **OrangeRoom > Build Scene**, then **OrangeRoom > Place IoT Devices** (`unity/Assets/Editor/OrangeRoomDevicePlacer.cs`). It puts the prefabs on the demo boards: board positions come from the Blender model, device spots from the board photos, and each device gets an `XRSimpleInteractable`. It compiles against the Unity 2022.3 assemblies but has not run in an Editor yet; it logs a Blender-to-Unity axis check against `Kitchen_Board`. Mapping (from `docs/devices/` and the board photos):

| IoT library prefab | Real device | Bridge name | Where in the room |
|---|---|---|---|
| 01_Zigbee_Dimmer | Aqara Dimmer Switch H2 | `dimmer1` | Aqara/Zigbee demo board (board 5) |
| 09_DALI_Touchscreen | Lunatone DALI-2 Display ("DALI puutepaneel") | `dali1` | DALI demo board (board 1), middle row |
| 06_Roller_Blind + 05_Aqara_Controller | Aqara Curtain Driver E1 on the curtain rail | `curtain1` | rail on top of board 5; board 1 also has a motor blind ("Mootor") |
| 04_Security_Camera | Aqara camera G5 (Frigate person detection) | `camera1` | board 3, top left |
| 07_Siemens_BACnet | KNX room sensor via Siemens OCT200.KNBA gateway | `room_sensor1` | board 3, top right (room unit) |
| 08_Nest_Speaker | Google Nest "Dali stand WhiteNest" (bridge default is the Sonos Roam "Office") | `speaker1` | bottom right of the DALI board |
| 02_Zigbee_Temperature_Sensor | Aqara temperature/humidity display | (none yet; `motion1` is the Aqara motion sensor) | board 5, bottom row |
| 03_ZWave_Thermostat | no lab counterpart in the bridge | - | prop only, or leave out |

4. **XR interaction.** The library ships mouse input only. Route the `XRSimpleInteractable` select events (poke/press: dimmer, DALI panel, thermostat; grab for the blind chain and camera head) to the same controller setters the mouse input uses.
5. **Bridge adapter.** A small MonoBehaviour with a WebSocket client (`ws://<bridge host>:8765`) that maps `{device, property, value}` messages onto the controllers' setters on the main thread and sends commands from their `StateChanged` events (see bridge/README.md, section 3).
