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

1. **Motion -> light:** camera detects motion, the room is marked occupied and the virtual ceiling lights turn on. The real lights stay under the DALI panel and the dimmer.
2. **XR control:** the real DALI panel (on/off, colour) and the real dimmer (brightness) drive the virtual ceiling lights; grabbing the virtual curtain or pressing Raise/Lower moves the real curtain, with two-way sync.
3. **Temperature alarm:** live temperature in XR; above a limit a warning appears, the speaker sounds and the curtains close.

## Architecture

```
Unity + XRI/OpenXR  <-- WebSocket (JSON) -->  Data layer (bridge/server.py)  <-->  KNX/IP, BACnet/IP, DALI, camera
```

Unity never talks to the lab protocols directly. The data layer translates between them and a simple JSON message format, and can generate simulated values instead.

Unity connects to `bridge/server.py` over WebSocket (`ws://<bridge host>:8765`, JSON messages as in [bridge/README.md](bridge/README.md) section 3). Unity has no HTTP client: port 8000 serves `/camera.jpg` (not used by Unity yet) and `/media/<song>` for the real speaker. `RoomBridge` maps incoming `{device, property, value}` messages onto the device controllers' public setters; commands (curtain, speaker) go back only from XR user input, never from `StateChanged`, so bridge updates cannot echo. `--simulate` gives the same messages without the lab.

## Tech Stack

| Area | Choice |
|---|---|
| Engine | Unity 2022.3.62f3 LTS (last public 2022.3, runs on a Personal licence), URP 14. Target: Meta Quest 3S (Android, OpenXR) |
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
  Assets/Scripts/                 runtime: RoomBridge (bridge client), XRDeviceInput, CeilingLights, BridgeTestPanel
  Assets/IoTDigitalTwin_Modular/  the 9-device IoT library (moved here from the repo root, history kept)
blender/       Blender model of the lab room: build_room.py + apply_materials.py rebuild main.blend from scripts;
               unity_export/ = FBX exporter for unity/Assets, textures/ (LICENSES.md), previews/ (renders)
bridge/        Data-exchange layer: device scripts and bridge server (working, see bridge/README.md)
```

## Status

- **Data layer:** works with the real lab. Curtain, dimmer, speaker, camera, room sensor and the DALI lamps can be read through `bridge/server.py`, and the curtain, dimmer and speaker can also be controlled. `lab.py` can switch and dim the DALI lamps, but only all together until the lamps are addressed again. See [bridge/README.md](bridge/README.md).
- **Devices:** one page per connected device in [docs/](docs/README.md).
- **Unity:** project created in `unity/` (URP, OpenXR, XRI 3.5). The IoT device library now lives in `unity/Assets/IoTDigitalTwin_Modular/` (moved from the repo root, as its README allows). Run **Tools > IoT Digital Twin > Generate Prefabs and Demo** once, then **OrangeRoom > Build Scene**. The bridge integration is implemented and checked in Editor play mode against `server.py --simulate` (`OrangeRoomBridgeCheck`, all PASS); not yet tested on the headset or with the real lab. See [unity/README.md](unity/README.md), [concept.md](concept.md) and [use-cases.md](use-cases.md).
- **3D room:** Blender model of the lab in `blender/` (renders in `blender/previews/`).

## Next Steps (Unity)

1. **Editor version.** `unity/ProjectSettings/ProjectVersion.txt` pins **2022.3.62f3**, the last public 2022.3 LTS patch, which opens with a Personal licence. 2022.3.63 and later (including 2022.3.76f1, which we pinned before) are Extended LTS builds that refuse a Personal licence at start-up ("requires either a valid Unity Industry or Unity Enterprise license").
2. **Quest 3S build.** Done headless by `unity/Assets/Editor/OrangeRoomQuest.cs` (Setup, Scene, Bake, Snapshots, Apk; commands in `unity/README.md`). The APK is attached to the GitHub release, not committed. Store builds: `tools/quest_release.sh` (release-signed, verified, ALPHA upload only with `--upload`), see [docs/store-release.md](docs/store-release.md). Still untested on a headset: install from the store ALPHA channel and check teleport, grab, door and that the IoT device screens show in both eyes.
3. **Devices.** All nine IoT prefabs generate in Unity 2022.3.62f3 and `OrangeRoom > Place IoT Devices` puts them on the demo boards (Blender-to-Unity check against `Kitchen_Board`: 0.000 m after fixing the axis mapping to `(x, z, y)`). Each device gets an `XRSimpleInteractable`. Fixes needed for a real Unity import: the library's texture `.meta` files declared every PNG as a cubemap (`textureShape: 2`), the dimmer's label pivot sits on the origin (generator now uses its mesh centre), and the display shader had no single-pass-instanced stereo macros (screens would render in one eye on Quest). Mapping (from `docs/devices/` and the board photos):

| IoT library prefab | Real device | Bridge name | Where in the room |
|---|---|---|---|
| 01_Zigbee_Dimmer | Aqara Dimmer Switch H2 | `dimmer1` | Aqara/Zigbee demo board (board 5) |
| 09_DALI_Touchscreen | Lunatone DALI-2 Display ("DALI puutepaneel") | `dali1` | DALI demo board (board 1), middle row |
| 06_Roller_Blind + 05_Aqara_Controller | Aqara Curtain Driver E1 on the curtain rail | `curtain1` | rail on top of board 5; board 1 also has a motor blind ("Mootor") |
| 04_Security_Camera | Aqara camera G5 (Frigate person detection) | `camera1` | board 3, top left |
| 07_Siemens_BACnet | KNX room sensor via Siemens OCT200.KNBA gateway | `room_sensor1` | board 3, top right (room unit) |
| 08_Nest_Speaker | Google Nest "Dali stand WhiteNest" (bridge default is the Sonos Roam "Office") | `speaker1` | bottom right of the DALI board |
| 02_Zigbee_Temperature_Sensor | Aqara temperature/humidity display | `room_sensor1` (temperature, humidity) | board 5, bottom row |
| 03_ZWave_Thermostat | no lab counterpart in the bridge | - | prop only, or leave out |

4. **XR interaction.** Done: `Assets/Scripts/XRDeviceInput.cs` sits next to each device's `XRSimpleInteractable` and turns XRI select/drag/release on a hit zone into the same `ControlDown/Drag/Up` calls the library's mouse input makes. The rig's rays are set to hit trigger colliders (the hit zones are triggers).
5. **Bridge adapter.** Done: `Assets/Scripts/RoomBridge.cs` on the "Bridge" object. Plain .NET `ClientWebSocket` (works in IL2CPP on Quest, no NativeWebSocket needed), reconnects every 2 s, applies `{device, property, value}` on the main thread. Sends only `curtain1` (Raise/Lower -> `open`/`close`/`stop`, blind grab release -> `set_position`) and `speaker1` (volume, mute) commands, only from user input. Ceiling lights (`CeilingLights.cs`): on/off and colour from the DALI panel, brightness from the dimmer, `virtual_light.on` (UC1) and the DALI on/off last writer wins; nothing in XR drives the real lights. DALI state comes from `dali1.all_*` (broadcast zone, preferred once the bridge sends it) with `group0_*` as fallback; `server.py` currently sends only `group<N>_*`. The colour arrives as kelvin only (no RGB on the wire). Mapping: bridge/README.md section 5. The APK step sets Android Internet permission.
6. **Room export.** `unity/Assets/Models|Textures` is the full-quality export of the final Blender v2 model: one run of `blender/unity_export/export_unity.py --quality high --res-max 1024` (Quest texture cap; 709 maps up to 1024 px, 8/64 bake samples). One run uses base material names (no `_Room2`/`_Room3` copies like the earlier two-run trial). `_validate_fbx.py` still reports three model issues, the same as the trial export: UV1 overlap on `Deskprops_CableUSB`, UV0 overlap on `Deskprops_CableWhite`, and `Room3_Play` listing `Room3_Plastic_Black` twice. Recipe note: copy `textures/` into the work dir too, otherwise `apply_materials.py` fails while Blender still exits 0.
7. **C# status.** Everything compiles and runs in Unity 2022.3.62f3 (Linux, batch mode): IoT library, the four editor scripts and `Assets/Scripts`. Lighting is mixed: baked GI on ProgressiveCPU (the 4 GB RTX 3050 is below the GPU lightmapper minimum) with OpenImageDenoise, a baked sun through the windows, neutral sky tint, no post-processing on Quest (HDR off), LED 8, window 4 (lab windows x0.6), hall (Room3) LEDs x1.5, lightmaps uncompressed (RGBM + ASTC broke them into blocks). The lab (Room2) LED panels are baked at 70 % and `CeilingLights` adds the rest at runtime (two shadowless realtime spot lights, limited by URP Light Layers to the lab and the IoT devices, + emissive panels), so the lab never goes fully dark. Knobs: unity/README.md, "Calibrate".
8. **In-VR test panel.** `BridgeTestPanel` (world-space panel beside board 5) fakes every real-world signal through `RoomBridge.Apply`, so each mapping can be checked in the headset without the lab, and shows the bridge status line.
9. **Bridge address.** Default `ws://192.168.160.57:8765` (the team laptop). Find the laptop IP with `ip -4 addr` / `ipconfig`; Wi-Fi addresses change. Set it with env `ORANGE_BRIDGE_URL` when running the Scene step, in the Inspector on the "Bridge" object, or in VR on the test panel (-/+ per octet, then **Apply & reconnect**). The VR value is saved on the headset and wins over the build value until changed again. Open TCP 8765 and 8000 on the laptop firewall. Look for `online` on the panel; if it stays on `connecting`, suspect Wi-Fi client isolation and use a phone hotspot for the laptop and the headset.
10. **Bridge check.** `Assets/Editor/OrangeRoomBridgeCheck.cs`: start `python3 bridge/server.py --simulate`, then `~/Unity/Hub/Editor/2022.3.62f3/Editor/Unity -batchmode -projectPath unity -executeMethod OrangeRoomBridgeCheck.Run -logFile -` (no `-quit`; it enters play mode, prints `[BridgeCheck] PASS/FAIL` per assertion and exits 0/1, 120 s timeout; `BRIDGE_CHECK_URL` overrides `ws://127.0.0.1:8765`). Covers parsing, connect + initial state, devices following messages, Lower -> simulated curtain closes, release -> stop holds, and dimmer/DALI -> ceiling lights. Full lab test plan: [docs/test-checklist.md](docs/test-checklist.md).
11. **Known issues in the 3D model** (Blender v2, see `blender/previews/`):
   - Lab desk layout does not fully match photo 150435.
   - Terrazzo floor is glossier than in the photos.
   - Hall: cyan colour cast, dark ceiling under the duct, glass offices read grey, foosball table too light, far corridor too dim, hall wall about +0.7 stop too bright.
   - Pink door is about 10 % narrower than the real one.
   - IoT device positions (`OrangeRoomDevicePlacer.cs`) are checked in the Editor snapshots (`Build/Snapshots/`), not yet on the headset.
