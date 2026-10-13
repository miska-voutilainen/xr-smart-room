# Procedural animation — Zigbee rotary dimmer

Left-drag the knob horizontally to adjust brightness. Scroll for fine adjustment. A short click toggles power and pushes the knob inward by 0.7 mm. Rotation spans −135° to +135° around the existing shaft pivot. The optional linked lamp fades with brightness.

Implemented in `../Scripts/RotaryDimmer.cs` and the referenced Shared helpers. No Animator, AnimationClip, rig or runtime asset lookup is required. Animation uses Time.deltaTime and saved local rest transforms. Do not animate the same transforms using a second Animator simultaneously.
