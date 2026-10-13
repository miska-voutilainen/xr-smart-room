# Procedural animation — Zigbee temperature and humidity LCD sensor

Click Plus/Minus for ±0.5 °C. Click Mode to switch those buttons to ±1% humidity. Side buttons depress by 0.4 mm and return. Click the small top pairing control for a five-second PAIR indicator. The static sample numbers are replaced with live mesh text.

Implemented in `../Scripts/TemperatureLCD.cs` and the referenced Shared helpers. No Animator, AnimationClip, rig or runtime asset lookup is required. Animation uses Time.deltaTime and saved local rest transforms. Do not animate the same transforms using a second Animator simultaneously.
