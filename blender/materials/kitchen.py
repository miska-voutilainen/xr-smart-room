# Kitchen: OSB smart-home demo board on the cabinet's door end + a few worktop props +
# the network cable bundle and PoE switch on the floor between the cabinet and the door wall.
# Photos: 122216 (straight-on, primary), 122250, 150448. Collection "Kitchen", objects Kitchen_*.
# Every prop is its own object, real scale, origin at its bottom centre (future XR grab objects).
#
# Board layout is measured in px of a crop of 122216 (board_full.png: x 825..1025, y 335..600 of
# the 1400 px copy, upscaled to 1166 px wide). Scale K = 0.513 mm/px = median of the LED pitch
# (Sonoff L1 strip, 30 LED/m), Sonoff 4CH Pro R3 (145 mm) and Waveshare 7" HDMI LCD (C) (164.9 mm).
# Real device sizes from the makers / retailers (see report); lamps, door sensor, L1 measured.
import math

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

TOP = 0.90                          # worktop top (cabinet.py)
K = 0.00052                         # m per crop px (devices 0.513, camera solve 0.532)
BCX, ZTOP = 0.975, 1.66             # board centre x (PnP back-projection of 122216), OSB top z
PX0, PY0 = 580, 60                  # crop px of the OSB top centre
OSB_X0, OSB_X1 = BCX - 0.265, BCX + 0.265
OSB_Y0, YF = 0.135, 0.147           # OSB back / front face (12 mm OSB)
PLATE_Z = TOP + 0.022               # base plate top


def P(px, py):
    """crop px -> world (x, z) on the OSB face; photo looks -y so image right = -x."""
    return BCX - (px - PX0) * K, ZTOP - (py - PY0) * K


# ---------------------------------------------------------------- mesh builder
class MB:
    def __init__(s):
        s.v, s.f, s.m, s.uv, s.sm = [], [], [], [], []

    def face(s, idx, m, uv=None, smooth=False):
        s.f.append(tuple(idx))
        s.m.append(m)
        s.uv.append(uv)
        s.sm.append(smooth)

    def add(s, pts, T):
        b = len(s.v)
        s.v.extend(T(Vector(p)) for p in pts)
        return b

    def box(s, lo, hi, m, T=lambda p: p, front_uv=None):
        (x0, y0, z0), (x1, y1, z1) = lo, hi
        b = s.add([(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
                   (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)], T)
        quads = ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7))
        for i, q in enumerate(quads):
            uv = None
            if front_uv is not None:          # +y face gets the sticker tile, others its corner
                (u0, v0), (u1, v1) = front_uv
                uv = [(u0, v0), (u1, v0), (u1, v1), (u0, v1)] if i == 4 else [(u0, v0)] * 4
            s.face([b + j for j in q], m, uv)

    def loft(s, rings, mats, T=lambda p: p, cap0=None, cap1=None, smooth=True, ring_uv=None, closed=True, wrap=False):
        """Quads between rings of equal length; caps are triangle fans (material index or None)."""
        n = len(rings[0])
        base = [s.add(r, T) for r in rings]
        e = n if closed else n - 1
        for i in range(len(rings) - 1 + wrap):          # wrap: last ring joins the first
            i1 = (i + 1) % len(rings)
            for k in range(e):
                k1 = (k + 1) % n
                uv = None
                if ring_uv:
                    uv = [ring_uv[i][k], ring_uv[i][k1], ring_uv[i1][k1], ring_uv[i1][k]]
                s.face((base[i] + k, base[i] + k1, base[i1] + k1, base[i1] + k),
                       mats[i] if isinstance(mats, (list, tuple)) else mats, uv, smooth)
        for ring, b, m in ((rings[0], base[0], cap0), (rings[-1], base[-1], cap1)):
            if m is None:
                continue
            c = s.add([tuple(sum((Vector(p) for p in ring), Vector()) / n)], T)
            for k in range(n):
                s.face((b + k, b + (k + 1) % n, c), m, None, False)

    def lathe(s, prof, mats, n=24, T=lambda p: p, axis="z"):
        """Revolve [(r, h)] around z (or y = out of the board). r == 0 ends become fan caps."""
        def ring(r, h):
            out = []
            for k in range(n):
                a = 2 * math.pi * k / n
                c, sn = r * math.cos(a), r * math.sin(a)
                out.append((c, sn, h) if axis == "z" else (c, h, sn))
            return out
        p = list(prof)
        cap0 = cap1 = None
        ms = list(mats) if isinstance(mats, (list, tuple)) else [mats] * (len(p) - 1)
        if p[0][0] == 0:
            cap0 = ms[0]
            p, ms = p[1:], ms[1:]
        if p[-1][0] == 0:
            cap1 = ms[-1]
            p, ms = p[:-1], ms[:-1]
        if len(p) == 1:
            p, ms = [p[0], p[0]], [ms[0]]
        s.loft([ring(r, h) for r, h in p], ms or [cap0], T, cap0, cap1)

    def tube(s, pts, r, m, sides=4, T=lambda p: p, sec=None, up=None, uv_len=False, smooth=True):
        """Sweep a cross-section along a polyline with parallel-transport frames."""
        pts = [Vector(p) for p in pts]
        tans = []
        for i in range(len(pts)):
            a, b = pts[max(i - 1, 0)], pts[min(i + 1, len(pts) - 1)]
            tans.append((b - a).normalized())
        nrm = Vector(up) if up else (Vector((0, 0, 1)) if abs(tans[0].z) < 0.9 else Vector((1, 0, 0)))
        nrm = (nrm - tans[0] * nrm.dot(tans[0])).normalized()
        sec = sec or [(r * math.cos(2 * math.pi * k / sides + math.pi / sides),
                       r * math.sin(2 * math.pi * k / sides + math.pi / sides)) for k in range(sides)]
        rings, uvs, L = [], [], 0.0
        for i, (p, t) in enumerate(zip(pts, tans)):
            if i:
                nrm = tans[i - 1].rotation_difference(t) @ nrm
                nrm = (nrm - t * nrm.dot(t)).normalized()
                L += (p - pts[i - 1]).length
            side = t.cross(nrm)
            rings.append([tuple(p + side * a + nrm * b) for a, b in sec])
            uvs.append([(L, 0.5 + a / (2 * max(abs(x) for x, _ in sec))) for a, b in sec])
        s.loft(rings, m, T, m, m, smooth, uvs if uv_len else None)


def smooth_path(ctrl, per=6):
    """Catmull-Rom through control points."""
    c = [Vector(p) for p in ctrl]
    c = [c[0]] + c + [c[-1]]
    out = []
    for i in range(1, len(c) - 2):
        p0, p1, p2, p3 = c[i - 1], c[i], c[i + 1], c[i + 2]
        for k in range(per):
            t = k / per
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t
                              + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    out.append(c[-2])
    return out


def rrect(w, h, r, segs=2):
    """Rounded rectangle outline in (x, z), centred."""
    pts = []
    for cx, cz, a0 in ((w / 2 - r, h / 2 - r, 0), (-w / 2 + r, h / 2 - r, 90),
                       (-w / 2 + r, -h / 2 + r, 180), (w / 2 - r, -h / 2 + r, 270)):
        for k in range(segs + 1):
            a = math.radians(a0 + 90 * k / segs)
            pts.append((cx + r * math.cos(a), cz + r * math.sin(a)))
    return pts


def rbox(mb, w, h, d, m, T, r=0.004, ch=0.0015, y0=0.0, cap_m=None):
    """Rounded box standing out of the board along +y: rounded corners + chamfered front edge."""
    o = rrect(w, h, r)
    i = rrect(w - 2 * ch, h - 2 * ch, max(r - ch, 0.0005))
    mb.loft([[(x, y0, z) for x, z in o], [(x, y0 + d - ch, z) for x, z in o],
             [(x, y0 + d, z) for x, z in i]], m, T, m, m if cap_m is None else cap_m, smooth=False)


def at(x, z, y=0.0, yaw=0.0):
    """Local device frame: local x = world x, local y = out of the board, local z = up."""
    R = Matrix.Rotation(yaw, 3, "Z")
    o = Vector((x, YF + y, z))
    return lambda p: o + R @ p


def stadium(a, L, m=8):
    pts = []
    for k in range(m + 1):
        f = math.pi * k / m
        pts.append((a * math.cos(f), L + a * math.sin(f)))
    for k in range(m + 1):
        f = math.pi * k / m
        pts.append((-a * math.cos(f), -L - a * math.sin(f)))
    return pts


# ---------------------------------------------------------------- materials
def node(nt, kind, loc=(0, 0), **inputs):
    nd = nt.nodes.new(kind)
    nd.location = loc
    for k, v in inputs.items():
        nd.inputs[k].default_value = v
    return nd


def sock(socks, ident):
    return next(x for x in socks if x.identifier == ident)


def material(name, rgb, rough=0.5, metal=0.0, **extra):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = node(nt, "ShaderNodeOutputMaterial", (600, 0))
    bsdf = node(nt, "ShaderNodeBsdfPrincipled", (300, 0))
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    bsdf.inputs["Base Color"].default_value = (*rgb, 1)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    for k, v in extra.items():
        bsdf.inputs[k].default_value = v
    m.diffuse_color = (*rgb, 1)
    return m, nt, bsdf


def mat_osb():
    m, nt, bsdf = material("Kitchen_OSB", (0.62, 0.42, 0.20), 0.75)
    co = node(nt, "ShaderNodeTexCoord", (-1200, 0))
    ramp_in = []
    for i, sc in enumerate(((10, 3, 40), (3, 10, 40))):          # strands elongated along x and z
        mp = node(nt, "ShaderNodeMapping", (-1000, 200 - 300 * i), Scale=sc)
        nt.links.new(co.outputs["Object"], mp.inputs["Vector"])
        vo = node(nt, "ShaderNodeTexVoronoi", (-800, 200 - 300 * i), Randomness=1.0)
        nt.links.new(mp.outputs["Vector"], vo.inputs["Vector"])
        ramp_in.append(vo)
    sel = node(nt, "ShaderNodeTexNoise", (-800, 500), Scale=18.0, Detail=1.0)
    nt.links.new(co.outputs["Object"], sel.inputs["Vector"])
    mix = node(nt, "ShaderNodeMix", (-500, 200))
    mix.data_type = "RGBA"
    nt.links.new(sel.outputs["Fac"], mix.inputs["Factor"])
    nt.links.new(ramp_in[0].outputs["Color"], sock(mix.inputs, "A_Color"))
    nt.links.new(ramp_in[1].outputs["Color"], sock(mix.inputs, "B_Color"))
    bw = node(nt, "ShaderNodeRGBToBW", (-300, 200))
    nt.links.new(sock(mix.outputs, "Result_Color"), bw.inputs["Color"])
    cr = node(nt, "ShaderNodeValToRGB", (-100, 200))
    cr.color_ramp.elements[0].color = (0.40, 0.24, 0.10, 1)
    cr.color_ramp.elements[1].color = (0.80, 0.58, 0.32, 1)
    nt.links.new(bw.outputs["Val"], cr.inputs["Fac"])
    nt.links.new(cr.outputs["Color"], bsdf.inputs["Base Color"])
    bp = node(nt, "ShaderNodeBump", (100, -200), Strength=0.3, Distance=0.0008)
    nt.links.new(ramp_in[0].outputs["Distance"], bp.inputs["Height"])
    nt.links.new(bp.outputs["Normal"], bsdf.inputs["Normal"])
    return m


def mat_wood():
    m, nt, bsdf = material("Kitchen_WoodDark", (0.10, 0.05, 0.025), 0.7)
    co = node(nt, "ShaderNodeTexCoord", (-900, 0))
    mp = node(nt, "ShaderNodeMapping", (-700, 0), Scale=(2.0, 60.0, 60.0))
    nt.links.new(co.outputs["Object"], mp.inputs["Vector"])
    nz = node(nt, "ShaderNodeTexNoise", (-500, 0), Scale=3.0, Detail=6.0)
    nt.links.new(mp.outputs["Vector"], nz.inputs["Vector"])
    cr = node(nt, "ShaderNodeValToRGB", (-250, 0))
    cr.color_ramp.elements[0].color = (0.05, 0.025, 0.012, 1)
    cr.color_ramp.elements[1].color = (0.20, 0.10, 0.05, 1)
    nt.links.new(nz.outputs["Fac"], cr.inputs["Fac"])
    nt.links.new(cr.outputs["Color"], bsdf.inputs["Base Color"])
    return m


def mat_led():
    """Black strip PCB with 5x5 mm 5050 packages every 33.3 mm (UV u = metres along the strip)."""
    m, nt, bsdf = material("Kitchen_LEDStrip", (0.015, 0.015, 0.015), 0.25)
    uvn = node(nt, "ShaderNodeUVMap", (-1100, 0))
    sep = node(nt, "ShaderNodeSeparateXYZ", (-900, 0))
    nt.links.new(uvn.outputs["UV"], sep.inputs["Vector"])
    pitch = 1 / 30
    f = node(nt, "ShaderNodeMath", (-700, 100))
    f.operation = "WRAP"
    f.inputs[1].default_value, f.inputs[2].default_value = pitch, 0.0          # max, min
    nt.links.new(sep.outputs["X"], f.inputs[0])
    a = node(nt, "ShaderNodeMath", (-500, 100))                # |wrap - pitch/2| < 2.5 mm
    a.operation = "SUBTRACT"
    a.inputs[1].default_value = pitch / 2
    nt.links.new(f.outputs[0], a.inputs[0])
    ab = node(nt, "ShaderNodeMath", (-350, 100))
    ab.operation = "ABSOLUTE"
    nt.links.new(a.outputs[0], ab.inputs[0])
    lt = node(nt, "ShaderNodeMath", (-200, 100))
    lt.operation, lt.inputs[1].default_value = "LESS_THAN", 0.0025
    nt.links.new(ab.outputs[0], lt.inputs[0])
    b = node(nt, "ShaderNodeMath", (-500, -100))               # across: middle half of the width
    b.operation, b.inputs[1].default_value = "SUBTRACT", 0.5
    nt.links.new(sep.outputs["Y"], b.inputs[0])
    bb = node(nt, "ShaderNodeMath", (-350, -100))
    bb.operation = "ABSOLUTE"
    nt.links.new(b.outputs[0], bb.inputs[0])
    lt2 = node(nt, "ShaderNodeMath", (-200, -100))
    lt2.operation, lt2.inputs[1].default_value = "LESS_THAN", 0.26
    nt.links.new(bb.outputs[0], lt2.inputs[0])
    led = node(nt, "ShaderNodeMath", (0, 0))
    led.operation = "MULTIPLY"
    nt.links.new(lt.outputs[0], led.inputs[0])
    nt.links.new(lt2.outputs[0], led.inputs[1])
    col = node(nt, "ShaderNodeMix", (150, 150))
    col.data_type = "RGBA"
    sock(col.inputs, "A_Color").default_value = (0.015, 0.015, 0.015, 1)
    sock(col.inputs, "B_Color").default_value = (0.85, 0.83, 0.75, 1)
    nt.links.new(led.outputs[0], col.inputs["Factor"])
    nt.links.new(sock(col.outputs, "Result_Color"), bsdf.inputs["Base Color"])
    em = node(nt, "ShaderNodeMath", (150, -150))               # LEDs off in the photos: strength 0 (g2 may raise)
    em.operation, em.inputs[1].default_value = "MULTIPLY", 0.0
    em.label = "LED emission strength"
    nt.links.new(led.outputs[0], em.inputs[0])
    nt.links.new(em.outputs[0], bsdf.inputs["Emission Strength"])
    bsdf.inputs["Emission Color"].default_value = (1.0, 0.85, 0.6, 1)
    return m


def qr_image(name="Kitchen_QR", tiles=4, tp=256):
    """Atlas of pseudo QR stickers (40 x 46 mm): grey label text bars + 25x25 code with finders."""
    img = bpy.data.images.get(name) or bpy.data.images.new(name, tiles * tp, tiles * tp)
    rng = np.random.default_rng(7)
    a = np.ones((tiles * tp, tiles * tp, 4), np.float32)
    mw, mh = 7, 6                               # module px (wide, tall): 40x46 mm sticker on a square tile
    for t in range(tiles * tiles):
        q = rng.random((25, 25)) < 0.5
        for (r0, c0) in ((0, 0), (0, 18), (18, 0)):
            q[r0:r0 + 7, c0:c0 + 7] = False
            q[r0:r0 + 7, c0] = q[r0:r0 + 7, c0 + 6] = q[r0, c0:c0 + 7] = q[r0 + 6, c0:c0 + 7] = True
            q[r0 + 2:r0 + 5, c0 + 2:c0 + 5] = True
        for rr, cc in ((7, slice(0, 8)), (17, slice(0, 8)), (7, slice(17, 25))):
            q[rr, cc] = False
        q[slice(0, 8), 7] = q[slice(17, 25), 7] = q[slice(0, 8), 17] = False
        q[6, 8:17] = q[8:17, 6] = (np.arange(9) % 2 == 0)
        q[16:21, 16:21] = True
        q[17:20, 17:20] = False
        q[18, 18] = True
        ty, tx = divmod(t, tiles)
        x0, y0 = tx * tp + (tp - 25 * mw) // 2, ty * tp + 18      # image rows go bottom-up
        for r in range(25):
            for c in range(25):
                if q[r, c]:
                    yy = y0 + (24 - r) * mh
                    a[yy:yy + mh, x0 + c * mw:x0 + (c + 1) * mw, :3] = 0.02
        nb = 2 + t % 2                                             # label text: grey word bars
        xs = x0
        for k in range(nb):
            wl = int(rng.integers(25, 60))
            a[ty * tp + 200:ty * tp + 212, xs:xs + wl, :3] = 0.35
            xs += wl + 8
    img.pixels.foreach_set(a.ravel())
    img.pack()
    return img


def mat_qr():
    m, nt, bsdf = material("Kitchen_QRSticker", (0.9, 0.9, 0.88), 0.55)
    tex = node(nt, "ShaderNodeTexImage", (-300, 0))
    tex.image = qr_image()
    tex.interpolation = "Closest"
    uvn = node(nt, "ShaderNodeUVMap", (-500, 0))
    nt.links.new(uvn.outputs["UV"], tex.inputs["Vector"])
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    return m


def mat_glass():
    m, nt, bsdf = material("Kitchen_LampGlass", (0.95, 0.96, 0.97), 0.15,
                           **{"Transmission Weight": 1.0, "IOR": 1.5})
    co = node(nt, "ShaderNodeTexCoord", (-700, 0))
    wv = node(nt, "ShaderNodeTexWave", (-500, 0), Scale=60.0, Distortion=0.0)
    wv.bands_direction = "Z"                                       # prismatic ribs across the lamp
    nt.links.new(co.outputs["Object"], wv.inputs["Vector"])
    bp = node(nt, "ShaderNodeBump", (-200, -200), Strength=0.4, Distance=0.001)
    nt.links.new(wv.outputs["Fac"], bp.inputs["Height"])
    nt.links.new(bp.outputs["Normal"], bsdf.inputs["Normal"])
    return m


def mat_pet():
    m, _, _ = material("Kitchen_PET", (0.95, 0.97, 0.98), 0.03, **{"Transmission Weight": 1.0, "IOR": 1.33})
    return m


M = {}
for mm in (mat_osb(), mat_wood(), mat_led(), mat_qr(), mat_glass(), mat_pet()):
    M[mm.name] = mm
for name, rgb, rough, metal in (
        ("Kitchen_PlasticWhite", (0.82, 0.82, 0.80), 0.35, 0),
        ("Kitchen_PlasticBlack", (0.02, 0.02, 0.02), 0.40, 0),
        ("Kitchen_PlasticGrey", (0.18, 0.18, 0.19), 0.35, 0),
        ("Kitchen_MetalCage", (0.62, 0.62, 0.60), 0.35, 1),
        ("Kitchen_Screen", (0.008, 0.008, 0.01), 0.04, 0),
        ("Kitchen_PCB", (0.02, 0.16, 0.45), 0.30, 0),
        ("Kitchen_CableBlack", (0.012, 0.012, 0.012), 0.45, 0),
        ("Kitchen_CableBlue", (0.05, 0.35, 0.75), 0.40, 0),
        ("Kitchen_WireRed", (0.60, 0.03, 0.02), 0.40, 0),
        ("Kitchen_CableWhite", (0.78, 0.78, 0.75), 0.50, 0),
        ("Kitchen_PaperCupOrange", (0.85, 0.42, 0.06), 0.55, 0),
        ("Kitchen_PaperCupBrown", (0.42, 0.28, 0.19), 0.60, 0),
        ("Kitchen_PaperWhite", (0.88, 0.88, 0.86), 0.70, 0),
        ("Kitchen_BottleLabel", (0.75, 0.08, 0.06), 0.40, 0),
        ("Kitchen_SugarBox", (0.08, 0.40, 0.80), 0.50, 0),
        ("Kitchen_TeaBox", (0.03, 0.16, 0.07), 0.45, 0),
        ("Kitchen_CardboardBlack", (0.025, 0.025, 0.025), 0.80, 0),
):
    M[name] = material(name, rgb, rough, metal)[0]


# ---------------------------------------------------------------- object helper
def make_object(name, mb, mats, origin):
    """Mesh from builder (world coords) -> object with origin at `origin`, in collection Kitchen."""
    col = bpy.data.collections.get("Kitchen")
    if col is None:
        col = bpy.data.collections.new("Kitchen")
    if col.name not in bpy.context.scene.collection.children:
        bpy.context.scene.collection.children.link(col)
    idx = {mm: i for i, mm in enumerate(mats)}
    o = Vector(origin)
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v - o) for v in mb.v], [], mb.f)
    for mm in mats:
        me.materials.append(M[mm])
    me.polygons.foreach_set("material_index", [idx[m] for m in mb.m])
    me.polygons.foreach_set("use_smooth", mb.sm)
    uvl = me.uv_layers.new(name="UVMap")
    data = []
    for poly, uv in zip(me.polygons, mb.uv):
        if uv is None:                                 # box projection in metres on the dominant axis
            n = poly.normal
            ax = max(range(3), key=lambda i: abs(n[i]))
            a, b = [(1, 2), (0, 2), (0, 1)][ax]
            uv = [(mb.v[vi][a], mb.v[vi][b]) for vi in poly.vertices]
        data.extend(uv)
    uvl.data.foreach_set("uv", [c for p in data for c in p])
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    me.validate()
    ob = bpy.data.objects.get(name)
    if ob is None:
        ob = bpy.data.objects.new(name, me)
    else:
        old = ob.data
        ob.data = me
        if old.users == 0:
            bpy.data.meshes.remove(old)
    me.name = name
    for c in list(ob.users_collection):
        if c != col:
            c.objects.unlink(ob)
    if ob.name not in col.objects:
        col.objects.link(ob)
    ob.location, ob.rotation_euler, ob.scale = o, (0, 0, 0), (1, 1, 1)
    tris = sum(len(p.vertices) - 2 for p in me.polygons)
    print(f"KITCHEN {name}: {len(me.polygons)} faces, {tris} tris")
    return ob


# ================================================================ the demo board
B = MB()
OSB, WOOD, WH, BK, GR, GLASS, CAGE = ("Kitchen_OSB", "Kitchen_WoodDark", "Kitchen_PlasticWhite",
                                      "Kitchen_PlasticBlack", "Kitchen_PlasticGrey", "Kitchen_LampGlass",
                                      "Kitchen_MetalCage")
LED, QR, SCR, PCB = "Kitchen_LEDStrip", "Kitchen_QRSticker", "Kitchen_Screen", "Kitchen_PCB"
CBK, CBL, CRD = "Kitchen_CableBlack", "Kitchen_CableBlue", "Kitchen_WireRed"

# base: plate on the worktop, front + rear battens clamping the OSB, two angle brackets
B.box((BCX - 0.295, 0.04, TOP), (BCX + 0.295, 0.29, PLATE_Z), WOOD)
B.box((BCX - 0.285, YF, PLATE_Z), (BCX + 0.285, YF + 0.040, 0.995), WOOD)
B.box((BCX - 0.285, 0.100, PLATE_Z), (BCX + 0.285, OSB_Y0, 0.995), WOOD)
B.box((OSB_X0, OSB_Y0, PLATE_Z), (OSB_X1, YF, ZTOP), OSB)
for bx in (P(260, 0)[0], P(960, 0)[0]):
    B.box((bx - 0.0125, YF + 0.040, PLATE_Z), (bx + 0.0125, YF + 0.042, PLATE_Z + 0.03), CAGE)
    B.box((bx - 0.0125, YF + 0.042, PLATE_Z), (bx + 0.0125, YF + 0.067, PLATE_Z + 0.002), CAGE)

# LED strip (Sonoff L1 kit, 5050 RGB, 30 LED/m, 10 mm): bottom-right -> left -> up -> top -> down right
e = 0.009
xl, xr, zt_, zb_ = OSB_X1 - e, OSB_X0 + e, ZTOP - e, P(0, 1275)[1]
corner = []
for (x, z) in ((xr + 0.01, zb_), (xl, zb_), (xl, zt_), (xr, zt_), (xr, P(0, 1240)[1])):
    corner.append(Vector((x, YF + 0.0012, z)))
path = [corner[0]]
for i in range(1, len(corner) - 1):                  # small folds at the corners
    a, b, c = corner[i - 1], corner[i], corner[i + 1]
    path += [b + (a - b).normalized() * 0.006, b + ((a - b).normalized() + (c - b).normalized()) * 0.0025,
             b + (c - b).normalized() * 0.006]
path.append(corner[-1])
B.tube(path, 0, LED, sec=[(-0.005, -0.0008), (0.005, -0.0008), (0.005, 0.0008), (-0.005, 0.0008)],
       up=(0, 1, 0), uv_len=True, smooth=False)

# extractor fan: Vents 100 S, face 150 x 150 x 12 mm, spigot D100 x 96 mm through the board
fx, fz = P(268, 275)
T = at(fx, fz)
o, i_ = rrect(0.150, 0.150, 0.006), rrect(0.112, 0.112, 0.004)
B.loft([[(x, 0, z) for x, z in o], [(x, 0.010, z) for x, z in o],
        [(x * 0.985, 0.012, z * 0.985) for x, z in o],
        [(x, 0.012, z) for x, z in i_], [(x, 0.004, z) for x, z in i_]],
       [WH, WH, WH, WH], T, WH, GR, smooth=False)
for k in range(11):                                  # horizontal louvres
    z = -0.050 + k * 0.010
    B.box((-0.056, 0.004, z - 0.0012), (0.056, 0.011, z + 0.0012), WH, T)
B.lathe([(0, 0.0045), (0.022, 0.0045), (0.022, 0.004), (0, 0.004)], WH, 16, T, axis="y")       # impeller hub
B.box((-0.012, 0.0115, -0.071), (0.012, 0.0125, -0.066), GR, T)                     # badge
B.lathe([(0, OSB_Y0 - 0.096 - YF), (0.050, OSB_Y0 - 0.096 - YF), (0.050, OSB_Y0 - YF), (0, OSB_Y0 - YF)], WH, 20, T, axis="y")

# Sonoff 4CH Pro R3: 145 x 90 x 34 mm, 4 buttons on the left, blue terminal covers top/bottom
sx, sz = P(607, 228)
T = at(sx, sz)
rbox(B, 0.145, 0.090, 0.020, WH, T, r=0.004)
rbox(B, 0.105, 0.090, 0.034, WH, T, r=0.004)
for k in range(4):
    z = 0.027 - k * 0.018
    B.lathe([(0, 0.0215), (0.004, 0.0215), (0.004, 0.019), (0, 0.019)], WH, 8, lambda p, z=z: T(p + Vector((0.061, 0, z))),
            axis="y")
for zz in (0.047, -0.047):
    B.box((-0.040, 0.004, zz - 0.002), (0.040, 0.016, zz + 0.002), CBL, T)
for ux in (-0.068, 0.068):
    B.lathe([(0, 0.0215), (0.0035, 0.0215), (0.0035, 0.0), (0, 0.0)], CAGE, 8,
            lambda p, ux=ux: T(p + Vector((ux, 0, 0.040))), axis="y")

# oval bulkhead lamps (E27, glass + wire cage, black PP base): photo-measured ~110 x 190 x 100 mm
def lamp(px, py):
    cx, cz = P(px, py)
    T = at(cx, cz)
    ab, ag, L, c = 0.055, 0.044, 0.040, 0.065
    B.loft([[(u, 0.0, w) for u, w in stadium(ab, L)], [(u * 0.96, 0.032, w * 0.985) for u, w in stadium(ab, L)]],
           BK, T, BK, WH)                                                          # base, white reflector face
    # glass as a 2 mm shell (outer dome -> 1 mm-wide crest -> inner dome -> rim), so it reads as thin glass
    ths = [math.radians(a) for a in (0, 25, 45, 62, 76, 86, 89.6)]
    outer = [[(u, 0.033 + c * math.sin(t), w) for u, w in stadium(ag * math.cos(t), L)] for t in ths]
    inner = [[(u, 0.033 + (c - 0.002) * math.sin(t), w) for u, w in stadium((ag - 0.002) * math.cos(t), L)]
             for t in reversed(ths)]
    B.loft(outer + inner, GLASS, T, wrap=True)
    for s in (1, -1):                                                              # mounting ears + screws
        B.box((s * ab - 0.004 if s > 0 else -ab - 0.022, 0.0, -0.016),
              (ab + 0.022 if s > 0 else -ab + 0.004, 0.009, 0.016), BK, T)
        B.lathe([(0, 0.011), (0.004, 0.011), (0.004, 0.0), (0, 0.0)], CAGE, 8,
                lambda p, s=s: T(p + Vector((s * (ab + 0.013), 0, 0))), axis="y")
    B.lathe([(0, -0.077), (0.012, -0.077), (0.012, -0.056), (0, -0.056)], WH, 12,
            lambda p: T(p + Vector((0, 0.046, 0))))                                # E27 lampholder
    B.lathe([(0, -0.056), (0.011, -0.054), (0.020, -0.035), (0.022, -0.008), (0.017, 0.016), (0, 0.026)],
            WH, 12, lambda p: T(p + Vector((0, 0.052, 0))))                        # bulb
    r = 0.0016
    top = 0.032 + c + 0.003
    arc = [(0, 0.032 + 0.003 + c * math.sin(f), -(L + (ag + 0.003) * math.cos(f))) for f in
           [math.radians(a) for a in range(0, 91, 15)]]
    spine = arc + [(0, top, 0)] + [(x, y, -z) for x, y, z in reversed(arc)]
    B.tube(spine, r, CAGE, T=T)
    for wz in (0.028, -0.028):
        hoop = [((ag + 0.003) * math.cos(f), 0.032 + (c + 0.003) * math.sin(f), wz)
                for f in [math.radians(a) for a in range(0, 181, 20)]]
        B.tube(hoop, r, CAGE, T=T)
    ringp = [(u, 0.035, w) for u, w in stadium(ag + 0.003, L, 6)]
    B.tube(ringp + [ringp[0]], r, CAGE, T=T)
    return T


TL = lamp(918, 262)
lamp(268, 855)

# small Sonoff devices (sizes from Sonoff/retailer specs; door sensor measured)
for px, py, w, h, d in ((260, 605, 0.043, 0.043, 0.016),           # SNZB-01 wireless button
                        (460, 550, 0.035, 0.039, 0.022),           # SNZB-03 PIR body
                        (583, 606, 0.062, 0.062, 0.020),           # ZBBridge (Zigbee hub, USB powered)
                        (862, 651, 0.074, 0.031, 0.017),           # door / window sensor body
                        (862, 607, 0.043, 0.013, 0.012)):          # its magnet
    rbox(B, w, h, d, WH, at(*P(px, py)), r=0.005 if w > 0.03 else 0.003)
B.lathe([(0, 0.032), (0.006, 0.030), (0.0095, 0.024), (0.0105, 0.018), (0, 0.018)], WH, 12,
        lambda p: at(*P(460, 545))(p), axis="y")                                       # PIR Fresnel dome
B.box((-0.016, 0.0195, -0.006), (0.016, 0.0205, 0.006), GR, at(*P(583, 606)))         # hub window

# Waveshare 7" HDMI LCD (C): 164.9 x 106.96 x 8 mm, blue PCB behind the panel, 4 corner tabs
dx, dz = P(836, 947)
T = at(dx, dz)
for ux in (-0.078, 0.078):
    for wz in (-0.050, 0.050):
        B.lathe([(0, 0.0), (0.0028, 0.0), (0.0028, 0.008), (0, 0.008)], CAGE, 6, lambda p, ux=ux, wz=wz: T(p + Vector((ux, 0, wz))),
                axis="y")
        B.box((ux - 0.006, 0.008, wz + (0.002 if wz > 0 else -0.012)), (ux + 0.006, 0.0096,
              wz + (0.012 if wz > 0 else -0.002)), PCB, T)
B.box((-0.08245, 0.008, -0.05348), (0.08245, 0.0096, 0.05348), PCB, T)
B.box((-0.08245, 0.0096, -0.050), (0.08245, 0.0141, 0.050), BK, T)
B.box((-0.0771, 0.0141, -0.0430), (0.0771, 0.0145, 0.0430), SCR, T)
for wz in (-0.026, -0.040):                                                             # HDMI + USB plugs
    B.box((0.0825, 0.008, wz - 0.006), (0.110, 0.019, wz + 0.006), BK, T)

# Sonoff L1 LED controller (measured ~65 x 30 x 20 mm), with its QR label on top
lx, lz = P(835, 1225)
rbox(B, 0.065, 0.030, 0.020, BK, at(lx, lz), r=0.004)

# QR stickers 40 x 46 mm
stickers = [(595, 415), (900, 515), (170, 610), (460, 650), (580, 760), (860, 745),
            (265, 1090), (835, 1100), (555, 1180)]
for t, (px, py) in enumerate(stickers + [(835, 1225)]):
    x, z = P(px, py)
    y0 = 0.0201 if t == len(stickers) else 0.0
    ty, tx = divmod(t, 4)
    B.box((-0.020, y0, -0.023), (0.020, y0 + 0.0004, 0.023), QR, at(x, z),
          front_uv=((tx / 4 + 0.005, ty / 4 + 0.005), ((tx + 1) / 4 - 0.005, (ty + 1) / 4 - 0.005)))

# white-headed screws holding the board
for px, py in ((115, 598), (1025, 590), (125, 1300)):
    B.lathe([(0, 0.004), (0.006, 0.003), (0.006, 0.0), (0, 0.0)], WH, 8, at(*P(px, py)), axis="y")


# wires and cables
def wire(pts_px, r, m, y=0.004, per=4):
    pts = []
    for p in pts_px:
        x, z = P(p[0], p[1])
        pts.append((x, YF + (p[2] if len(p) > 2 else y), z))
    B.tube(smooth_path(pts, per), r, m)


wire([(530, 318, 0.006), (522, 340), (540, 360, 0.002), (548, 368, -0.003)], 0.0012, CRD)
wire([(640, 318, 0.006), (652, 342), (632, 362, 0.002), (626, 370, -0.003)], 0.0012, CBL)
wire([(865, 438, 0.010), (850, 470), (845, 488, -0.003)], 0.0012, CRD)
wire([(880, 438, 0.010), (872, 468), (862, 482, -0.003)], 0.0012, CBL)
wire([(660, 522, 0.002), (690, 520, 0.004), (705, 528, -0.003)], 0.0012, CBL)
wire([(600, 668, 0.010), (606, 760, 0.008), (612, 900, 0.008), (618, 985, 0.012), (650, 985, 0.024),
      (668, 980, 0.026)], 0.0022, CBK, per=5)                                          # USB hub -> display
wire([(668, 1000, 0.024), (630, 1010, 0.02), (600, 1015, 0.006), (590, 1018, -0.003)], 0.003, CBK)
# blue flat ribbon from the L1 to the strip start (bottom right)
rib = [(lx - 0.033, YF + 0.010, lz), (lx - 0.06, YF + 0.012, lz - 0.01), (P(1040, 1270)[0], YF + 0.012,
       P(0, 1270)[1]), (P(1060, 1290)[0], YF + 0.004, P(0, 1290)[1])]
B.tube(smooth_path(rib, 5), 0, CBL, sec=[(-0.005, -0.0005), (0.005, -0.0005), (0.005, 0.0005),
       (-0.005, 0.0005)], up=(0, 1, 0), smooth=False)
# 12 V lead: L1 -> DC jack (red ring) -> over the batten -> along the plate -> PSU on the worktop
jx, jz = P(800, 1330)
B.tube(smooth_path([(lx + 0.033, YF + 0.010, lz), (lx + 0.04, YF + 0.02, lz - 0.03), (jx, YF + 0.05, jz + 0.02)],
                   5), 0.0016, CBK)
RJ = Matrix.Rotation(math.radians(35), 3, "Y")
B.lathe([(0, -0.02), (0.0045, -0.02), (0.0045, 0.0), (0.0055, 0.0), (0.0055, 0.006), (0.0045, 0.006),
         (0.0045, 0.02), (0, 0.02)], [BK, BK, CRD, CRD, CRD, BK, BK], 10,
        lambda p: Vector((jx, YF + 0.05, jz)) + RJ @ p)                            # DC barrel jack, red ring
psu = Vector((BCX - 0.33, 0.085, TOP))
B.tube(smooth_path([(jx - 0.012, YF + 0.05, jz - 0.016), (jx - 0.03, YF + 0.055, 0.985),
                    (jx - 0.05, YF + 0.075, PLATE_Z + 0.003), (BCX - 0.22, 0.24, PLATE_Z + 0.002),
                    (BCX - 0.275, 0.20, PLATE_Z + 0.002), (BCX - 0.30, 0.14, TOP + 0.008),
                    (psu.x + 0.03, psu.y + 0.01, TOP + 0.015)], 4), 0.0016, CBK)
B.box((psu.x - 0.030, psu.y - 0.0225, TOP), (psu.x + 0.030, psu.y + 0.0225, TOP + 0.032), BK)

board = make_object("Kitchen_Board", B, [OSB, WOOD, WH, BK, GR, GLASS, CAGE, LED, QR, SCR, PCB, CBK, CBL, CRD],
                    (BCX, 0.165, TOP))


# ================================================================ worktop props (local coords)
def prop(name, build, mats, loc, yaw=0.0):
    mb = MB()
    build(mb)
    ob = make_object(name, mb, mats, (0, 0, 0))
    ob.location = loc
    ob.rotation_euler = (0, 0, yaw)
    return ob


ORG, BRN, PW, LBL = "Kitchen_PaperCupOrange", "Kitchen_PaperCupBrown", "Kitchen_PaperWhite", "Kitchen_BottleLabel"

# 16 oz (~450 ml) paper cup, D90 top / D60 base, 165 mm, white snap lid (122216, 122250)
prop("Kitchen_CupLid", lambda mb: mb.lathe(
    [(0, 0.0), (0.030, 0.0), (0.030, 0.002), (0.045, 0.160), (0.0465, 0.163), (0.0475, 0.168),
     (0.044, 0.172), (0.036, 0.178), (0, 0.180)], [ORG, ORG, ORG, ORG, WH, WH, WH, WH], 24),
     [ORG, WH], (1.48, 0.46, TOP))


# 8 oz (~250 ml) paper cup D80/D55 x 93 mm holding black plastic stirrers
def cup_small(mb):
    mb.lathe([(0, 0.0), (0.0275, 0.0), (0.040, 0.093), (0.0415, 0.094), (0.039, 0.092), (0.026, 0.006),
              (0, 0.006)], BRN, 20)
    for k, (a, tilt) in enumerate(((0.3, 0.12), (2.0, -0.15), (3.6, 0.1), (5.0, -0.08))):
        R = Matrix.Rotation(tilt, 3, "X") @ Matrix.Rotation(a, 3, "Z")
        o = Vector((0.01 * math.cos(a), 0.01 * math.sin(a), 0.008))
        mb.box((-0.0025, -0.001, 0), (0.0025, 0.001, 0.14), BK, lambda p, R=R, o=o: o + R @ p)


prop("Kitchen_CupPaper", cup_small, [BRN, BK], (1.82, 0.26, TOP))

# stack of D180 paper plates
prop("Kitchen_PlateStack", lambda mb: mb.lathe(
    [(0, 0.0), (0.062, 0.0), (0.072, 0.012), (0.088, 0.024), (0.090, 0.026), (0.088, 0.027),
     (0.072, 0.017), (0, 0.016)], PW, 32), [PW], (1.97, 0.25, TOP))   # s2_boxes: behind/right of sugar box, in front of tea (122216); was inside the box

# 0.5 l still water PET bottle (Akvile, 150448): D66 x 205 mm, white cap, red label
prop("Kitchen_Bottle", lambda mb: mb.lathe(
    [(0, 0.003), (0.020, 0.0), (0.031, 0.004), (0.033, 0.012), (0.033, 0.060), (0.0332, 0.060),
     (0.0332, 0.125), (0.033, 0.125), (0.032, 0.140), (0.022, 0.168), (0.0135, 0.180),
     (0.0135, 0.184), (0.0150, 0.184), (0.0150, 0.205), (0, 0.205)],
    ["Kitchen_PET"] * 5 + [LBL] * 2 + ["Kitchen_PET"] * 4 + [WH] * 3, 24),
     ["Kitchen_PET", LBL, WH], (2.40, 0.36, TOP))


# "UNIQUE white sugar" stick display box (the brief's "tissue box"): 180 x 90 x 60, tall back flap
def sugar(mb):
    sb = "Kitchen_SugarBox"
    mb.box((-0.090, -0.045, 0), (0.090, 0.045, 0.050), PW)                  # sticks filling the box
    mb.box((-0.090, 0.040, 0.050), (0.090, 0.045, 0.060), sb)               # front lip
    mb.box((-0.090, -0.045, 0.050), (-0.086, 0.040, 0.060), sb)
    mb.box((0.086, -0.045, 0.050), (0.090, 0.040, 0.060), sb)
    mb.box((-0.090, -0.045, 0.0), (0.090, 0.044, 0.045), sb)                # printed sleeve below
    mb.box((-0.090, -0.049, 0.0), (0.090, -0.045, 0.125), sb)               # back flap


prop("Kitchen_SugarBox", sugar, [PW, "Kitchen_SugarBox"], (2.05, 0.47, TOP), yaw=0.78)   # ~45 deg, end panel faces the camera in 122216/122209/122250

# Greenfield tea box 75 x 60 x 125 (122216, back of the worktop)
prop("Kitchen_TeaBox", lambda mb: mb.box((-0.0375, -0.030, 0), (0.0375, 0.030, 0.125), "Kitchen_TeaBox"),
     ["Kitchen_TeaBox"], (1.96, 0.08, TOP), yaw=-0.1)

# black product box standing behind the board (122250)
prop("Kitchen_BlackBox", lambda mb: mb.box((-0.09, -0.03, 0), (0.09, 0.03, 0.32), "Kitchen_CardboardBlack"),
     ["Kitchen_CardboardBlack"], (BCX + 0.15, 0.068, PLATE_Z))

# ================================================================ floor: PoE switch + cable bundle
# TP-Link TL-SG1016PE class 16-port desktop PoE switch, 294 x 180 x 44 mm, ports facing the cables
SW_C, SW_YAW = Vector((0.22, 0.40, 0.0)), math.radians(-65)
N_CAB = 8


def switch(mb):
    mb.box((-0.147, -0.090, 0.002), (0.147, 0.090, 0.044), BK)
    for sx in (-0.13, 0.13):                                                   # rubber feet
        for sy in (-0.07, 0.07):
            mb.box((sx - 0.008, sy - 0.008, 0.0), (sx + 0.008, sy + 0.008, 0.002), BK)
    for k in range(16):
        x = -0.127 + k * 0.0169
        mb.box((x - 0.007, 0.0895, 0.012), (x + 0.007, 0.0905, 0.026), "Kitchen_CableBlack")
        if k < N_CAB:                                                           # RJ45 boots, one red
            mb.box((x - 0.006, 0.0905, 0.013), (x + 0.006, 0.112, 0.025), CRD if k == 3 else "Kitchen_CableWhite")


prop("Kitchen_PoESwitch", switch, [BK, "Kitchen_CableBlack", "Kitchen_CableWhite", CRD], tuple(SW_C), SW_YAW)

R = Matrix.Rotation(SW_YAW, 3, "Z")
nrm = R @ Vector((0, 1, 0))
C = MB()


def floor_path(ctrl, r, per=2):
    """Catmull-Rom overshoots below the floor between floor points: clamp to lie on it."""
    return [Vector((p.x, p.y, max(p.z, r))) for p in smooth_path(ctrl, per)]


rng = np.random.default_rng(3)
DUCT = Vector((0.05, 0.022, 0.30))            # bottom of trim.py's vertical trunking drop (x 0.01..0.09, y 0..0.04, z 0.30)
SOCKET = Vector((0.05, 0.058, 0.475))         # trim.py's single socket in that drop (z 0.44..0.51, face y 0.046)
rc = 0.0028                                    # Cat6 U/UTP ~ 5.6 mm
# ponytail: one tied trunk (~20 cables) + 8 loose cables fanning out to the ports keeps it under the 1k prop budget
C.tube(smooth_path([DUCT, DUCT + Vector((0.004, 0.004, -0.12)), Vector((0.085, 0.05, 0.03)),
                    Vector((0.13, 0.07, 0.013)), Vector((0.30, 0.07, 0.013)), Vector((0.48, 0.11, 0.013)),
                    Vector((0.575, 0.28, 0.013)), Vector((0.575, 0.36, 0.013))], 2), 0.013,
       "Kitchen_CableWhite", sides=6)
for k in range(N_CAB):
    s_ = (k - (N_CAB - 1) / 2) / ((N_CAB - 1) / 2)                     # -1..1 across the fan
    j = Vector((rng.normal(0, 0.005), rng.normal(0, 0.005), 0))
    port = SW_C + R @ Vector((-0.127 + k * 0.0169, 0.112, 0.019))
    ctrl = [Vector((0.575, 0.33, 0.012)) + j * 0.6, Vector((0.572 + 0.008 * s_, 0.50 + 0.03 * s_, rc)) + j,
            Vector((0.50 + 0.03 * s_, 0.64 + 0.03 * s_, rc)) + j,
            port + nrm * (0.09 + 0.006 * k) + Vector((0, 0, -0.016)), port + nrm * 0.025, port]
    C.tube(floor_path(ctrl, rc), rc, "Kitchen_CableWhite")
# black mains cord: socket on the duct -> switch inlet at its back
inlet = SW_C + R @ Vector((0.12, -0.09, 0.02))
C.tube(floor_path([SOCKET, SOCKET + Vector((-0.012, 0.03, -0.06)), Vector((0.03, 0.09, 0.15)),
                    Vector((0.04, 0.12, 0.02)), Vector((0.10, 0.20, 0.0)), inlet - (R @ Vector((0, -1, 0))) * -0.04 + Vector((0, 0, -0.016)),
                    inlet], 0.0035, per=1), 0.0035, "Kitchen_CableBlack")
lo = Vector([min(v[i] for v in C.v) for i in range(3)])
hi = Vector([max(v[i] for v in C.v) for i in range(3)])
make_object("Kitchen_CableBundle", C, ["Kitchen_CableWhite", "Kitchen_CableBlack"],
            ((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, lo.z))
print("KITCHEN done")
