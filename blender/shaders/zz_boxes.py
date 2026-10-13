# Printed cardboard packaging on the kitchen worktop, owner s2_boxes. Sorts after kitchen.py / hard.py.
# Replaces the MESH DATA, UVs and materials of
#   Kitchen_SugarBox  "UNIQUE white sugar" 80-stick display box: open tray + tall printed back flap, a few sticks inside
#   Kitchen_TeaBox    Greenfield Earl Grey Fantasy, 25 tea bags (official artwork, front = local -x)
# keeping object names, location, rotation and collection. Origin = bottom centre, real scale (metres).
# Prints: textures/s2_boxes/{sugar,tea}_{albedo,rough}.png from textures/s2_boxes/_make_atlas.py (dieline rects
# below must match that script). Bake-friendly: image maps + object-space noise bump only.
import math
import os
import random
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import _lib as L  # noqa: E402

TEX = os.path.join(os.path.dirname(HERE), "textures", "s2_boxes")
AT = 2048.0

# ---- dimensions (mm in the atlas script) + atlas rects (x0, y0, w, h px, image y down) -- keep in sync
S_L, S_D, S_H, S_F = 0.170, 0.090, 0.060, 0.165      # sugar length (flap side), depth, wall height, flap top
S_EYE_TOP = S_F - 0.032                              # tab (logo) sits above this line
T = 0.0012                                           # board thickness (double-folded rim)
SR = {"flap": (0, 0, 1190, 1155), "front": (0, 1163, 1190, 420), "end": (1200, 0, 630, 420),
      "kraft": (1200, 540, 600, 600), "stick": (1200, 1150, 700, 105)}
T_W, T_D, T_H = 0.065, 0.050, 0.130                  # tea front width (along y), depth (x), height
TR = {"front": (0, 0, 520, 1040), "sideA": (530, 0, 400, 1040), "back": (940, 0, 520, 1040),
      "sideB": (1470, 0, 400, 1040), "top": (0, 1050, 520, 400), "bot": (530, 1050, 520, 400)}


def uv_in(rect, u, v):
    """u, v in 0..1 of a panel (v = 0 at the panel's TOP) -> atlas UV (inset half a texel against bleeding)."""
    x0, y0, w, h = rect
    u = min(max(u, 0.0), 1.0)
    v = min(max(v, 0.0), 1.0)
    return ((x0 + 0.5 + u * (w - 1)) / AT, 1.0 - (y0 + 0.5 + v * (h - 1)) / AT)


def kraft_uv(co, n):
    ax = max(range(3), key=lambda i: abs(n[i]))
    a, b = [(1, 2), (0, 2), (0, 1)][ax]
    return uv_in(SR["kraft"], co[a] / 0.2 + 0.5, co[b] / 0.2 + 0.5)


class Out:
    """Accumulates verts / faces / per-loop UVs from several bmesh parts into one mesh."""

    def __init__(self):
        self.v, self.f, self.uv = [], [], []

    def add(self, bm, mapper=None, uvs=None):
        """mapper(co, normal, face_centre) -> uv, or uvs = precomputed per-face lists (same face order)."""
        base = len(self.v)
        self.v += [tuple(v.co) for v in bm.verts]
        bm.verts.index_update()
        for i, f in enumerate(bm.faces):
            self.f.append([v.index + base for v in f.verts])
            c, n = f.calc_center_median(), f.normal
            self.uv.append(uvs[i] if uvs else [mapper(v.co, n, c) for v in f.verts])
        bm.free()

    def mesh(self, name, mat):
        me = bpy.data.meshes.new(name)
        me.from_pydata(self.v, [], self.f)
        me.materials.append(mat)
        uvl = me.uv_layers.new(name="UVMap")
        uvl.data.foreach_set("uv", [c for p in self.uv for uv in p for c in uv])
        bm = bmesh.new()
        bm.from_mesh(me)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.to_mesh(me)
        bm.free()
        me.validate()
        return me


def slab(lo, hi):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector([lo[i] + (hi[i] - lo[i]) * (v.co[i] + 0.5) for i in range(3)])
    return bm


def bevel(bm, w):
    bmesh.ops.bevel(bm, geom=list(bm.edges), offset=w, segments=1, profile=0.5, affect="EDGES", clamp_overlap=True)
    return bm


def flap_slab():
    """Back wall + display flap: outline in x-z (tab inset, rounded top corners), extruded by T toward +y."""
    hx, ins, r, y0 = S_L / 2, 0.010, 0.006, -S_D / 2
    pts = [(-hx, 0.0), (hx, 0.0), (hx, S_EYE_TOP), (hx - ins, S_EYE_TOP)]
    for cx, a0 in ((hx - ins - r, 0.0), (-hx + ins + r, 90.0)):          # right then left rounded corner
        for k in range(5):
            a = math.radians(a0 + 90.0 * k / 4)
            pts.append((cx + r * math.cos(a), S_F - r + r * math.sin(a)))
    pts += [(-hx + ins, S_EYE_TOP), (-hx, S_EYE_TOP)]
    bm = bmesh.new()
    vs = [bm.verts.new((x, y0, z)) for x, z in pts]
    face = bm.faces.new(vs)
    ext = bmesh.ops.extrude_face_region(bm, geom=[face])
    bmesh.ops.translate(bm, vec=(0, T, 0), verts=[e for e in ext["geom"] if isinstance(e, bmesh.types.BMVert)])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


# ------------------------------------------------------------------ sugar box
def sugar_mapper(part):
    hx, hy = S_L / 2, S_D / 2

    def m(co, n, c):
        x, y, z = co
        if part == "front" and n.y > 0.7:                       # outer front, read from +y (right = -x)
            return uv_in(SR["front"], (hx - x) / S_L, (S_H - z) / S_H)
        if part == "end" and abs(n.x) > 0.7 and abs(c.x) > hx - T * 0.5:   # outer end panels
            u = (y + hy) / S_D if n.x > 0 else (hy - y) / S_D
            return uv_in(SR["end"], u, (S_H - z) / S_H)
        if part == "flap" and abs(n.y) > 0.7:                   # printed both sides (as the real header card)
            u = (hx - x) / S_L if n.y > 0 else (x + hx) / S_L
            return uv_in(SR["flap"], u, (S_F - z) / S_F)
        return kraft_uv(co, n)
    return m


def stick_mapper(L_, W_):
    def m(co, n, c):
        if abs(n.z) > 0.5:
            return uv_in(SR["stick"], co.x / L_ + 0.5, 0.5 - co.y / W_)
        return uv_in(SR["stick"], co.x / L_ + 0.5, 0.02)
    return m


def sugar(mat):
    out = Out()
    hx, hy = S_L / 2, S_D / 2
    b = 0.0004
    out.add(bevel(slab((-hx, -hy, 0), (hx, hy, T)), b), sugar_mapper("bottom"))
    out.add(bevel(slab((-hx, hy - T, 0), (hx, hy, S_H)), b), sugar_mapper("front"))
    out.add(bevel(slab((-hx, -hy + T, 0), (-hx + T, hy - T, S_H)), b), sugar_mapper("end"))
    out.add(bevel(slab((hx - T, -hy + T, 0), (hx, hy - T, S_H)), b), sugar_mapper("end"))
    out.add(bevel(flap_slab(), b), sugar_mapper("flap"))
    # a few loose 5 g sticks left on the floor of the tray (seen in 122209 / 122250): 100 x 15 x 5 mm
    rnd = random.Random(11)
    sl, sw, sh = 0.100, 0.015, 0.005
    spots = [(-0.030, -0.028, 0), (0.028, -0.012, 0), (-0.024, 0.006, 0), (0.030, 0.024, 0),
             (-0.012, 0.030, 0), (0.008, -0.020, 1), (-0.006, 0.012, 1)]
    for x, y, layer in spots:
        bm = slab((-sl / 2, -sw / 2, -sh / 2), (sl / 2, sw / 2, sh / 2))
        # pillowed wrapper: pinch the crimped ends thinner
        for v in bm.verts:
            if abs(v.co.x) > sl / 2 - 1e-6:
                v.co.z *= 0.3
        mp = stick_mapper(sl, sw)
        uvs = [[mp(v.co, f.normal, None) for v in f.verts] for f in bm.faces]
        mtx = (Matrix.Translation((x, y, T + sh / 2 + layer * sh * 0.9))
               @ Matrix.Rotation(rnd.uniform(-0.12, 0.12), 4, "Z") @ Matrix.Rotation(rnd.uniform(-0.05, 0.05), 4, "X"))
        bm.transform(mtx)
        out.add(bm, uvs=uvs)
    return out.mesh("Kitchen_SugarBox", mat)


# ------------------------------------------------------------------ tea box
def tea(mat):
    hx, hy = T_D / 2, T_W / 2

    def m(co, n, c):
        x, y, z = co
        v = (T_H - z) / T_H
        if n.x < -0.7:
            return uv_in(TR["front"], (hy - y) / T_W, v)
        if n.x > 0.7:
            return uv_in(TR["back"], (y + hy) / T_W, v)
        if n.y < -0.7:
            return uv_in(TR["sideA"], (x + hx) / T_D, v)
        if n.y > 0.7:
            return uv_in(TR["sideB"], (hx - x) / T_D, v)
        if n.z > 0:
            return uv_in(TR["top"], (hy - y) / T_W, (x + hx) / T_D)
        return uv_in(TR["bot"], (hy - y) / T_W, (hx - x) / T_D)
    out = Out()
    out.add(bevel(slab((-hx, -hy, 0), (hx, hy, T_H)), 0.0008), m)
    return out.mesh("Kitchen_TeaBox", mat)


# ------------------------------------------------------------------ materials
def load(fname, color):
    img = bpy.data.images.load(os.path.join(TEX, fname), check_existing=True)
    img.reload()
    img.colorspace_settings.name = "sRGB" if color else "Non-Color"
    return img


def card_material(name, prefix, bump=0.04):
    r = L.reset(name)
    if r is None:
        bpy.data.materials.new(name)
        r = L.reset(name)
    m, nt, b, co = r
    uv = nt.nodes.new("ShaderNodeUVMap")
    uv.uv_map = "UVMap"
    col = nt.nodes.new("ShaderNodeTexImage")
    col.image = load(prefix + "_albedo.png", True)
    col.interpolation = "Cubic"
    nt.links.new(uv.outputs[0], col.inputs[0])
    rough = nt.nodes.new("ShaderNodeTexImage")
    rough.image = load(prefix + "_rough.png", False)
    nt.links.new(uv.outputs[0], rough.inputs[0])
    nt.links.new(col.outputs[0], b.inputs["Base Color"])
    nt.links.new(rough.outputs[0], b.inputs["Roughness"])
    b.inputs["Specular IOR Level"].default_value = 0.5
    # board fibre / print-varnish orange peel, object space (bakes)
    n = L.noise(nt, co, 900.0, 4.0, 0.6)
    bp = nt.nodes.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = bump
    bp.inputs["Distance"].default_value = 0.0002
    nt.links.new(n, bp.inputs["Height"])
    nt.links.new(bp.outputs[0], b.inputs["Normal"])
    return m


def replace(obj_name, me):
    ob = bpy.data.objects.get(obj_name)
    if ob is None:
        print("zz_boxes: missing", obj_name)
        bpy.data.meshes.remove(me)
        return
    old = ob.data
    ob.data = me
    if old.users == 0:
        bpy.data.meshes.remove(old)
    me.name = obj_name
    me.calc_loop_triangles()
    print("zz_boxes:", obj_name, len(me.loop_triangles), "tris")


replace("Kitchen_SugarBox", sugar(card_material("Kitchen_SugarBox", "sugar")))
replace("Kitchen_TeaBox", tea(card_material("Kitchen_TeaBox", "tea")))
