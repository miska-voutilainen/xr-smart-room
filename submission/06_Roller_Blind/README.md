# 06 Roller Blind

Real device: Roller blind (curtain1)

## vr_click.mp4: click in VR, result in VR
- What is clicked: Point at the bottom rail of the blind, hold the trigger and pull down.
- What happens in VR: The blind follows the drag; on release Unity sends curtain1 set_position.

## real_click.mp4: click in the real lab, result in VR
- What to do in real life: Raise the real curtain (Raise button on the chain controller or the Home Assistant app).
- What the bridge sends and what happens in VR: curtain1.position 0 > 10 > ... > 100 every 0.5 s. The virtual blind rolls up to open. Same device as 05, opposite direction.
