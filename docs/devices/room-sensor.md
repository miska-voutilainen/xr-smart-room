# Room Sensor - via Siemens KNX/BACnet Gateway

A KNX room sensor for temperature, humidity and air quality. A Siemens gateway publishes its values as BACnet objects. This is the data source for UC3, the temperature alarm.

| | |
|---|---|
| Gateway | Siemens OCT200.KNBA (KNX to BACnet) |
| Address | 192.168.15.132, UDP 47808 (BACnet/IP) |
| BACnet device | Instance 1223, name `KNBA5F0004C7` |
| Access | Read only (ReadProperty) |
| Bridge name | `room_sensor1` |

## BACnet Objects

The gateway has seven objects, listed with `lab.py bacnet objects`:

| Object | Name | Meaning | Unit | Example |
|---|---|---|---|---|
| analog-input 0 | `1_/p/rts/temproom` | Room temperature | °C | 22.3 |
| analog-input 2 | `1_/p/rrhs/humrelroom` | Relative humidity | % | 46 |
| analog-input 3 | `1_/p/raqs/aqroom` | Air quality (CO2) | ppm | 930 |
| multi-state-value 0 | `1_/p/raqs/aqroomind` | Air quality level: 1 unknown, 2 poor, 3 okay, 4 good | - | 4 |
| binary-value 0 | `1_/p/sdev/batterylow` | Sensor battery low | - | 0 |
| structured-view 0 | `1` | Groups the objects above | - | - |

The air quality unit is BACnet unit 96 (ppm), so the value is CO2. The level names come from the object's own state texts. The gateway doesn't support high/low limit properties, so the alarm threshold is set in the bridge.

## Testing

```
python bridge/lab.py sensor                     # all values once
python bridge/lab.py sensor watch --alarm 25    # changes, and a warning above 25 °C
python bridge/lab.py bacnet discover            # find BACnet devices (like Who-Is in YABE)
python bridge/lab.py bacnet objects             # every object with its value
```

- **YABE.** Close YABE before `bacnet discover`; both need UDP port 47808.
- **Firewall.** Windows Firewall must let Python receive UDP on private networks.

The BACnet client in `lab.py` is a small built-in implementation that only supports ReadProperty and needs no extra packages.

## Bridge Server

The server reads the gateway every 5 seconds.

| Sends to XR |
|---|
| `temperature` (°C), `humidity` (%), `co2` (ppm), `air_quality` (good, okay, poor, unknown), `battery_low`, `alarm`, `status` |

**UC3 rule.** `alarm` is true while `temperature` is above `--temp-alarm` (default 26 °C). For now this is only a signal to the XR app. Closing the real curtain and sounding a real speaker are not wired up; agree on that with the lab staff first.

**Simulation.** In simulation mode the temperature moves between 22 and 28 °C every two minutes, so the alarm can be shown without heating the room.

## Test Results

| Test | Result |
|---|---|
| Who-Is discovery | Works. The gateway is the only BACnet device on the network |
| Read all values | Works |
| Alarm logic (`sensor watch --alarm 20`) | Works, reported the alarm at 22.2 °C |
| Values in `server.py` | Works |

## Notes

- **Read only.** Writing to the gateway is not implemented, on purpose.
- **Writing later.** If writing is needed, only write to objects the lab staff approve, with a low BACnet priority, as planned in [concept.md](../../concept.md).

## In XR

- **UC3 display:** the temperature appears above the virtual sensor as a label or thermometer, and the room is tinted by the value.
- **UC3 alarm:** when `alarm` turns true, a warning panel appears.
- **Information panel:** CO2 and humidity can go on the sensor's information panel.
