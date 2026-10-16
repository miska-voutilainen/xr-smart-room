# Wall switch closes the curtain: VR twin of the lab video

vr_switch_curtain.mp4, 30 s, 1920x1080, 30 fps. Filmed in the virtual lab, in the same spot as the real video.

| Time | Real lab video | VR video |
|---|---|---|
| 0:00 to 0:06 | The person stands at demo board 1, looks at the sensor, then to the right | The headset view is at demo board 1: the PIR sensor, then right, then down to the switch |
| 0:06 | Presses the wall switch once | The right hand presses the rocker switch on board 1, in the same place as the real switch (board photo, 57 % across, 89 % down). The rocker tips in and springs back. Unity sends {"device": "curtain1", "command": "close"} |
| 0:06 to 0:09 | The camera turns to the window | The view turns to window N1 (about 2.5 s) |
| 0:09 to 0:30 | The roller blind closes from the top | The N1 blind follows curtain1.position from the bridge |
| 0:30 | 75 % closed | 75 % closed (curtain1.position = 25) |

The rocker rests with its top pressed in and its bottom out. The hand pushes the bottom, the rocker tips the other way and springs back, like the real momentary switch.

The bridge for this video was a stand-in that moves the curtain at the real motor's speed from the lab video (75 % in 24 s). The hand is the XR Hands sample mesh, posed by script.

Regenerate: CLIP=switch with unity/Assets/Editor/OrangeRoomClickClip.cs (see the top of the file).
