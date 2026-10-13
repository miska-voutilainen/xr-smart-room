# Kitchen_Bottle (owner: s2_bottle). Runs after materials/kitchen.py + shaders/hard.py and replaces the bottle's
# mesh + materials, keeping the object (name, location, collection).
#
# What it really is (Photos/2/20261012_150448.jpg; absent from the 1222xx shots): Akvile "Peach Bubbles" lightly
# sparkling flavoured water, 0.6 l light-blue PET, white 28 mm PCO cap, clear shrink sleeve printed with a white
# logo blob + two peaches. Not cola. Profile and label come from the retailer pack shot
# textures/s2_bottle/akvile_peach_06l_rimi_src.png, scaled by the cap (183 px = 30 mm PCO closure OD):
# 0.164 mm/px -> body D72.3 x H223 mm (matches 0.6 l: ~640 ml brimful). Label wrap: textures/s2_bottle/make_label.py.
#
# Geometry (one object, origin bottom centre, z up, metres):
#   liquid zone : the bottle's outer surface from the petaloid base up to the fill line + a flat top, material
#                 Kitchen_BottleLiquid (IOR 1.33). A 0.35 mm PET wall is a thin parallel slab, so air->PET->water
#                 refracts like air->water; reflection is boosted a bit for the PET's 1.57.
#   head space  : double-walled PET shell (outer + 0.35..1.5 mm inner) from the fill line to the neck lip,
#                 neck support ring, Kitchen_PET (IOR 1.57).
#   sleeve      : open cylinder 0.15 mm outside the body, cylindrical UVs 1:1 with the wrap (Kitchen_BottleLabel).
#   cap         : ribbed HDPE screw cap + tamper band (ribs are bump), Kitchen_BottleCap.
import math
import os
import sys

import bmesh
import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _lib  # noqa: E402

N = 40                                  # segments (8 per petaloid foot)
MM = 0.001
FRONT = math.atan2(0.35, -1.0)          # label front faces the hero Camera (-x), turned a bit to the room (+y)
LABEL_Z = (34.8, 161.2)                 # sleeve band, mm (pack shot rows 1222..445)
LABEL_R = 36.31
Z_FILL = 186.1                          # fill line (pack shot row 295), in the shoulder
TEX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "textures", "s2_bottle",
                   "akvile_peach_label.png")

# outer profile (r, z) mm, base -> neck lip, measured from the pack-shot silhouette
BASE = [(8.0, 4.6), (17.0, 1.0), (24.0, 0.0), (28.0, 1.6), (30.0, 4.9), (32.3, 10.7), (34.7, 19.7),
        (35.8, 29.5), (36.16, 33.5)]
# petaloid: per base ring (radius pull-in, z lift) at the valley centres between the five feet
VALLEY = [(0.10, 0.6), (0.18, 5.0), (0.22, 7.5), (0.20, 7.0), (0.17, 5.5), (0.12, 3.0), (0.06, 1.0), (0.02, 0.0),
          (0.0, 0.0)]
BODY = [(36.16, 161.5), (35.92, 164.8), (35.51, 167.3), (34.60, 169.7), (33.29, 172.2), (31.82, 174.7),
        (30.09, 177.1), (28.37, 179.6), (26.65, 182.0), (24.19, 185.3)]
HEAD = [(21.81, 188.6), (19.35, 191.9), (16.89, 195.2), (14.92, 197.6), (13.61, 199.8), (13.45, 204.2),
        (16.0, 204.7), (17.2, 205.3), (17.2, 206.0), (16.0, 206.6), (12.7, 207.0), (12.7, 208.6)]
CAP = [(12.9, 208.4), (15.0, 208.4), (15.0, 212.9), (14.7, 213.25), (15.0, 213.6), (15.0, 222.2), (14.3, 223.0),
       (0.0, 223.1)]


def r_at(z):
    """Outer radius at height z on the shoulder (linear in BODY+HEAD)."""
    pts = BODY + HEAD[:5]
    for (r0, z0), (r1, z1) in zip(pts, pts[1:]):
        if z0 <= z <= z1:
            return r0 + (r1 - r0) * (z - z0) / (z1 - z0)
    raise ValueError(z)


def valley(a):
    """0 on the feet, 1 at the valley centres between them."""
    return (0.5 + 0.5 * math.cos(5 * a)) ** 2


class Lathe:
    def __init__(s):
        s.bm = bmesh.new()
        s.uv = s.bm.loops.layers.uv.new("UVMap")

    def ring(s, r, z, mod=None):
        vs = []
        for k in range(N):
            a = 2 * math.pi * k / N
            rr, zz = r, z
            if mod:
                f = valley(a)
                rr, zz = r * (1 - mod[0] * f), z + mod[1] * f
            vs.append(s.bm.verts.new((rr * math.cos(a) * MM, rr * math.sin(a) * MM, zz * MM)))
        return vs

    def _face(s, vs, uvs, mat):
        f = s.bm.faces.new(vs)
        f.material_index, f.smooth = mat, True
        for lp, uv in zip(f.loops, uvs):
            lp[s.uv].uv = uv
        return f

    def band(s, lo, hi, v0, v1, mat, uoff=0.0):
        """Quads between two rings; u = angle (seam column duplicated in UV space), v given per ring."""
        for k in range(N):
            k1 = (k + 1) % N
            u0, u1 = k / N + uoff, (k + 1) / N + uoff
            s._face((lo[k], lo[k1], hi[k1], hi[k]), ((u0, v0), (u1, v0), (u1, v1), (u0, v1)), mat)

    def loft(s, prof, mat, mods=None, v_of=lambda z: z / 223.0):
        rings = [s.ring(r, z, mods[i] if mods else None) for i, (r, z) in enumerate(prof)]
        for i in range(len(rings) - 1):
            s.band(rings[i], rings[i + 1], v_of(prof[i][1]), v_of(prof[i + 1][1]), mat)
        return rings

    def fan(s, ring, z, mat, down=False):
        c = s.bm.verts.new((0, 0, z * MM))
        for k in range(N):
            k1 = (k + 1) % N
            if down:
                k, k1 = k1, k
            a0, a1 = 2 * math.pi * k / N, 2 * math.pi * k1 / N
            s._face((ring[k], ring[k1], c), ((0.5 + 0.5 * math.cos(a0), 0.5 + 0.5 * math.sin(a0)),
                                             (0.5 + 0.5 * math.cos(a1), 0.5 + 0.5 * math.sin(a1)), (0.5, 0.5)), mat)


PET, LABEL, CAPM, LIQ = range(4)


def build_mesh(name, mats):
    L = Lathe()
    # liquid zone: push-up centre -> petaloid base -> body -> shoulder -> fill line, flat top
    liq = BASE + BODY + [(r_at(Z_FILL), Z_FILL)]
    rings = L.loft(liq, LIQ, VALLEY + [None] * (len(liq) - len(BASE)))
    L.fan(rings[0], 5.2, LIQ, down=True)                        # push-up dome
    L.fan(rings[-1], Z_FILL, LIQ)
    # head space: outer from the fill line to the lip, inner back down (0.35 mm wall, 1.6 mm at the neck finish)
    outer = [(r_at(Z_FILL), Z_FILL)] + HEAD
    inner = [(10.9, 208.6), (10.9, 199.8)] + [(r - 0.35, z) for r, z in reversed(HEAD[:4])] + \
            [(r_at(Z_FILL + 0.3) - 0.35, Z_FILL + 0.3)]
    L.loft(outer + inner + [outer[0]], PET)
    # sleeve: open cylinder, UV u = 0.5 at the FRONT angle, v = 0..1 over the printed band
    lo, hi = L.ring(LABEL_R, LABEL_Z[0]), L.ring(LABEL_R, LABEL_Z[1])
    L.band(lo, hi, 0.0, 1.0, LABEL, uoff=0.5 - FRONT / (2 * math.pi))
    # cap: outer shell + top, inner wall + ceiling (closed solid)
    L.fan(L.loft(CAP[:-1], CAPM)[-1], CAP[-1][1], CAPM)
    L.fan(L.loft([(12.9, 221.4), (12.9, 208.4)], CAPM)[0], 221.4, CAPM, down=True)
    # every profile runs counter-clockwise in the (r, z) half-plane, so faces already point out of their solid
    bm = L.bm
    me = bpy.data.meshes.new(name)
    for mt in mats:
        me.materials.append(mt)
    bm.to_mesh(me)
    bm.free()
    return me


def material(name):
    if bpy.data.materials.get(name) is None:
        bpy.data.materials.new(name)
    return _lib.reset(name)


def shadow_clear(nt, bsdf_out, tint):
    """Caustics are off: let shadow rays pass (tinted) instead of a black shadow. Shader mix, bake-safe."""
    lp = nt.nodes.new("ShaderNodeLightPath")
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    tr.inputs["Color"].default_value = (*tint, 1)
    mx = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(lp.outputs["Is Shadow Ray"], mx.inputs[0])
    nt.links.new(bsdf_out, mx.inputs[1])
    nt.links.new(tr.outputs[0], mx.inputs[2])
    return mx.outputs[0]


def clear_mat(name, ior, tint, level):
    m, nt, b, _ = material(name)
    b.inputs["Base Color"].default_value = (*tint, 1)
    b.inputs["Transmission Weight"].default_value = 1.0
    b.inputs["Roughness"].default_value = 0.02
    b.inputs["IOR"].default_value = ior
    b.inputs["Specular IOR Level"].default_value = level
    out = [n for n in nt.nodes if n.type == "OUTPUT_MATERIAL"][0]
    nt.links.new(shadow_clear(nt, b.outputs[0], tuple(0.5 + 0.5 * c for c in tint)), out.inputs["Surface"])
    m.diffuse_color = (*tint, 0.2)
    _lib.tidy(nt)
    return m


def label_mat():
    m, nt, b, _ = material("Kitchen_BottleLabel")
    img = bpy.data.images.load(os.path.normpath(TEX), check_existing=True)
    img.alpha_mode = "STRAIGHT"
    tx = nt.nodes.new("ShaderNodeTexImage")
    tx.image = img
    uv = nt.nodes.new("ShaderNodeUVMap")
    uv.uv_map = "UVMap"
    nt.links.new(uv.outputs[0], tx.inputs["Vector"])
    nt.links.new(tx.outputs["Color"], b.inputs["Base Color"])
    nt.links.new(tx.outputs["Alpha"], b.inputs["Alpha"])
    b.inputs["Roughness"].default_value = 0.22                  # glossy printed PETG shrink film
    _lib.tidy(nt)
    return m


def cap_mat():
    m, nt, b, co = material("Kitchen_BottleCap")
    b.inputs["Base Color"].default_value = (0.86, 0.87, 0.87, 1)
    b.inputs["Roughness"].default_value = 0.42
    b.inputs["Subsurface Weight"].default_value = 0.25             # HDPE is a little translucent
    b.inputs["Subsurface Radius"].default_value = (1.0, 1.0, 1.0)
    b.inputs["Subsurface Scale"].default_value = 0.002
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(co, sep.inputs[0])
    ang = _lib.math(nt, "ARCTAN2", sep.outputs["Y"], sep.outputs["X"])
    ribs = _lib.math(nt, "SINE", _lib.math(nt, "MULTIPLY", ang, 60.0))      # 60 knurl ribs
    band = _lib.maprange(nt, sep.outputs["Z"], 0.2140, 0.2146, 0.0, 1.0)  # ribs only above the tamper band
    top = _lib.maprange(nt, sep.outputs["Z"], 0.2218, 0.2212, 0.0, 1.0)
    h = _lib.math(nt, "MULTIPLY", ribs, _lib.math(nt, "MULTIPLY", band, top))
    nt.links.new(_lib.bump(nt, h, 0.35, 0.0004), b.inputs["Normal"])
    _lib.tidy(nt)
    return m


ob = bpy.data.objects.get("Kitchen_Bottle")
if ob is not None:
    old = ob.data
    ob.data = build_mesh("Kitchen_Bottle", (clear_mat("Kitchen_PET", 1.57, (0.84, 0.92, 1.0), 0.5),
                                            label_mat(),
                                            cap_mat(),
                                            clear_mat("Kitchen_BottleLiquid", 1.33, (0.87, 0.94, 1.0), 0.62)))
    if old.users == 0:
        bpy.data.meshes.remove(old)
    ob.data.name = "Kitchen_Bottle"
    print("zz_bottle: Kitchen_Bottle", len(ob.data.polygons), "faces,",
          sum(len(p.vertices) - 2 for p in ob.data.polygons), "tris")
