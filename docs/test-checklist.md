# XR Smart-Room Twin - Test Checklist

**Project:** Erasmus+ BIP - XR Smart-Room Twin  
**Test date:** 15 October 2026  
**Location:** TalTech Virumaa College, KNX Laboratory

## 1. Testing Objective

The purpose of testing is to verify the three main use cases (UC1-UC3) of the XR Smart-Room Twin from [concept.md](../concept.md), end to end: real lab device -> `bridge/server.py` -> WebSocket -> Unity (`RoomBridge`) -> virtual device, and XR input -> `RoomBridge` -> bridge -> real curtain / speaker.

Testing will be performed in three different conditions:

- **Simulation mode:** `python3 bridge/server.py --simulate` on the laptop. Fake devices, no lab network or Home Assistant token needed.
- **Real laboratory mode:** `python3 bridge/server.py` on the laptop, connected to the lab Wi-Fi and the real devices.
- **Connection failure:** the bridge server is stopped or unreachable while the XR app runs.

Each test will be marked with one of the following results:

- **PASS** - The test completed successfully.
- **FAIL** - The test did not meet the expected result.
- **N/T** - The test has not been performed.

What the XR app does with each bridge message (from `RoomBridge.Apply`):

| Bridge message | Virtual device |
|---|---|
| `dimmer1.on`, `dimmer1.level` | Dimmer model (`01_Zigbee_Dimmer`); ceiling brightness. Dimmer off = ceiling lights off |
| `dali1.all_on`, `dali1.all_kelvin` (fallback `dali1.group0_on`, `dali1.group0_kelvin`; `server.py` sends only `group<N>_*` so far) | DALI panel model (`09_DALI_Touchscreen`); ceiling on/off and colour temperature |
| `virtual_light.on` (UC1 rule) | Ceiling on/off. Last writer wins with the DALI on/off |
| `camera1.occupied` | Camera model: red recording LED = person seen |
| `curtain1.position` | Roller blind (0 = closed) |
| `room_sensor1.temperature`, `humidity` | Temperature display (value + tint from [temperature-tint-scale.md](temperature-tint-scale.md)), Siemens room unit display |
| `room_sensor1.alarm` (UC3) | Floodlight on the camera model (the warning in this build; no warning panel or room tint yet) |
| `speaker1.state`, `speaker1.volume` | Speaker model active while `playing`, volume |

Nothing in XR controls the real lights. XR sends commands only for the curtain and the speaker, and only from user input.

While the bridge is `online`, the mirrored devices (dimmer, DALI panel, camera, temperature display, Siemens room unit) are read-only in XR. To change them, use the real device or the test panel.

## 2. Preparation

- [ ] Laptop on the lab Wi-Fi. Find its IP with `ip -4 addr` (Linux) or `ipconfig` (Windows). Default in the app: `ws://192.168.160.57:8765`.
- [ ] Open the bridge ports on the laptop: Fedora `sudo firewall-cmd --add-port=8765/tcp --add-port=8000/tcp`, Windows: allow Python on private networks.
- [ ] Start the bridge: `python3 bridge/server.py --simulate` (simulation) or `python3 bridge/server.py` (real lab).
- [ ] Start the XR app (Quest build from the store ALPHA channel, or Editor play mode with the XR Device Simulator).
- [ ] If the laptop IP differs from the default: set it on the in-VR test panel (-/+ per octet) and press **Apply & reconnect**. The address is saved on the headset.
- [ ] Verify the status line on the test panel shows `ws://<laptop IP>:8765: online`. If it stays on `connecting`, suspect Wi-Fi client isolation and put the laptop and the headset on a phone hotspot.

**Expected result:** The app connects to the bridge within a few seconds and the virtual devices take the bridge's current state.

**Result:** N/T

## 3. Automated Bridge Check

**Objective:** Verify the Unity side of the bridge path without a headset.

### Test BC.1 - Editor Play Mode vs Simulation Server

- [ ] Start `python3 bridge/server.py --simulate` on the laptop.
- [ ] Run `~/Unity/Hub/Editor/2022.3.62f3/Editor/Unity -batchmode -projectPath unity -executeMethod OrangeRoomBridgeCheck.Run -logFile -` from the repo root (Unity closed; no `-quit`).
- [ ] Verify every line `[BridgeCheck] PASS: ...`, no `FAIL`, and `[BridgeCheck] DONE: all passed`; exit code 0.

**Expected result:** Message parsing works, `RoomBridge` connects and receives the initial state, the DALI panel, temperature display and curtain follow the messages, Lower closes the simulated curtain and release stops it, and dimmer/DALI drive the ceiling lights. Finishes within 120 s.

**Result:** PASS (all assertions, Editor play mode against `--simulate`)

## 4. In-VR Bridge Test Panel

**Objective:** Verify every message mapping in the headset without the lab. The panel next to board 5 fakes real-world signals by calling `RoomBridge.Apply` with the same device/property/value the bridge would send.

### Test TP.1 - Fake Signals

- [ ] Toggle **Dimmer on** and move **Dimmer level %**. Verify the dimmer knob follows and the lab ceiling lights brighten and dim.
- [ ] Toggle **Dimmer on** off. Verify the ceiling lights go dark (dimmer off = ceiling off).
- [ ] Turn **Dimmer on** back on, then toggle **DALI lamps on**. Verify the ceiling lights switch off and on.
- [ ] Move **DALI colour K** from 2000 to 6500. Verify the ceiling light colour moves from warm to cool.
- [ ] Toggle **Person seen, UC1**. Verify the camera's red LED and the ceiling lights follow.
- [ ] Move **Curtain open %**. Verify the virtual curtain moves (0 = closed).
- [ ] Move **Temperature C** from 15 to 30. Verify the display value and its tint follow the tint scale (blue -> green -> red, darkest red from 26 °C).
- [ ] Toggle **Temperature alarm, UC3**. Verify the camera floodlight switches on and off.
- [ ] Move **Speaker volume %**. Verify the speaker model follows.

**Expected result:** Each control changes the matching virtual device immediately, with or without a bridge connection.

**Result:** N/T

### Test TP.2 - Editable Bridge Address

- [ ] Change one octet to a wrong address with -/+ and press **Apply & reconnect**. Verify the status line shows the new address, `connecting`, then `offline`.
- [ ] Set the laptop IP and press **Apply & reconnect**. Verify the status line shows `online`.
- [ ] Restart the app. Verify the saved address is still used.

**Expected result:** The bridge address can be changed in VR without rebuilding the app.

**Result:** N/T

## 5. UC1 - Camera / Motion -> Virtual Ceiling Lights

**Objective:** Verify that a person seen by the camera (or the motion sensor, with `--presence motion`) marks the room occupied and turns on the virtual ceiling lights. The real lights are not switched. The ceiling brightness comes from the dimmer, so the dimmer must be on (dimmer off = ceiling off).

### Test UC1.1 - Simulation Mode

- [ ] Start `python3 bridge/server.py --simulate` and the XR app (status `online`).
- [ ] On the test panel, set **Dimmer on** and a level above 0 (the simulated dimmer stays off; the dimmer model itself is read-only while `online`).
- [ ] Verify the camera's red LED switches every 15 seconds (`camera1.occupied`).
- [ ] Verify the ceiling lights turn on while occupied and off when empty (`virtual_light.on`).
- [ ] Restart the server with `--presence motion`. Verify the lights follow the motion sensor (10 seconds of motion every 40 seconds).

**Expected result:** The virtual ceiling lights follow `virtual_light.on` within 1 second.

**Result:** N/T

### Test UC1.2 - Real Laboratory

- [ ] Start `python3 bridge/server.py` (real devices) and the XR app.
- [ ] Make sure the real dimmer is on (ceiling brightness comes from it).
- [ ] Walk into the camera's view. Verify the server logs `camera1.occupied = True` and `virtual_light.on = True`.
- [ ] Verify the camera's red LED and the virtual ceiling lights turn on.
- [ ] Leave the view. Verify both turn off after `--hold` (30 s by default).
- [ ] Verify the real ceiling lights do not change.
- [ ] Optional: repeat with `--presence motion` and the Aqara motion sensor.

**Expected result:** Presence in the real room switches the virtual ceiling lights only.

**Result:** N/T

## 6. UC2 - DALI Panel + Dimmer -> Virtual Lights, XR -> Real Curtain

**Objective:** Verify that the real DALI panel (on/off, colour) and the real dimmer (on/off, brightness) drive the virtual ceiling lights, and that the virtual curtain (grab or Raise/Lower buttons) drives the real curtain.

### Test UC2.1 - Simulation Mode

- [ ] Start `python3 bridge/server.py --simulate` and the XR app.
- [ ] Verify the DALI panel model shows on and about 4350 K (`dali1.group0_kelvin`), and the dimmer model shows off, so the ceiling lights are dark.
- [ ] Try to change the dimmer and DALI panel models in XR. Verify they ignore the input while `online` (mirrored, read-only); use the test panel instead.
- [ ] Press **Lower** on the curtain controller. Verify the virtual curtain closes and the server logs a `curtain1 close` command.
- [ ] Release the button. Verify a `stop` command is sent.
- [ ] Press **Raise**. Verify the curtain opens (`open`).
- [ ] Grab the roller blind, move it, release it. Verify one `set_position` command is sent on release and the simulated curtain moves to that position.

**Expected result:** Commands reach the bridge only from user input, one per press/release, with no echo loop.

**Result:** N/T

### Test UC2.2 - Real Laboratory

- [ ] Start `python3 bridge/server.py` (real devices) and the XR app.
- [ ] Turn the real dimmer on and turn its knob. Verify the virtual dimmer knob and the ceiling brightness follow.
- [ ] Turn the real dimmer off. Verify the virtual ceiling lights go dark.
- [ ] Switch group 0 on the real DALI panel. Verify the virtual ceiling lights follow on/off (the bridge does not report the "all lamps" broadcast zone yet, see the note below).
- [ ] Change the colour temperature on the real DALI panel. Verify the virtual lights shift warm/cool (`dali1.group0_kelvin`; RGB is not sent by the bridge).
- [ ] Press **Lower** / **Raise** in XR. Verify the real curtain closes / opens within a few seconds, and release stops it.
- [ ] Grab and release the virtual curtain. Verify the real curtain moves to the released position.
- [ ] Move the real curtain from the Aqara app or its own switch. Verify the virtual curtain follows (`curtain1.position`).

**Expected result:** The real wall devices drive the virtual lights, nothing in XR changes the real lights, and the real and virtual curtains stay in sync in both directions.

**Note:** Curtain commands through the server have not yet been tested on the real curtain (bridge/README.md section 3). Only "all lamps" commands reach the DALI lamps until they are addressed again (bridge/README.md open issue 1), but the bridge does not report the broadcast zone yet: `server.py` sends only `group<N>_*`, so the virtual lights follow group 0 until the bridge sends `dali1.all_*` (bridge/README.md open issue 7). The dimmer and DALI panel models are read-only in XR while `online`; change them on the real devices.

**Result:** N/T

## 7. UC3 - Temperature, Tint Scale and Alarm

**Objective:** Verify the live temperature display, its tint, and the alarm above the threshold (26 °C, `--temp-alarm`), with and without `--alarm-actions` (close the curtain, play the alarm sound).

### Test UC3.1 - Simulation Mode

- [ ] Start `python3 bridge/server.py --simulate` and the XR app.
- [ ] Verify the temperature display and the room unit follow the simulated temperature (22-28 °C over two minutes).
- [ ] Verify the tint follows [temperature-tint-scale.md](temperature-tint-scale.md): green below 24 °C, light/medium red at 24-26 °C, deep red from 26 °C.
- [ ] Verify the camera floodlight switches on when the temperature rises above 26 °C and off when it falls back.
- [ ] Restart with `--alarm-actions --alarm-sound "Alarm Sound Effect.mp3"` (the default `alarm.mp3` does not exist; without a sound the server only closes the curtain). Verify that when the alarm starts the curtain closes and the speaker model shows playing.

**Expected result:** Display, tint and alarm follow the temperature; with `--alarm-actions` several devices react to one event.

**Result:** N/T

### Test UC3.2 - Real Laboratory

- [ ] Start `python3 bridge/server.py` and the XR app.
- [ ] Compare the virtual temperature with the real room sensor (`python3 bridge/lab.py sensor`).
- [ ] To trigger the alarm without heating the room, restart with `--temp-alarm` just below the current temperature. Verify the floodlight switches on.
- [ ] Only if the lab staff agree: restart with `--alarm-actions --alarm-sound "Alarm Sound Effect.mp3"`. Verify the real curtain closes and the real speaker plays the sound.
- [ ] Record any tests that cannot be performed safely with the available laboratory equipment.

**Expected result:** The real temperature is shown correctly in XR and the alarm responds to the configured threshold.

**Result:** N/T

## 8. Connection Failure

**Objective:** Verify that the XR app shows the bridge as offline and the virtual devices keep working without it.

### Test CF.1 - Bridge Offline

- [ ] With the XR app connected, stop the bridge server (Ctrl+C).
- [ ] Verify the test panel status line shows `offline` (the app retries every 2 seconds).
- [ ] Press **Raise** / **Lower** and grab the curtain. Verify the virtual curtain still moves (commands are dropped while offline).
- [ ] Use the test panel controls. Verify the virtual devices still respond.
- [ ] Start the server again. Verify the status returns to `online` within a few seconds and the virtual devices take the bridge's state.

**Expected result:** The app never blocks or crashes without the bridge, and reconnects on its own.

**Result:** N/T

### Test CF.2 - Lab Devices Offline

- [ ] Run `python3 bridge/server.py` (real mode) on a network without the lab devices.
- [ ] Verify the server reports every device `offline` and the app stays `online` to the bridge.
- [ ] Verify the green status indicator on the Siemens room unit model goes off (`room_sensor1.status`).

**Expected result:** Offline lab devices do not break the XR app.

**Result:** N/T

## 9. Preliminary Software and Connectivity Tests

**Test date:** 13 October 2026  
**Environment:** Windows laptop, Visual Studio Code, Python, college Wi-Fi  
**Project:** xr-smart-room

### Test PRE-01 — Python Script Startup

**Procedure:** Execute `python bridge/lab.py --help`.

**Expected result:** The script starts and displays the available commands without errors.

**Actual result:** The command completed successfully and displayed the available device commands.

**Result:** PASS

### Test PRE-02 — Device Diagnostic Command

**Procedure:** Execute `python bridge/lab.py check`.

**Expected result:** The script completes its read-only diagnostic and reports the connectivity status of laboratory devices.

**Actual result:** The diagnostic command executed and reported connection failures for Home Assistant, camera, room sensor, DALI, and KNX.

**Result:** PASS — diagnostic execution only. Device connectivity was not successful.

### Test PRE-03 — KNX Network Connectivity

**Procedure:** Connect to the college Wi-Fi and execute `ping 192.168.15.191`.

**Expected result:** The KNX/IP interface responds to network requests.

**Actual result:** The laptop received IP address `192.168.152.181`. All four ping requests timed out, with 100% packet loss.

**Result:** FAIL — no ping response received. The cause has not yet been confirmed.

### Testing Summary

The Python bridge script and its diagnostic command executed successfully.

Physical laboratory device connectivity could not be established from the tested network configuration. Access to the laboratory device network requires further investigation.

The functional tests for UC1, UC2, and UC3 remain **N/T (Not Tested)** until the required application and device connections are available.

### Test PRE-04 — Python Syntax Validation

**Procedure:** Execute `python -m py_compile bridge/lab.py bridge/server.py`.

**Expected result:** Both Python files compile without syntax errors.

**Actual result:** Both files compiled without reported syntax errors.

**Result:** PASS

### Test PRE-05 — Python Dependency Consistency

**Test date:** 13 October 2026

**Procedure:** Execute `python -m pip check`.

**Expected result:** No broken package requirements are detected.

**Actual result:** The terminal displayed `No broken requirements found.`

**Result:** PASS

### Test PRE-06 — Project Dependencies Installation

**Test date:** 13 October 2026

**Procedure:** Execute `python -m pip install -r bridge/requirements.txt`, followed by `python -m pip check`.

**Expected result:** Required Python packages are installed without dependency conflicts.

**Actual result:** Package installation completed successfully. The dependency check displayed `No broken requirements found.`

**Result:** PASS

### Test PRE-07 — Bridge Server Help Command

**Test date:** 13 October 2026

**Procedure:** Execute `python bridge/server.py --help`.

**Expected result:** The server script displays available command-line options and exits without errors.

**Actual result:** The help menu was displayed successfully, including the `--simulate` option. The script exited normally.

**Result:** PASS

### Test PRE-08 — Bridge Server Simulation Mode

**Test date:** 13 October 2026

**Procedure:** Execute `python bridge/server.py --simulate`.

**Expected result:** The bridge server starts in simulation mode and generates virtual device events without requiring laboratory hardware.

**Actual result:** The server started and continuously displayed simulated events, including motion detection, camera occupancy, virtual light state changes, temperature alarms, and DALI lamp status changes.

**Result:** PASS — simulation server startup and event generation.

**Note:** This test does not verify the Unity application or the complete UC1–UC3 workflows.

### Test PRE-09 — Local WebSocket Port Availability

**Test date:** 13 October 2026

**Procedure:** Start the bridge server using `python bridge/server.py --simulate` and check TCP connectivity to `127.0.0.1:8765`.

**Expected result:** The server accepts TCP connections on port 8765.

**Actual result:** The terminal displayed `WebSocket port 8765: True`.

**Result:** PASS — TCP port availability only.

**Note:** WebSocket message exchange and Unity integration have not yet been tested.


### Test PRE-10 — WebSocket Message Reception

**Test date:** 13 October 2026

**Procedure:** Start the bridge server using `python bridge/server.py --simulate`, then execute `python bridge/test_websocket.py` in a second terminal.

**Expected result:** The client connects to the WebSocket server and receives a simulated device message.

**Actual result:** The client successfully connected and received a JSON message containing the device `curtain1`, property `status`, and value `simulated`.

**Result:** PASS

**Note:** This confirms WebSocket communication with the simulation server. Unity integration and complete UC1–UC3 functionality remain untested.

### Test PRE-11 — WebSocket Client Reconnection

**Test date:** 13 October 2026

**Procedure:** Run `python bridge/test_websocket.py` a second time while the simulation server remains active.

**Expected result:** A new WebSocket connection is established and a simulated device message is received.

**Actual result:** The client connected successfully and received another JSON message from `curtain1`.

**Result:** PASS

**Note:** This test verifies a new connection after the previous client exited, not simultaneous connections.