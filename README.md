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
Unity + VRTK  <-- MQTT / WebSocket -->  Data layer  <-->  KNX/IP, BACnet/IP, camera
```

Unity never talks to the lab protocols directly. The data layer translates between them and a simple JSON message format, and can generate simulated values instead.

## Tech Stack

| Area | Choice |
|---|---|
| Engine | Unity 2022.3.76f1 |
| XR framework | VRTK v4 |
| Data layer | Python or Node.js |
| Messaging | MQTT or WebSocket |
| Tools | YABE, ETS, Blender |

## Repository Structure

```
concept.md     Project concept: objectives, architecture, plan, risks
use-cases.md   Use cases for each device
unity/         Unity project (planned)
bridge/        Data-exchange layer (planned)
```

## Status

Concept phase. See [concept.md](concept.md) and [use-cases.md](use-cases.md).
