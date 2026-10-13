# Orthographic check sheet for one or more objects (Workbench, fast, no materials needed).
# Usage:
#   tools/bl -b scene.blend --python tools/ortho.py -- --objects Chair_1,Chair_2 --out /some/dir/chair [--res 700]
# Writes <out>_sheet.png: 3x2 grid
#   top row:    FRONT (looking +Y) | RIGHT (looking -X) | TOP (looking -Z)
#   bottom row: BACK  (looking -Y) | LEFT  (looking +X) | PERSP (3/4 view)
# A 10 cm checker floor is NOT drawn; instead each view prints its ortho width (metres) to stdout:
#   ORTHO <view> width_m=<w>  -> 1 px = w / res metres.
# Children of the named objects are included automatically.
import math
import sys

import bpy
import numpy as np
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
opts = dict(zip(argv[::2], argv[1::2]))
names = [n for n in opts["--objects"].split(",") if n]
out = opts["--out"]
res = int(opts.get("--res", 700))

sc = bpy.context.scene
targets = set()


def collect(ob):
    targets.add(ob)
    for ch in ob.children:
        collect(ch)


for n in names:
    ob = bpy.data.objects.get(n)
    if ob is None:
        print("ORTHO missing object", n)
        continue
    collect(ob)
if not targets:
    sys.exit("ORTHO no objects")

for ob in sc.objects:
    ob.hide_render = ob not in targets

deps = bpy.context.evaluated_depsgraph_get()
pts = []
for ob in targets:
    if ob.type == "MESH":
        ev = ob.evaluated_get(deps)
        pts += [ev.matrix_world @ Vector(c) for c in ev.bound_box]
lo = Vector([min(p[i] for p in pts) for i in range(3)])
hi = Vector([max(p[i] for p in pts) for i in range(3)])
ctr, size = (lo + hi) / 2, hi - lo
print("ORTHO bbox min", tuple(round(v, 4) for v in lo), "max", tuple(round(v, 4) for v in hi),
      "size", tuple(round(v, 4) for v in size))

sc.render.engine = "BLENDER_WORKBENCH"
sh = sc.display.shading
sh.light, sh.color_type = "STUDIO", "MATERIAL"
sh.show_cavity, sh.cavity_type = True, "BOTH"
sh.show_object_outline = True
sh.show_shadows = False
sc.render.film_transparent = False
sc.render.resolution_x = sc.render.resolution_y = res
sc.render.resolution_percentage = 100
sc.view_settings.view_transform = "Standard"
if sc.world:
    sc.world.color = (0.18, 0.18, 0.2)

cam_data = bpy.data.cameras.new("ORTHO_cam")
cam = bpy.data.objects.new("ORTHO_cam", cam_data)
sc.collection.objects.link(cam)
sc.camera = cam
far = size.length * 2 + 2
cam_data.clip_start, cam_data.clip_end = 0.001, far * 2

# view: (direction camera looks, which two bbox axes span the image)
views = [
    ("FRONT", Vector((0, 1, 0)), (0, 2)),
    ("RIGHT", Vector((-1, 0, 0)), (1, 2)),
    ("TOP", Vector((0, 0, -1)), (0, 1)),
    ("BACK", Vector((0, -1, 0)), (0, 2)),
    ("LEFT", Vector((1, 0, 0)), (1, 2)),
    ("PERSP", Vector((-1, 1.2, -0.8)).normalized(), None),
]
tiles = []
for name, d, axes in views:
    cam.location = ctr - d * far
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()  # camera up = world Z
    if name == "TOP":
        cam.rotation_euler = (0, 0, 0)
    if axes:
        cam_data.type = "ORTHO"
        cam_data.ortho_scale = max(size[axes[0]], size[axes[1]]) * 1.12 + 0.01
        print(f"ORTHO {name} width_m={cam_data.ortho_scale:.4f}")
    else:
        cam_data.type = "PERSP"
        cam_data.lens = 50
        cam.location = ctr - d * (size.length * 1.6 + 0.2)
    path = f"{out}_{name}.png"
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    img = bpy.data.images.load(path)
    tiles.append(np.array(img.pixels[:], dtype=np.float32).reshape(res, res, 4))
    bpy.data.images.remove(img)

# Blender pixel rows are bottom-up: stack bottom row first.
row_top = np.concatenate(tiles[0:3], axis=1)
row_bot = np.concatenate(tiles[3:6], axis=1)
sheet = np.concatenate([row_bot, row_top], axis=0)
img = bpy.data.images.new("ORTHO_sheet", res * 3, res * 2, alpha=True)
img.pixels = sheet.ravel()
img.filepath_raw = f"{out}_sheet.png"
img.file_format = "PNG"
img.save()
print("ORTHO sheet", f"{out}_sheet.png")
