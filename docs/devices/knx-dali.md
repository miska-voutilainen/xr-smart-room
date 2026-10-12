# KNX Bus and DALI Panel - via KNX IP BAOS 777

The DALI panel has no network address of its own. It sits on the lab's KNX bus, most likely behind a KNX to DALI gateway. From the network, the only way onto the bus is the KNX IP BAOS 777 interface.

The bridge can connect to the KNX bus, but the group addresses of the DALI lamps are still unknown, so the DALI panel can't be controlled yet.

| | |
|---|---|
| Interface | Weinzierl KNX IP BAOS 777 |
| Address | 192.168.15.191 |
| KNX address | 1.5.1 |
| KNXnet/IP | UDP 3671. Services: core, device management, tunnelling |
| Other ports | Web interface on 80/443 (needs a login), BAOS object server on TCP 12004 |
| Our tunnel address | Assigned per connection, e.g. 1.1.255, 1.5.250 |
| Home Assistant | Has its own tunnel (1.5.248), but exposes no KNX or DALI devices |

## How It Was Found

1. **Home Assistant.** No DALI devices, and no DALI IP gateway on the network.
2. **Multicast search.** A KNXnet/IP search request to the multicast address got no answer. The Wi-Fi probably blocks multicast.
3. **Direct search.** The same request sent directly to each address on the subnet found the BAOS 777. It is the only KNX/IP device.

## Testing

```
python bridge/lab.py check                     # last line shows whether the KNX interface answers
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
| `scan 0/0/1 0/0/40` | No answers |
| BAOS object server (TCP 12004) | Port open, but no reply. May need another protocol version or encryption |
| BAOS web interface | Needs a login. Not attempted |

## Getting DALI to Work

The group addresses of the DALI lamps can be found in one of these ways:

1. **Monitor the bus.** Run `python bridge/lab.py knx monitor` while someone uses the DALI panel. Switch and dim each lamp with a few seconds between actions, and note the order. Each action appears as a telegram such as `1.1.10 -> 2/1/5  write  1-bit 1 (on)`, which shows the address and the type of value.
2. **ETS project.** Ask the lab staff for the ETS project or its group address list. This is the most reliable option, and it also gives the data types.
3. **BAOS login.** Ask the lab staff for the BAOS 777 web login. Its datapoint list may name the DALI objects.
4. **Wider scan.** This works but sends many read requests on the bus. Keep the delay (`--delay 0.05` or more) and ask the staff first.

Once the addresses are known:
- **Test them** with `knx read <address>` and `knx write <address> on` or `40%`.
- **Add a `dali1` device to `server.py`:** on/off and level per lamp or group, and lamp failure if the gateway reports it. The concept uses it for an XR DALI panel and a flashing red fixture when a lamp fails.

## Notes

- **The bus belongs to the lab.** Only write to addresses that have been identified and that the lab staff are fine with.
- **No password guessing.** Don't guess passwords for the BAOS web interface or other equipment.
