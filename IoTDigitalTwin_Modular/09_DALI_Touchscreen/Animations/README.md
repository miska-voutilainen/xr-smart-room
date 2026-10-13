# Procedural animation — DALI touchscreen lighting panel

Click On/Off, drag Brightness vertically, drag Colour Temperature vertically, click/drag the Colour Field, and click any of the three scenes. Runtime numeric readouts and four visual markers overlay a cleaned version of the original UI, without duplicate static sample readings. Task uses 100%/4500 K; Presentation 1 uses 30% warm RGB; Presentation 2 uses 15% blue RGB.

Implemented in `../Scripts/DALILightingPanel.cs` and the referenced Shared helpers. No Animator, AnimationClip, rig or runtime asset lookup is required. Animation uses Time.deltaTime and saved local rest transforms. Do not animate the same transforms using a second Animator simultaneously.
