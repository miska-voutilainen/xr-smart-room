# Build stage 2: details, shaders, lighting/render. Run after build_room.py:
#   blender -b main.blend --python build_room.py --python apply_materials.py
# Auto-discovers scripts (no list to edit), in this order:
#   materials/*.py  geometry + detail per part (sorted by name)
#   shaders/*.py    procedural material library, overrides materials by name
#   render/*.py     world, weather, lights, cameras, render + compositor settings
# Files starting with "_" are skipped (helpers/modules). Every script must be standalone and idempotent.
import glob
import os

import bpy

# Scripts live next to this file, not next to the blend (a scratch copy elsewhere used to apply nothing, silently).
HERE = os.path.dirname(os.path.abspath(__file__))

for stage in ("materials", "shaders", "render"):
    paths = sorted(glob.glob(os.path.join(HERE, stage, "*.py")))
    assert paths, "no scripts in " + os.path.join(HERE, stage)
    for path in paths:
        if os.path.basename(path).startswith("_"):
            continue
        exec(compile(open(path).read(), path, "exec"), {"__name__": "__main__", "__file__": path})
        print("APPLIED", stage, os.path.basename(path))

bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
