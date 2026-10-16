# 05 Aqara Controller

Real device: Aqara curtain chain controller (curtain1)

## vr_click.mp4: click in VR, result in VR
- What is clicked: Point at the Lower button and hold the trigger for 4 s. Bridge online (server.py --simulate).
- What happens in VR: Unity sends curtain1 close, the bridge answers with curtain1.position updates and the blind comes down. Releasing sends stop.

## real_click.mp4: click in the real lab, result in VR
- What to do in real life: Press and hold the Lower button on the real chain controller.
- What the bridge sends and what happens in VR: curtain1.position 100 > 90 > ... > 0 every 0.5 s. The virtual blind rolls down to closed.
