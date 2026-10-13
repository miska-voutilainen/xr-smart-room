# KNX Bus - via KNX IP BAOS 777

The lab's KNX bus is reachable from the network only through the KNX IP BAOS 777 interface. The bridge can connect to it, but no KNX device is used yet.

The DALI panel is **not** on KNX. It has its own network interface, see [dali.md](dali.md).

| | |
|---|---|
| Interface | Weinzierl KNX IP BAOS 777 |
| Address | 192.168.15.191 (MAC `00-24-6d-03-9e-df`) |
| KNX address | 1.5.1 |
| KNXnet/IP | UDP 3671. Services: core, device management, tunnelling |
| Other ports | Web interface on 80/443 (needs a login), BAOS object server on TCP 12004 |
| Our tunnel address | Assigned per connection, e.g. 1.1.255, 1.5.250 |
| Home Assistant | Has its own tunnel (1.5.248), but exposes no KNX devices |

## How It Was Found

1. **Home Assistant.** No KNX devices.
2. **Multicast search.** A KNXnet/IP search request to the multicast address got no answer. The Wi-Fi probably blocks multicast.
3. **Direct search.** The same request sent directly to each address on the subnet found the BAOS 777. It is the only KNX/IP device.

## Testing

```
python bridge/lab.py check                     # the "knx" row shows whether the interface answers
python bridge/lab.py knx monitor               # print every bus telegram until Ctrl+C
python bridge/lab.py knx read 1/2/3            # ask a group address for its value
python bridge/lab.py knx scan 0/0/1 0/0/255    # read a range and list addresses that answer
python bridge/lab.py knx write 1/2/3 on        # switch on/off, or 40% (dim), or 128 (raw byte)
```

The KNX commands need the `xknx` package (`pip install -r bridge/requirements.txt`). `monitor`, `read` and `scan` only listen or ask; only `write` changes anything.

The real data type of a group address is only known from the ETS project. Telegram values are therefore shown as raw bytes plus the common interpretations (switch, percent, 2-byte float).

## What Has Been Tried

| Attempt | Result |
|---|---|
| Tunnel connection | Works |
| `monitor` for 60 seconds with nobody using the lab | No telegrams. Nothing on the bus sends on its own |
| `monitor` on 13.10.2026 while the DALI panel was used | No telegrams. The panel is not on KNX |
| `scan 0/0/1 0/0/40` | No answers |
| BAOS object server (TCP 12004) | Port open, but no reply. May need another protocol version or encryption |
| BAOS web interface | Needs a login. Not attempted |

## Group Addresses

KNX group addresses look like `main/middle/sub`, e.g. `1/2/3` (main 0-31, middle 0-7, sub 0-255). Device addresses use dots, e.g. `1.5.1`. To find the group addresses of the devices on this bus:

1. **ETS project.** Ask the lab staff for the ETS project or its group address list. This is the most reliable option, and it also gives the data types.
2. **Monitor the bus** while someone uses the KNX wall switches.
3. **BAOS login.** Ask the lab staff for the BAOS 777 web login. Its datapoint list may name the objects.
4. **Wider scan.** This works but sends many read requests on the bus. Keep the delay (`--delay 0.05` or more) and ask the staff first.

The room sensor is a KNX device too, but the bridge reads it through the Siemens BACnet gateway. See [room-sensor.md](room-sensor.md).

## Notes

- **The bus belongs to the lab.** Only write to addresses that have been identified and that the lab staff are fine with.
- **No password guessing.** Don't guess passwords for the BAOS web interface or other equipment.
