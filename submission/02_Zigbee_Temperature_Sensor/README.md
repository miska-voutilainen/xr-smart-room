# 02 Zigbee Temperature Sensor

Real device: Aqara temperature and humidity display (room_sensor1)

## vr_click.mp4: click in VR, result in VR
- What is clicked: Point at the display and press the trigger (Pair zone).
- What happens in VR: The display reacts to the press (pairing state).

## real_click.mp4: click in the real lab, result in VR
- What to do in real life: Warm the real room sensor (hold it in your hand or breathe on it).
- What the bridge sends and what happens in VR: room_sensor1.temperature 22 > 24 > 26.5 and humidity 52. The display shows the new values and the digits change colour (temperature tint scale).
