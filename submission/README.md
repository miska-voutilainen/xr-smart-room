# Submission videos and screenshots

XR Smart Room twin, 1920x1080 at 30 fps, recorded in Unity play mode on 16 October 2026.

Each device folder has:
- vr_click.mp4: a scripted controller ray selects the device in VR and the result shows in VR. It makes the same calls as the XR controller trigger (XRDeviceInput: ControlDown/ControlUp and RoomBridge.UserControl). The ray line is drawn for the video.
- real_click.mp4: the JSON messages the bridge sends when a person uses the real device are fed into the app (RoomBridge.Parse and Apply, the same path as a WebSocket message), and the result shows in VR.
- README.md: what to click in real life and what happens in VR.

Only 05 (Aqara controller, VR click) ran with the bridge online against bridge/server.py --simulate. The other VR clicks run with the bridge offline, because the app ignores VR input on mirrored devices while online (the real device is in charge).
03 Z-Wave thermostat has no videos: it has no lab device and is not placed in the scene.

screenshots/: room views from eye height (four directions per room), reference camera views and the device wall.

Regenerate: unity/Assets/Editor/OrangeRoomClickClip.cs (instructions at the top of the file).
