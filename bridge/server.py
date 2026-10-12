"""Data-exchange layer between Unity and the lab devices.

Unity connects to ws://<this-pc>:8765. The server pushes state changes and accepts commands.

State (server -> Unity), one JSON object per message:
    {"device": "dimmer1", "property": "level", "value": 60, "source": "real", "timestamp": "..."}

Commands (Unity -> server):
    {"device": "curtain1", "command": "set_position", "value": 40}

Devices, properties and commands:
    curtain1      position 0-100, state, status        open, close, stop, set_position <0-100>
    dimmer1       on, level 0-100, power (W), status   on, off, toggle, set_level <0-100>
    speaker1      state, volume 0-100, title, status   play <file in bridge/>, pause, resume, stop,
                                                       volume_up, volume_down, set_volume <0-100>, restore
    camera1       occupied, status                     -
    motion1       motion, illuminance (lx), status     -
    room_sensor1  temperature, humidity, co2, air_quality, battery_low, alarm, status   -
    virtual_light on (rule: on while the room is occupied, see --presence)

HTTP on port 8000: /camera.jpg (latest camera frame for Unity), /media/<file> (songs for the speaker).

Usage:
    python server.py                    # real devices (Home Assistant, Frigate, BACnet)
    python server.py --simulate         # fake devices, no lab needed
    python server.py --temp-alarm 25    # room_sensor1 alarm threshold in °C
    python server.py --alarm-actions    # alarm also closes the curtain and plays alarm.mp3
    python server.py --presence motion  # virtual light follows the motion sensor instead of the camera
"""

import argparse
import asyncio
import datetime
import http.server
import json
import math
import os
import random
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

import websockets

from lab import (AUDIO_EXTENSIONS, BRIDGE_DIR, CURTAIN, DIMMER, DIMMER_POWER, FRIGATE_CAMERA, FRIGATE_URL,
                 GATEWAY_IP, MOTION, MOTION_LUX, SPEAKER, BACnetClient, BACnetError, HAError, HomeAssistant,
                 curtain_stop, local_ip, read_room_sensor)

ENTITIES = {"curtain1": CURTAIN, "dimmer1": DIMMER, "dimmer1_power": DIMMER_POWER, "speaker1": SPEAKER,
            "motion1": MOTION, "motion1_lux": MOTION_LUX}
PRESENCE = {"camera": [("camera1", "occupied")], "motion": [("motion1", "motion")],
            "any": [("camera1", "occupied"), ("motion1", "motion")]}


def parse_args():
    p = argparse.ArgumentParser(description="XR Smart Room bridge server")
    p.add_argument("--port", type=int, default=8765, help="WebSocket port for Unity")
    p.add_argument("--http-port", type=int, default=8000, help="HTTP port for camera frames and media")
    p.add_argument("--simulate", action="store_true", help="fake all devices")
    p.add_argument("--temp-alarm", type=float, default=26.0, help="room temperature alarm threshold (°C)")
    p.add_argument("--hold", type=float, default=30.0, help="seconds without a person before the room is empty")
    p.add_argument("--min-score", type=float, default=0.5, help="ignore person detections below this score")
    p.add_argument("--presence", choices=PRESENCE, default="camera",
                   help="what switches the virtual light: camera, motion sensor, or any of them")
    p.add_argument("--alarm-actions", action="store_true",
                   help="when the alarm starts, close the curtain and play --alarm-sound on the speaker")
    p.add_argument("--alarm-sound", default="alarm.mp3", help="sound file in bridge/ for --alarm-actions")
    return p.parse_args()


def log(*parts):
    print(time.strftime("%H:%M:%S"), *parts, flush=True)


def media_path(name):
    """Resolve a song name to a file in bridge/ (no directories allowed)."""
    path = os.path.join(BRIDGE_DIR, os.path.basename(str(name)))
    if not path.lower().endswith(AUDIO_EXTENSIONS) or not os.path.isfile(path):
        raise ValueError(f"no audio file '{name}' in bridge/")
    return path


class Hub:
    """Holds the latest state, broadcasts changes to Unity, and applies the room rules."""

    def __init__(self, source, args):
        self.source = source
        self.args = args
        self.devices = None  # set in main(); rules send commands through it
        self.clients = set()
        self.state = {}
        self.rule_tasks = set()  # keeps running rule commands from being garbage collected

    def message(self, device, prop, value):
        return json.dumps({
            "device": device, "property": prop, "value": value, "source": self.source,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        })

    def publish(self, device, prop, value):
        if self.state.get((device, prop), object()) == value:
            return
        self.state[(device, prop)] = value
        if prop not in ("power", "temperature", "humidity", "co2", "illuminance"):  # frequent; alarms still log
            log(f"{device}.{prop} = {value}")
        websockets.broadcast(self.clients, self.message(device, prop, value))
        self.apply_rules(device, prop, value)

    def publish_all(self, device, values):
        for prop, value in values.items():
            self.publish(device, prop, value)

    def apply_rules(self, device, prop, value):
        triggers = PRESENCE[self.args.presence]
        if (device, prop) in triggers:  # UC1: presence -> virtual light
            self.publish("virtual_light", "on", any(self.state.get(t) is True for t in triggers))
        if (device, prop) == ("room_sensor1", "temperature") and value is not None:  # UC3
            self.publish("room_sensor1", "alarm", value > self.args.temp_alarm)
        if (device, prop) == ("room_sensor1", "alarm") and value and self.args.alarm_actions:
            log("alarm started: closing the curtain and playing the alarm sound")
            self.run_command("curtain1", "close")
            self.run_command("speaker1", "play", self.args.alarm_sound)

    def run_command(self, device, command, value=None):
        """Send a command from a rule, in the background like a command from Unity."""
        async def run():
            try:
                await asyncio.to_thread(self.devices.command, device, command, value)
            except (ValueError, HAError) as e:
                log(f"rule command {device}.{command} failed: {e}")

        task = asyncio.get_running_loop().create_task(run())
        self.rule_tasks.add(task)
        task.add_done_callback(self.rule_tasks.discard)

    async def send_error(self, ws, device, text):
        log(f"command error for {device}: {text}")
        await ws.send(self.message(device, "error", text))


# ---------------------------------------------------------------- real devices

class RealDevices:
    def __init__(self, hub, args):
        self.hub = hub
        self.args = args
        self.ha = HomeAssistant.from_env(exit_on_error=False)
        self.my_ip = local_ip()
        self.media = {"path": None}  # file currently served at /media/<name>
        self.playing_url = None      # our song on the speaker, for auto-restore
        self.song_started = False

    def tasks(self):
        return [self.poll_home_assistant(), self.poll_camera(), self.poll_room_sensor()]

    # ---- Home Assistant: curtain, dimmer, speaker
    async def poll_home_assistant(self):
        online = None
        while True:
            try:
                states = await asyncio.to_thread(self.ha.request, "GET", "states")
                by_id = {s["entity_id"]: s for s in states}
                self.publish_curtain(by_id.get(ENTITIES["curtain1"]))
                self.publish_dimmer(by_id.get(ENTITIES["dimmer1"]), by_id.get(ENTITIES["dimmer1_power"]))
                await self.publish_speaker(by_id.get(ENTITIES["speaker1"]))
                self.publish_motion(by_id.get(ENTITIES["motion1"]), by_id.get(ENTITIES["motion1_lux"]))
                if online is not True:
                    online = True
            except HAError as e:
                if online is not False:
                    log(f"Home Assistant unreachable: {e}")
                    online = False
                for device in ("curtain1", "dimmer1", "speaker1", "motion1"):
                    self.hub.publish(device, "status", "offline")
            await asyncio.sleep(1)

    def status(self, s):
        return "offline" if s is None or s["state"] == "unavailable" else "online"

    def publish_curtain(self, s):
        self.hub.publish("curtain1", "status", self.status(s))
        if self.status(s) == "online":
            self.hub.publish_all("curtain1", {
                "position": s["attributes"].get("current_position"), "state": s["state"],
            })

    def publish_dimmer(self, s, power):
        self.hub.publish("dimmer1", "status", self.status(s))
        if self.status(s) == "online":
            brightness = s["attributes"].get("brightness")
            self.hub.publish_all("dimmer1", {
                "on": s["state"] == "on",
                "level": round(brightness * 100 / 255) if brightness else 0,
            })
        if power and power["state"] not in ("unavailable", "unknown"):
            self.hub.publish("dimmer1", "power", float(power["state"]))

    def publish_motion(self, s, lux):
        self.hub.publish("motion1", "status", self.status(s))
        if self.status(s) == "online" and s["state"] in ("on", "off"):
            self.hub.publish("motion1", "motion", s["state"] == "on")
        if lux and lux["state"] not in ("unavailable", "unknown"):
            self.hub.publish("motion1", "illuminance", float(lux["state"]))

    async def publish_speaker(self, s):
        self.hub.publish("speaker1", "status", self.status(s))
        if self.status(s) != "online":
            return
        attrs = s["attributes"]
        content = str(attrs.get("media_content_id", ""))
        title = attrs.get("media_title") or ("Bluetooth" if "bluetooth" in content else "")
        if self.playing_url and content == self.playing_url:
            title = os.path.basename(self.media["path"] or "")
        self.hub.publish_all("speaker1", {
            "state": s["state"],
            "volume": round(attrs["volume_level"] * 100) if "volume_level" in attrs else None,
            "title": title,
        })
        # Auto-restore the Sonos once our song has finished or been replaced
        if self.playing_url:
            ours = content == self.playing_url and s["state"] in ("playing", "paused", "buffering")
            if ours:
                self.song_started = True
            elif self.song_started:
                self.playing_url = None
                log("song finished, restoring the speaker's previous audio")
                await asyncio.to_thread(self.ha.call, "sonos", "restore", {"entity_id": ENTITIES["speaker1"]})

    # ---- Frigate: camera occupancy
    def person_present(self):
        params = urllib.parse.urlencode({
            "cameras": FRIGATE_CAMERA, "labels": "person", "after": time.time() - self.args.hold - 300, "limit": 20,
        })
        with urllib.request.urlopen(f"{FRIGATE_URL}/api/events?{params}", timeout=10) as resp:
            events = json.load(resp)
        now = time.time()
        for e in events:
            score = e.get("top_score") or e.get("data", {}).get("top_score") or 0
            if score >= self.args.min_score and (e.get("end_time") is None or now - e["end_time"] < self.args.hold):
                return True
        return False

    async def poll_camera(self):
        while True:
            try:
                present = await asyncio.to_thread(self.person_present)
                self.hub.publish("camera1", "status", "online")
                self.hub.publish("camera1", "occupied", present)
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
                self.hub.publish("camera1", "status", "offline")
            await asyncio.sleep(1)

    # ---- BACnet: room sensor
    async def poll_room_sensor(self):
        client = BACnetClient(GATEWAY_IP)
        while True:
            try:
                values = await asyncio.to_thread(read_room_sensor, client)
                self.hub.publish("room_sensor1", "status", "online")
                self.hub.publish_all("room_sensor1", values)
            except BACnetError:
                self.hub.publish("room_sensor1", "status", "offline")
            await asyncio.sleep(5)

    # ---- commands from Unity
    def command(self, device, command, value):
        call = self.ha.call
        if device == "curtain1":
            target = {"entity_id": ENTITIES["curtain1"]}
            if command == "set_position":
                return call("cover", "set_cover_position", {**target, "position": clamp_percent(value)})
            if command == "stop":
                return curtain_stop(self.ha, ENTITIES["curtain1"])
            if command in ("open", "close"):
                return call("cover", f"{command}_cover", target)
        elif device == "dimmer1":
            target = {"entity_id": ENTITIES["dimmer1"]}
            if command == "set_level":
                level = clamp_percent(value)
                if level == 0:
                    return call("light", "turn_off", target)
                return call("light", "turn_on", {**target, "brightness_pct": level})
            if command in ("on", "off"):
                return call("light", f"turn_{command}", target)
            if command == "toggle":
                return call("light", "toggle", target)
        elif device == "speaker1":
            target = {"entity_id": ENTITIES["speaker1"]}
            simple = {"pause": "media_pause", "resume": "media_play", "stop": "media_stop",
                      "volume_up": "volume_up", "volume_down": "volume_down"}
            if command in simple:
                return call("media_player", simple[command], target)
            if command == "set_volume":
                return call("media_player", "volume_set", {**target, "volume_level": clamp_percent(value) / 100})
            if command == "play":
                return self.play(media_path(value), target)
            if command == "restore":
                self.playing_url = None
                return call("sonos", "restore", target)
        raise ValueError(f"unknown command '{command}' for {device}")

    def play(self, path, target):
        if not self.playing_url:  # keep the first snapshot if songs are played back to back
            self.ha.call("sonos", "snapshot", target)
        self.media["path"] = path
        url = f"http://{self.my_ip}:{self.args.http_port}/media/{urllib.parse.quote(os.path.basename(path))}"
        self.playing_url, self.song_started = url, False
        self.ha.call("media_player", "play_media", {**target, "media_content_id": url, "media_content_type": "music"})

    def camera_jpeg(self):
        with urllib.request.urlopen(f"{FRIGATE_URL}/api/{FRIGATE_CAMERA}/latest.jpg", timeout=10) as resp:
            return resp.read()


def clamp_percent(value):
    return max(0, min(100, int(round(float(value)))))


# ---------------------------------------------------------------- simulation

class SimulatedDevices:
    def __init__(self, hub, args):
        self.hub = hub
        self.args = args
        self.media = {"path": None}
        self.curtain_target = 100
        self.s = {
            "curtain1": {"status": "simulated", "position": 100, "state": "open"},
            "dimmer1": {"status": "simulated", "on": False, "level": 0, "power": 0.0},
            "speaker1": {"status": "simulated", "state": "idle", "volume": 30, "title": ""},
            "camera1": {"status": "simulated", "occupied": False},
            "motion1": {"status": "simulated", "motion": False, "illuminance": 120.0},
            "room_sensor1": {"status": "simulated", "temperature": 22.0, "humidity": 45.0, "co2": 800.0,
                             "air_quality": "good", "battery_low": False},
        }

    def tasks(self):
        return [self.tick()]

    async def tick(self):
        start = time.monotonic()
        while True:
            t = time.monotonic() - start
            c = self.s["curtain1"]
            if c["position"] != self.curtain_target:  # curtain moves 10 % per tick
                step = 10 if self.curtain_target > c["position"] else -10
                c["position"] = max(0, min(100, c["position"] + step))
                if abs(c["position"] - self.curtain_target) < 10:
                    c["position"] = self.curtain_target
                c["state"] = "opening" if step > 0 else "closing"
            else:
                c["state"] = "closed" if c["position"] == 0 else "open"
            sensor = self.s["room_sensor1"]  # temperature swings 22-28 °C over 2 minutes
            sensor["temperature"] = round(25 + 3 * math.sin(t * 2 * math.pi / 120), 1)
            sensor["co2"] = round(800 + 150 * math.sin(t / 30) + random.uniform(-5, 5))
            self.s["camera1"]["occupied"] = int(t // 15) % 2 == 0  # toggles every 15 s
            self.s["motion1"]["motion"] = int(t // 10) % 4 == 1   # 10 s of motion every 40 s
            for device, values in self.s.items():
                self.hub.publish_all(device, values)
            await asyncio.sleep(0.5)

    def command(self, device, command, value):
        if device == "curtain1":
            targets = {"open": 100, "close": 0}
            if command in targets:
                self.curtain_target = targets[command]
            elif command == "stop":
                self.curtain_target = self.s["curtain1"]["position"]
            elif command == "set_position":
                self.curtain_target = clamp_percent(value)
            else:
                raise ValueError(f"unknown command '{command}' for {device}")
        elif device == "dimmer1":
            d = self.s["dimmer1"]
            if command == "on":
                d.update(on=True, level=d["level"] or 100)
            elif command == "off":
                d["on"] = False
            elif command == "toggle":
                d.update(on=not d["on"], level=d["level"] or 100)
            elif command == "set_level":
                level = clamp_percent(value)
                d.update(on=level > 0, level=level or d["level"])
            else:
                raise ValueError(f"unknown command '{command}' for {device}")
            d["power"] = round(6.3 * d["level"] / 100, 2) if d["on"] else 0.0
        elif device == "speaker1":
            sp = self.s["speaker1"]
            if command == "play":
                path = media_path(value)
                sp.update(state="playing", title=os.path.basename(path))
            elif command in ("pause", "resume", "stop"):
                sp["state"] = {"pause": "paused", "resume": "playing", "stop": "idle"}[command]
            elif command in ("volume_up", "volume_down"):
                sp["volume"] = max(0, min(100, sp["volume"] + (5 if command == "volume_up" else -5)))
            elif command == "set_volume":
                sp["volume"] = clamp_percent(value)
            elif command == "restore":
                sp.update(state="idle", title="")
            else:
                raise ValueError(f"unknown command '{command}' for {device}")
        else:
            raise ValueError(f"unknown device '{device}'")

    def camera_jpeg(self):
        raise FileNotFoundError("no camera in simulation mode")


# ---------------------------------------------------------------- servers

def start_http(devices, port):
    """Serve /camera.jpg (proxied from Frigate) and /media/<file> (the current song)."""

    class Handler(http.server.SimpleHTTPRequestHandler):
        def translate_path(self, request_path):
            name = urllib.parse.unquote(urllib.parse.urlparse(request_path).path)
            current = devices.media["path"]
            if current and name == f"/media/{os.path.basename(current)}":
                return current
            return ""

        def do_GET(self):
            if urllib.parse.urlparse(self.path).path == "/camera.jpg":
                try:
                    image = devices.camera_jpeg()
                except Exception:
                    self.send_error(503, "camera unavailable")
                    return
                self.send_response(200)
                self.send_header("Content-Type", "image/jpeg")
                self.send_header("Content-Length", str(len(image)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(image)
                return
            super().do_GET()

        def handle(self):
            try:
                super().handle()
            except ConnectionError:
                pass  # speakers open several connections and drop the ones they don't need

        def log_message(self, fmt, *args):
            pass  # requests happen several times per second; logging them is noise

    server = http.server.ThreadingHTTPServer(("0.0.0.0", port), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()


async def main():
    args = parse_args()
    hub = Hub("simulated" if args.simulate else "real", args)
    devices = SimulatedDevices(hub, args) if args.simulate else RealDevices(hub, args)
    hub.devices = devices
    if args.alarm_actions:
        try:
            media_path(args.alarm_sound)
        except ValueError as e:
            log(f"warning: {e}; the alarm will close the curtain but play nothing")

    async def handle_client(ws):
        hub.clients.add(ws)
        log(f"Unity connected from {ws.remote_address[0]} ({len(hub.clients)} client(s))")
        try:
            for (device, prop), value in list(hub.state.items()):
                await ws.send(hub.message(device, prop, value))
            async for raw in ws:
                try:
                    msg = json.loads(raw)
                    device, command = msg["device"], msg["command"]
                except (json.JSONDecodeError, KeyError, TypeError):
                    await hub.send_error(ws, "bridge", f"bad command: {raw!r}")
                    continue
                log(f"command {device}.{command} {msg.get('value', '')}".rstrip())
                try:
                    await asyncio.to_thread(devices.command, device, command, msg.get("value"))
                except (ValueError, HAError) as e:
                    await hub.send_error(ws, device, str(e))
        except websockets.ConnectionClosed:
            pass
        finally:
            hub.clients.discard(ws)
            log(f"Unity disconnected ({len(hub.clients)} client(s))")

    start_http(devices, args.http_port)
    async with websockets.serve(handle_client, "0.0.0.0", args.port):
        mode = "SIMULATION" if args.simulate else "real devices"
        log(f"Bridge running with {mode}: ws://0.0.0.0:{args.port}, http://0.0.0.0:{args.http_port}/camera.jpg")
        await asyncio.gather(*devices.tasks())


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
