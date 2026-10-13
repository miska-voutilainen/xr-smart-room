# Procedural animation — Z-Wave temperature controller

Click all five existing touch regions: Schedule toggles a simulated schedule indicator; Mode cycles Auto → Heat → Cool; Down/Up change target by 0.5 °C; Power toggles the display state. OFF hides the measured reading. Schedule is an indicator, not a time-based schedule engine.

Implemented in `../Scripts/TemperatureController.cs` and the referenced Shared helpers. No Animator, AnimationClip, rig or runtime asset lookup is required. Animation uses Time.deltaTime and saved local rest transforms. Do not animate the same transforms using a second Animator simultaneously.
