# Visibility probe: one world-space BVH of every rendered (evaluated, instance-realised) polygon; rays from a
# grid of eye points in room 1, the lab (Room2) and the corridor beyond the door, many directions.
# See-through surfaces (glass materials, fog volume, rain, leaf cards, blinds) let the ray continue.
# Usage: blender -b X --python probe.py -- NDIR STEP OUT.json
import bpy, math, sys, json, time
from mathutils import Vector
from mathutils.bvhtree import BVHTree
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
NDIR = int(argv[0]) if argv else 1500
STEP = float(argv[1]) if len(argv) > 1 else 0.6
OUT = argv[2] if len(argv) > 2 else "probe_out.json"
sc = bpy.context.scene
dg = bpy.context.evaluated_depsgraph_get()

verts, polys, owner, thru, area = [], [], [], [], []
nfaces, ntris = {}, {}
for inst in dg.object_instances:
    ob = inst.object
    if ob.type != "MESH":
        continue
    if inst.is_instance:
        name = inst.parent.original.name + "#inst:" + ob.original.name
    else:
        if ob.original.hide_render:
            continue
        name = ob.original.name
    me = ob.data
    mw = inst.matrix_world.copy()
    base = len(verts)
    verts += [mw @ v.co for v in me.vertices]
    mats = me.materials
    st = name.startswith(("Light_Fog", "Ext_Rain")) or "#inst:Ext_Leaf" in name or "Blind" in name
    nfaces[name] = nfaces.get(name, 0) + len(me.polygons)
    off = 0 if not inst.is_instance else nfaces[name] - len(me.polygons)
    for p in me.polygons:
        polys.append([base + i for i in p.vertices])
        m = mats[p.material_index] if p.material_index < len(mats) else None
        owner.append((name, off + p.index, len(p.vertices) - 2, m.name if m else "<none>"))
        thru.append(st or bool(m and "Glass" in m.name))
print("polys", len(polys), flush=True)
bvh = BVHTree.FromPolygons(verts, polys, all_triangles=False, epsilon=0.0)

ga = math.pi * (3 - math.sqrt(5))
DIRS = []
for i in range(NDIR):
    z = 1 - 2 * (i + 0.5) / NDIR
    r = math.sqrt(1 - z * z)
    DIRS.append(Vector((r * math.cos(ga * i), r * math.sin(ga * i), z)))

def grid(x0, x1, y0, y1, zs):
    nx, ny = max(1, int((x1 - x0) / STEP) + 1), max(1, int((y1 - y0) / STEP) + 1)
    return [Vector((x0 + (x1 - x0) * i / max(nx - 1, 1), y0 + (y1 - y0) * j / max(ny - 1, 1), z))
            for i in range(nx) for j in range(ny) for z in zs]

ZS = (0.5, 1.15, 1.75)
REGIONS = {"room1": grid(0.25, 6.25, 0.25, 2.3, ZS),
           "lab": grid(0.25, 6.25, 2.9, 8.7, ZS),
           "corridor": grid(-8.7, -0.4, -1.8, 5.8, ZS)}

def inside_solid(p):
    for d in (Vector((0, 0, 1)), Vector((0, 0, -1)), Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((-1, 0, 0))):
        loc, nrm, idx, dist = bvh.ray_cast(p, d)
        if loc is not None and not thru[idx]:
            fn = Vector(nrm)
            if fn.dot(d) > 0:
                return True
    return False

hit = set()
regions = {}
t0 = time.time(); nray = 0
for reg, eyes in REGIONS.items():
    eyes = [e for e in eyes if not inside_solid(e)]
    print("REGION", reg, len(eyes), "eyes", flush=True)
    for e in eyes:
        for d in DIRS:
            o = e
            for _ in range(32):
                loc, nrm, idx, dist = bvh.ray_cast(o, d)
                nray += 1
                if loc is None:
                    break
                if idx not in hit:
                    hit.add(idx)
                regions.setdefault(owner[idx][0], set()).add(reg)
                if not thru[idx]:
                    break
                o = loc + d * 1e-3
print("rays", nray, "time", round(time.time() - t0, 1), flush=True)
# phase 2: re-test every unseen (non-instance) face with directed rays from a coarse eye set to its
# centre and to its corners pulled 20 % inward; a face counts as seen if the first opaque hit is that face.
coarse = []
for reg, eyes in REGIONS.items():
    coarse += [e for k, e in enumerate(eyes) if k % 6 == 0 and not inside_solid(e)]
rescued = 0
for i, (name, fi, nt, mn) in enumerate(owner):
    if i in hit or "#inst:" in name:
        continue
    vs = [verts[v] for v in polys[i]]
    c = sum(vs, Vector()) / len(vs)
    targets = [c] + [v.lerp(c, 0.2) for v in vs]
    found = False
    for e in coarse:
        for t in targets:
            d = t - e
            dist = d.length
            if dist < 1e-6:
                continue
            d /= dist
            o = e
            for _ in range(32):
                loc, nrm, idx, dd = bvh.ray_cast(o, d)
                if loc is None:
                    break
                if idx == i:
                    found = True
                    break
                if not thru[idx]:
                    break
                o = loc + d * 1e-3
            if found:
                break
        if found:
            break
    if found:
        hit.add(i); rescued += 1
print("phase2 rescued", rescued, "coarse eyes", len(coarse), flush=True)
per = {}
mats = {}
for i, (name, fi, nt, mn) in enumerate(owner):
    r = per.setdefault(name, {"faces": 0, "tris": 0, "hit_faces": 0, "hit_tris": 0})
    r["faces"] += 1; r["tris"] += nt
    q = mats.setdefault(mn, {"tris": 0, "hit_tris": 0, "objs": set()})
    q["tris"] += nt; q["objs"].add(name.split("#")[0])
    if i in hit:
        r["hit_faces"] += 1; r["hit_tris"] += nt; q["hit_tris"] += nt
unseen = {}
for i, (name, fi, nt, mn) in enumerate(owner):
    if i not in hit and "#inst:" not in name:
        unseen.setdefault(name, []).append(fi)
mats = {k: {"tris": v["tris"], "hit_tris": v["hit_tris"], "objs": sorted(v["objs"])} for k, v in mats.items()}
json.dump({"mats": mats, "per": per, "regions": {k: sorted(v) for k, v in regions.items()}, "unseen": unseen}, open(OUT, "w"))
print("PROBE DONE")
