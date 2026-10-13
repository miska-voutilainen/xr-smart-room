# DALI Panel - Lunatone DALI-2 Display

The DALI panel ("DALI puutepaneel" on the wall) is a Lunatone DALI-2 Display. It sits directly on the DALI line and has its own REST API on the lab Wi-Fi. It is not behind KNX, which is why the KNX monitor showed nothing when the panel was used.

| | |
|---|---|
| Device | Lunatone DALI-2 Display, article 86456840, serial 71748, GTIN 9010342013577, made 2025 week 36 |
| Firmware | v1.14.1/1.4.3, tier "plus" |
| Address | 192.168.15.120 (network name `dm1-sqly-rorootfs`, MAC `8c-f6-81-36-58-b7`) |
| Web page | `http://192.168.15.120/`: upload, download, firmware update, cloud link, settings, reboot |
| REST API | `http://192.168.15.120/`, description at `/docs` and `/openapi.json`. There is also a websocket API for status events (not documented by Lunatone yet) |
| Login | None. Anyone on the lab Wi-Fi can read and change everything |
| DALI | 1 line, status `ok`, 10 lamps (short addresses 0-9) in 3 groups |

## Lamps and Groups

| Short address | API device id | Name | DALI type | Group |
|---|---|---|---|---|
| 0 | 1 | Line 0 - DALI#00 | DT8 (colour temperature) | G0 |
| 1 | 2 | Line 0 - DALI#01 | DT6 (LED) | G1 |
| 2 | 3 | Line 0 - DALI#02 | DT6 + DT8 | G1 |
| 3 | 4 | Line 0 - DALI#03 | DT6 | G1 |
| 4 | 5 | Line 0 - DALI#04 | DT6 | G1 |
| 5 | 6 | Line 0 - DALI#05 | DT6 | G2 |
| 6 | 7 | Line 0 - DALI#06 | DT6 | G2 |
| 7 | 8 | Line 0 - DALI#07 | DT6 | G2 |
| 8 | 9 | Line 0 - DALI#08 | DT6 | G2 |
| 9 | 10 | Line 0 - DALI#09 | DT6 + DT8 | G0 |

The group column comes from the panel's own device list. The API's `groups` field is empty for every lamp.

| Zone id | Zone name | Target |
|---|---|---|
| 1 | broadcast | all lamps |
| 2 | group 0 | G0 |
| 3 | group 1 | G1 |
| 4 | group 2 | G2 |
| 5 | lighting G1 | G1 |
| 6 | lighting G2 | G2 |
| 7 | lighting G3 | G0 (despite the name) |

The panel's screens also show "Task light 1" and "Task light 2". Which lamps or groups these are is not known yet.

## What Can Be Read

| Value | Where | Meaning |
|---|---|---|
| Lamp on | `GET /devices` -> `status.lampOn` | From the panel's DALI status query, per lamp |
| Lamp failure | `status.lampFailure`, `status.controlGearFailure` | Per lamp. Used for the "flashing red fixture" idea |
| Lamp available | `available` | The lamp answers on the DALI line |
| Group on, level, colour temperature | `GET /zones` -> `features` | The values last sent to the group. DALI cannot read a group back |

`features.switchable` and `features.dimmable` on a single lamp only change when that lamp is controlled on its own, so they are not used.

## Testing

```
python bridge/lab.py dali info      # device, firmware, DALI line status
python bridge/lab.py dali           # every lamp (on/off, failure, type) and group
python bridge/lab.py dali watch     # print changes every 2 s until Ctrl+C
python bridge/lab.py check          # includes a "dali" row
```

These only read. `server.py` publishes the same values as device `dali1`. See [bridge/README.md](../../bridge/README.md).

The lamp values only change while the panel's periodic status queries are on. They were off until 13.10.2026; line 0 now queries every 5 s (`GET /automations/statusQueries`, remove with `DELETE /automations/statusQueries/0`).

Control, by DALI short address (`lab.py` looks up the API device id):

```
python bridge/lab.py dali on 3                  # lamp with short address 3
python bridge/lab.py dali off g1                # group G1
python bridge/lab.py dali level all 40 --fade 2
python bridge/lab.py dali kelvin 0 3000         # DT8 lamps only: 0, 2, 9
python bridge/lab.py dali up all                # 1-5 steps
python bridge/lab.py dali scene g2 0
```

## Control

**Only commands to all lamps work (13.10.2026).** The panel accepts every command, but single lamps and groups don't react, also from the panel's own screen. With status queries on, none of the short addresses 0-9 answer. The lamps probably no longer have the addresses and groups the panel has stored, and need to be addressed again by the lab staff. One thing doesn't fit yet: later the lamps showed different levels per group (G0 177, G1 210, G2 170 of 254) while the group zones still said 100 %.

The API calls behind `lab.py dali`:

```
POST /device/{id}/control      {"switchable": true}   or {"dimmable": 40}
POST /group/{group}/control    {"dimmableWithFade": {"dimValue": 40, "fadeTime": 1}}
POST /zone/{id}/control        {"colorKelvin": 3000}
POST /broadcast/control        {"switchable": false}
```

`{id}` is the API device id from the table above, not the DALI short address.

## How It Was Found

1. **KNX monitor.** Nothing appeared on the KNX bus while the panel was used.
2. **Photo of the panel.** Its screen showed DALI addresses 0-9, groups G0-G2 and an "addressing - search devices" button, so it is a DALI controller rather than a KNX switch.
3. **Network sweep.** Pinging the subnet and checking web ports found a web page titled "DALI-2 Display" at .120, with a link to `iot.lunatone.com`.
4. **API.** The web server (uvicorn/FastAPI) publishes its API description at `/openapi.json`. `GET /info`, `/devices` and `/zones` gave the tables above.

The configuration download (`/downloads/systemConfiguration`) is AES-encrypted and was not opened. The device-name download (`/downloads/deviceNames`) is a plain CSV with the names above.

## Notes

- **Do not touch** "addressing - search devices" or the gear on the panel. Addressing can renumber or remove every lamp.
- **Only GET and `control`.** The API also has `DELETE /devices`, `POST /dali/scan`, `DELETE /reset`, `POST /reboot`, `POST /wifi` and the upload endpoints. The bridge must never call them.
- **No login.** The lab staff may want to know that the panel is open to everyone on the Wi-Fi.
