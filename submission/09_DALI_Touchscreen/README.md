# 09 DALI Touchscreen

Real device: Lunatone DALI-2 display panel (dali1)

## vr_click.mp4: click in VR, result in VR
- What is clicked: Point at each zone of the panel and press the trigger.
- What happens in VR: The panel changes state; the ceiling lights follow its on/off and colour.

## real_click.mp4: click in the real lab, result in VR
- What to do in real life: On the real DALI panel switch all lights off, then on, then set cold white.
- What the bridge sends and what happens in VR: dali1.all_on false > true, all_kelvin 6500. The ceiling lights go off, come back on, then turn cold white.
