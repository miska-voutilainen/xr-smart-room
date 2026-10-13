# Door end of room 1 (photos 122224, 120945, 150319): two white surface-mounted distribution boards
# (Hager Volta VA48CN size, 4 rows x 12 modules, 305 x 640 x 96.5 mm) with 90 x 60 mm PVC ducts up to the
# ceiling, the corner riser above the trunking, the PIR detector in the corner, the A3 EU co-funding notice on
# the partition next to the pillar, and the open cardboard carton on the floor by the pillar.
# Light switch = g1_trim (Trim_Switch). Trunking + its drop below 1.11 m = g1_trim.
# Runs after build_room.py (via apply_materials.py). Standalone, idempotent. Touches only Doorend_* objects.
import math
import os

import bpy

H, D = 2.90, 2.50                              # ceiling (room.py Room_Ceiling underside), partition face y
BOX_W, BOX_H, BOX_D = 0.305, 0.640, 0.0965     # Hager Volta VA48CN (H x W x D 640 x 305 x 96.5)
BOX_Z0 = 1.07                                  # bottom edge (122224: 1.05..1.71 measured)
BOX_Y0 = (0.068, 0.443)                         # left edges on the door wall x = 0 (122224 / 150319)
DUCT_W, DUCT_D = 0.090, 0.060                  # OBO WDK 60090-type wall duct
CORNER_Z0 = 0.98 + 0.13                        # top of g1_trim's 130 mm trunking at 0.98 (trim.py TR_Z0 + TR_H)
POSTER = (0.41, 0.83, 1.25, 1.547)             # A3 landscape on the partition face y = 2.5 (x0, x1, z0, z1)
CARTON = ((0.41, 2.30), -6.0)                  # carton footprint centre and yaw (deg)


# ---------- mesh helpers (same as door.py) ----------

def solid_mesh(solids, holes=()):
    """Boolean-free all-quad manifold union of boxes minus holes."""
    axes = [sorted({round(b[s][a], 5) for b in (*solids, *holes) for s in (0, 1)}) for a in range(3)]

    def inside(p, b):
        return all(b[0][a] < p[a] < b[1][a] for a in range(3))

    def solid(n):
        if any(n[a] < 0 or n[a] >= len(axes[a]) - 1 for a in range(3)):
            return False
        c = [(axes[a][n[a]] + axes[a][n[a] + 1]) / 2 for a in range(3)]
        return any(inside(c, b) for b in solids) and not any(inside(c, b) for b in holes)

    verts, index, faces = [], {}, []

    def vid(p):
        if p not in index:
            index[p] = len(verts)
            verts.append(p)
        return index[p]

    for i in range(len(axes[0]) - 1):
        for j in range(len(axes[1]) - 1):
            for k in range(len(axes[2]) - 1):
                n = (i, j, k)
                if not solid(n):
                    continue
                for a in range(3):
                    b, c = (a + 1) % 3, (a + 2) % 3
                    for step in (1, -1):
                        m = list(n)
                        m[a] += step
                        if solid(m):
                            continue
                        pa = axes[a][n[a] + (step > 0)]
                        b0, b1 = axes[b][n[b]], axes[b][n[b] + 1]
                        c0, c1 = axes[c][n[c]], axes[c][n[c] + 1]
                        quad = [(b0, c0), (b1, c0), (b1, c1), (b0, c1)]
                        if step < 0:
                            quad.reverse()
                        pts = []
                        for qb, qc in quad:
                            p = [0, 0, 0]
                            p[a], p[b], p[c] = pa, qb, qc
                            pts.append(vid(tuple(p)))
                        faces.append(tuple(pts))
    return verts, faces


def rounded_box(center, half, cuts=3, p=3.0):
    """All-quad closed superellipsoid (subdivided cube pushed out to a p-norm shell)."""
    n = cuts + 1
    verts, index, faces = [], {}, []

    def vid(g):
        if g not in index:
            v = [2 * x / n - 1 for x in g]
            r = sum(abs(x) ** p for x in v) ** (1 / p)
            index[g] = len(verts)
            verts.append(tuple(center[a] + half[a] * v[a] / r for a in range(3)))
        return index[g]

    for a in range(3):
        b, c = (a + 1) % 3, (a + 2) % 3
        for side in (0, n):
            for i in range(n):
                for j in range(n):
                    q = [(i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1)]
                    if side == 0:
                        q.reverse()
                    pts = []
                    for qb, qc in q:
                        g = [0, 0, 0]
                        g[a], g[b], g[c] = side, qb, qc
                        pts.append(vid(tuple(g)))
                    faces.append(tuple(pts))
    return verts, faces


def obox(o, u, v, w):
    """Parallelepiped from corner o and edge vectors u, v, w (right-handed u x v . w > 0 -> outward normals)."""
    P = [tuple(o[k] + a * u[k] + b * v[k] + c * w[k] for k in range(3))
         for c in (0, 1) for b in (0, 1) for a in (0, 1)]
    return P, [(0, 2, 3, 1), (4, 5, 7, 6), (0, 1, 5, 4), (1, 3, 7, 5), (3, 2, 6, 7), (2, 0, 4, 6)]


def prism_x(poly, x0, x1):
    """Extrude a CCW (y, z) polygon along +x from x0 to x1 (front cap faces +x)."""
    n = len(poly)
    verts = [(x0, y, z) for y, z in poly] + [(x1, y, z) for y, z in poly]
    faces = [tuple(reversed(range(n))), tuple(n + i for i in range(n))]
    faces += [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
    return verts, faces


def merge(*parts):
    verts, faces = [], []
    for v, f in parts:
        faces += [tuple(i + len(verts) for i in q) for q in f]
        verts += v
    return verts, faces


def coll():
    c = bpy.data.collections.get("Doorend")
    if c is None:
        c = bpy.data.collections.new("Doorend")
        bpy.context.scene.collection.children.link(c)
    return c


def obj(name, groups, smooth=False, bevel=0.0, loc=(0, 0, 0), yaw=0.0):
    """groups = [(mesh data, material), ...] -> one object with per-face material slots."""
    ob = bpy.data.objects.get(name)
    if ob is None:
        me = bpy.data.meshes.get(name) or bpy.data.meshes.new(name)
        ob = bpy.data.objects.new(name, me)
    c = coll()
    for uc in list(ob.users_collection):
        if uc != c:
            uc.objects.unlink(ob)
    if c not in ob.users_collection:
        c.objects.link(ob)
    verts, faces, mids, slots = [], [], [], []
    for (v, f), m in groups:
        if m not in slots:
            slots.append(m)
        faces += [tuple(i + len(verts) for i in q) for q in f]
        mids += [slots.index(m)] * len(f)
        verts += v
    me = ob.data
    me.clear_geometry()
    me.from_pydata(verts, [], faces)
    me.validate()
    me.materials.clear()
    for m in slots:
        me.materials.append(m)
    me.polygons.foreach_set("material_index", mids)
    if smooth or bevel:
        me.shade_smooth()
    if bevel:
        mod = ob.modifiers.get("Doorend_Bevel") or ob.modifiers.new("Doorend_Bevel", "BEVEL")
        mod.width, mod.segments, mod.limit_method = bevel, 2, "ANGLE"
        mod.angle_limit = math.radians(40)
        mod.harden_normals = True
    ob.location = loc
    ob.rotation_euler = (0, 0, math.radians(yaw))
    return ob


# ---------- materials (simple placeholders; group 2 overrides by name) ----------

def mat(name, rgb, rough, noise=0.0):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    m.diffuse_color = (*rgb, 1)
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    out.location = (400, 0)
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (100, 0)
    bsdf.inputs["Base Color"].default_value = (*rgb, 1)
    bsdf.inputs["Roughness"].default_value = rough
    nt.links.new(bsdf.outputs[0], out.inputs["Surface"])
    if noise:   # mottled tone (cardboard fibres)
        tx = nt.nodes.new("ShaderNodeTexNoise")
        tx.location = (-500, 0)
        tx.inputs["Scale"].default_value = 80.0
        tx.inputs["Detail"].default_value = 6.0
        ramp = nt.nodes.new("ShaderNodeValToRGB")
        ramp.location = (-250, 0)
        ramp.color_ramp.elements[0].color = tuple(c * (1 - noise) for c in rgb) + (1,)
        ramp.color_ramp.elements[1].color = tuple(min(1, c * (1 + noise)) for c in rgb) + (1,)
        nt.links.new(tx.outputs["Fac"], ramp.inputs[0])
        nt.links.new(ramp.outputs[0], bsdf.inputs["Base Color"])
    return m


def poster_mat():
    m = mat("Doorend_Poster", (0.86, 0.86, 0.84), 0.55)
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "doorend_poster.png")
    img = bpy.data.images.get("Doorend_Poster")
    if img is None and os.path.exists(path):
        img = bpy.data.images.load(path)
        img.name = "Doorend_Poster"
        img.pack()                       # keep the .blend self-contained
    if img is None:
        print("DOOREND poster texture missing:", path)
        return m
    nt = m.node_tree
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.location = (-300, 0)
    tex.image = img
    uv = nt.nodes.new("ShaderNodeUVMap")
    uv.location = (-500, 0)
    nt.links.new(uv.outputs[0], tex.inputs["Vector"])
    nt.links.new(tex.outputs["Color"], nt.nodes["Principled BSDF"].inputs["Base Color"])
    return m


WHITE = mat("Doorend_Enclosure_White", (0.80, 0.80, 0.77), 0.35)      # RAL 9010 powder-coat / ABS
PVC = mat("Doorend_Duct_PVC", (0.78, 0.78, 0.76), 0.30)               # RAL 9010 PVC duct, PIR housing
YELLOW = mat("Doorend_Sticker_Yellow", (0.95, 0.42, 0.0), 0.35)       # ISO 7010 W012 yellow
PRINT = mat("Doorend_Print_Black", (0.02, 0.02, 0.02), 0.4)
LENS = mat("Doorend_PIR_Lens", (0.62, 0.62, 0.60), 0.45)
CARD = mat("Doorend_Cardboard", (0.40, 0.24, 0.11), 0.85, noise=0.12)  # kraft corrugated board
PAPER = mat("Doorend_Paper", (0.80, 0.80, 0.78), 0.6)
POSTER_M = poster_mat()


# ---------- distribution boards + ducts (door wall x = 0, facing +x) ----------

def triangle(cy, cz, side):
    h = side * math.sqrt(3) / 2
    return [(cy - side / 2, cz - h / 3), (cy + side / 2, cz - h / 3), (cy, cz + 2 * h / 3)]


stickers = []
for k, y0 in enumerate(BOX_Y0):
    y1, z0, z1 = y0 + BOX_W, BOX_Z0, BOX_Z0 + BOX_H
    yc = (y0 + y1) / 2
    fd = BOX_D - 0.011                                      # tub front; door 11 mm, 5 mm inset all round
    body = solid_mesh([((0, y0, z0), (fd, y1, z1)),
                       ((fd, y0 + 0.005, z0 + 0.005), (BOX_D, y1 - 0.005, z1 - 0.005))])
    latch = rounded_box((BOX_D + 0.003, y1 - 0.030, z0 + BOX_H * 0.5 - 0.01), (0.004, 0.013, 0.018), 2, 2.2)
    xs = BOX_D + 0.0002                                     # stickers 0.2 mm proud of the door
    label = solid_mesh([((BOX_D, y0 + 0.020, z1 - 0.030), (xs, y0 + 0.020 + (0.026 if k == 0 else 0.016), z1 - 0.024))])
    groups = [(body, WHITE), (latch, WHITE)]
    stickers.append((label, PRINT))
    if k == 0:   # ISO 7010 W012 electricity warning triangle, 60 mm, top right of the left board (150319)
        tc = (y1 - 0.042, z1 - 0.042)
        bolt = [(0.004, 0.016), (-0.006, -0.001), (-0.0005, -0.001), (-0.004, -0.014),
                (0.006, 0.004), (0.0005, 0.004)]
        stickers.extend([(prism_x(triangle(*tc, 0.060), BOX_D, xs), PRINT),
                         (prism_x(triangle(*tc, 0.050), xs, xs + 0.0002), YELLOW),
                         (prism_x([(tc[0] + a, tc[1] - 0.002 + b) for a, b in bolt], xs + 0.0002, xs + 0.0004), PRINT)])
    obj(f"Doorend_Board_{k + 1}", groups, bevel=0.002)   # < half the 5 mm door inset: no collapsed bevels

    # duct from the board top to the ceiling, cover with two grip grooves
    d0, d1 = yc - DUCT_W / 2, yc + DUCT_W / 2
    duct = solid_mesh([((0, d0, z1), (DUCT_D, d1, H))],
                      [((DUCT_D - 0.0015, d0 + 0.006, z1 - 0.01), (DUCT_D + 0.01, d0 + 0.008, H + 0.01)),
                       ((DUCT_D - 0.0015, d1 - 0.008, z1 - 0.01), (DUCT_D + 0.01, d1 - 0.006, H + 0.01))])
    obj(f"Doorend_Duct_{k + 1}", [(duct, PVC)], bevel=0.0006)   # grooves are 2 mm wide

obj("Doorend_Board_Labels", stickers)   # circuit labels + W012 triangle, flat, unbevelled

# corner riser on the cabinet wall (y = 0, facing +y) from g1_trim's trunking up to the ceiling,
# same 80 x 40 section as trim's drop below the trunking (122224, 150319)
riser = solid_mesh([((0.01, 0, CORNER_Z0), (0.09, 0.04, H))],
                   [((0.016, 0.0385, CORNER_Z0 - 0.01), (0.018, 0.05, H + 0.01)),
                    ((0.082, 0.0385, CORNER_Z0 - 0.01), (0.084, 0.05, H + 0.01))])
obj("Doorend_Duct_Corner", [(riser, PVC)], bevel=0.0006)

# PIR motion detector high on the cabinet wall next to the riser (150319, 122224): ~62 x 95 x 45 mm
pir = rounded_box((0.140, 0.0225, 2.745), (0.031, 0.0225, 0.0475), 3, 4.0)
lens = rounded_box((0.140, 0.043, 2.758), (0.022, 0.004, 0.024), 2, 3.0)
obj("Doorend_PIR", [(pir, PVC), (lens, LENS)], smooth=True)

# ---------- A3 co-funding notice on the partition (y = 2.5 face, facing -y) ----------

px0, px1, pz0, pz1 = POSTER
sheet = solid_mesh([((px0, D - 0.0008, pz0), (px1, D, pz1))])
po = obj("Doorend_Poster", [(sheet, POSTER_M)])
me = po.data
uvl = me.uv_layers.get("UVMap") or me.uv_layers.new(name="UVMap")
for loop in me.loops:
    x, _, z = me.vertices[loop.vertex_index].co
    uvl.data[loop.index].uv = ((x - px0) / (px1 - px0), (z - pz0) / (pz1 - pz0))

# ---------- carton on the floor by the pillar (122224): RSC 330 x 300 x 260, flaps open ----------

L, Wd, Hc, t = 0.25, 0.32, 0.24, 0.004          # along local x (front faces +x), along y, height, board
hx, hy = L / 2, Wd / 2
shell = solid_mesh([((-hx, -hy, 0), (hx, hy, Hc))], [((-hx + t, -hy + t, t), (hx - t, hy - t, Hc + 0.01))])


def flap(edge, ang):
    """Flap on a top edge ('x+','x-','y+','y-'); ang = tilt from vertical, + outward (90 = flat outward)."""
    sg = 1 if edge[1] == "+" else -1
    n = (sg, 0, 0) if edge[0] == "x" else (0, sg, 0)
    e = (0, 1, 0) if edge[0] == "x" else (1, 0, 0)
    span, depth = (Wd, Wd / 2) if edge[0] == "x" else (L, L / 2)  # RSC flaps: half the box width deep
    c, s = math.cos(math.radians(ang)), math.sin(math.radians(ang))
    o = (n[0] * hx - e[0] * hx, n[1] * hy - e[1] * hy, Hc)
    u = tuple(span * k for k in e)
    v = tuple(depth * (c * z + s * k) for k, z in zip(n, (0, 0, 1)))
    w = tuple(t * (-c * k + s * z) for k, z in zip(n, (0, 0, 1)))
    cr = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
    if sum(cr[k] * w[k] for k in range(3)) < 0:
        u, v = v, u
    return obox(o, u, v, w)


sheet_in = obox((-0.09, -0.12, 0.05), (0.0, 0.21, 0.0), (0.05, 0.0, 0.24), (0.002, 0, 0))   # papers inside
obj("Doorend_Carton", [(shell, CARD), (flap("x-", -4), CARD), (flap("x+", 105), CARD),
                       (flap("y-", 50), CARD), (flap("y+", -6), CARD), (sheet_in, PAPER)],
    bevel=0.0015, loc=(*CARTON[0], 0), yaw=CARTON[1])

print("DOOREND OK")
