# Procedural animation — Siemens BACnet device

Click the grey display face to increment the number; scroll to adjust it. Click the green status point to toggle it. The original static LED_Dot_Display renderer is retained but disabled. A generated 36-dot mesh displays two 3×5 digits, five level dots and one cursor; per-vertex colours change at runtime.

Implemented in `../Scripts/SiemensBACnetDevice.cs` and the referenced Shared helpers. No Animator, AnimationClip, rig or runtime asset lookup is required. Animation uses Time.deltaTime and saved local rest transforms. Do not animate the same transforms using a second Animator simultaneously.
