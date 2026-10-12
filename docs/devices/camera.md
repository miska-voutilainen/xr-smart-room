# Camera - Aqara Camera via Frigate

An Aqara IP camera that films the lab room. The bridge doesn't read the camera directly: Frigate, which runs on the Home Assistant machine, already receives the video and detects people, so the bridge uses Frigate's API.

| | |
|---|---|
| Camera | Aqara camera, listed in Home Assistant as "Aqara Wired Outdoor Camera G5", 192.168.15.144 |
| Camera stream | RTSP on port 8554, path `ch3`, needs a login |
| Frigate | `http://192.168.15.249:5000`, version 0.17.2, no login |
| Frigate camera name | `cam_192_168_15_144` |
| Bridge name | `camera1` |

## How It Works

```
Aqara camera --RTSP--> Frigate (person detection) --HTTP--> bridge --> XR
```

| Frigate setting | Value |
|---|---|
| Detection | 1280x720 at 5 fps |
| Tracked objects | Person only (min score 0.4, threshold 0.5) |
| Snapshots | On |
| Recording | Off |
| Zones | None |
| MQTT | Off, so the bridge reads events over HTTP |

The bridge uses three Frigate endpoints:
- `/api/stats`: frame rates.
- `/api/<camera>/latest.jpg`: the current frame.
- `/api/events?cameras=...&labels=person`: person detections.

## Testing

```
python bridge/lab.py camera status              # camera and detection frame rates
python bridge/lab.py camera snapshot room.jpg   # save the current frame
python bridge/lab.py camera watch               # print each person detection
```

## Bridge Server

| Sends to XR | Meaning |
|---|---|
| `occupied` | True while a person is detected (score at least `--min-score`, default 0.5) and for `--hold` seconds (default 30) after the last detection |
| `status` | Whether Frigate can be reached |

**UC1 rule.** When `camera1.occupied` changes, `virtual_light.on` follows. Only the virtual room light is switched.

**Camera frame.** The server also serves the current frame at `http://<bridge PC>:8000/camera.jpg`, so the XR app can show the camera without talking to Frigate itself.

## Test Results

| Test | Result |
|---|---|
| Frigate frame rates | Works, about 5 fps from the camera and 15 fps detection |
| Current frame, from Frigate and from the bridge | Works, 1280x720 picture of the lab room |
| Person detection | Works, 3 detections in 20 seconds with scores 0.57-0.64 |
| Occupancy -> virtual light in `server.py` | Works |

## Notes

- **RTSP login.** The Frigate config we were given contains an RTSP login, but the camera rejected it when used directly. Frigate still receives video, so it probably uses newer credentials. The current login is shown in the Aqara Home app under the camera's RTSP LAN preview setting. We don't need it while Frigate works.
- **Home Assistant snapshots.** Home Assistant's own camera entity (`camera.192_168_15_144_cam1`) returns error 500 for snapshots. Use Frigate instead.
- **Image size.** Frigate ignored the resize parameter we tried and always returned 720p.
- **Occupancy.** Detection scores are fairly low (about 0.5-0.65), and someone is almost always in the room during the day, so `occupied` stays true most of the time.

## Privacy

The camera films people in the lab.
- **Snapshots stay out of git.** `*.jpg` is git-ignored.
- **Tell people** when the XR view shows the camera.
- **Only the occupied state** goes through the data flow. Frames are only served when the XR app asks for one.

## Next Steps

- **Frigate zone.** A zone such as "in front of stand 1" would make UC1 react when someone walks up, not whenever anyone is in view. The Frigate config belongs to the lab, so ask the staff to add it.
- **Live panel in XR.** Load `/camera.jpg` 2-5 times per second into a texture. Avoid RTSP or WebRTC in Unity; both need native plugins.
- **Stretch goal.** Frigate events include a bounding box. It could be mapped to a floor position to show where people stand in the virtual room.
