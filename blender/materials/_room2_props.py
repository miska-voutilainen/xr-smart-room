# Lab (room 2) props + textured materials, imported by materials/room2.py ("_" = not auto-run by apply_materials).
# Builders write into room2.Mesh-like accumulators: m.add((verts, faces), slot, uv) with m.T the local->world matrix,
# local frame u = +x, v = +y (device fronts face -v), z up. `uv` is a per-face list: None = box projection in metres
# (done in room2.obj), or 4 (u, v) corners for image-mapped faces (screens, keycaps, board photos).
# Sizes are real products seen in Photos/3: LG 24-27" IPS (thin bezel, arc base), old Dell 19" 5:4 with a round
# silver column, 14" black laptops, Dell OptiPlex/Precision towers, Acer projector, task chair with mesh back.
import math
import os

import bpy
from mathutils import Vector

TEX = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "textures", "s1_lab")


# ---------- primitives (same face order as room2.box: bottom, top, -y front, +x, +y back, -x) ----------

def hexa(p):
    """8 corner points in box order (bottom ring x0y0, x1y0, x1y1, x0y1, then the top ring) -> verts, faces."""
    return list(p), [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]


def bx(lo, hi):
    (x0, y0, z0), (x1, y1, z1) = lo, hi
    return hexa([(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
                 (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)])


def rect(r):
    """(u0, v0, u1, v1) UV rect -> 4 loop UVs for a box face listed as (x0,lo),(x1,lo),(x1,hi),(x0,hi)."""
    u0, v0, u1, v1 = r
    return [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]


def img_rect(r):
    """Image rect given from the TOP-left (x0, y0, x1, y1 in 0..1, as read off the photo) -> UV rect."""
    x0, y0, x1, y1 = r
    return (x0, 1 - y1, x1, 1 - y0)


def box(m, lo, hi, mi, front=None, top=None):
    uv = [None] * 6
    if front:
        uv[2] = rect(front)
    if top:
        uv[1] = rect(top)
    m.add(bx(lo, hi), mi, uv)


def face_split(m, vf, mi_face, mi_rest, k, uv):
    """Add a hexa with face k in its own slot (image) and UV, the other five faces in mi_rest."""
    v, f = vf
    m.add((v, [f[k]]), mi_face, [uv])
    m.add((v, [q for i, q in enumerate(f) if i != k]), mi_rest)


def cyl(p0, p1, r, n=8):
    p0, p1 = Vector(p0), Vector(p1)
    t = (p1 - p0).normalized()
    a = t.cross(Vector((0, 0, 1)) if abs(t.z) < 0.9 else Vector((1, 0, 0))).normalized()
    b = t.cross(a)
    ring = [a * math.cos(2 * math.pi * i / n) + b * math.sin(2 * math.pi * i / n) for i in range(n)]
    v = [tuple(p0 + q * r) for q in ring] + [tuple(p1 + q * r) for q in ring]
    f = [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
    for k in range(n // 2 - 1):
        a_, b_, c_, d_ = k, k + 1, n - 2 - k, n - 1 - k
        f += [(d_, c_, b_, a_), (n + a_, n + b_, n + c_, n + d_)]
    return v, f


def tube(pts, r, n=6):
    """Open cable tube along a polyline (shared rings, n*segments quads)."""
    pts = [Vector(p) for p in pts]
    v, f = [], []
    for i, p in enumerate(pts):
        t = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
        a = t.cross(Vector((0, 0, 1)) if abs(t.z) < 0.9 else Vector((1, 0, 0))).normalized()
        b = t.cross(a)
        v += [tuple(p + (a * math.cos(2 * math.pi * k / n) + b * math.sin(2 * math.pi * k / n)) * r) for k in range(n)]
    for i in range(len(pts) - 1):
        f += [(i * n + k, i * n + (k + 1) % n, (i + 1) * n + (k + 1) % n, (i + 1) * n + k) for k in range(n)]
    return v, f


def sag(p0, p1, drop, n=6):
    """Cable points p0 -> p1 hanging `drop` m below the chord at mid-span (parabola)."""
    p0, p1 = Vector(p0), Vector(p1)
    return [p0.lerp(p1, i / n) - Vector((0, 0, drop * 4 * (i / n) * (1 - i / n))) for i in range(n + 1)]


# ---------- materials ----------

def _img(name, colour=True):
    im = bpy.data.images.load(os.path.join(TEX, name), check_existing=True)
    im.colorspace_settings.name = "sRGB" if colour else "Non-Color"
    return im


def pbr(name, rgb, maps=None, tile=0.5, rough=(0.3, 0.6), nstr=0.3, metal=0.0, base=None, emit=None, power=1.0,
        coat=0.0):
    """Image-based Principled material (UV channel "UVMap"). maps = ambientCG id for roughness + normal (tiled at
    `tile` m on the metre box-projection UVs), base/emit = image file name on 0..1 UVs. Keeps any existing
    datablock (other scripts' slots stay valid); the TEX_IMAGE nodes make shaders/hard.py + arch.py skip it."""
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    m.diffuse_color = (*rgb, 1)
    nt = m.node_tree
    nt.nodes.clear()
    N, L = nt.nodes.new, nt.links.new
    out, b = N("ShaderNodeOutputMaterial"), N("ShaderNodeBsdfPrincipled")
    L(b.outputs[0], out.inputs["Surface"])
    uv = N("ShaderNodeUVMap")
    uv.uv_map = "UVMap"
    b.inputs["Base Color"].default_value = (*rgb, 1)
    b.inputs["Metallic"].default_value = metal
    b.inputs["Roughness"].default_value = sum(rough) / 2
    if coat:
        b.inputs["Coat Weight"].default_value = coat
        b.inputs["Coat Roughness"].default_value = 0.08
    if maps:
        mp = N("ShaderNodeMapping")
        mp.inputs["Scale"].default_value = (1 / tile, 1 / tile, 1)
        L(uv.outputs[0], mp.inputs["Vector"])
        tr = N("ShaderNodeTexImage")
        tr.image = _img(maps + "_Roughness.jpg", False)
        L(mp.outputs[0], tr.inputs["Vector"])
        mr = N("ShaderNodeMapRange")
        mr.inputs[3].default_value, mr.inputs[4].default_value = rough
        L(tr.outputs["Color"], mr.inputs[0])
        L(mr.outputs[0], b.inputs["Roughness"])
        tn = N("ShaderNodeTexImage")
        tn.image = _img(maps + "_NormalGL.jpg", False)
        L(mp.outputs[0], tn.inputs["Vector"])
        nm = N("ShaderNodeNormalMap")
        nm.inputs["Strength"].default_value = nstr
        L(tn.outputs["Color"], nm.inputs["Color"])
        L(nm.outputs[0], b.inputs["Normal"])
    if base:
        tb = N("ShaderNodeTexImage")
        tb.image = _img(base)
        L(uv.outputs[0], tb.inputs["Vector"])
        if rgb != (1, 1, 1):
            mul = N("ShaderNodeMix")
            mul.data_type, mul.blend_type = "RGBA", "MULTIPLY"
            mul.inputs[0].default_value = 1.0
            L(tb.outputs["Color"], mul.inputs[6])
            mul.inputs[7].default_value = (*rgb, 1)
            L(mul.outputs[2], b.inputs["Base Color"])
        else:
            L(tb.outputs["Color"], b.inputs["Base Color"])
    if emit:
        te = N("ShaderNodeTexImage")
        te.image = _img(emit)
        L(uv.outputs[0], te.inputs["Vector"])
        L(te.outputs["Color"], b.inputs["Emission Color"])
        b.inputs["Emission Strength"].default_value = power
    return m


def materials(P):
    """Textured lab materials, by slot key. Black/white/grey device plastics get NEW names (Room2_ABS_*) so the
    Room2_Plastic_* datablocks other scripts share keep their hard.py presets."""
    pl_w, pl_b, metal = "Plastic013A", "Plastic012A", "Metal027"
    return {
        "red_top": pbr(P + "Laminate_Red", (0.25, 0.04, 0.042), pl_w, 0.6, (0.35, 0.45), 0.2),       # HPL, 151011
        "laminate": pbr(P + "Laminate_Grey", (0.50, 0.51, 0.50), pl_w, 0.6, (0.30, 0.45), 0.12),
        "steel": pbr(P + "Steel_Grey", (0.58, 0.60, 0.59), metal, 0.25, (0.30, 0.50), 0.35),          # RAL 7035 powder
        "red": pbr(P + "Drawer_Red", (0.24, 0.04, 0.045), pl_w, 0.5, (0.30, 0.42), 0.12),
        "abs_black": pbr(P + "ABS_Black", (0.018, 0.018, 0.020), pl_b, 0.12, (0.30, 0.55), 0.25),
        "abs_white": pbr(P + "ABS_White", (0.78, 0.78, 0.76), pl_w, 0.25, (0.30, 0.45), 0.15),
        "abs_grey": pbr(P + "ABS_Silver", (0.42, 0.43, 0.44), pl_w, 0.25, (0.25, 0.40), 0.12, metal=0.4),
        "keys": pbr(P + "Keycaps", (1, 1, 1), pl_b, 0.05, (0.40, 0.60), 0.15, base="keys.png"),
        "mesh": pbr(P + "Mesh_Fabric", (0.62, 0.62, 0.60), "Fabric082A", 0.08, (0.6, 0.85), 0.5,
                    base="Fabric082A_Color.jpg"),
        "inst_scope": pbr(P + "Inst_Scope", (1, 1, 1), pl_w, 0.2, (0.3, 0.45), 0.1, base="inst_scope.jpg"),
        "inst_dmm1": pbr(P + "Inst_DMM1", (1, 1, 1), pl_w, 0.2, (0.3, 0.45), 0.1, base="inst_dmm1.jpg"),
        "inst_dmm2": pbr(P + "Inst_DMM2", (1, 1, 1), pl_w, 0.2, (0.3, 0.45), 0.1, base="inst_dmm2.jpg"),
        "blue": pbr(P + "Plastic_Blue", (0.02, 0.18, 0.75), pl_b, 0.12, (0.2, 0.35), 0.1),
        # screens: black glass + emissive image (~250 cd/m^2 at power 1.15 in this scene's photometric units)
        "scr_clock": pbr(P + "Screen_Clock", (0.004, 0.004, 0.005), rough=(0.05, 0.05), emit="screen_clock.png", power=1.0),
        "scr_sheet": pbr(P + "Screen_Sheet", (0.004, 0.004, 0.005), rough=(0.25, 0.25), emit="screen_sheet.png", power=1.0),
        "scr_code": pbr(P + "Screen_Code", (0.004, 0.004, 0.005), rough=(0.12, 0.12), emit="screen_code.png", power=1.2),
        "scr_code2": pbr(P + "Screen_Code2", (0.004, 0.004, 0.005), rough=(0.12, 0.12), emit="screen_code2.png", power=1.2),
        "scr_term": pbr(P + "Screen_Term", (0.004, 0.004, 0.005), rough=(0.25, 0.25), emit="screen_term.png", power=1.2),
    }


def board_material(P, n):
    return pbr(P + "Board_%d" % n, (1, 1, 1), "Plastic013A", 0.4, (0.30, 0.45), 0.08, base="board_%d.jpg" % n)


# ---------- IT ----------

def lcd(m, S, u, v, h, w, scr, ar=0.585, bezel=0.007, chin=0.018, base_d=0.19):
    """Modern IPS monitor facing -v (LG 24MP/27UL): panel front at v, 12 mm slab + rear electronics hump,
    tilted neck, arc-ish flat base (two plates). w = panel width; scr = screen slot key ('off' = TV_Screen)."""
    sh = w * ar
    zb = h + 0.085
    k = S["abs_black"]
    box(m, (u - w / 2, v, zb), (u + w / 2, v + 0.012, zb + sh), k)                                   # panel slab
    box(m, (u - w / 2 + bezel, v - 0.0008, zb + chin), (u + w / 2 - bezel, v, zb + sh - bezel), S[scr],
        front=(0, 0, 1, 1))
    box(m, (u - w * 0.33, v + 0.012, zb + sh * 0.18), (u + w * 0.33, v + 0.038, zb + sh * 0.72), k)  # rear hump
    m.add(hexa([(u - 0.03, v + 0.055, h + 0.008), (u + 0.03, v + 0.055, h + 0.008),                  # neck
                (u + 0.03, v + 0.078, h + 0.008), (u - 0.03, v + 0.078, h + 0.008),
                (u - 0.03, v + 0.036, zb + sh * 0.55), (u + 0.03, v + 0.036, zb + sh * 0.55),
                (u + 0.03, v + 0.058, zb + sh * 0.55), (u - 0.03, v + 0.058, zb + sh * 0.55)]), k)
    box(m, (u - 0.13, v - 0.06, h), (u + 0.13, v - 0.06 + base_d, h + 0.008), k)                     # base
    box(m, (u - 0.04, v + 0.04, h + 0.008), (u + 0.04, v + 0.10, h + 0.018), k)                      # base boss


def dell_old(m, S, u, v, h, scr="scr_clock"):
    """Dell E1913S-style 19in 5:4 monitor (151025): silver-black housing, round silver column, flat round base."""
    w, sh, d = 0.405, 0.345, 0.055
    zb = h + 0.13
    box(m, (u - w / 2, v, zb), (u + w / 2, v + 0.022, zb + sh), S["abs_grey"])                       # housing front
    box(m, (u - w / 2 + 0.014, v - 0.0015, zb + 0.026), (u + w / 2 - 0.014, v, zb + sh - 0.014), S["abs_black"])
    box(m, (u - 0.168, v - 0.0025, zb + 0.040), (u + 0.168, v - 0.0015, zb + sh - 0.026), S[scr],
        front=(0, 0, 1, 1))
    m.add(hexa([(u - w / 2 + 0.01, v + 0.022, zb + 0.01), (u + w / 2 - 0.01, v + 0.022, zb + 0.01),   # tapered back
                (u + 0.13, v + d, zb + 0.06), (u - 0.13, v + d, zb + 0.06),
                (u - w / 2 + 0.01, v + 0.022, zb + sh - 0.01), (u + w / 2 - 0.01, v + 0.022, zb + sh - 0.01),
                (u + 0.13, v + d, zb + sh - 0.07), (u - 0.13, v + d, zb + sh - 0.07)]), S["abs_black"])
    m.add(cyl((u, v + 0.08, h + 0.012), (u, v + 0.08, zb + sh * 0.6), 0.032, 10), S["abs_grey"])  # column
    m.add(cyl((u, v + 0.07, h), (u, v + 0.07, h + 0.012), 0.11, 12), S["abs_grey"])               # round foot
    box(m, (u - 0.04, v + 0.04, zb + sh * 0.35), (u + 0.04, v + 0.08, zb + sh * 0.6), S["abs_black"])


def laptop(m, S, u, v, h, scr, open_deg=112, body="abs_black"):
    """14in laptop (322 x 220 x 17 mm) facing -v at (u, v) = front edge centre; lid hinged at the back edge."""
    W2, Dp, t = 0.161, 0.22, 0.016
    k = S[body]
    m.add(hexa([(u - W2, v, h), (u + W2, v, h), (u + W2, v + Dp, h), (u - W2, v + Dp, h),               # wedge base
                (u - W2, v, h + t - 0.004), (u + W2, v, h + t - 0.004), (u + W2, v + Dp, h + t), (u - W2, v + Dp, h + t)]),
          k)
    box(m, (u - 0.140, v + 0.105, h + t - 0.0015), (u + 0.140, v + 0.200, h + t + 0.0004), S["keys"],
        top=(0.0, 0.0, 0.78, 1.0))                                                                     # keyboard well
    box(m, (u - 0.052, v + 0.018, h + t - 0.0035), (u + 0.052, v + 0.085, h + t - 0.0025), S["abs_grey"])  # touchpad
    keep = m.T
    from mathutils import Matrix
    m.T = keep @ Matrix.Translation((u, v + Dp, h + t)) @ Matrix.Rotation(-math.radians(open_deg - 90), 4, 'X')
    box(m, (-W2, -0.006, 0.0), (W2, 0.0, 0.212), k)                                                    # lid
    box(m, (-W2 + 0.008, -0.0068, 0.016), (W2 - 0.008, -0.006, 0.204), S[scr], front=(0, 0, 1, 1))
    m.add(cyl((-W2 + 0.02, -0.004, 0.0), (W2 - 0.02, -0.004, 0.0), 0.006, 6), k)                       # hinge barrel
    m.T = keep


def keyboard(m, S, u, v, h, numpad=True):
    """Full-size keyboard 440 x 135, wedge 18 -> 28 mm, keycap image on top; facing -v at front edge v."""
    L = 0.44 if numpad else 0.36
    k = S["abs_black"]
    m.add(hexa([(u - L / 2, v, h), (u + L / 2, v, h), (u + L / 2, v + 0.135, h), (u - L / 2, v + 0.135, h),
                (u - L / 2, v, h + 0.017), (u + L / 2, v, h + 0.017), (u + L / 2, v + 0.135, h + 0.026),
                (u - L / 2, v + 0.135, h + 0.026)]), k)
    m.add(hexa([(u - L / 2 + 0.01, v + 0.008, h + 0.0171), (u + L / 2 - 0.01, v + 0.008, h + 0.0171),
                (u + L / 2 - 0.01, v + 0.127, h + 0.0259), (u - L / 2 + 0.01, v + 0.127, h + 0.0259),
                (u - L / 2 + 0.01, v + 0.008, h + 0.0185), (u + L / 2 - 0.01, v + 0.008, h + 0.0185),
                (u + L / 2 - 0.01, v + 0.127, h + 0.0273), (u - L / 2 + 0.01, v + 0.127, h + 0.0273)]),
          S["keys"], [None, rect((0, 0, 1 if numpad else 0.78, 1))] + [None] * 4)


def mouse(m, S, u, v, h):
    k = S["abs_black"]
    m.add(hexa([(u - 0.031, v, h), (u + 0.031, v, h), (u + 0.031, v + 0.112, h), (u - 0.031, v + 0.112, h),
                (u - 0.022, v + 0.012, h + 0.024), (u + 0.022, v + 0.012, h + 0.024),
                (u + 0.024, v + 0.085, h + 0.038), (u - 0.024, v + 0.085, h + 0.038)]), k)


def tower(m, S, u, v, z=0.0, w=0.154, d=0.292, ht=0.324):
    """Dell OptiPlex tower (151011 / 151124): black case, front bezel with a silver strip + red/white badge, feet."""
    k = S["abs_black"]
    box(m, (u - w / 2, v + 0.012, z + 0.012), (u + w / 2, v + d, z + ht), k)                        # case
    box(m, (u - w / 2, v, z + 0.012), (u + w / 2, v + 0.012, z + ht), k)                            # front bezel
    box(m, (u - w / 2 + 0.012, v - 0.003, z + 0.03), (u + w / 2 - 0.012, v, z + ht - 0.10), S["abs_black"])  # grille
    box(m, (u - w / 2 + 0.012, v - 0.004, z + ht - 0.09), (u + w / 2 - 0.012, v, z + ht - 0.02), S["abs_grey"])
    box(m, (u - 0.012, v - 0.005, z + ht - 0.075), (u + 0.012, v - 0.004, z + ht - 0.051), S["red_badge"])
    for a in (u - w / 2 + 0.01, u + w / 2 - 0.04):
        for b in (v + 0.02, v + d - 0.04):
            box(m, (a, b, z), (a + 0.03, b + 0.02, z + 0.012), k)


def projector(m, S, u, v, h):
    """Acer short-throw projector (151124) facing -v: black glossy box, blue ring lens on the left."""
    box(m, (u - 0.155, v, h + 0.01), (u + 0.155, v + 0.235, h + 0.105), S["abs_black"])
    for a in (u - 0.13, u + 0.11):
        box(m, (a, v + 0.02, h), (a + 0.02, v + 0.04, h + 0.01), S["abs_black"])
    m.add(cyl((u - 0.07, v + 0.004, h + 0.058), (u - 0.07, v - 0.012, h + 0.058), 0.048, 12), S["blue"])
    m.add(cyl((u - 0.07, v - 0.002, h + 0.058), (u - 0.07, v - 0.014, h + 0.058), 0.034, 10), S["abs_black"])


def task_chair(m, S):
    """Mesh-back task chair facing -v (151124): black 5-star base + castors, grey seat, white mesh back, headrest."""
    k = S["abs_black"]
    for i in range(5):
        a = 2 * math.pi * i / 5 + math.pi / 5
        c, s = math.cos(a), math.sin(a)
        p = lambda r, o, z: (r * c - o * s, r * s + o * c, z)
        m.add(hexa([p(0.04, -0.02, 0.07), p(0.31, -0.012, 0.045), p(0.31, 0.012, 0.045), p(0.04, 0.02, 0.07),
                    p(0.04, -0.02, 0.10), p(0.31, -0.012, 0.065), p(0.31, 0.012, 0.065), p(0.04, 0.02, 0.10)]), k)
        m.add(cyl(p(0.30, -0.02, 0.028), p(0.30, 0.02, 0.028), 0.028, 8), k)                           # castor
    m.add(cyl((0, 0, 0.08), (0, 0, 0.27), 0.032, 8), k)                                               # column shroud
    m.add(cyl((0, 0, 0.27), (0, 0, 0.43), 0.014, 8), S["chrome"])                                     # gas lift
    box(m, (-0.19, -0.18, 0.43), (0.19, 0.20, 0.46), k)                                               # mechanism
    m.add(hexa([(-0.25, -0.25, 0.46), (0.25, -0.25, 0.46), (0.25, 0.22, 0.46), (-0.25, 0.22, 0.46),     # seat cushion
                (-0.24, -0.24, 0.515), (0.24, -0.24, 0.515), (0.24, 0.21, 0.53), (-0.24, 0.21, 0.53)]), S["mesh"])
    for x in (-0.27, 0.23):                                                                           # armrests
        box(m, (x, 0.0, 0.46), (x + 0.04, 0.04, 0.66), k)
        box(m, (x - 0.01, -0.12, 0.66), (x + 0.05, 0.14, 0.685), k)
    box(m, (-0.04, 0.20, 0.44), (0.04, 0.26, 0.62), k)                                                # spine
    from mathutils import Matrix
    keep = m.T
    m.T = keep @ Matrix.Translation((0, 0.25, 0.60)) @ Matrix.Rotation(-math.radians(12), 4, 'X')
    W2 = 0.23
    for x0, x1 in ((-W2, -W2 + 0.03), (W2 - 0.03, W2)):                                              # back frame sides
        box(m, (x0, 0.0, 0.0), (x1, 0.03, 0.56), k)
    box(m, (-W2, 0.0, 0.0), (W2, 0.03, 0.04), k)
    box(m, (-W2, 0.0, 0.53), (W2, 0.03, 0.56), k)
    box(m, (-W2 + 0.03, 0.01, 0.04), (W2 - 0.03, 0.018, 0.53), S["mesh"])                             # mesh panel
    box(m, (-0.02, 0.03, 0.50), (0.02, 0.05, 0.68), k)                                                # headrest post
    box(m, (-0.15, 0.0, 0.66), (0.15, 0.04, 0.70), k)
    box(m, (-0.15, 0.0, 0.70), (0.15, 0.03, 0.80), S["mesh"])
    box(m, (-0.15, 0.0, 0.80), (0.15, 0.04, 0.82), k)
    m.T = keep


# ---------- demo boards (photo faces + relief) ----------

def demo_board(m, S, u0, u1, v, z0, z1, img, rects, depth_back=0.45):
    """White demo panel, front face at v (devices toward -v) mapped with the rectified photo `img` slot; each
    rect (x0, y0, x1, y1, depth) of the photo (top-left origin) is extruded as a box whose front shows the same
    photo region, so DIN modules, e-stops and cameras get real relief. Acrylic sides on the profile cube behind."""
    face_split(m, bx((u0, v, z0), (u1, v + 0.012, z1)), S[img], S["abs_white"], 2, rect((0, 0, 1, 1)))
    W, H = u1 - u0, z1 - z0
    for x0, y0, x1, y1, d in rects:
        lo = (u0 + x0 * W, v - d, z1 - y1 * H)
        hi = (u0 + x1 * W, v, z1 - y0 * H)
        face_split(m, bx(lo, hi), S[img], S["abs_white"], 2, rect(img_rect((x0, y0, x1, y1))))
    for uu in (u0 + 0.005, u1 - 0.009):                                                               # acrylic sides
        box(m, (uu, v + 0.02, z0 + 0.04), (uu + 0.004, v + depth_back - 0.02, z1 - 0.04), S["glass"])


def antennas(m, S, u0, u1, v, z0, z1, xs, y_top, y_bot):
    """Router antennas (board 5): thin black sticks standing off the board, photo x / y fractions."""
    W, H = u1 - u0, z1 - z0
    for x in xs:
        box(m, (u0 + x * W - 0.006, v - 0.035, z1 - y_bot * H), (u0 + x * W + 0.006, v - 0.022, z1 - y_top * H),
            S["abs_black"])
