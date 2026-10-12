"""Test every lab device from one script.

    python lab.py check                        # quick read-only test of all devices

    python lab.py curtain status|watch|open|close|stop|position 0-100
    python lab.py dimmer  status|watch|on|off|toggle|level 0-100
    python lab.py speaker status|play <file or URL> [--volume N]|pause|resume|stop|volume up/down/N|restore
    python lab.py camera  status|snapshot [file.jpg]|watch
    python lab.py sensor  [watch [--alarm 25]]          # room sensor over BACnet
    python lab.py bacnet  discover|objects [--json file]
    python lab.py knx     monitor|read <ga>|scan <first> <last>|write <ga> <value> [--type ...]
    python lab.py list    curtain|dimmer|speaker        # Home Assistant entities of that kind

Home Assistant token: HA_TOKEN in the environment or a line HA_TOKEN=<token> in bridge/.env.
Every device command accepts --entity / --ip style options to target another device.
Only commands that change something: curtain open/close/stop/position, dimmer on/off/toggle/level,
speaker play/pause/resume/stop/volume/restore, knx write.
"""

import argparse
import asyncio
import datetime
import http.server
import ipaddress
import itertools
import json
import os
import socket
import struct
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

# ---------------------------------------------------------------- lab configuration

BRIDGE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_FILE = os.path.join(BRIDGE_DIR, ".env")

HA_URL = "http://192.168.15.249:8123"
CURTAIN = "cover.curtain_2"  # the physical curtain; cover.aqara_curtain_driver_e1 does not move it
DIMMER = "light.aqara_dimmer_switch_h2"
DIMMER_POWER = "sensor.aqara_dimmer_switch_h2_power"
SPEAKER = "media_player.roam_2_2"  # Sonos "Office"; Nest: media_player.googlehome6580 / famnest2

FRIGATE_URL = "http://192.168.15.249:5000"
FRIGATE_CAMERA = "cam_192_168_15_144"

GATEWAY_IP = "192.168.15.132"  # Siemens OCT200.KNBA KNX/BACnet gateway
GATEWAY_INSTANCE = 1223
KNX_GATEWAY_IP = "192.168.15.191"  # KNX IP BAOS 777

MEDIA_PORT = 8000
AUDIO_EXTENSIONS = (".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg")


def stamp():
    return time.strftime("%H:%M:%S")


def local_ip(towards="192.168.15.249"):
    """The address of this PC on the network that can reach `towards`."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.connect((towards, 80))
        return s.getsockname()[0]


# ---------------------------------------------------------------- Home Assistant client

def load_env_file(path=ENV_FILE):
    """Load KEY=value lines from the git-ignored bridge/.env without overriding real env vars."""
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip().removeprefix("export ").strip()
            os.environ.setdefault(key, value.strip().strip("'\""))


class HAError(Exception):
    pass


class HomeAssistant:
    def __init__(self, url, token, exit_on_error=True):
        self.url = url.rstrip("/")
        self.token = token
        self.exit_on_error = exit_on_error  # the CLI exits; the bridge server raises HAError

    @classmethod
    def from_env(cls, url=HA_URL, exit_on_error=True):
        load_env_file()
        token = os.getenv("HA_TOKEN")
        if not token:
            sys.exit(f"Set HA_TOKEN, or add a line HA_TOKEN=<token> to {ENV_FILE}.")
        return cls(url, token, exit_on_error)

    def _fail(self, message):
        if self.exit_on_error:
            sys.exit(message)
        raise HAError(message)

    def request(self, method, path, body=None):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(
            f"{self.url}/api/{path}", data=data, method=method,
            headers={"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as e:
            if e.code == 401:
                self._fail("Home Assistant rejected the token (401). Check HA_TOKEN.")
            if e.code == 404:
                self._fail(f"Not found: {path}. Check the entity id with 'lab.py list'.")
            self._fail(f"Home Assistant error {e.code}: {e.read().decode(errors='replace')}")
        except (urllib.error.URLError, TimeoutError) as e:
            self._fail(f"Cannot reach Home Assistant at {self.url}: {getattr(e, 'reason', e)}")

    def states(self, domain):
        return [s for s in self.request("GET", "states") if s["entity_id"].startswith(f"{domain}.")]

    def state(self, entity):
        return self.request("GET", f"states/{entity}")

    def call(self, domain, service, data):
        return self.request("POST", f"services/{domain}/{service}", data)


def watch_entity(ha, entity, describe, until=None, timeout=None):
    """Print state changes; stop when until(state) is true, on timeout, or on Ctrl+C."""
    last = None
    deadline = time.monotonic() + timeout if timeout else None
    try:
        while deadline is None or time.monotonic() < deadline:
            state = ha.state(entity)
            line = describe(state)
            if line != last:
                print(stamp(), line, flush=True)
                last = line
            if until and until(state):
                return
            time.sleep(1)
    except KeyboardInterrupt:
        pass


# ---------------------------------------------------------------- curtain

def describe_curtain(s):
    return f"{s['entity_id']}: {s['state']}, position {s['attributes'].get('current_position', '?')}"


def cmd_curtain(args):
    ha = HomeAssistant.from_env()
    target = {"entity_id": args.entity}
    if args.action == "status":
        print(describe_curtain(ha.state(args.entity)))
        return
    if args.action == "watch":
        print(f"Watching {args.entity} (Ctrl+C to quit)")
        watch_entity(ha, args.entity, describe_curtain)
        return
    if args.action == "position":
        ha.call("cover", "set_cover_position", {**target, "position": percent_arg(args.value)})
    else:
        ha.call("cover", f"{args.action}_cover", target)
    print(f"Sent {args.action} {args.value or ''}".rstrip())

    # The hub sometimes reports a brief stale state mid-move: only stop after 4 steady readings.
    steady = {"count": 0, "last": None}

    def stopped(s):
        line = describe_curtain(s)
        moving = s["state"] in ("opening", "closing")
        steady["count"] = 0 if moving or line != steady["last"] else steady["count"] + 1
        steady["last"] = line
        return steady["count"] >= 4

    time.sleep(1)
    watch_entity(ha, args.entity, describe_curtain, until=stopped, timeout=40)


# ---------------------------------------------------------------- dimmer

def describe_dimmer(ha, s):
    brightness = s["attributes"].get("brightness")
    level = f", level {round(brightness * 100 / 255)}%" if brightness is not None else ""
    line = f"{s['entity_id']}: {s['state']}{level}"
    if s["entity_id"] == DIMMER:
        power = ha.state(DIMMER_POWER)
        line += f", power {power['state']} W"
    return line


def cmd_dimmer(args):
    ha = HomeAssistant.from_env()
    target = {"entity_id": args.entity}
    describe = lambda s: describe_dimmer(ha, s)  # noqa: E731
    if args.action == "status":
        print(describe(ha.state(args.entity)))
        return
    if args.action == "watch":
        print(f"Watching {args.entity} (Ctrl+C to quit)")
        watch_entity(ha, args.entity, describe)
        return
    if args.action == "level":
        level = percent_arg(args.value)
        if level == 0:
            ha.call("light", "turn_off", target)
        else:
            ha.call("light", "turn_on", {**target, "brightness_pct": level})
    elif args.action == "toggle":
        ha.call("light", "toggle", target)
    else:
        ha.call("light", f"turn_{args.action}", target)
    print(f"Sent {args.action} {args.value or ''}".rstrip())
    time.sleep(2)  # let the dimmer and its power sensor report back
    print(describe(ha.state(args.entity)))


# ---------------------------------------------------------------- speaker

def describe_speaker(s):
    attrs = s["attributes"]
    parts = [f"{s['entity_id']}: {s['state']}"]
    if "volume_level" in attrs:
        parts.append(f"volume {round(attrs['volume_level'] * 100)}%")
    content = str(attrs.get("media_content_id", ""))
    title = " - ".join(x for x in (attrs.get("media_artist"), attrs.get("media_title")) if x)
    if title or "bluetooth" in content:
        parts.append(title or "Bluetooth")
    return ", ".join(parts)


def is_sonos(s):
    # Sonos entities report group_members (and x-sonos content ids); Google Cast ones do not.
    attrs = s["attributes"]
    return "group_members" in attrs or str(attrs.get("media_content_id", "")).startswith("x-sonos")


def find_media(name):
    """A local audio file: as given, or kept in bridge/."""
    for path in (os.path.abspath(name), os.path.join(BRIDGE_DIR, os.path.basename(name))):
        if os.path.isfile(path):
            return path
    sys.exit(f"File not found: {name} (looked in the current folder and in bridge/)")


def serve_file(path, port=MEDIA_PORT):
    """Serve exactly one file over HTTP so the speaker can stream it. Returns its URL path."""
    url_path = f"/song{os.path.splitext(path)[1].lower()}"

    class Handler(http.server.SimpleHTTPRequestHandler):
        def translate_path(self, request_path):
            return path if urllib.parse.urlparse(request_path).path == url_path else ""

        def handle(self):
            try:
                super().handle()
            except ConnectionError:
                pass  # Sonos opens several connections and drops the ones it doesn't need

        def log_message(self, fmt, *args):
            pass  # the speaker requests the file several times; logging each request is noise

    server = http.server.ThreadingHTTPServer(("0.0.0.0", port), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return url_path


def cmd_speaker(args):
    ha = HomeAssistant.from_env()
    target = {"entity_id": args.entity}
    if args.action == "status":
        print(describe_speaker(ha.state(args.entity)))
    elif args.action == "play":
        speaker_play(ha, args, target)
    elif args.action == "volume":
        if args.value in ("up", "down"):
            ha.call("media_player", f"volume_{args.value}", target)
        else:
            ha.call("media_player", "volume_set", {**target, "volume_level": percent_arg(args.value) / 100})
        time.sleep(1)
        print(describe_speaker(ha.state(args.entity)))
    elif args.action == "restore":
        ha.call("sonos", "restore", target)
        time.sleep(2)
        print(describe_speaker(ha.state(args.entity)))
    else:
        service = {"pause": "media_pause", "resume": "media_play", "stop": "media_stop"}[args.action]
        ha.call("media_player", service, target)
        time.sleep(1)
        print(describe_speaker(ha.state(args.entity)))


def speaker_play(ha, args, target):
    if not args.value:
        sys.exit("Give a file or URL: lab.py speaker play song.mp3")
    if args.value.startswith(("http://", "https://")):
        url = args.value
    else:
        url = f"http://{local_ip()}:{MEDIA_PORT}{serve_file(find_media(args.value))}"

    before = ha.state(args.entity)
    print("Before:", describe_speaker(before))
    restore = is_sonos(before)
    if restore:
        ha.call("sonos", "snapshot", target)
        print("Saved the speaker's current state; it will be restored afterwards.")
    else:
        print("Not a Sonos: the previous audio cannot be restored automatically.")

    try:
        if args.volume is not None:
            ha.call("media_player", "volume_set", {**target, "volume_level": args.volume / 100})
        ha.call("media_player", "play_media", {**target, "media_content_id": url, "media_content_type": "music"})
        print(f"Playing {os.path.basename(args.value)} - Ctrl+C to stop early")
        started = {"yes": False}

        def finished(s):
            ours = s["attributes"].get("media_content_id") == url and s["state"] in ("playing", "paused", "buffering")
            started["yes"] = started["yes"] or ours
            return started["yes"] and not ours

        watch_entity(ha, args.entity, describe_speaker, until=finished, timeout=3600)
    finally:
        if restore:
            ha.call("sonos", "restore", target)
            time.sleep(2)
            print("Restored:", describe_speaker(ha.state(args.entity)))


# ---------------------------------------------------------------- camera (Frigate)

def frigate_get(path, params=None):
    query = f"?{urllib.parse.urlencode(params)}" if params else ""
    try:
        with urllib.request.urlopen(f"{FRIGATE_URL}/api/{path}{query}", timeout=15) as resp:
            return resp.read()
    except urllib.error.URLError as e:
        sys.exit(f"Cannot reach Frigate at {FRIGATE_URL}: {getattr(e, 'reason', e)}")


def cmd_camera(args):
    if args.action == "status":
        cam = json.loads(frigate_get("stats")).get("cameras", {}).get(args.camera)
        if cam is None:
            sys.exit(f"Camera {args.camera} not found in Frigate.")
        print(f"{args.camera}: camera {cam['camera_fps']} fps, detection {cam['detection_fps']} fps, "
              f"detection {'on' if cam.get('detection_enabled') else 'off'}")
    elif args.action == "snapshot":
        image = frigate_get(f"{args.camera}/latest.jpg")
        file = args.value or "snapshot.jpg"
        with open(file, "wb") as f:
            f.write(image)
        print(f"Saved {len(image)} bytes to {os.path.abspath(file)} (contains people - don't commit it)")
    elif args.action == "watch":
        print(f"Watching {args.camera} for people (Ctrl+C to quit)")
        seen, after = set(), time.time()
        try:
            while True:
                events = json.loads(frigate_get("events", {
                    "cameras": args.camera, "labels": "person", "after": after, "limit": 20}))
                for e in reversed(events):
                    if e["id"] not in seen:
                        seen.add(e["id"])
                        score = e.get("top_score") or e.get("data", {}).get("top_score") or 0
                        start = datetime.datetime.fromtimestamp(e["start_time"]).strftime("%H:%M:%S")
                        print(f"{start} person detected (score {score:.2f})", flush=True)
                time.sleep(2)
        except KeyboardInterrupt:
            pass


# ---------------------------------------------------------------- BACnet client (read-only)

BACNET_PORT = 47808
OBJECT_TYPES = {0: "analog-input", 1: "analog-output", 2: "analog-value", 3: "binary-input",
                4: "binary-output", 5: "binary-value", 8: "device", 13: "multi-state-input",
                14: "multi-state-output", 15: "notification-class", 19: "multi-state-value",
                29: "structured-view"}
PROP_DESCRIPTION, PROP_MODEL_NAME, PROP_OBJECT_LIST, PROP_OBJECT_NAME = 28, 70, 76, 77
PROP_PRESENT_VALUE, PROP_UNITS, PROP_VENDOR_NAME = 85, 117, 121
UNITS = {62: "°C", 98: "%", 95: "", 47: "W", 19: "kWh", 29: "%RH", 37: "lx", 53: "Pa", 96: "ppm"}

# Room sensor objects on the gateway: (key, object type, instance, unit)
SENSOR_POINTS = [("temperature", 0, 0, "°C"), ("humidity", 0, 2, "%"), ("co2", 0, 3, "ppm"),
                 ("air_quality", 19, 0, ""), ("battery_low", 5, 0, "")]
AIR_QUALITY_LEVELS = {1: "unknown", 2: "poor", 3: "okay", 4: "good"}


class BACnetError(Exception):
    pass


def _context_unsigned(tag, value):
    data = value.to_bytes(max(1, (value.bit_length() + 7) // 8), "big")
    return bytes([(tag << 4) | 0x08 | len(data)]) + data


def _decode_values(data, pos):
    """Decode application-tagged values from `pos` up to the closing tag 0x3F."""
    values = []
    while pos < len(data):
        b = data[pos]
        if b == 0x3F:
            break
        tag, context, lvt = b >> 4, b & 0x08, b & 0x07
        pos += 1
        if lvt in (6, 7) and context:  # nested opening/closing tags
            continue
        if tag == 1 and not context:  # boolean: value is in the tag itself
            values.append(bool(lvt))
            continue
        length = lvt
        if lvt == 5:
            length = data[pos]
            pos += 1
            if length == 254:
                length = struct.unpack(">H", data[pos:pos + 2])[0]
                pos += 2
        raw = data[pos:pos + length]
        pos += length
        if context:
            values.append(raw)
        elif tag == 0:
            values.append(None)
        elif tag in (2, 9):  # unsigned, enumerated
            values.append(int.from_bytes(raw, "big"))
        elif tag == 3:
            values.append(int.from_bytes(raw, "big", signed=True))
        elif tag == 4:
            values.append(round(struct.unpack(">f", raw)[0], 3))
        elif tag == 5:
            values.append(struct.unpack(">d", raw)[0])
        elif tag == 7:
            values.append(raw[1:].decode("utf-8", errors="replace"))  # skip encoding byte
        elif tag == 12:
            oid = int.from_bytes(raw, "big")
            values.append((oid >> 22, oid & 0x3FFFFF))
        else:
            values.append(raw)
    return values


class BACnetClient:
    def __init__(self, ip, port=BACNET_PORT, timeout=2.0, retries=2):
        self.addr = (ip, port)
        self.retries = retries
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("0.0.0.0", 0))
        self.sock.settimeout(timeout)
        self._ids = itertools.cycle(range(256))

    def close(self):
        self.sock.close()

    def read(self, obj_type, instance, prop, index=None):
        """ReadProperty; returns the decoded value (a list if the property holds several)."""
        invoke_id = next(self._ids)
        apdu = bytes([0x00, 0x05, invoke_id, 0x0C, 0x0C]) + struct.pack(">I", (obj_type << 22) | instance)
        apdu += _context_unsigned(1, prop)
        if index is not None:
            apdu += _context_unsigned(2, index)
        npdu = bytes([0x01, 0x04])
        packet = bytes([0x81, 0x0A]) + struct.pack(">H", 4 + len(npdu) + len(apdu)) + npdu + apdu
        for _ in range(self.retries + 1):
            self.sock.sendto(packet, self.addr)
            try:
                while True:
                    data, src = self.sock.recvfrom(1500)
                    if src[0] != self.addr[0]:
                        continue
                    values = self._parse_reply(data, invoke_id)
                    if values is not None:
                        return values[0] if len(values) == 1 else values
            except (socket.timeout, ConnectionResetError):
                continue
        raise BACnetError(f"no reply from {self.addr[0]}")

    @staticmethod
    def _parse_reply(data, invoke_id):
        if len(data) < 6 or data[0] != 0x81:
            return None
        pos = 6
        if data[5] & 0x08:  # source specifier
            pos += 3 + data[pos + 2]
        pdu_type = data[pos] >> 4
        if data[pos + 1] != invoke_id:
            return None
        if pdu_type == 3:  # ComplexACK
            if data[pos] & 0x08:
                raise BACnetError("segmented reply not supported; read with an array index")
            pos += 3 + 5  # header + object identifier
            pos += 1 + (data[pos] & 0x07)  # property identifier
            if data[pos] >> 4 == 2 and data[pos] & 0x08:  # optional array index
                pos += 1 + (data[pos] & 0x07)
            if data[pos] != 0x3E:
                raise BACnetError("unexpected reply format")
            return _decode_values(data, pos + 1)
        if pdu_type == 5:
            raise BACnetError(f"error reply (class/code {data[pos + 3:].hex()})")
        if pdu_type in (6, 7):
            raise BACnetError("request rejected/aborted by device")
        return None


def read_room_sensor(client):
    values = {}
    for key, obj_type, instance, _ in SENSOR_POINTS:
        value = client.read(obj_type, instance, PROP_PRESENT_VALUE)
        if key == "air_quality":
            value = AIR_QUALITY_LEVELS.get(value, value)
        elif key == "battery_low":
            value = bool(value)
        elif isinstance(value, float):
            value = round(value, 1)
        values[key] = value
    return values


def describe_sensor(values):
    units = {key: unit for key, _, _, unit in SENSOR_POINTS}
    return ", ".join(f"{k} {v}{units[k] and ' ' + units[k]}" for k, v in values.items())


def cmd_sensor(args):
    client = BACnetClient(args.ip)
    try:
        if args.action != "watch":
            print(describe_sensor(read_room_sensor(client)))
            return
        print(f"Watching room sensor at {args.ip} every {args.interval:g} s (Ctrl+C to quit)")
        last, alarm = None, False
        while True:
            try:
                values = read_room_sensor(client)
            except BACnetError as e:
                print(stamp(), f"gateway not answering: {e}", flush=True)
                time.sleep(args.interval)
                continue
            if values != last:
                print(stamp(), describe_sensor(values), flush=True)
                last = values
            if args.alarm is not None and (values["temperature"] > args.alarm) != alarm:
                alarm = not alarm
                print(stamp(), f"{'ALARM: above' if alarm else 'back to normal, below'} {args.alarm:g} °C", flush=True)
            time.sleep(args.interval)
    except KeyboardInterrupt:
        pass
    finally:
        client.close()


# ---------------------------------------------------------------- BACnet discovery

# BVLC Original-Broadcast-NPDU + NPDU (global broadcast, hop count 255) + APDU Who-Is
WHO_IS = bytes([0x81, 0x0B, 0x00, 0x0C, 0x01, 0x20, 0xFF, 0xFF, 0x00, 0xFF, 0x10, 0x08])


def parse_i_am(data):
    """Return the device instance if `data` is an I-Am, else None."""
    if len(data) < 6 or data[0] != 0x81:
        return None
    npdu, i = data[4:], 2
    control = npdu[1]
    if control & 0x20:  # destination specifier
        i += 3 + npdu[i + 2]
    if control & 0x08:  # source specifier
        i += 3 + npdu[i + 2]
    if control & 0x20:
        i += 1  # hop count
    apdu = npdu[i:]
    if len(apdu) < 7 or apdu[0] != 0x10 or apdu[1] != 0x00 or apdu[2] != 0xC4:
        return None
    object_id = struct.unpack(">I", apdu[3:7])[0]
    return object_id & 0x3FFFFF if object_id >> 22 == 8 else None


def bacnet_discover(wait):
    me = local_ip()
    broadcast = str(ipaddress.ip_network(f"{me}/24", strict=False).broadcast_address)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    try:
        sock.bind(("0.0.0.0", BACNET_PORT))  # devices answer Who-Is on the BACnet port
    except OSError:
        sys.exit(f"UDP {BACNET_PORT} is busy - close YABE or other BACnet tools and retry.")
    sock.settimeout(0.5)
    print(f"Sending Who-Is from {me} to {broadcast}, listening {wait:g} s ...")
    for target in (broadcast, "255.255.255.255"):
        sock.sendto(WHO_IS, (target, BACNET_PORT))
    found = []
    deadline = time.monotonic() + wait
    while time.monotonic() < deadline:
        try:
            data, (ip, _) = sock.recvfrom(1500)
        except (socket.timeout, ConnectionResetError):
            continue
        instance = parse_i_am(data) if ip != me else None
        if instance is not None and (ip, instance) not in found:
            found.append((ip, instance))
    sock.close()
    return found


def cmd_bacnet(args):
    if args.action == "discover":
        found = bacnet_discover(args.wait)
        client = BACnetClient("0.0.0.0")
        for ip, instance in found:
            client.addr = (ip, BACNET_PORT)
            details = []
            for label, prop in (("name", PROP_OBJECT_NAME), ("model", PROP_MODEL_NAME), ("vendor", PROP_VENDOR_NAME)):
                try:
                    details.append(f"{label}: {client.read(8, instance, prop)}")
                except BACnetError:
                    pass
            print(f"  {ip}  device {instance}  {', '.join(details)}")
        client.close()
        if not found:
            print("No BACnet devices answered. Check the network and that the firewall allows UDP 47808.")
        return

    client = BACnetClient(args.ip)  # objects
    count = client.read(8, args.instance, PROP_OBJECT_LIST, index=0)
    print(f"Device {args.instance} at {args.ip} has {count} objects\n")
    objects = []
    for i in range(1, count + 1):
        obj_type, instance = client.read(8, args.instance, PROP_OBJECT_LIST, index=i)
        if obj_type == 8:
            continue
        info = {"type": OBJECT_TYPES.get(obj_type, str(obj_type)), "type_id": obj_type, "instance": instance}
        for key, prop in (("name", PROP_OBJECT_NAME), ("description", PROP_DESCRIPTION), ("value", PROP_PRESENT_VALUE)):
            try:
                info[key] = client.read(obj_type, instance, prop)
            except BACnetError:
                info[key] = None
        units = None
        if obj_type in (0, 1, 2):
            try:
                units = client.read(obj_type, instance, PROP_UNITS)
            except BACnetError:
                pass
        info["units"] = UNITS.get(units, units)
        objects.append(info)
        shown = f"{info['value']} {info['units'] or ''}".strip() if info["value"] is not None else "-"
        desc = f"  [{info['description']}]" if info["description"] and info["description"] != info["name"] else ""
        print(f"{info['type']:>19} {instance:<6} {str(info['name']):<40} {shown}{desc}", flush=True)
    client.close()
    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump({"ip": args.ip, "instance": args.instance, "objects": objects}, f, indent=2, ensure_ascii=False)
        print(f"\nSaved {len(objects)} objects to {args.json}")


# ---------------------------------------------------------------- KNX (DALI lamps sit behind KNX)

def knx_search(ip, timeout=3):
    """KNXnet/IP search request sent directly to `ip`; returns (name, knx address) or None."""
    me = local_ip()
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.bind((me, 0))
        s.settimeout(timeout)
        hpai = bytes([8, 1]) + socket.inet_aton(me) + struct.pack(">H", s.getsockname()[1])
        s.sendto(bytes([6, 0x10, 0x02, 0x01]) + struct.pack(">H", 6 + len(hpai)) + hpai, (ip, 3671))
        try:
            data, _ = s.recvfrom(1024)
        except (socket.timeout, ConnectionResetError):
            return None
    if data[2:4] != b"\x02\x02":
        return None
    dib = data[14:]
    ia = struct.unpack(">H", dib[4:6])[0]
    return dib[24:54].split(b"\0")[0].decode(errors="replace"), f"{ia >> 12}.{(ia >> 8) & 15}.{ia & 255}"


def knx_interpret(payload):
    from xknx.dpt import DPTArray, DPTBinary
    value = getattr(payload, "value", None)
    if isinstance(value, DPTBinary):
        return f"1-bit {value.value} ({'on' if value.value else 'off'})"
    if isinstance(value, DPTArray):
        raw = value.value
        parts = [f"raw {bytes(raw).hex()}"]
        if len(raw) == 1:
            parts.append(f"{raw[0]} = {round(raw[0] * 100 / 255)} %")
        elif len(raw) == 2:  # DPT 9, 2-byte float (e.g. temperature)
            word = (raw[0] << 8) | raw[1]
            mantissa = (word & 0x07FF) - (2048 if word & 0x8000 else 0)
            parts.append(f"2-byte float {round(0.01 * mantissa * 2 ** ((word >> 11) & 0x0F), 2):g}")
        return ", ".join(parts)
    return ""


def knx_describe(telegram):
    from xknx.telegram.apci import GroupValueRead, GroupValueResponse, GroupValueWrite
    kind = {GroupValueWrite: "write", GroupValueResponse: "response", GroupValueRead: "read"}.get(
        type(telegram.payload), type(telegram.payload).__name__)
    return f"{telegram.source_address} -> {telegram.destination_address}  {kind:8} {knx_interpret(telegram.payload)}"


def knx_value(text, kind):
    text = text.strip().lower()
    if kind == "switch" or (kind is None and text in ("on", "off", "true", "false", "1", "0")):
        return "switch", text in ("on", "true", "1")
    if kind == "percent" or (kind is None and text.endswith("%")):
        return "percent", max(0, min(100, int(float(text.rstrip("%")))))
    return "1byte_unsigned", max(0, min(255, int(text)))


async def knx_main(args):
    try:
        from xknx import XKNX
        from xknx.io import ConnectionConfig, ConnectionType
        from xknx.telegram import GroupAddress
        from xknx.telegram.apci import GroupValueResponse
        from xknx.tools import group_value_read, group_value_write
    except ImportError:
        sys.exit("KNX needs the xknx package: pip install -r bridge/requirements.txt")

    callback, found = None, {}
    if args.action == "monitor":
        callback = lambda t: print(stamp(), knx_describe(t), flush=True)  # noqa: E731
    elif args.action in ("read", "scan"):
        def callback(t):
            if isinstance(t.payload, GroupValueResponse) and str(t.destination_address) not in found:
                found[str(t.destination_address)] = t
                print("  " + knx_describe(t), flush=True)

    xknx = XKNX(connection_config=ConnectionConfig(connection_type=ConnectionType.TUNNELING, gateway_ip=args.ip),
                telegram_received_cb=callback)
    await xknx.start()
    print(f"Connected to {args.ip}, our address {xknx.current_address}", flush=True)
    try:
        if args.action == "monitor":
            print("Listening - operate switches or the DALI panel now (Ctrl+C to quit)", flush=True)
            await asyncio.Event().wait()
        elif args.action == "read":
            group_value_read(xknx, args.address)
            await asyncio.sleep(2)
            if not found:
                print(f"No answer from {args.address} (nothing there, or its read flag is off).")
        elif args.action == "scan":
            first, last = GroupAddress(args.address).raw, GroupAddress(args.value).raw
            print(f"Reading {last - first + 1} addresses, about {(last - first + 1) * args.delay:.0f} s ...", flush=True)
            for raw in range(first, last + 1):
                group_value_read(xknx, GroupAddress(raw))
                await asyncio.sleep(args.delay)
            await asyncio.sleep(2)
            print(f"{len(found)} address(es) answered.")
        elif args.action == "write":
            value_type, value = knx_value(args.value, args.type)
            group_value_write(xknx, args.address, value, value_type=value_type)
            await asyncio.sleep(0.5)
            print(f"Wrote {args.value} ({value_type}) to {args.address}")
    finally:
        await xknx.stop()


def cmd_knx(args):
    if args.action in ("read", "write") and not args.address:
        sys.exit(f"Give a group address: lab.py knx {args.action} 1/2/3")
    if args.action == "write" and args.value is None:
        sys.exit("Give a value: lab.py knx write 1/2/3 on|off|40%|128")
    if args.action == "scan" and not (args.address and args.value):
        sys.exit("Give a range: lab.py knx scan 0/0/1 3/7/255")
    try:
        asyncio.run(knx_main(args))
    except KeyboardInterrupt:
        pass


# ---------------------------------------------------------------- check everything

def cmd_check(args):
    def row(name, ok, detail):
        print(f"  {'OK  ' if ok else 'FAIL'} {name:<13} {detail}", flush=True)

    print("Checking lab devices (read-only)\n")
    try:
        ha = HomeAssistant.from_env(exit_on_error=False)
        by_id = {s["entity_id"]: s for s in ha.request("GET", "states")}
        for name, entity, describe in (("curtain", CURTAIN, describe_curtain),
                                       ("dimmer", DIMMER, lambda s: describe_dimmer(ha, s)),
                                       ("speaker", SPEAKER, describe_speaker)):
            s = by_id.get(entity)
            row(name, s is not None and s["state"] != "unavailable",
                describe(s) if s else f"{entity} not found")
    except (HAError, SystemExit) as e:
        row("home assist.", False, str(e))

    try:
        with urllib.request.urlopen(f"{FRIGATE_URL}/api/stats", timeout=10) as resp:
            cam = json.load(resp).get("cameras", {}).get(FRIGATE_CAMERA)
        row("camera", cam is not None and cam["camera_fps"] > 0,
            f"{FRIGATE_CAMERA}: {cam['camera_fps']} fps" if cam else "not in Frigate")
    except (urllib.error.URLError, TimeoutError) as e:
        row("camera", False, f"Frigate unreachable: {getattr(e, 'reason', e)}")

    client = BACnetClient(GATEWAY_IP)
    try:
        row("room sensor", True, describe_sensor(read_room_sensor(client)))
    except BACnetError as e:
        row("room sensor", False, f"BACnet gateway {GATEWAY_IP}: {e}")
    finally:
        client.close()

    knx = knx_search(KNX_GATEWAY_IP)
    row("knx / dali", knx is not None,
        f"{knx[0]} at {KNX_GATEWAY_IP}, KNX address {knx[1]} (DALI group addresses still unknown)"
        if knx else f"no KNX/IP interface at {KNX_GATEWAY_IP}")


def cmd_list(args):
    ha = HomeAssistant.from_env()
    domain = {"curtain": "cover", "dimmer": "light", "speaker": "media_player"}[args.kind]
    for s in ha.states(domain):
        print(f"{s['entity_id']:45} {s['state']:12} {s['attributes'].get('friendly_name', '')}")


# ---------------------------------------------------------------- command line

def percent_arg(value):
    try:
        level = int(round(float(str(value).rstrip("%"))))
    except (TypeError, ValueError):
        sys.exit(f"Expected a number 0-100, got {value!r}")
    if not 0 <= level <= 100:
        sys.exit("Expected a number 0-100")
    return level


def parse_args():
    p = argparse.ArgumentParser(description="Test the XR Smart Room lab devices",
                                formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    sub = p.add_subparsers(dest="device", required=True)

    sub.add_parser("check", help="read-only test of every device")

    lst = sub.add_parser("list", help="list Home Assistant entities of one kind")
    lst.add_argument("kind", choices=("curtain", "dimmer", "speaker"))

    c = sub.add_parser("curtain", help="Aqara curtain via Home Assistant")
    c.add_argument("action", choices=("status", "watch", "open", "close", "stop", "position"))
    c.add_argument("value", nargs="?", help="position 0-100 (0 = closed)")
    c.add_argument("--entity", default=CURTAIN)

    d = sub.add_parser("dimmer", help="Aqara dimmer via Home Assistant")
    d.add_argument("action", choices=("status", "watch", "on", "off", "toggle", "level"))
    d.add_argument("value", nargs="?", help="level 0-100")
    d.add_argument("--entity", default=DIMMER)

    s = sub.add_parser("speaker", help="Sonos / Nest speaker via Home Assistant")
    s.add_argument("action", choices=("status", "play", "pause", "resume", "stop", "volume", "restore"))
    s.add_argument("value", nargs="?", help="play: file or URL; volume: up, down or 0-100")
    s.add_argument("--volume", type=int, choices=range(0, 101), metavar="0-100", help="volume for 'play'")
    s.add_argument("--entity", default=SPEAKER)

    cam = sub.add_parser("camera", help="Aqara camera via Frigate")
    cam.add_argument("action", choices=("status", "snapshot", "watch"))
    cam.add_argument("value", nargs="?", help="snapshot file name")
    cam.add_argument("--camera", default=FRIGATE_CAMERA)

    se = sub.add_parser("sensor", help="room sensor via the BACnet gateway")
    se.add_argument("action", nargs="?", choices=("status", "watch"), default="status")
    se.add_argument("--interval", type=float, default=5.0)
    se.add_argument("--alarm", type=float, help="warn above this temperature (°C)")
    se.add_argument("--ip", default=GATEWAY_IP)

    b = sub.add_parser("bacnet", help="find BACnet devices / list their objects")
    b.add_argument("action", choices=("discover", "objects"))
    b.add_argument("--wait", type=float, default=4.0, help="discover: seconds to listen")
    b.add_argument("--ip", default=GATEWAY_IP, help="objects: device address")
    b.add_argument("--instance", type=int, default=GATEWAY_INSTANCE, help="objects: device instance")
    b.add_argument("--json", help="objects: save the list to this file")

    k = sub.add_parser("knx", help="KNX bus (DALI lamps) via the KNX IP BAOS 777")
    k.add_argument("action", choices=("monitor", "read", "scan", "write"))
    k.add_argument("address", nargs="?", help="group address, e.g. 1/2/3 (scan: first address)")
    k.add_argument("value", nargs="?", help="write: on/off/40%%/128; scan: last address")
    k.add_argument("--type", choices=("switch", "percent", "byte"), help="write: value type")
    k.add_argument("--delay", type=float, default=0.05, help="scan: seconds between reads")
    k.add_argument("--ip", default=KNX_GATEWAY_IP)
    return p.parse_args()


def main():
    args = parse_args()
    if getattr(args, "type", None) == "byte":
        args.type = "1byte_unsigned"
    needs_value = {("curtain", "position"), ("dimmer", "level"), ("speaker", "volume")}
    if (args.device, getattr(args, "action", None)) in needs_value and args.value is None:
        sys.exit(f"Give a value: lab.py {args.device} {args.action} <value>")
    {
        "check": cmd_check, "list": cmd_list, "curtain": cmd_curtain, "dimmer": cmd_dimmer,
        "speaker": cmd_speaker, "camera": cmd_camera, "sensor": cmd_sensor, "bacnet": cmd_bacnet, "knx": cmd_knx,
    }[args.device](args)


if __name__ == "__main__":
    main()
