# Worktop tableware (owner s2_tableware). Runs after materials/kitchen.py and shaders/hard.py + arch.py.
# Replaces the mesh data (real profiles + UVs) and materials of Kitchen_CupLid (16 oz yellow cup + white snap lid),
# Kitchen_CupPaper (8 oz knit-print cup + black stirrers), Kitchen_PlateStack (paper plates + napkins), keeping
# their names / location / rotation, and adds Kitchen_CupPaper2 (second, empty knit cup) and Kitchen_Bowl (glazed
# ceramic bowl) seen in 122216 / 122250. Origins at bottom centre, real scale, each object < 2k tris.
# Textures: textures/s2_tableware (ambientCG CC0 paper/porcelain scans + wraps from make_wraps.py, see SOURCES.txt).
# Cup UVs: u = (theta - 270 deg) / 360 -> glue seam faces the wall (-y), print centre faces the room (+y).
# Only Kitchen_PaperCupOrange / Kitchen_PaperCupBrown are rebuilt among kitchen.py's materials; everything else
# here is a new Tableware_* material. Stirrers keep Kitchen_PlasticBlack (hard.py abs_black_satin).
import math
import os

import bpy

TEX = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "textures", "s2_tableware")
TOP = 0.90
N = 32                                                     # radial segments


# ================================================================ geometry
class Mesh:
    def __init__(s):
        s.v, s.f, s.m, s.uv = [], [], [], []

    def lathe(s, prof, mats, uvfn, n=N, xf=None):
        """Revolve [(r, h)]; mats per segment; uvfn(x, y, z, ufrac, i) -> uv. r == 0 points become fans."""
        rings = []
        for i, (r, h) in enumerate(prof):
            if r == 0:
                rings.append([len(s.v)] * (n + 1))
                s.v.append((0.0, 0.0, h) if xf is None else xf(0.0, 0.0, h, i))
                continue
            b = len(s.v)
            for k in range(n):
                a = 1.5 * math.pi + 2 * math.pi * k / n                       # k = 0 at -y (seam)
                x, y = r * math.cos(a), r * math.sin(a)
                s.v.append((x, y, h) if xf is None else xf(x, y, h, i))
            rings.append([b + k % n for k in range(n + 1)])
        for i in range(len(prof) - 1):
            for k in range(n):
                q = [(i, k), (i, k + 1), (i + 1, k + 1), (i + 1, k)]
                idx = [rings[a][b] for a, b in q]
                keep = [j for j in range(4) if idx[j] not in idx[:j]]
                if len(keep) < 3:
                    continue
                s.f.append([idx[j] for j in keep])
                s.m.append(mats[i])
                s.uv.append([uvfn(*s.v[idx[j]], q[j][1] / n, q[j][0]) for j in keep])

    def quad(s, pts, m, uvs):
        b = len(s.v)
        s.v.extend(pts)
        s.f.append(list(range(b, b + len(pts))))
        s.m.append(m)
        s.uv.append(uvs)


def build(name, mesh, mats, loc=None, yaw=0.0):
    me = bpy.data.meshes.new(name)
    me.from_pydata(mesh.v, [], mesh.f)
    for mm in mats:
        me.materials.append(mm)
    me.polygons.foreach_set("material_index", mesh.m)
    me.polygons.foreach_set("use_smooth", [True] * len(mesh.f))
    uvl = me.uv_layers.new(name="UVMap")
    uvl.data.foreach_set("uv", [c for face in mesh.uv for p in face for c in p])
    me.validate()
    me.set_sharp_from_angle(angle=math.radians(70))
    ob = bpy.data.objects.get(name)
    if ob is None:                                         # new prop: Kitchen collection, given placement
        ob = bpy.data.objects.new(name, me)
        col = bpy.data.collections.get("Kitchen") or bpy.context.scene.collection
        col.objects.link(ob)
        ob.location, ob.rotation_euler = loc, (0, 0, yaw)
    elif ob.data is not me:                                # existing prop: swap data only, keep transform
        old = ob.data
        ob.data = me
        if old.users == 0:
            bpy.data.meshes.remove(old)
    if loc is not None and ob.get("tw_new"):              # re-runs keep the authored placement of new props
        ob.location, ob.rotation_euler = loc, (0, 0, yaw)
    me.name = name
    tris = sum(len(p.vertices) - 2 for p in me.polygons)
    print(f"TABLEWARE {name}: {len(me.polygons)} faces, {tris} tris")
    return ob


def uv_metric(x, y, z, uf, i):                             # unwrap paper/ceramic: metres around x height
    r = math.hypot(x, y)
    return (uf * 2 * math.pi * max(r, 0.01), z)


def uv_top(x, y, z, uf, i):                                # planar from above (lid, plates)
    return (0.5 + x / 0.2, 0.5 + y / 0.2)


def paper_cup(rb, rt, H, foot, wrap_v0, rim=0.0016, thick=0.0005):
    """Cup profile (bottom centre -> foot -> printed wall -> rolled rim -> inner wall -> inner base) + materials
    0 = wrap, 1 = white paper. Returns (profile, mats, uvfn)."""
    hw = H - 2 * rim
    rw = lambda h: rb + (rt - rb) * h / hw                 # noqa: E731
    bead = [(rt + rim * (0.4 + math.cos(a)), H - rim + rim * math.sin(a))
            for a in (math.radians(d) for d in (-80, -20, 40, 100, 160, 220))]
    prof = [(0, foot), (rb - 0.003, foot), (rb - 0.0012, 0.0004), (rb - 0.0004, 0.0), (rb, 0.0006),
            (rw(hw * 0.5), hw * 0.5), (rw(hw), hw)] + bead + \
           [(rw(hw * 0.97) - thick, hw * 0.97), (rw(foot + 0.002) - thick, foot + 0.002), (0, foot + 0.001)]
    mats = [1, 1, 1, 1, 0, 0] + [1] * (len(prof) - 7)
    wall0, wall1 = 4, 6                                    # profile indices of the printed wall

    def uvfn(x, y, z, uf, i):
        if wall0 <= i <= wall1:
            return (uf, (z - 0.0006) / (hw - 0.0006) * (1 - wrap_v0) + wrap_v0)
        return uv_metric(x, y, z, uf, i)
    return prof, mats, uvfn


def orange_cup():
    m = Mesh()
    H, rt = 0.137, 0.045                                   # 16 oz: D90 / D62, 137 mm + lid -> 158 mm (122216 ratio)
    prof, mats, uvfn = paper_cup(0.031, rt, H, 0.008, 0.0)
    m.lathe(prof, mats, uvfn)
    # snap lid (polystyrene): skirt over the bead, recessed ring, raised drink-through shelf at the back (-y)
    R = rt + 0.0016 * 1.4
    lid = [(rt - 0.0015, H - 0.004), (R + 0.0002, H - 0.0075), (R + 0.0012, H - 0.006), (R + 0.0014, H - 0.002),
           (R + 0.0010, H + 0.002), (R - 0.0002, H + 0.0035), (rt - 0.0015, H + 0.004), (rt - 0.0028, H + 0.0125),
           (rt - 0.0042, H + 0.0145), (rt - 0.0062, H + 0.0150), (rt - 0.0080, H + 0.0125), (0.031, H + 0.0118),
           (0.024, H + 0.0122), (0.016, H + 0.0126), (0.008, H + 0.0128), (0, H + 0.013)]
    shelf0 = 9                                             # profile points from here inward may rise

    def xf(x, y, z, i):
        if i >= shelf0:
            t = min(max((-y - 0.002) / 0.008, 0.0), 1.0)   # step across x, full height for y < -10 mm
            z += 0.0055 * t * t * (3 - 2 * t)
        return (x, y, z)
    m.lathe(lid, [2] * (len(lid) - 1), uv_top, xf=xf)
    return m


def knit_cup(stirrers):
    m = Mesh()
    prof, mats, uvfn = paper_cup(0.0275, 0.040, 0.093, 0.007, 0.0)    # 8 oz: D80 / D55 x 93 mm
    m.lathe(prof, mats, uvfn)
    if stirrers:                                           # flat black stirrers, 7 x 1.6 x 140 mm, fanned
        for k, (a, tilt, dz) in enumerate(((0.3, 0.16, 0.0), (1.2, 0.10, 0.004), (2.1, 0.18, 0.002),
                                           (3.0, 0.12, 0.006), (3.9, 0.17, 0.001), (4.8, 0.09, 0.005),
                                           (5.7, 0.15, 0.003), (0.75, 0.05, 0.008))):
            ca, sa = math.cos(a), math.sin(a)
            o = (0.012 * ca, 0.012 * sa, 0.0075 + dz)
            d = (math.sin(tilt) * ca, math.sin(tilt) * sa, math.cos(tilt))         # leaning outwards
            w = (-sa, ca, 0.0)                                                     # flat side tangential
            t = (d[1] * w[2] - d[2] * w[1], d[2] * w[0] - d[0] * w[2], d[0] * w[1] - d[1] * w[0])
            P = lambda a_, b_, c_: tuple(o[j] + w[j] * a_ + t[j] * b_ + d[j] * c_ for j in range(3))  # noqa
            hw, ht, L = 0.0045, 0.0009, 0.14
            c = [P(sx * hw, sy * ht, sz * L) for sz in (0, 1) for sy in (-1, 1) for sx in (-1, 1)]
            for q in ((0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)):
                m.quad([c[j] for j in q], 2, [(0, 0), (1, 0), (1, 1), (0, 1)])
    return m


def plate_stack():
    m = Mesh()
    n, pitch = 12, 0.0018                                  # D180 paper plates, 12 stacked
    top = (n - 1) * pitch
    up = [(0.060, 0.0), (0.066, 0.003), (0.072, 0.0090), (0.075, 0.0110), (0.088, 0.0125), (0.0905, 0.0110)]
    t = 0.0004                                             # board thickness of the bottom plate
    prof = [(0, top + t)] + [(r, h + top + t) for r, h in up] + list(reversed(up)) + [(0, 0.0)]
    m.lathe(prof, [0] * (len(prof) - 1), uv_top, n=48)
    # folded paper napkins on top (122216 / 122250): ~165 mm square, 9 mm thick, crumpled, rotated + offset
    G, S, Z0 = 6, 0.165, top + 0.0131
    import random
    rnd = random.Random(7)
    ca, sa, ox, oy = math.cos(0.35), math.sin(0.35), 0.010, 0.012
    hgt = [[0.009 + rnd.uniform(-0.0015, 0.0015) for _ in range(G + 1)] for _ in range(G + 1)]

    def P(i, j, z):
        u, v = (i / G - 0.5) * S, (j / G - 0.5) * S
        d = math.hypot(u, v)
        zz = Z0 - 0.006 * max(0.0, 1 - d / 0.075) - 0.35 * max(0.0, d - 0.088) + (hgt[i][j] if z else 0.0)
        return (ox + u * ca - v * sa, oy + u * sa + v * ca, zz)
    for i in range(G):
        for j in range(G):
            uv = [(i / G, j / G), ((i + 1) / G, j / G), ((i + 1) / G, (j + 1) / G), (i / G, (j + 1) / G)]
            m.quad([P(i, j, 1), P(i + 1, j, 1), P(i + 1, j + 1, 1), P(i, j + 1, 1)], 1, uv)
            m.quad([P(i, j + 1, 0), P(i + 1, j + 1, 0), P(i + 1, j, 0), P(i, j, 0)], 1, uv)
    edge = [(i, 0) for i in range(G)] + [(G, j) for j in range(G)] + \
           [(G - i, G) for i in range(G)] + [(0, G - j) for j in range(G)]
    for e in range(len(edge)):
        a, b = edge[e], edge[(e + 1) % len(edge)]
        m.quad([P(*a, 0), P(*b, 0), P(*b, 1), P(*a, 1)], 1, [(e / 24, 0), ((e + 1) / 24, 0), ((e + 1) / 24, 0.05),
                                                           (e / 24, 0.05)])
    return m


def bowl():
    m = Mesh()                                             # white glazed bowl D150 x 62 mm, foot ring D74
    prof = [(0, 0.004), (0.031, 0.004), (0.0335, 0.0), (0.0370, 0.0), (0.0390, 0.006), (0.046, 0.012),
            (0.055, 0.021), (0.063, 0.032), (0.069, 0.043), (0.073, 0.053)] + \
           [(0.0732 + 0.0019 * math.cos(math.radians(a)), 0.0602 + 0.0019 * math.sin(math.radians(a)))
            for a in (-30, 10, 50, 90, 130, 170)] + \
           [(0.0712, 0.0560), (0.0675, 0.0470), (0.0620, 0.0370),
            (0.0545, 0.0270), (0.0450, 0.0180), (0.0330, 0.0120), (0.0180, 0.0095), (0, 0.009)]
    mats = [0] * (len(prof) - 1)
    mats[2] = mats[3] = 1                                  # unglazed foot ring
    m.lathe(prof, mats, uv_metric, n=36)
    for k, (x, y, yaw, tilt) in enumerate(((0.0, 0.0, 0.3, 0.0), (0.020, 0.010, 1.2, 0.18), (-0.019, 0.013, 2.6, -0.2),
                                          (0.004, -0.022, 0.9, -0.18), (-0.017, -0.015, 2.0, 0.2))):
        ca, sa, ct, st = math.cos(yaw), math.sin(yaw), math.cos(tilt), math.sin(tilt)   # white sugar sachets
        z0 = 0.0095 + 0.003 * k + 0.12 * math.hypot(x, y)                               # piled, up the curved floor

        def T(a, b, c, x=x, y=y, z0=z0, ca=ca, sa=sa, ct=ct, st=st):
            a, c = a * ct, c + a * st                                                      # tilt about local y
            return (x + a * ca - b * sa, y + a * sa + b * ca, z0 + c)
        c8 = [T(sx * 0.024, sy * 0.015, sz * 0.003) for sz in (0, 1) for sy in (-1, 1) for sx in (-1, 1)]
        for q in ((0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)):
            m.quad([c8[j] for j in q], 2, [(0, 0), (1, 0), (1, 1), (0, 1)])
    return m


# ================================================================ materials
def img(name, colour=False):
    p = os.path.join(TEX, name)
    im = bpy.data.images.load(p, check_existing=True)
    assert im.size[0] > 0, "missing texture " + p
    im.colorspace_settings.name = "sRGB" if colour else "Non-Color"
    return im


def mat(name):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(b.outputs[0], out.inputs[0])
    return m, nt, b


def uvs(nt, scale=(1, 1, 1)):
    u = nt.nodes.new("ShaderNodeUVMap")
    u.uv_map = "UVMap"
    if scale == (1, 1, 1):
        return u.outputs[0]
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = scale
    nt.links.new(u.outputs[0], mp.inputs[0])
    return mp.outputs[0]


def tex(nt, image, vec):
    t = nt.nodes.new("ShaderNodeTexImage")
    t.image = image
    nt.links.new(vec, t.inputs[0])
    return t.outputs[0]


def nmap(nt, image, vec, strength):
    n = nt.nodes.new("ShaderNodeNormalMap")
    n.uv_map = "UVMap"
    n.inputs[0].default_value = strength
    nt.links.new(tex(nt, image, vec), n.inputs[1])
    return n.outputs[0]


def mathn(nt, op, a, b=0.0, clamp=False):
    n = nt.nodes.new("ShaderNodeMath")
    n.operation, n.use_clamp = op, clamp
    for i, v in enumerate((a, b)):
        if isinstance(v, bpy.types.NodeSocket):
            nt.links.new(v, n.inputs[i])
        else:
            n.inputs[i].default_value = v
    return n.outputs[0]


def bump(nt, h, strength, dist, normal=None):
    n = nt.nodes.new("ShaderNodeBump")
    nt.links.new(h, n.inputs["Height"])
    n.inputs["Strength"].default_value, n.inputs["Distance"].default_value = strength, dist
    if normal is not None:
        nt.links.new(normal, n.inputs["Normal"])
    return n.outputs[0]


def xyz(nt, vec):
    s = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(vec, s.inputs[0])
    return s.outputs


def obj(nt):
    return nt.nodes.new("ShaderNodeTexCoord").outputs["Object"]


def remap(nt, v, a, b, c, d):
    n = nt.nodes.new("ShaderNodeMapRange")
    nt.links.new(v, n.inputs[0])
    for i, x in zip((1, 2, 3, 4), (a, b, c, d)):
        n.inputs[i].default_value = x
    return n.outputs[0]


def set_(b, **kw):
    for k, v in kw.items():
        b.inputs[k.replace("_", " ")].default_value = v


def printed_paper(name, wrap, fibre, circ, height, diffuse):
    """Printed PE-coated cup board: wrap image, real fibre normal/roughness, glue-seam overlap step at u = 0."""
    m, nt, b = mat(name)
    nt.links.new(tex(nt, img(wrap, True), uvs(nt)), b.inputs["Base Color"])
    fv = uvs(nt, (circ / 0.12, height / 0.12, 1))          # fibre scan ~120 mm across
    rough = tex(nt, img(fibre + "_Roughness.jpg"), fv)
    nt.links.new(remap(nt, rough, 0, 1, 0.34, 0.52), b.inputs["Roughness"])
    u = xyz(nt, uvs(nt))[0]
    seam = mathn(nt, "LESS_THAN", u, 0.0045)              # 0.6 mm overlap strip, slightly proud
    nt.links.new(bump(nt, seam, 0.35, 0.0002, nmap(nt, img(fibre + "_NormalGL.jpg"), fv, 0.25)), b.inputs["Normal"])
    set_(b, Coat_Weight=0.18, Coat_Roughness=0.28, Sheen_Weight=0.12, Sheen_Roughness=0.5)
    m.diffuse_color = (*diffuse, 1)


def white_paper(name, plate=False):
    m, nt, b = mat(name)
    v = uvs(nt, (1 / 0.15, 1 / 0.15, 1))
    tint = nt.nodes.new("ShaderNodeMix")
    tint.data_type, tint.blend_type = "RGBA", "MULTIPLY"
    tint.inputs[0].default_value = 1.0
    nt.links.new(tex(nt, img("Paper001_1K-JPG_Color.jpg", True), v), tint.inputs[6])
    tint.inputs[7].default_value = (0.93, 0.93, 0.91, 1)
    nt.links.new(tint.outputs[2], b.inputs["Base Color"])
    nt.links.new(remap(nt, tex(nt, img("Paper001_1K-JPG_Roughness.jpg"), v), 0, 1, 0.45, 0.7), b.inputs["Roughness"])
    n = nmap(nt, img("Paper001_1K-JPG_NormalGL.jpg"), v, 0.3)
    if plate:                                              # fluted rim/wall (~96 flutes) + stacked plate edges
        o = obj(nt)
        x, y, z = xyz(nt, o)
        ang = mathn(nt, "ARCTAN2", y, x)
        flute = mathn(nt, "SINE", mathn(nt, "MULTIPLY", ang, 96.0))
        r = nt.nodes.new("ShaderNodeVectorMath")
        r.operation = "LENGTH"
        sep2 = nt.nodes.new("ShaderNodeCombineXYZ")
        nt.links.new(x, sep2.inputs[0])
        nt.links.new(y, sep2.inputs[1])
        nt.links.new(sep2.outputs[0], r.inputs[0])
        rad = r.outputs["Value"]
        band = mathn(nt, "MULTIPLY", remap(nt, rad, 0.061, 0.066, 0, 1), remap(nt, rad, 0.086, 0.089, 1, 0))
        layers = mathn(nt, "PINGPONG", mathn(nt, "MULTIPLY", z, 1 / 0.0018), 0.5)
        edge = mathn(nt, "MULTIPLY", remap(nt, rad, 0.0895, 0.0903, 0, 1), layers)
        h = mathn(nt, "ADD", mathn(nt, "MULTIPLY", flute, band), mathn(nt, "MULTIPLY", edge, 2.0))
        n = bump(nt, h, 0.5, 0.0003, n)
    nt.links.new(n, b.inputs["Normal"])
    set_(b, Sheen_Weight=0.2, Sheen_Roughness=0.5)
    m.diffuse_color = (0.88, 0.88, 0.86, 1)


def napkin():
    m, nt, b = mat("Tableware_Napkin")
    v = uvs(nt, (1.4, 1.4, 1))                            # crumpled tissue, ~120 mm per tile
    nt.links.new(remap(nt, tex(nt, img("Paper003_1K-JPG_Color.jpg"), v), 0.75, 0.95, 0.78, 0.93), b.inputs["Base Color"])
    nt.links.new(remap(nt, tex(nt, img("Paper003_1K-JPG_Roughness.jpg"), v), 0, 1, 0.75, 0.95), b.inputs["Roughness"])
    nt.links.new(nmap(nt, img("Paper003_1K-JPG_NormalGL.jpg"), v, 0.8), b.inputs["Normal"])
    set_(b, Sheen_Weight=0.35, Sheen_Roughness=0.6, Subsurface_Weight=0.1, Subsurface_Scale=0.002)
    m.diffuse_color = (0.86, 0.86, 0.85, 1)


def lid_ps():
    """White polystyrene lid, satin, faint sink marks, dark sip hole (object coords: (0, -27 mm) on the shelf)."""
    m, nt, b = mat("Tableware_LidPS")
    x, y, z = xyz(nt, obj(nt))
    ax = mathn(nt, "MAXIMUM", mathn(nt, "SUBTRACT", mathn(nt, "ABSOLUTE", x), 0.0045), 0.0)
    ay = mathn(nt, "ADD", y, 0.0275)
    d = mathn(nt, "SQRT", mathn(nt, "ADD", mathn(nt, "MULTIPLY", ax, ax), mathn(nt, "MULTIPLY", ay, ay)))
    hole = mathn(nt, "MULTIPLY", remap(nt, d, 0.0021, 0.0017, 0, 1), remap(nt, z, 0.15, 0.152, 0, 1))
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    nt.links.new(hole, mix.inputs[0])
    mix.inputs[6].default_value = (0.86, 0.86, 0.84, 1)
    mix.inputs[7].default_value = (0.02, 0.018, 0.015, 1)
    nt.links.new(mix.outputs[2], b.inputs["Base Color"])
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 400.0
    nt.links.new(obj(nt), nz.inputs[0])
    nt.links.new(remap(nt, nz.outputs[0], 0.3, 0.7, 0.28, 0.34), b.inputs["Roughness"])
    nt.links.new(bump(nt, mathn(nt, "SUBTRACT", mathn(nt, "MULTIPLY", nz.outputs[0], 0.03), hole), 0.4, 0.001),
                 b.inputs["Normal"])
    set_(b, Subsurface_Weight=0.15, Subsurface_Scale=0.003, Specular_IOR_Level=0.5, IOR=1.59)
    m.diffuse_color = (0.86, 0.86, 0.84, 1)


def ceramic():
    m, nt, b = mat("Tableware_CeramicGlaze")
    v = uvs(nt, (1 / 0.2, 1 / 0.2, 1))
    rough = tex(nt, img("Porcelain001_1K-JPG_Roughness.jpg"), v)
    nt.links.new(remap(nt, rough, 0, 0.12, 0.05, 0.14), b.inputs["Roughness"])
    nz = nt.nodes.new("ShaderNodeTexNoise")               # glaze orange-peel / slight waviness
    nz.inputs["Scale"].default_value = 60.0
    nt.links.new(obj(nt), nz.inputs[0])
    nt.links.new(bump(nt, nz.outputs[0], 0.06, 0.0005), b.inputs["Normal"])
    set_(b, Base_Color=(0.85, 0.85, 0.83, 1), Coat_Weight=1.0, Coat_Roughness=0.03, Coat_IOR=1.52,
         Subsurface_Weight=0.08, Subsurface_Scale=0.004)
    m.diffuse_color = (0.85, 0.85, 0.83, 1)
    m2, nt, b = mat("Tableware_CeramicBisque")              # unglazed foot ring
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 900.0
    nt.links.new(obj(nt), nz.inputs[0])
    nt.links.new(bump(nt, nz.outputs[0], 0.3, 0.0002), b.inputs["Normal"])
    set_(b, Base_Color=(0.72, 0.70, 0.66, 1), Roughness=0.8)
    m2.diffuse_color = (0.72, 0.70, 0.66, 1)
    return m, m2


printed_paper("Kitchen_PaperCupOrange", "cup_orange_wrap.png", "Paper001_1K-JPG", 0.24, 0.133, (0.85, 0.42, 0.06))
printed_paper("Kitchen_PaperCupBrown", "cup_brown_wrap.png", "Paper006_1K-JPG", 0.21, 0.09, (0.30, 0.20, 0.16))
white_paper("Tableware_PaperWhite")
white_paper("Tableware_PaperPlate", plate=True)
napkin()
lid_ps()
glaze, bisque = ceramic()
D = bpy.data.materials
BLACK = D.get("Kitchen_PlasticBlack") or D.new("Kitchen_PlasticBlack")

build("Kitchen_CupLid", orange_cup(), [D["Kitchen_PaperCupOrange"], D["Tableware_PaperWhite"], D["Tableware_LidPS"]])
build("Kitchen_CupPaper", knit_cup(True), [D["Kitchen_PaperCupBrown"], D["Tableware_PaperWhite"], BLACK])
build("Kitchen_PlateStack", plate_stack(), [D["Tableware_PaperPlate"], D["Tableware_Napkin"]])
for nm, mesh, mats, loc, yaw in (
        ("Kitchen_CupPaper2", knit_cup(False), [D["Kitchen_PaperCupBrown"], D["Tableware_PaperWhite"]],
         (1.775, 0.13, TOP), math.radians(-140)),          # empty knit cup behind the stirrer cup (122216)
        ("Kitchen_Bowl", bowl(), [glaze, bisque, D["Tableware_PaperWhite"]], (1.685, 0.30, TOP), 0.0)):   # bowl of sugar sachets (122216)
    fresh = bpy.data.objects.get(nm) is None
    ob = build(nm, mesh, mats, loc, yaw)
    if fresh:
        ob["tw_new"] = True
