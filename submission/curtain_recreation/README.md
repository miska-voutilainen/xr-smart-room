# Curtain close: VR recreation of the lab video

vr_curtain_close.mp4, 30 s, 1920x1080, 30 fps. Same timing as the real lab video.

| Time | Real lab video | VR video |
|---|---|---|
| 0:00 to 0:06 | The person looks at the sensor, then to the right | The headset view looks at the device wall (temperature display), then right towards the TV and window, then back to the curtain controller |
| 0:06 | Presses the curtain switch | The controller ray points at the Lower button on the Aqara chain controller and the trigger is pressed. Unity sends {"device": "curtain1", "command": "close"} to the bridge |
| 0:06 to 0:09 | The camera turns towards the curtains | The view turns up to the roller blind (about 2.5 s) |
| 0:09 to 0:30 | The curtain closes from the top | The bridge reports curtain1.position every 0.5 s and the virtual blind follows. The TV bridge screen shows the same position live |
| 0:30 | The curtain is 75 % closed | The curtain is 75 % closed (curtain1.position = 25) |

The bridge for this video was a stand-in that moves the curtain at the real motor's speed from the lab video (75 % in 24 s). bridge/server.py --simulate moves it much faster (10 % every 0.5 s).
In VR the Lower button is held down, like the real chain controller: releasing it sends stop.

Regenerate: CLIP=curtain with unity/Assets/Editor/OrangeRoomClickClip.cs (see the top of the file).
