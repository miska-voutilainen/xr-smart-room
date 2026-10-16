# 04 Security Camera

Real device: Aqara camera G5 (camera1)

## vr_click.mp4: click in VR, result in VR
- What is clicked: Point at the camera head and press the trigger.
- What happens in VR: The camera powers on and its red recording LED lights.

## real_click.mp4: click in the real lab, result in VR
- What to do in real life: Walk into the camera view, then trigger the room alarm (temperature above the threshold).
- What the bridge sends and what happens in VR: camera1.occupied true, then room_sensor1.alarm true. The virtual camera turns on, then its floodlight switches on.
