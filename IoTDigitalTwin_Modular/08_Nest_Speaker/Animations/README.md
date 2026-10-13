# Procedural animation — Google/Nest-style smart speaker

Click the rim mute switch. Left-drag or scroll the fabric face for volume. A short click on the face toggles active state. The mute switch slides 3 mm. Muted lights are red; active unmuted lights animate using four colours; changing volume briefly displays a four-light level indication.

Implemented in `../Scripts/NestSpeakerDevice.cs` and the referenced Shared helpers. No Animator, AnimationClip, rig or runtime asset lookup is required. Animation uses Time.deltaTime and saved local rest transforms. Do not animate the same transforms using a second Animator simultaneously.
