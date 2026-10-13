# Procedural animation — Roller blind mechanism

Drag horizontally along the bottom rail to choose a 0–100% target, or call Open/Close/Stop. At 100%, cloth Raise_Blind reaches its imported maximum frame weight and the rail moves from Y=−0.484 m to −0.05875 m. Roller and clutch rotate together about their existing pivots; chain beads circulate inside one mesh. The rail and cloth share the same 0.42525 m travel.

Implemented in `../Scripts/RollerBlindDevice.cs` and the referenced Shared helpers. No Animator, AnimationClip, rig or runtime asset lookup is required. Animation uses Time.deltaTime and saved local rest transforms. Do not animate the same transforms using a second Animator simultaneously.
