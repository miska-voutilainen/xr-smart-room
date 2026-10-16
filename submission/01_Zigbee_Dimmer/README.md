# 01 Zigbee Dimmer

Real device: Aqara Dimmer Switch H2 (dimmer1)

## vr_click.mp4: click in VR, result in VR
- What is clicked: Point the controller ray at the dimmer knob and press the trigger once.
- What happens in VR: The dimmer switches off and the ceiling lights in the lab fade out.

## real_click.mp4: click in the real lab, result in VR
- What to do in real life: Press the real H2 dimmer to switch it on, then turn the knob up.
- What the bridge sends and what happens in VR: dimmer1.on true, then dimmer1.level 20 > 45 > 70 > 100. The virtual dimmer turns on and the ceiling lights fade in brighter with every step.
