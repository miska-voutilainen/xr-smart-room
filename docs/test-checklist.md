# XR Smart-Room Twin — Test Checklist

**Project:** Erasmus+ BIP — XR Smart-Room Twin  
**Test date:** 15 October 2026  
**Location:** TalTech Virumaa College, KNX Laboratory

## 1. Testing Objective

The purpose of testing is to verify the correct operation of the three main use cases (UC1–UC3) of the XR Smart-Room Twin application.

Testing will be performed in three different conditions:

- **Simulation mode (SimulatedLink):** Testing virtual devices without connecting to real KNX hardware.
- **Real laboratory mode (MqttLink):** Testing communication between the XR application and real KNX devices through MQTT.
- **Connection failure:** Testing application behaviour when the MQTT broker or KNX connection becomes unavailable.

Each test will be marked with one of the following results:

- **PASS** — The test completed successfully.
- **FAIL** — The test did not meet the expected result.
- **N/T** — The test has not been performed.

## 2. UC1 — Wall Switch → Lamp

**Objective:** Verify that pressing the virtual wall switch correctly controls the lamp and updates its state.

### Test UC1.1 — Simulation Mode

- [ ] Start the application in SimulatedLink mode.
- [ ] Press the virtual wall switch 10 times.
- [ ] Verify that the lamp alternates between ON and OFF after every press.
- [ ] Verify that the switch rotates 180° when its state changes.
- [ ] Verify that the lamp turns yellow and emits light when ON.
- [ ] Verify that the lamp turns OFF when the switch is pressed again.

**Expected result:** All 10 presses are registered correctly, with no double toggles.

**Result:** N/T

### Test UC1.2 — Real Laboratory

- [ ] Connect the application to the MQTT broker using MqttLink.
- [ ] Press the virtual wall switch.
- [ ] Verify that the real KNX lamp changes state within 1 second.
- [ ] Verify that the XR lamp matches the real lamp state.
- [ ] Compare the displayed state with `lab/light/main/state`.

**Expected result:** The real and virtual lamps remain synchronized.

**Result:** N/T

### Test UC1.3 — Connection Failure

- [ ] Disconnect the MQTT broker.
- [ ] Verify that the application indicates the connection is offline.
- [ ] Switch to SimulatedLink mode.
- [ ] Press the virtual wall switch.
- [ ] Verify that the virtual lamp continues working.

**Expected result:** The application remains functional in simulation mode without a KNX connection.

**Result:** N/T

## 3. UC2 — Motion Sensor → Automatic Light

**Objective:** Verify that the motion sensor detects movement, automatically controls the lamp, and correctly handles the timeout and manual override.

### Test UC2.1 — Simulation Mode

- [ ] Start the application in SimulatedLink mode.
- [ ] Enter the virtual PIR sensor's detection cone.
- [ ] Verify that the sensor indicator LED turns green.
- [ ] Verify that the detection cone briefly highlights.
- [ ] Verify that the lamp turns ON within 0.5 seconds.
- [ ] Leave the detection area.
- [ ] Verify that the lamp turns OFF after 10 seconds without motion.
- [ ] Turn the lamp ON manually using the virtual wall switch.
- [ ] Verify that the manual ON state overrides the automatic timeout.

**Expected result:** The sensor detects movement, activates the lamp within 0.5 seconds, and switches it off after 10 seconds of inactivity unless manual control overrides it.

**Result:** N/T

### Test UC2.2 — Real Laboratory

- [ ] Connect the application to the MQTT broker using MqttLink.
- [ ] Verify that the KNX–MQTT bridge is connected.
- [ ] Walk past the real KNX presence detector.
- [ ] Verify that the topic `lab/motion/pir1/state` receives a detection message.
- [ ] Verify that the virtual PIR indicator turns green.
- [ ] Verify that the virtual lamp turns ON.
- [ ] Verify that the displayed state matches the received MQTT messages.

**Expected result:** Motion detected by the real KNX sensor is correctly transmitted to the XR application and activates the virtual lamp.

**Result:** N/T

### Test UC2.3 — Connection Failure

- [ ] Disconnect the MQTT broker or KNX bridge.
- [ ] Verify that the application indicates the connection is offline.
- [ ] Switch to SimulatedLink mode.
- [ ] Enter the virtual sensor's detection area.
- [ ] Verify that the virtual lamp still turns ON.
- [ ] Leave the detection area and verify that the automatic timeout still works.

**Expected result:** The virtual motion sensor and automatic lighting continue functioning in simulation mode without a real KNX connection.

**Result:** N/T

## 4. UC3 — Temperature Warning → Ventilation

**Objective:** Verify that the temperature is displayed correctly, the overheating alarm activates at the configured threshold, and the ventilation fan responds appropriately.

**Note:** The project concept specifies a default threshold of 27 °C and a hysteresis of 1 °C. The task description mentions 26 °C. The final threshold must be confirmed before testing.

### Test UC3.1 — Simulation Mode

- [ ] Start the application in SimulatedLink mode.
- [ ] Set the temperature slider to 22 °C.
- [ ] Verify that the thermostat displays the correct temperature.
- [ ] Gradually increase the temperature to 30 °C.
- [ ] Verify that the warning panel appears when the configured alarm threshold is exceeded.
- [ ] Verify that the thermostat display turns red.
- [ ] Verify that the ventilation fan starts spinning.
- [ ] Lower the temperature below the alarm threshold minus 1 °C.
- [ ] Verify that the warning disappears and the fan stops.

**Expected result:** The alarm and ventilation fan respond correctly to temperature changes, including the 1 °C hysteresis.

**Result:** N/T

### Test UC3.2 — Real Laboratory

- [ ] Connect the application to the MQTT broker using MqttLink.
- [ ] Verify that the KNX–MQTT bridge is connected.
- [ ] Check the temperature received from the real KNX sensor.
- [ ] Verify that `lab/climate/temp1/state` publishes the temperature value.
- [ ] Compare the MQTT value with the XR thermostat display.
- [ ] Verify that the alarm and fan respond correctly if the temperature crosses the configured threshold.
- [ ] Record any tests that cannot be performed safely with the available laboratory equipment.

**Expected result:** The real KNX temperature value is correctly displayed in XR, and the alarm logic responds according to the configured threshold.

**Result:** N/T

### Test UC3.3 — Connection Failure

- [ ] Disconnect the MQTT broker or KNX bridge.
- [ ] Verify that the application indicates the connection is offline.
- [ ] Switch to SimulatedLink mode.
- [ ] Change the temperature using the virtual slider.
- [ ] Verify that the temperature display continues updating.
- [ ] Increase the temperature above the configured threshold.
- [ ] Verify that the warning appears and the virtual fan starts.
- [ ] Lower the temperature below the reset threshold.
- [ ] Verify that the warning clears and the fan stops.

**Expected result:** Temperature monitoring, overheating warnings, and virtual ventilation continue functioning in simulation mode without a real KNX connection.

**Result:** N/T

## 5. Preliminary Software and Connectivity Tests

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