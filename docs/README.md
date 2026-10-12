# Lab Devices

Documentation for the devices in the Virumaa College KNX lab that the XR Smart Room connects to. Each page describes the device, how the bridge reaches it, how to test it with `bridge/lab.py`, what `bridge/server.py` sends to the XR app, and what has been tested so far.

Everything was found and tested on 12.10.2026 from the lab Wi-Fi.

## Devices

| Device | Page | Reached through | Status |
|---|---|---|---|
| Curtain (Aqara Curtain Driver E1) | [curtain.md](devices/curtain.md) | Home Assistant | Read and control |
| Light dimmer (Aqara Dimmer Switch H2) | [dimmer.md](devices/dimmer.md) | Home Assistant | Read and control |
| Speaker (Sonos Roam, Google Nest) | [speaker.md](devices/speaker.md) | Home Assistant | Read and control |
| Camera (Aqara, via Frigate) | [camera.md](devices/camera.md) | Frigate | Read |
| Room sensor (via BACnet gateway) | [room-sensor.md](devices/room-sensor.md) | BACnet/IP | Read |
| KNX bus and DALI panel | [knx-dali.md](devices/knx-dali.md) | KNXnet/IP | Bus connected, DALI addresses unknown |
| Home Assistant | [home-assistant.md](devices/home-assistant.md) | REST API | Platform for the first three |

## Network

All devices are on the lab Wi-Fi, `192.168.15.0/24`.

```
                         Lab PC (lab.py / server.py)
                                    |
       +-------------------+--------+-----------+----------------------+
       | REST (token)      | HTTP               | BACnet/IP            | KNXnet/IP
       v                   v                    v                      v
 Home Assistant       Frigate              Siemens OCT200.KNBA     KNX IP BAOS 777
 .249:8123            .249:5000            .132                    .191
   |- Aqara Hub M3      |- Aqara camera       |- room sensor (KNX)    |- KNX bus
   |    |- curtain      |  .144                                       |- DALI panel (?)
   |    |- dimmer
   |- Sonos "Office" .183
   |- Google Nest speakers
```

| Address | Device |
|---|---|
| 192.168.15.249 | Home Assistant, Frigate and MQTT broker (one Raspberry Pi) |
| 192.168.15.144 | Aqara camera |
| 192.168.15.183 | Sonos Roam "Office" |
| 192.168.15.132 | Siemens OCT200.KNBA KNX/BACnet gateway |
| 192.168.15.191 | KNX IP BAOS 777 |

Other addresses that answered but were not identified:
- **.206:** likely the Aqara hub, judging by its MAC address.
- **.179 and .240:** probably Google devices.
- **.115, .122 and .245:** Raspberry Pis.

## Working With the Lab Devices

- **Shared devices.** Other people use the devices too. Check the state before testing and put it back afterwards.
- **Read first.** Only use the commands that change something when you mean to.
- **Secrets.** The Home Assistant token lives in `bridge/.env`, which is git-ignored. Keep tokens and passwords out of docs, code and commits.
- **Passwords.** Don't guess passwords for lab equipment; ask the lab staff.
