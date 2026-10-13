# Home Assistant

Home Assistant runs on a Raspberry Pi in the lab at `http://192.168.15.249:8123` (also `homeassistant.local`). The bridge reaches the curtain, the dimmer and the speakers through it. Frigate and an MQTT broker run on the same machine.

## Connection

The bridge uses the REST API with a long-lived access token:

| Request | Used for |
|---|---|
| `GET /api/states` | All entities. The server polls this once a second |
| `GET /api/states/<entity_id>` | One entity |
| `POST /api/services/<domain>/<service>` | Actions, e.g. `cover/open_cover`, `light/turn_on` |

The bridge also reads the Aqara motion sensor through it (see Other Entities).

The client is the `HomeAssistant` class in `bridge/lab.py`. `server.py` uses the same class.

## Token

1. Log in at `http://192.168.15.249:8123`.
2. Open your profile, then Security, then Long-lived access tokens, and create a token. Ours is called `xr-smart-room-bridge`.
3. Add it to `bridge/.env` as `HA_TOKEN=<token>`. The file is git-ignored.

The token has the same rights as the account that created it. Revoke it after the project.

## Testing

```
python bridge/lab.py check            # reads curtain, dimmer and speaker through Home Assistant
python bridge/lab.py list curtain     # all cover entities (also: dimmer, speaker)
```

## Other Entities

Home Assistant has about 440 entities. Some that could be useful later:

| Entity | Device |
|---|---|
| `binary_sensor.aqara_motion_sensor` | Aqara motion sensor, with `sensor.aqara_motion_sensor_illuminance` in lux. Used by the bridge as `motion1` (`--presence motion` or `any`), not tested in the lab yet |
| `binary_sensor.aqara_door_and_window_sensor_t1_door` | Door/window contact |
| `binary_sensor.aqara_water_leak_sensor_t1_water_leak` | Water leak sensor |
| `climate.aqara_radiator_thermostat_e1` | Radiator thermostat with room temperature |
| `climate.aqara_floor_heating_thermostat` | Floor heating thermostat with temperature and humidity |
| `cover.aqara_roller_shade_driver_e1` | Second motorised shade |
| `light.rgbw_controller_2*` | RGBW LED controller channels |
| `lock.aqara_smart_lock_u200_lite` | Smart lock. Leave it alone |

The Aqara Hub M3 shows up as `update.aqara_hub_m3_firmware` (firmware 4.5.80) and "Aqara-Hub-M3-88E5". The curtain and the dimmer reach Home Assistant through it.

## Other Services on the Same Machine

| Service | Port | Notes |
|---|---|---|
| Frigate | 5000 | Camera software, open API without login. See [camera.md](camera.md) |
| Mosquitto (MQTT) | 1883 | Needs a login. The login works, but nothing is published, so the bridge doesn't use it |
| KNX integration | - | Home Assistant has its own KNX tunnel (address `1.5.248`) but exposes no KNX entities. See [knx.md](knx.md) |

## Notes

- **Non-admin account.** Our account isn't an admin, so admin-only APIs are not available. Template rendering (`/api/template`) returns 401, and the integration settings can't be read. Which integration a device uses (Aqara hub, Matter, Zigbee) can't be seen directly.
- **Duplicate entries.** Some devices appear twice, and one of the duplicates can be misleading. See [curtain.md](curtain.md) and [dimmer.md](dimmer.md).
