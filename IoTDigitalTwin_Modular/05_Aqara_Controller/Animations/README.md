# Procedural animation — Aqara bead-chain controller

Hold the physical Raise/Lower buttons to drive; release to Stop. Demo-panel Raise/Lower commands continue to their endpoints until Stop. Click the sliding drive cover to move it 18 mm upwards. Buttons depress 0.4 mm. The sprocket rotates and bead islands travel around a closed capsule loop inside one mesh. Standalone operation is the prefab default.

Implemented in `../Scripts/AqaraChainController.cs` and the referenced Shared helpers. No Animator, AnimationClip, rig or runtime asset lookup is required. Animation uses Time.deltaTime and saved local rest transforms. Do not animate the same transforms using a second Animator simultaneously.
