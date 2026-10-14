# Concept: XR Smart Room - KNX Lab Digital Twin

**Project:** Development of a Practical XR Application Prototype (Erasmus+ BIP, TalTech Virumaa College, 5-16.10.2026)
**Team:** Orange Team - Serhii Voitov, Miska Sebastian Voutilainen, Lode Van Hoof, Pjotr Harlamov, Natalia Luneva

---

## 1. Idea

An XR "smart room" in which the user sees and controls the devices of the KNX laboratory stand. Each virtual device mirrors a real one: when the real device changes, the virtual one changes too, and controlling the virtual device can control the real one. The application can run fully simulated, connected to the real stand, or a mix of both.

## 2. Objectives

- Visualize the state of real sensors and actuators in XR (on/off, levels, measured values, warnings).
- Let the user interact with devices using natural XR actions: press, grab, slide, point.
- Allow flexible placement of virtual devices in the scene.
- Communicate with the real stand through a separate data-exchange layer on the local network.
- Demonstrate at least three clearly distinguishable use cases.

## 3. Devices

| Device | Role | Data |
|---|---|---|
| Ceiling lights | Actuator | RGB lamps: on/off, brightness, color |
| Light dimmer | Sensor / status | Real wall switch (Aqara Dimmer Switch H2): on/off and knob level 0-100%, drives the brightness of the virtual ceiling lights |
| DALI panel | Actuator / status | Real panel that drives the virtual ceiling lights: color (RGB), lamp on/off, group, lamp failure |
| Curtains | Actuator | Position 0-100%, moving/stopped |
| Temperature sensor | Sensor | Temperature in degrees Celsius |
| Camera | Sensor | Video stream, motion/presence |
| Speaker | Actuator | Play sound, volume |
| BACnet/IP gateway | Communication | Exposes KNX values as BACnet objects |

### Ceiling lights

The white lights on the ceiling are RGB lamps. Two controls sit next to each other on the wall (the DALI panel is where it sits in the room render, the dimmer is next to it):

- **DALI panel (real -> virtual)** - the real DALI panel in the lab controls the virtual ceiling lights. When someone switches the lamps or changes the RGB color on the real panel, the bridge reads the new state and the virtual lights follow: on/off and the color tint.
- **Dimmer (real -> virtual)** - the real dimmer switch on the wall sets the brightness of the virtual ceiling lights. Turning its knob changes the level (0-100%), and the bridge passes it on so the virtual lights brighten or dim. The dimmer model in XR (`01_Zigbee_Dimmer`) mirrors the real switch: its knob turns and its on/off state follows the real one.

So both real wall devices drive the virtual lights: the color and on/off state come from the DALI panel, the brightness from the dimmer. Nothing in XR controls the real lights. Until the lamps are given individual DALI addresses, the panel only reaches all ceiling lights at once (broadcast), so all virtual lights show the same state.

### Curtain controller

The two-button controller model (Aqara bead-chain controller, `05_Aqara_Controller`) operates the curtains in the virtual room:

- **Lower** button - closes the virtual curtains.
- **Raise** button - opens them again.

Pressing a button with the XR controller or hand moves the virtual curtain; releasing it stops the curtain where it is. The button press is a virtual control first: the curtain closes in XR even when the real stand is not connected (simulation mode). When the bridge is connected, the same press can also send `close`/`open` to the real curtain, like the grab interaction in UC2.

## 4. Use Cases

### Core use cases (demo)

**UC1 - Motion -> light**
The camera detects motion. The room is marked "occupied" in XR and the virtual ceiling lights turn on. The real lights stay under the control of the DALI panel and the dimmer.
*Proves: real sensor -> XR, and logic reacting in the XR scene.*

**UC2 - XR control of light and curtains**
The lights are controlled with the DALI panel and the dimmer: the real DALI panel sets the color and on/off state of the virtual ceiling lights, and the real dimmer switch sets their brightness. The user grabs the virtual curtain to open or close it, and the real curtain follows. Changes made on the real devices update the XR scene.
*Proves: XR interaction (press, grab, slide) and real device control.*

**UC3 - Temperature monitoring and alarm**
The real temperature is shown above the sensor as a label or thermometer, and the room tints according to the value. Above a defined limit, a warning panel appears, the speaker sounds an alert and the curtains close.
*Proves: measured value display, warning visualization, several devices reacting to one event.*

### Optional extensions

- Live camera feed on a floating panel in XR.
- Scene buttons ("Work", "Presentation", "Off") setting light, curtains and speaker together.
- DALI lamp failure shown as a flashing red fixture.
- BACnet dashboard panel listing all gateway objects and their status.
- Temperature read via BACnet/IP instead of KNX, to show a second protocol path.

## 5. XR Interactions

| Interaction | Used for |
|---|---|
| Press (button) | Scenes, doorbell/speaker, curtain controller raise/lower |
| Grab and move | Curtain position, placing devices in the room |
| Slide / rotate | Speaker volume |
| Point and select | Open a device's information panel, select an individual DALI lamp |

Each device has an information panel showing its name, current state, last update time and connection status (real / simulated / offline).

## 6. Architecture

```
+--------------------------+
|  Unity 2022.3 + VRTK v4  |
|  - 3D room and devices   |
|  - XR interactions       |
|  - Device state model    |
+------------+-------------+
             | MQTT or WebSocket (JSON)
+------------v-------------+
|     Data-exchange layer   |
|  (Python or Node.js, runs |
|   on a PC in the lab)     |
|  - Protocol adapters      |
|  - Simulation mode        |
|  - Rules (limits, alarms) |
+--+---------+---------+---+
   |         |         |
 KNX/IP   BACnet/IP  Camera stream
   |         |      (MJPEG/RTSP)
+--v---------v--+     +--v-----+
| KNX lab stand |     | Camera |
| dimmer, DALI, |     +--------+
| curtains,     |
| temp, speaker |
+---------------+
```

**Message format (example):**

```json
{ "device": "dimmer1", "property": "level", "value": 60, "source": "real", "timestamp": "2026-10-13T10:15:00Z" }
```

- Unity subscribes to device state topics and publishes commands; it never talks to KNX or BACnet directly.
- **Simulation mode:** the data layer generates fake values (e.g. a slowly changing temperature) so development and the demo work without the lab connection.
- BACnet uses UDP port 47808 on the lab subnet; the data-layer PC must be on the same network as the gateway.

## 7. Technology

| Area | Choice |
|---|---|
| Engine | Unity 2022.3.62f3 |
| XR framework | VRTK v4 |
| Data layer | Python (BAC0, xknx, paho-mqtt) or Node.js |
| Messaging | MQTT (e.g. Mosquitto broker) or WebSocket |
| Tools | YABE (BACnet explorer), ETS (KNX), Git |
| 3D models | Blender / Unity primitives |

## 8. Work Plan

| Day | Focus |
|---|---|
| Virtual week (5-9.10) | Concept, 3D models of devices, Unity scene setup |
| Mon 12.10 | Lab access, find device IPs and object lists, data layer skeleton |
| Tue 13.10 | UC2 in simulation, then connected to the real dimmer/curtains |
| Wed 14.10 | Excursion; UC1 and UC3 in simulation |
| Thu 15.10 | Real connections for UC1/UC3, testing, documentation |
| Fri 16.10 | Final fixes, project defense |

## 9. Testing

- Each XR interaction (press, grab, slide, select) works in the headset.
- States in XR match the real devices in both directions.
- Each of UC1-UC3 works end to end, in simulation and with the real stand.
- The application handles connection loss: devices show "offline" and simulation mode can be switched on.

## 10. Risks

| Risk | Mitigation |
|---|---|
| No access to the lab network or devices | Simulation mode, so everything can be demonstrated without the stand |
| Unknown IPs or object mapping | Discover with YABE/ETS, confirm with lab staff |
| Unsafe control of real equipment | Write only to devices approved by staff, use low BACnet priority |
| Camera stream latency in Unity | Use low-resolution MJPEG, or use motion events only |
| Limited time | Core use cases first, extensions only if time allows |

## 11. Deliverables

- Working XR prototype in Unity with at least three use cases.
- Data-exchange layer with simulation mode.
- Short documentation: objective, devices and software, architecture diagram, use cases, user instructions, results and further development.
