"""Re-import the exported FBX files into an empty Blender and check them against the manifest.
    tools/bl -b --factory-startup --python unity/_validate_fbx.py -- <Assets dir>
Checks: names + hierarchy, world bbox (scale/axes round trip), root scale, UV0/UV1 present, in 0..1 and
non-overlapping (UV1 per object, UV0 per material), material names, texture files + sizes. Exit 1 on failure."""
import json
import os
import struct
import sys

import bpy
import numpy as np
from mathutils import Vector

ASSETS = os.path.abspath(sys.argv[sys.argv.index("--") + 1])
man = json.load(open(os.path.join(ASSETS, "Models", "OrangeRoom_manifest.json")))
fails, notes = [], []


def check(ok, msg):
    if not ok:
        fails.append(msg)
    return ok


def png_size(path):
    with open(path, "rb") as f:
        return struct.unpack(">II", f.read(24)[16:24])


def uv_tris(o, layer, mats=None):
    me = o.data
    me.calc_loop_triangles()
    uv = np.array([d.uv[:] for d in me.uv_layers[layer].data])
    return np.array([uv[list(t.loops)] for t in me.loop_triangles
                     if mats is None or o.material_slots[t.material_index].material.name in mats]).reshape(-1, 3, 2)


def overlap(tri, res=256):
    """Fraction of covered texels covered more than once (pixel-centre sampling, edges excluded)."""
    cnt = np.zeros((res, res), np.int16)
    for a, b, c in tri * res:
        x0, y0 = np.floor(np.minimum(np.minimum(a, b), c)).astype(int)
        x1, y1 = np.ceil(np.maximum(np.maximum(a, b), c)).astype(int)
        x0, y0, x1, y1 = max(x0, 0), max(y0, 0), min(x1, res), min(y1, res)
        if x1 <= x0 or y1 <= y0:
            continue
        gx, gy = np.meshgrid(np.arange(x0, x1) + 0.5, np.arange(y0, y1) + 0.5)
        d = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
        if abs(d) < 1e-12:
            continue
        w1 = ((gx - a[0]) * (c[1] - a[1]) - (gy - a[1]) * (c[0] - a[0])) / d
        w2 = ((b[0] - a[0]) * (gy - a[1]) - (b[1] - a[1]) * (gx - a[0])) / d
        e = 1e-4
        inside = (w1 > e) & (w2 > e) & (1 - w1 - w2 > e)
        cnt[y0:y1, x0:x1] += inside
    cov = (cnt > 0).sum()
    return float((cnt > 1).sum()) / max(cov, 1)


def world_bbox(o):
    pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
    return [[min(p[i] for p in pts) for i in range(3)], [max(p[i] for p in pts) for i in range(3)]]


for rel in man["files"]:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=os.path.join(ASSETS, rel))
    area = os.path.splitext(os.path.basename(rel))[0]
    objs = {o.name: o for o in bpy.data.objects}
    entries = [e for e in man["objects"] if e["area"] == area]
    per_mat = {}
    for e in entries:
        name = e["lods"][0]["name"] if "lods" in e else e["name"]
        o = objs.get(name)
        if not check(o is not None, f"{rel}: missing {name}"):
            continue
        if "lods" in e:
            root = objs.get(e["name"])
            check(root and all(objs.get(x["name"]) and objs[x["name"]].parent == root for x in e["lods"]),
                  f"{rel}: LOD hierarchy broken for {e['name']}")
        elif e["parent"]:
            check(o.parent and o.parent.name == e["parent"], f"{rel}: {name} parent {o.parent} != {e['parent']}")
        got = world_bbox(o)
        err = max(abs(got[i][k] - e["bbox_blender"][i][k]) for i in range(2) for k in range(3))
        check(err < 2e-3, f"{rel}: {name} bbox off by {err:.4f} m")
        top = o
        while top.parent:
            top = top.parent
        check(all(abs(s - 1) < 1e-4 for s in top.matrix_world.to_scale()), f"{rel}: {top.name} root scale "
              f"{tuple(round(s, 4) for s in top.matrix_world.to_scale())}")
        slots = [s.material.name if s.material else None for s in o.material_slots]
        check(slots == e["materials"], f"{rel}: {name} materials {slots} != {e['materials']}")
        if e["glass"]:
            continue
        uvs = [u.name for u in o.data.uv_layers]
        if not check(len(uvs) == 2, f"{rel}: {name} UV layers {uvs}"):
            continue
        t1 = uv_tris(o, 1)
        check(t1.min() >= -1e-4 and t1.max() <= 1 + 1e-4, f"{rel}: {name} UV1 outside 0..1")
        ov = overlap(t1)
        check(ov < 0.005, f"{rel}: {name} UV1 overlap {ov:.3%}")
        for m in set(slots):
            per_mat.setdefault(m, []).append(uv_tris(o, 0, {m}))
    for m, parts in per_mat.items():
        t0 = np.concatenate(parts)
        check(t0.min() >= -1e-4 and t0.max() <= 1 + 1e-4, f"{rel}: material {m} UV0 outside 0..1")
        ov = overlap(t0)
        check(ov < 0.005, f"{rel}: material {m} UV0 overlap {ov:.3%}")
        info = man["materials"][m]
        for mp in info["maps"]:
            p = os.path.join(ASSETS, "Textures", f"{m}_{mp}.png")
            if check(os.path.exists(p), f"missing texture {p}"):
                check(png_size(p) == (info["resolution"],) * 2, f"{p} size {png_size(p)} != {info['resolution']}")
    door = objs.get("Door_Leaf")
    if door:
        h = next(e["hinge"] for e in entries if e["name"] == "Door_Leaf")
        err = (door.matrix_world.translation - Vector(h["origin_blender"])).length
        check(err < 1e-3, f"{rel}: Door_Leaf origin off hinge by {err:.4f} m")
        notes.append(f"Door_Leaf children: {[c.name for c in door.children]}")
    notes.append(f"{rel}: {len(objs)} objects, {sum(len(o.data.polygons) for o in objs.values() if o.type == 'MESH')} tris")

print("\n".join("[validate] " + n for n in notes))
print("[validate] FAIL\n  " + "\n  ".join(fails) if fails else "[validate] PASS: all checks ok")
sys.exit(1 if fails else 0)
