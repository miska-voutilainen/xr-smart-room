# Render reference-photo cameras for photo/render comparison. NOT run by apply_materials ("_" prefix).
#   tools/bl -b <copy>.blend -t 2 --python render/_compare.py -- [--cams 120939,112212|all] [--out DIR]
#            [--long 960] [--samples 64] [--mode cycles|lines] [--nocomp]
# cycles: Cam_<id> at the photo aspect, exposure = light.py baseline + (9.34 - photo EV100) so each frame is exposed
#         like its photo.  lines: Workbench flat/outline render for checking the camera match (blend it over the photo).
# Then: python3 render/_sbs.py DIR <ids...>  -> photo | render | 50 % blend sheets.
import os
import sys

import bpy

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
opt = {k.lstrip("-"): (argv[i + 1] if i + 1 < len(argv) and not argv[i + 1].startswith("--") else "1")
       for i, k in enumerate(argv) if k.startswith("--")}
s = bpy.context.scene
names = sorted(o.name for o in bpy.data.objects if o.name.startswith("Cam_"))
if opt.get("cams", "all") != "all":
    names = ["Cam_" + c for c in opt["cams"].split(",")]
cams = [bpy.data.objects[n] for n in names]
out = opt.get("out", os.path.join(os.path.dirname(bpy.data.filepath), "compare"))
os.makedirs(out, exist_ok=True)
long_px = int(opt.get("long", 960))
mode = opt.get("mode", "cycles")
base_exposure = s.view_settings.exposure                 # set by render/light.py for EV100 9.34
if mode == "lines":
    s.render.engine = 'BLENDER_WORKBENCH'
    sh = s.display.shading
    sh.light, sh.color_type = 'FLAT', 'RANDOM'
    sh.show_object_outline, sh.object_outline_color = True, (0, 0, 0)
    s.render.use_compositing = False
    s.view_settings.view_transform, s.view_settings.look, s.view_settings.exposure = 'Standard', 'None', 0.0
else:
    if "samples" in opt:
        s.cycles.samples = int(opt["samples"])
    s.render.use_compositing = "nocomp" not in opt
s.render.resolution_percentage = 100
for cam in cams:
    rx, ry = cam.get("res_x", 1400), cam.get("res_y", 1050)
    k = long_px / max(rx, ry)
    s.render.resolution_x, s.render.resolution_y = round(rx * k), round(ry * k)
    s.camera = cam
    if mode != "lines":
        s.view_settings.exposure = base_exposure + (9.34 - cam.get("ev100", 9.34))
    pid = cam.name[4:]
    s.render.filepath = os.path.join(out, "%s_%s.png" % (pid, mode))
    bpy.ops.render.render(write_still=True)
    print("COMPARE", pid, s.render.resolution_x, s.render.resolution_y, "exp %.2f" % s.view_settings.exposure)
