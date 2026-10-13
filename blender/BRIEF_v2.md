# Wave v2 brief (shared by every agent)

Project: photo-real Blender 5.2 recreation of an office/kitchenette ("room 1") + the lab to its left (Room2) +
the space beyond the pink entrance door, later exported to Unity 2022.3 URP (XR). v1 is frozen in `versions/v1/`.
Goal of v2: realism. Reference look: `Photos/4/Modern Tech Classroom and Coffee Station.png` (soft real light,
glossy terrazzo reflections, natural falloff, real materials). Geometry truth: phone photos `Photos/1..3`
(EXIF-matched cameras `Cam_<photoid>` exist in the scene, see `render/cameras.py`). Hero view = camera `Camera`.

## Pipeline (read before touching anything)
- Scene is rebuilt from scripts: `build_room.py` then `apply_materials.py`, which runs `materials/*.py`,
  `shaders/*.py`, `render/*.py` in sorted order (files starting with `_` skipped). Every script is standalone + idempotent.
- `shaders/hard.py` / `shaders/arch.py` override materials BY NAME after `materials/*.py`. If you take over a
  material, do it in your own later-sorting script (e.g. `shaders/zz_<you>.py`) so it wins; do not edit hard.py/arch.py
  unless you own them.
- **Never save over `main.blend`.** Work on a copy in your own scratch dir:
  `cp main.blend $MY/test.blend; tools/bl -b $MY/test.blend -t 2 --python <your script> --python-expr "import bpy; bpy.ops.wm.save_mainfile()"`
  The orchestrator does the single full rebuild of main.blend between waves.
- Only edit files you own (listed in your task). Need a change elsewhere: say so in your report.
- `tools/bl` = shared slot lock (3 Blender processes max on this laptop, 15 GB RAM, 4 GB GPU). Always use it for local
  Blender, always `-t 2`. **No local Cycles renders above 32 samples / 50 %.** Local Workbench/Eevee checks are fine.

## Rendering on the HPC (L40S GPUs, through the Pi)
- `hpc/submit <file.blend> <tag> [CAM=Cam_122209] [SAMPLES=64] [PCT=50]` blocks until done (~40-90 s with a warm
  worker), writes `renders/hpc/<tag>/frame_0001.png` (+ `log.txt`). Tag must be unique: `<yourname>_<step>`.
  It packs images automatically. It uses the scene camera unless CAM is given (photo cams set their own aspect).
- Never ssh to the cluster yourself (the login node rate-limits SSH connections). A line `Ncat: Could not resolve hostname
  "<PI_HOST>"` is harmless noise.
- Iterate at SAMPLES=64 PCT=50; one final at SAMPLES=256 PCT=100. Run several submits in parallel (`&`) if needed.
- Photo comparison: `render/_compare.py` + `render/_sbs.py` (photo | render | 50 % blend) exist; reuse them.

## Progress screenshots (the user watches live)
Put a handful of meaningful images (not every iteration) in `renders/v2/<yourname>/`, named `NN_<what>.png|jpg`
(before / during / after, side-by-side with the photo when relevant). Keep it to ~3-6 images.

## Downloads
CC0 / free sources first (ambientCG, Poly Haven, textures.com free, Wikimedia). Images only. Save to
`textures/<yourname>/`, with `SOURCES.txt` (URL + licence per file). Max 2K resolution per map (Unity budget).
Load them in Blender with absolute-path-independent paths (`//textures/...` relative to the blend in the project
root, or os.path from the script's `__file__`).

## Unity constraints (keep in mind, don't over-engineer)
Real-scale meshes, sane tri counts (hero prop <= ~5k tris, whole scene < 300k), UVs on anything textured,
no view-dependent nodes feeding Base Color/Roughness/Normal (they get baked later).

## Report back (final message, concise)
Files changed/created, objects/materials touched, tri counts before/after, image paths in `renders/v2/<you>/`,
open problems, anything another owner must change.
