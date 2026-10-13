# Lab Devices

Documentation for the devices in the Virumaa College KNX lab that the XR Smart Room connects to. Each page describes the device, how the bridge reaches it, how to test it with `bridge/lab.py`, what `bridge/server.py` sends to the XR app, and what has been tested so far.

Everything was found and tested on 12.10.2026 from the lab Wi-Fi. The DALI panel was found on 13.10.2026.

## Devices

| Device | Page | Reached through | Status |
|---|---|---|---|
| Curtain (Aqara Curtain Driver E1) | [curtain.md](devices/curtain.md) | Home Assistant | Read and control |
| Light dimmer (Aqara Dimmer Switch H2) | [dimmer.md](devices/dimmer.md) | Home Assistant | Read and control |
| Speaker (Sonos Roam, Google Nest) | [speaker.md](devices/speaker.md) | Home Assistant | Read and control |
| Camera (Aqara, via Frigate) | [camera.md](devices/camera.md) | Frigate | Read |
| Room sensor (via BACnet gateway) | [room-sensor.md](devices/room-sensor.md) | BACnet/IP | Read |
| DALI panel (Lunatone DALI-2 Display) | [dali.md](devices/dali.md) | REST API | Read (lamps, groups, lamp failure) |
| KNX bus | [knx.md](devices/knx.md) | KNXnet/IP | Bus connected, no devices used |
| Home Assistant | [home-assistant.md](devices/home-assistant.md) | REST API | Platform for the first three |

## Network

All devices are on the lab Wi-Fi, `192.168.15.0/24`.

```
                              Lab PC (lab.py / server.py)
                                         |
     +----------------+------------------+----------------+-------------------+
     | REST (token)   | HTTP             | BACnet/IP      | HTTP (no login)   | KNXnet/IP
     v                v                  v                v                   v
 Home Assistant   Frigate          Siemens OCT200   Lunatone DALI-2     KNX IP BAOS 777
 .249:8123        .249:5000        .132             Display .120        .191
   |- Aqara Hub M3  |- Aqara camera  |- room sensor   |- DALI line 0      |- KNX bus
   |  |- curtain    |  .144             (KNX)            10 lamps, G0-G2
   |  |- dimmer
   |- Sonos "Office" .183
   |- Google Nest speakers
```

Devices the bridge uses:

| Address | Device |
|---|---|
| 192.168.15.249 | Home Assistant, Frigate and MQTT broker (one Raspberry Pi) |
| 192.168.15.144 | Aqara camera |
| 192.168.15.183 | Sonos Roam "Office" |
| 192.168.15.132 | Siemens OCT200.KNBA KNX/BACnet gateway |
| 192.168.15.120 | Lunatone DALI-2 Display (DALI panel) |
| 192.168.15.191 | KNX IP BAOS 777 |

All devices that answered a ping on 13.10.2026. The maker is taken from the network name and the MAC address prefix.

| Address | MAC | Network name | Device |
|---|---|---|---|
| .1 | `20-97-27-78-f4-71` | RUT361 | Teltonika router (the Wi-Fi) |
| .2 | `20-4e-7f-e9-ce-46` | - | Probably a Netgear switch (Telnet, old HTTPS only) |
| .101 | `ac-17-02-22-39-ae` | HC3L-00091858 | Fibaro Home Center 3 Lite |
| .115 | `d8-3a-dd-99-48-ef` | CC-Jigsaw | ComfortClick Jigsaw (bOS server), for the IoT devices |
| .120 | `8c-f6-81-36-58-b7` | dm1-sqly-rorootfs | Lunatone DALI-2 Display (DALI panel) |
| .122 | `88-a2-9e-42-83-0f` | homeassistant11 | A second Home Assistant (Raspberry Pi) |
| .126 | `46-67-47-73-5a-bf` | - | Random MAC: a phone or laptop |
| .132 | `00-a0-03-97-0e-52` | KNBA5F0004C7 | Siemens OCT200.KNBA KNX/BACnet gateway |
| .144 | `18-c2-3c-62-e8-50` | Camera-Hub-G5Pro | Aqara camera |
| .145 | `c4-38-75-cd-9e-ac` | - | A second Sonos speaker |
| .146 | `7a-bb-37-4e-bc-5c` | Redmi-Pad-2 | Tablet |
| .151 | `ac-17-02-1d-9c-fb` | FGIC-00014992 | Fibaro Intercom |
| .179 | `14-c1-4e-5f-08-af` | Google-Nest-Mini | Google Nest Mini |
| .183 | `c4-38-75-c9-35-4c` | SonosZP | Sonos Roam "Office" |
| .191 | `00-24-6d-03-9e-df` | knxipbaos | Weinzierl KNX IP BAOS 777 |
| .196 | `d0-39-57-89-ca-53` | DESKTOP-NQSPED4 | A Windows PC |
| .206 | `18-c2-3c-55-e3-fc` | Aqara-Hub-M3 | Aqara Hub M3 |
| .240 | `f0-72-ea-d8-b4-74` | - | Probably a Google device (ports 8443, 9000, 10001) |
| .245 | `88-a2-9e-42-81-56` | admin | Raspberry Pi, role unknown (SSH only) |
| .249 | `88-a2-9e-42-81-59` | homeassistant | Home Assistant, Frigate, MQTT |

## Working With the Lab Devices

- **Shared devices.** Other people use the devices too. Check the state before testing and put it back afterwards.
- **Read first.** Only use the commands that change something when you mean to.
- **Secrets.** The Home Assistant token lives in `bridge/.env`, which is git-ignored. Keep tokens and passwords out of docs, code and commits.
- **Passwords.** Don't guess passwords for lab equipment; ask the lab staff.
