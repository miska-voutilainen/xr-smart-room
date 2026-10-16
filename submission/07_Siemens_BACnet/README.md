# 07 Siemens BACnet

Real device: Siemens KNX room unit via BACnet gateway (room_sensor1)

## vr_click.mp4: click in VR, result in VR
- What is clicked: Point at the display and then the status LED, pressing the trigger on each.
- What happens in VR: The display and status indicator change state.

## real_click.mp4: click in the real lab, result in VR
- What to do in real life: Change the room temperature (heater or open window) so the room unit reads a new value.
- What the bridge sends and what happens in VR: room_sensor1.status online, temperature 21 > 23 > 25. The Siemens unit display shows the new reading.
