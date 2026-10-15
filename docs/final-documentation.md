# XR Smart-Room Twin — Final Documentation

**Project:** Erasmus+ BIP — XR Smart-Room Twin  
**Institution:** TalTech Virumaa College  
**Project period:** 5–16 October 2026

## 1. Project Overview

XR Smart-Room Twin is an extended reality (XR) application designed to demonstrate the interaction between a virtual smart room and real KNX building automation devices.

The project combines a Unity-based virtual environment with MQTT communication and a KNX–MQTT bridge. It supports both simulated device behaviour and communication with physical laboratory equipment.

The application demonstrates three main use cases:

- **UC1 — Wall Switch → Lamp:** A virtual wall switch controls the lamp and displays its current state.
- **UC2 — Motion Sensor → Automatic Light:** A PIR motion sensor detects movement and controls the lighting automatically.
- **UC3 — Temperature Warning → Ventilation:** Temperature changes trigger visual warnings and ventilation behaviour.

The project is designed to work in two modes:

- **SimulatedLink:** Virtual devices operate without a connection to real KNX hardware.
- **MqttLink:** The application exchanges device states and commands with the laboratory system through MQTT.

The goal is to provide an interactive demonstration of smart-building automation and show how virtual and physical devices can remain synchronized.


## 2. System Architecture

The XR Smart-Room Twin system is designed around the following components:

- **Unity 2022.3.62f3:** Provides the virtual smart-room environment and interactive device models.
- **VRTK v4:** Supports XR interactions with virtual objects.
- **SimulatedLink:** Handles virtual device behaviour without external hardware.
- **MqttLink:** Connects the Unity application to the MQTT messaging system.
- **Mosquitto MQTT Broker:** Exchanges messages between Unity and the KNX bridge.
- **Python KNX–MQTT Bridge:** Translates MQTT messages into KNX commands and publishes KNX device states to MQTT.
- **KNX Gateway:** Provides access to the physical KNX laboratory devices.

### 2.1 Communication Flow

In laboratory mode, the planned communication path is:

`Unity → MqttLink → Mosquitto MQTT Broker → Python KNX–MQTT Bridge → KNX Gateway → Physical KNX Devices`

Device state updates are sent back through the bridge and MQTT broker to the Unity application.

### 2.2 Simulation Mode

When SimulatedLink is selected, the application operates without the MQTT broker or KNX laboratory equipment.

This mode allows the three use cases to be demonstrated and tested using virtual devices.

### 2.3 Connection Failure

The application is intended to indicate when the external connection is unavailable.

SimulatedLink provides a fallback for demonstrating virtual device behaviour without an active KNX connection.

## 3. MQTT Topics and Device Mapping

The XR Smart-Room Twin project uses MQTT topics to exchange commands and device states between Unity and the KNX–MQTT bridge.

### 3.1 MQTT Topic List

| MQTT Topic | Purpose |
|---|---|
| `lab/light/main/set` | Sends a command to control the main lamp. |
| `lab/light/main/state` | Reports the current state of the main lamp. |
| `lab/motion/pir1/state` | Reports motion detection from the PIR sensor. |
| `lab/climate/temp1/state` | Reports the current temperature. |
| `lab/climate/alarm` | Reports the temperature alarm state. |
| `lab/fan/vent1/set` | Sends a command to control the ventilation fan. |
| `lab/fan/vent1/state` | Reports the current ventilation fan state. |

### 3.2 KNX Group Address Mapping

The Python KNX–MQTT bridge requires KNX group addresses and corresponding Data Point Types (DPTs) to communicate with physical devices.

The exact group addresses must be obtained from the laboratory's ETS configuration or confirmed by the team responsible for the KNX installation.

**Current status:** The group addresses have not yet been confirmed. Placeholder addresses in the bridge documentation must not be used as real laboratory addresses.

| Device | KNX Group Address | DPT | Status |
|---|---|---|---|
| Main lamp — command | TBD | TBD | Awaiting confirmation |
| Main lamp — state | TBD | TBD | Awaiting confirmation |
| PIR motion sensor — state | TBD | TBD | Awaiting confirmation |
| Temperature sensor — value | TBD | TBD | Awaiting confirmation |
| Ventilation fan — command | TBD | TBD | Awaiting confirmation |
| Ventilation fan — state | TBD | TBD | Awaiting confirmation |

### 3.3 Mapping Verification

Before laboratory testing, the team must confirm that:

- Each MQTT topic is associated with the correct KNX group address.
- Each group address uses the correct DPT.
- Commands reach the intended physical device.
- State updates are published to the correct MQTT topic.
- The XR application displays the received device state correctly.

## 4. Use Case Descriptions

The XR Smart-Room Twin project includes three main use cases that demonstrate smart-building automation in a virtual environment.

UC1: Motion → light

Goal: Show that a real sensor event changes the XR scene and that logic reacts to it.

Devices: Aqara camera (via Frigate), virtual ceiling lights, room “occupied” indicator.

Preconditions: The bridge is running, either connected to Frigate or in --simulate. Camera and lights show their connection status (real, simulated or offline) on their info panels.

Main flow:

A person enters the camera’s view and Frigate reports a person detection.
The bridge sends a camera1 motion/presence message over WebSocket.
Unity marks the room as occupied, and the camera panel shows the detection.
The virtual ceiling lights turn on.
When the camera no longer sees anyone, the room returns to empty.

Alternative flow: If Frigate is unreachable, the camera shows offline and simulation mode can generate motion events instead.

Result: The virtual lights follow the camera’s presence state. The real lights are not touched, because the DALI panel and dimmer own them.

UC2: XR control of light and curtains

Goal: Show XR interaction (press, grab, slide) and two-way sync with real devices.

Devices: DALI panel (Lunatone), dimmer (Aqara H2), curtain driver (Aqara E1), curtain controller model.

Preconditions: Home Assistant and the DALI panel are reachable, or the bridge is simulating them.

Main flow, lights (real → virtual):

A person switches the lamps or changes the RGB color on the real DALI panel.
The bridge reads the new state, and the virtual ceiling lights follow with the same on/off state and color tint.
A person turns the real dimmer’s knob (0–100%).
The bridge passes on the level, and the virtual lights brighten or dim. The dimmer model’s knob turns in XR to match.

Main flow, curtains (XR → real):

The user grabs the virtual curtain, or presses Lower/Raise on the controller model.
The virtual curtain moves, and releasing the button stops it where it is.
With the bridge connected, the same action sends close/open or a position (0–100%) to the real curtain.
If someone uses the real wall switch, the virtual curtain animates to match.

Alternative flow: In simulation mode the curtain still moves in XR, with no real command sent.

Result: Both real wall devices drive the virtual lights, and the curtain stays in sync in both directions. Until the DALI lamps get individual addresses, all virtual lights show the same state.

UC3: Temperature monitoring and alarm

Goal: Show a measured value, a warning, and several devices reacting to one event.

Devices: Room sensor (via the BACnet/IP gateway), speaker, curtains, warning panel.

Preconditions: The alarm limit is configured (default 26 °C, to be confirmed) and the room sensor is readable, either real or simulated.

Main flow:

The bridge reads the room sensor and publishes the temperature, humidity and CO₂.
XR shows the value above the sensor and tints the room along the 9-step blue/green/red scale.
The temperature rises above the limit.
A Temperature too high warning panel appears with the value and time.
The speaker plays an alert sound and the curtains start closing, with their progress shown on the panel.
The user can press Mute sound or Show sensor.

Alternative flow: If the sensor goes offline, the display greys out and shows the connection status. In simulation mode the bridge generates a slowly changing temperature, so the alarm can be demonstrated without the lab.

Result: One sensor reading triggers the warning, the sound and the curtain movement, and the tint shows how close the room is to the limit.

### 4.1 UC1 — Wall Switch → Lamp

**Purpose:** Control the main lamp using a virtual wall switch.

**Planned behaviour:**

1. The user presses the virtual wall switch.
2. The switch rotates 180° to indicate its new state.
3. The lamp changes between ON and OFF.
4. When ON, the virtual lamp displays a yellow emissive effect.
5. In laboratory mode, the command is transmitted through MQTT and the KNX bridge.
6. The XR lamp state is synchronized with the real KNX lamp state.

**Acceptance criteria:**

- All 10 consecutive switch presses are registered without double toggles.
- The virtual switch and lamp correctly reflect their states.
- The real KNX lamp responds within 1 second.

### 4.2 UC2 — Motion Sensor → Automatic Light

**Purpose:** Automatically control the lamp based on motion detection.

**Planned behaviour:**

1. The user enters the virtual PIR sensor's detection cone.
2. The sensor indicator LED turns green.
3. The detection cone briefly highlights.
4. The lamp turns ON automatically.
5. After the user leaves the detection area, a 10-second inactivity timer begins.
6. The lamp turns OFF when the timer expires, unless a manual ON override is active.
7. In laboratory mode, motion events are received from the real KNX presence detector through MQTT.

**Acceptance criteria:**

- The lamp turns ON within 0.5 seconds after motion detection.
- The lamp turns OFF after 10 seconds without motion, unless manually overridden.
- The virtual sensor correctly represents the received motion state.

### 4.3 UC3 — Temperature Warning → Ventilation

**Purpose:** Display the temperature and activate an overheating warning and ventilation when necessary.

**Planned behaviour:**

1. The application receives a temperature value from a virtual slider or real KNX sensor.
2. The temperature is displayed on the virtual thermostat.
3. When the configured threshold is exceeded, a red warning appears.
4. The ventilation fan starts spinning.
5. When the temperature falls below the reset threshold, the warning clears and the fan stops.
6. A hysteresis of 1 °C prevents repeated switching near the threshold.

**Acceptance criteria:**

- The displayed temperature matches the input value.
- The warning and fan activate at the configured threshold.
- The alarm resets according to the 1 °C hysteresis.

**Threshold clarification:** The project concept specifies 27 °C, while the original assignment mentions 26 °C. The team must confirm the final threshold before testing.


## 5. Testing and Validation

The XR Smart-Room Twin application will be tested against the acceptance criteria defined for UC1, UC2, and UC3.

The planned laboratory testing date is **15 October 2026** at TalTech Virumaa College.

### 5.1 Test Conditions

Testing is divided into three conditions:

- **Simulation Mode (SimulatedLink):** Verifies the behaviour of virtual devices without real KNX hardware.
- **Real Laboratory Mode (MqttLink):** Verifies MQTT communication, KNX device responses, and synchronization between virtual and physical devices.
- **Connection Failure:** Verifies the offline connection indicator and the ability to continue the demonstration in simulation mode.

### 5.2 Test Checklist

Detailed test procedures are documented in:

`docs/test-checklist.md`

The checklist contains nine test cases covering the three use cases under all three test conditions.

Each test includes:

- Steps to perform.
- Expected results.
- A test result field.

### 5.3 Test Result Status

The following result values are used:

- **PASS:** The test meets the expected result.
- **FAIL:** The test does not meet the expected result.
- **N/T:** The test has not yet been performed.

**Current status:** Testing is pending. No test cases are reported as passed or failed until they have been executed and their results recorded.

### 5.4 Issues to Confirm Before Testing

Before laboratory validation, the team must:

- Confirm the KNX group addresses and Data Point Types (DPTs).
- Verify that the MQTT broker and KNX–MQTT bridge are available.
- Confirm the final UC3 temperature threshold (26 °C or 27 °C).
- Ensure that both SimulatedLink and MqttLink modes are ready for testing.


## 6. Known Limitations and Pending Items

This section records the project items that require confirmation or further validation before the final demonstration.

### 6.1 KNX Group Addresses

The actual KNX group addresses and Data Point Types (DPTs) have not yet been confirmed.

The KNX–MQTT bridge documentation currently contains placeholder addresses. These must be replaced with the correct values from the laboratory ETS configuration.

**Status:** Awaiting confirmation from the team.

### 6.2 Temperature Alarm Threshold

Two different temperature thresholds appear in the project materials:

- **26 °C** in the original assignment.
- **27 °C** in the project concept.

The final threshold must be agreed upon and used consistently in the application, test checklist, and documentation.

**Status:** Awaiting confirmation.

### 6.3 Laboratory Integration

Communication between Unity, the MQTT broker, the Python KNX–MQTT bridge, and physical KNX devices must be verified in the laboratory.

The documentation describes the planned integration architecture but does not yet establish that all physical device interactions have passed testing.

**Status:** Laboratory validation pending.

### 6.4 Connection Failure and Offline Operation

The project includes a planned offline indication and simulation fallback when the external connection becomes unavailable.

The behaviour must be verified by disconnecting the MQTT broker or KNX bridge and testing the virtual devices in SimulatedLink mode.

**Status:** Testing pending.

### 6.5 Final Test Results

The detailed test checklist is available in `docs/test-checklist.md`.

All test results currently remain marked as **N/T (Not Tested)** until the corresponding procedures have been performed.

**Status:** Testing planned for 15 October 2026.

## 7. Conclusion and Next Steps

The XR Smart-Room Twin project is designed to demonstrate the integration of extended reality with KNX building automation through MQTT communication.

The project covers three main use cases: virtual lighting control, motion-based automatic lighting, and temperature-based ventilation control.

The documentation describes the planned system architecture, MQTT communication topics, device mapping, expected behaviour, and testing procedures.

### 7.1 Next Steps

Before the final project demonstration, the team should:

1. Confirm the real KNX group addresses and Data Point Types (DPTs).
2. Update the KNX–MQTT bridge configuration with the confirmed addresses.
3. Agree on the final UC3 temperature alarm threshold.
4. Complete the integration of the Unity application with the MQTT broker and KNX laboratory devices.
5. Execute the UC1–UC3 tests using `docs/test-checklist.md`.
6. Record actual test results and document any unresolved issues.
7. Prepare and rehearse the final demonstration, including the simulation fallback.

### 7.2 Final Demonstration

The final project demonstration is planned for **16 October 2026**.

The demonstration should present the three use cases, explain the system architecture, and show how the application communicates with KNX devices.

If the laboratory connection is unavailable, SimulatedLink should be used to demonstrate the virtual device interactions.

**Documentation status:** Initial documentation prepared. Final updates are required after integration and laboratory testing.


## 8. Blender 3D Assets

The project includes Blender assets representing the TalTech Virumaa College KNX laboratory and its interactive devices.

The main laboratory model is stored in `blender/xr_knx_lab.blend`. It includes room geometry, furniture, windows, blinds, lighting, ventilation equipment, and KNX device models.

Additional assets include:

- `blender/xr_knx_devices.blend` — KNX device models.
- `blender/xr_hands.blend` — XR hand models.
- `blender/export/xr_knx_devices.fbx` — exported KNX device meshes.
- `blender/export/xr_hand_left.fbx` — exported left-hand model.
- `blender/export/xr_hand_right.fbx` — exported right-hand model.

The laboratory geometry was created using estimated dimensions based on reference photographs. Actual room measurements have not yet been verified.

The Blender scripts provide scene setup, device preview behaviour, and FBX export functionality. Successful integration of these assets into Unity must be confirmed separately.

## Preliminary Testing Results — 13 October 2026

Preliminary software testing was performed on a Windows laptop using Python and Visual Studio Code.

The following components were successfully checked:

- Python command-line tools and bridge server help commands.
- Python syntax validation.
- Installation and consistency of Python dependencies.
- Bridge server startup in simulation mode.
- Generation of simulated device events.
- Local WebSocket port availability (port 8765).
- Successful WebSocket connection and JSON message reception.
- Successful reconnection of the WebSocket client.

**Laboratory connectivity:** The laboratory devices could not be reached from the tested college Wi-Fi connection. Further network access configuration is required.

**Current testing status:** Preliminary software tests were successful. Full functional testing of UC1, UC2, and UC3 in Unity and with real laboratory devices has not yet been performed.

Detailed test procedures and results are recorded in `docs/test-checklist.md`.

## DALI Addressing Status — 13 October 2026

The laboratory uses a Lunatone DALI-2 Display panel with a REST API at `192.168.15.120`.

According to the existing device documentation, the panel has records for 10 DALI lamps with short addresses 0–9, organized into three groups:

| DALI Group | Recorded Lamp Short Addresses |
|---|---|
| G0 | 0, 9 |
| G1 | 1, 2, 3, 4 |
| G2 | 5, 6, 7, 8 |

The panel is connected directly to the DALI line rather than operating as a KNX switch. No KNX group addresses were observed when the panel was operated.

**Current limitation:** Broadcast control has been reported to work, but individual lamp and group control do not respond correctly. The recorded DALI addresses and group assignments may no longer match the physical devices.

**Next step:** Laboratory staff should verify the actual DALI addressing and group configuration using the appropriate configuration tools. Addressing or reset operations must not be performed without authorization.

**Status:** Address information documented; physical addressing verification pending.