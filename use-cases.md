# XR Application Use Cases - KNX Lab Devices

Use cases per device, written to fit the brief: Unity 2022.3 + VRTK v4, at least 2-3 distinct use cases, and a separate data-exchange layer on the local network.

## Speaker

1. **Virtual doorbell or intercom:** The user presses a virtual doorbell in XR and the real speaker plays a chime. *(XR -> real device)*
2. **Audible alarm:** When a temperature limit is crossed or the camera detects motion, the speaker sounds an alert and a red warning panel appears in XR. *(warning use case)*
3. **Volume knob:** The user grabs and turns a virtual knob, and the real volume follows. A bar in XR shows the current level. *(grab interaction + value display)*

## Curtains

1. **Grab the curtain:** The user drags the virtual curtain open or closed and the real motor follows to the same position (0-100%).
2. **Live mirroring:** Someone uses the real wall switch, and the virtual curtain animates to match. *(real state -> XR)*
3. **Sun protection:** Above a set temperature (or light level), the curtains close by themselves and a message explains why.

## Camera

1. **Live video panel:** A floating window in XR shows the camera feed (MJPEG/RTSP -> Unity texture). Point at the camera model to open it. *(information panel)*
2. **Motion -> lamp:** Motion on the camera turns on the lamp in XR and, optionally, the real one. This matches the brief's own example.
3. **Presence indicator:** The room in XR shows "occupied" or "empty" based on camera detection.

## Temperature Sensor

1. **Live reading:** A 3D thermometer or text label above the sensor shows the real value. *(required "measured value displayed")*
2. **Colour overlay:** The room tints blue, green or red depending on temperature (heatmap-style).
3. **Threshold warning:** Past a set limit, a warning pops up, the speaker beeps and the curtains close. Triggers several devices at once.

## Light Dimmer

1. **Virtual slider:** The user drags a slider in XR, the real lamp dims, and the virtual lamp's brightness matches.
2. **Two-way sync:** Dimming at the real wall panel updates the XR lamp's intensity.
3. **Scenes:** Buttons like "Movie / Work / Off" set dimmer level, curtain position and speaker together.

## BACnet/IP Gateway

Assumes it is the gateway that exposes KNX values as BACnet objects - confirm with the lab.

1. **Second protocol path:** Read the temperature over BACnet/IP instead of KNX, showing the data layer supports more than one protocol. Good material for the architecture section.
2. **Building dashboard:** A floating BMS-style panel lists all BACnet object values (name, value, status).
3. **Fault display:** If a BACnet value goes offline or reports a fault flag, the device in XR turns grey and shows a warning icon.

## DALI Panel

1. **Individual lamp control:** Point at a specific virtual light fixture and switch or dim only that one. With DALI, each light has its own address.
2. **Lamp failure:** DALI reports a broken lamp, and that fixture in XR flashes red.
3. **Group control:** A virtual control panel switches DALI groups or scenes, showing group control versus single-lamp control.

---

## Suggested Demo Set

These three cover every required category, use clearly different devices, and stay low risk:

| # | Use case | What it proves |
|---|---|---|
| 1 | Camera motion -> lamp on (XR + real DALI/dimmer) | Real sensor -> XR and XR -> real device |
| 2 | Dimmer slider + curtain grab in XR, synced both ways | XR interaction (press, grab, slide) and real control |
| 3 | Temperature display + threshold alarm (speaker + curtains + warning) | Measured value, warning, several devices reacting |

If time allows, use BACnet/IP as the source for the temperature reading in #3. It adds a second protocol to the architecture diagram without adding a new use case.

## Architecture

Unity (VRTK) <-> data layer (e.g. a small Node.js or Python service using MQTT or WebSocket) <-> KNX IP interface, BACnet/IP and the camera stream.

Add a "simulation mode" switch in the data layer so the demo still works if the lab connection fails on defense day.
