# Procedural animation — Security camera

Left-drag the head for tilt and yaw. A short head click toggles power. Click the round floodlight surface to toggle it. The head smoothly rotates about Camera_Tilt_Pivot; the wall mount and cable remain fixed. A powered camera shows a red status light; floodlight emission and its spot light require both power and floodlight enabled.

Implemented in `../Scripts/SecurityCameraDevice.cs` and the referenced Shared helpers. No Animator, AnimationClip, rig or runtime asset lookup is required. Animation uses Time.deltaTime and saved local rest transforms. Do not animate the same transforms using a second Animator simultaneously.
