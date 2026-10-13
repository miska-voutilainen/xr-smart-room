# Room 2: the lab beyond the wide passage in the partition y=2.5 (the corridor stub moved to room3_entrance.py).
# Standalone and idempotent; runs after build_room.py + room.py, chair.py, radiator.py (via apply_materials.py).
# Objects Room2_*, collection Room2. Layout from Photos/3 (151011..151124, all of the lab) cross-checked with Photos/1
# 122209/122224/122228 and Photos/2 150435 (see the ASSUMPTIONS block).
# Meshes are built in world space (origin 0) from boxes / prisms / quad-capped cylinders, every face gets a UV
# (box projection in metres, or 0..1 for screens, keycaps and the demo-board photos): see obj().
# Room-1 products are reused, not copied: the window (Window_Frame/Glass/Sill/Reveal) is instanced as is; the
# MS-140 radiator and the ISO chair are instanced from one decimated copy each of Radiator / Chair_Mesh
# (Room2_LOD_*, rebuilt every run from the room-1 mesh, ~30 % of its tris: 4 radiators + 9 chairs at full
# resolution alone would be 55k tris, the lab budget is 60k).
# Props, textured materials and the board-photo relief live in materials/_room2_props.py; images in
# textures/s1_lab (made by materials/_room2_textures.py, CC0 maps listed in textures/s1_lab/SOURCES.txt).
import importlib
import math
import os
import random
import sys

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _room2_props as props  # noqa: E402
importlib.reload(props)

# ---------- room 1 constants (build_room.py) ----------
W, D, H = 6.50, 2.50, 2.90
T, T_TOP, T_WIN = 0.10, 0.12, 0.10
Y0 = D + T_TOP                       # 2.62: lab side face of the partition

# ---------- ASSUMPTIONS (photo estimates, no plan of room 2 exists) ----------
# The lab is a CORNER room: west wall on the corridor wall line x=0 (wall bench with boards 5/4, 151018/151040),
# east facade x=6.5 shared with room 1 (windows E2 with board 1 beside it, E1 with the dual-monitor desk; 122209,
# 150435, 151022, 151033, 151124), north facade y=9.0 (windows N1 with a desk, N2 with board 3, board 2 at the NE
# corner; 151011, 151025, 151124). Depth 6.4 m from the partition, from the run of benches along the west wall.
Y1 = 9.00
WIN_Z0, WIN_Z1 = 0.85, 2.75                      # room-1 window module (sill 0.85, head 2.75), 1.6 m wide
# (wall, start, end, blind bottom z): 'N' runs along x at y=Y1, 'E' along y at x=W. Same 1.6 m product as room 1
# (3 lower lights with a centre sash, transom, 3 top lights: 122209 vs 151022). Blinds 1/3 .. 2/3 down (Photos/3).
LAB_WINDOWS = [("N", 0.70, 2.30, 1.50), ("N", 2.80, 4.40, 2.12), ("E", 7.05, 8.65, 1.50), ("E", 4.95, 6.55, 2.12)]
WIN_IDS = ["N1", "N2", "E1", "E2"]
R1_WIN_YC = 1.00                                 # room-1 window centre (window.py WIN_Y0..WIN_Y1 = 0.2..1.8, x = W)

GX0, GY0, CELL = 0.25, 0.35, 0.60
P = "Room2_"


# ---------- mesh helpers ----------

def box(lo, hi):
    return props.bx(lo, hi)


def solid_mesh(solids, holes=()):
    """Boolean-free union of boxes minus holes -> one manifold all-quad mesh (copied from build_room.py)."""
    axes = [sorted({round(b[s][a], 4) for b in (*solids, *holes) for s in (0, 1)}) for a in range(3)]

    def inside(p, b):
        return all(b[0][a] < p[a] < b[1][a] for a in range(3))

    def solid(i, j, k):
        n = (i, j, k)
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

    nx, ny, nz = (len(a) - 1 for a in axes)
    for i in range(nx):
        for j in range(ny):
            for k in range(nz):
                if not solid(i, j, k):
                    continue
                n = (i, j, k)
                for a in range(3):
                    b, c = (a + 1) % 3, (a + 2) % 3
                    for step in (1, -1):
                        m = list(n)
                        m[a] += step
                        if solid(*m):
                            continue
                        pa = axes[a][n[a] + (1 if step > 0 else 0)]
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


cyl = props.cyl


class Mesh:
    """Accumulates parts with a material slot (int index, or a key of MAT) and optional per-face UVs;
    T = local->world matrix for the next adds."""
    def __init__(self):
        self.v, self.f, self.m, self.uv = [], [], [], []
        self.T = Matrix.Identity(4)

    def add(self, vf, mi=0, uv=None):
        v, f = vf
        b = len(self.v)
        self.v += [tuple(self.T @ Vector(p)) for p in v]
        self.f += [tuple(i + b for i in q) for q in f]
        self.m += [mi] * len(f)
        self.uv += list(uv) if uv else [None] * len(f)

    def box(self, lo, hi, mi=0):
        self.add(box(lo, hi), mi)

    def solid(self, boxes, mi=0, holes=()):
        self.add(solid_mesh(boxes, holes), mi)


def frame(x, y, rz_deg=0.0, z=0.0):
    return Matrix.Translation((x, y, z)) @ Matrix.Rotation(math.radians(rz_deg), 4, 'Z')


# ---------- scene helpers ----------

def wipe():
    c = bpy.data.collections.get("Room2")
    if c:
        for o in list(c.objects):
            bpy.data.objects.remove(o, do_unlink=True)
    else:
        c = bpy.data.collections.new("Room2")
        bpy.context.scene.collection.children.link(c)
    for coll in (bpy.data.meshes, bpy.data.lights):
        for d in list(coll):
            if d.name.startswith(P) and d.users == 0:
                coll.remove(d)
    return c


def mat(name, rgb, rough=0.5, metal=0.0, emit=0.0, alpha=1.0, transmission=0.0):
    """Simple placeholder Principled material (group 2 overrides by name). Shared room materials are reused, not made."""
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.diffuse_color = (*rgb, 1)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    o = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(b.outputs[0], o.inputs[0])
    b.inputs["Base Color"].default_value = (*rgb, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    b.inputs["Transmission Weight"].default_value = transmission
    if emit:
        b.inputs["Emission Color"].default_value = (*rgb, 1)
        b.inputs["Emission Strength"].default_value = emit
    if alpha < 1:
        b.inputs["Alpha"].default_value = alpha
    return m


def shared(name, rgb):
    return bpy.data.materials.get(name) or mat(P + name, rgb)


def box_uv(pts):
    """Per-face box projection in metres: drop the dominant normal axis (Unity-ready UVs, tiling maps)."""
    n = Vector()
    for k in range(len(pts)):
        n += pts[k].cross(pts[(k + 1) % len(pts)])
    a = max(range(3), key=lambda i: abs(n[i]))
    b, c = ((1, 2), (0, 2), (0, 1))[a]
    return [(p[b], p[c]) for p in pts]


def obj(name, mesh, mats, coll):
    """mats: list (mesh.m holds indices) or None (mesh.m holds MAT keys; only the used ones become slots)."""
    if mats is None:
        keys = list(dict.fromkeys(mesh.m))
        mats, idx = [MAT[k] for k in keys], [keys.index(k) for k in mesh.m]
    else:
        idx = mesh.m
    me = bpy.data.meshes.new(P + name)
    me.from_pydata(mesh.v, [], mesh.f)
    for m in mats:
        me.materials.append(m)
    me.polygons.foreach_set("material_index", idx)
    uvs = []
    for f, uv in zip(mesh.f, mesh.uv):
        uvs += uv if uv else box_uv([Vector(mesh.v[i]) for i in f])
    me.uv_layers.new(name="UVMap").data.foreach_set("uv", [x for p in uvs for x in p])
    me.validate()
    ob = bpy.data.objects.new(P + name, me)
    coll.objects.link(ob)
    return ob


def inst(name, data, mw):
    """Object sharing room-1 mesh data `data` (world-space verts) moved by world matrix mw."""
    ob = bpy.data.objects.new(P + name, data)
    ob.matrix_world = mw
    coll.objects.link(ob)
    return ob


def lod(src, ratio, name):
    """Decimated copy of mesh datablock `src` (same materials, UVs) for instancing in the lab."""
    tmp = bpy.data.objects.new(P + "tmp_lod", src)
    coll.objects.link(tmp)
    d = tmp.modifiers.new("lod", 'DECIMATE')
    d.ratio = ratio
    dg = bpy.context.evaluated_depsgraph_get()
    dg.update()
    me = bpy.data.meshes.new_from_object(tmp.evaluated_get(dg))
    me.name = P + name
    bpy.data.objects.remove(tmp, do_unlink=True)
    return me


# ---------- furniture builders (local frame: u = +x length, v = +y depth, front edge at v=0) ----------

# chair placement bookkeeping (floor plan, world xy): table front edges, obstacles chairs must not touch, seats
TABLES, OBST, SEATS = [], [], []


def rect2(M, x0, y0, x1, y1):
    return [(M @ Vector((x, y, 0))).xy for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1))]


def table(m, L, Dp, legs):
    TABLES.append((m.T.copy(), L))
    OBST.extend(rect2(m.T, *r) for r in legs)


def seats(us, kind="iso"):
    """Chairs at the current table (fm.T) front edge, one per u (workstation centre along the edge)."""
    SEATS.extend((fm.T.copy(), u, kind) for u in us)


def bench(m, L, Dp, h, top, fr):
    """Lab bench: 25 mm top, two welded rectangular end frames (60x30 tube, sled foot), back beam."""
    m.box((0, 0, h - 0.025), (L, Dp, h), top)
    table(m, L, Dp, [(u, 0.06, u + 0.06, Dp - 0.06) for u in (0.06, L - 0.12)])
    for u in (0.06, L - 0.12):
        m.solid([((u, 0.06, 0.0), (u + 0.06, Dp - 0.06, 0.035)),              # sled foot
                 ((u, 0.09, 0.035), (u + 0.06, 0.12, h - 0.065)),              # front post
                 ((u, Dp - 0.15, 0.035), (u + 0.06, Dp - 0.12, h - 0.065)),    # back post
                 ((u, 0.06, h - 0.065), (u + 0.06, Dp - 0.06, h - 0.025))], fr)   # top rail
        for v in (0.07, Dp - 0.10):                                            # levelling glides
            m.box((u + 0.01, v, -0.001), (u + 0.05, v + 0.03, 0.002), "abs_black")
    m.box((0.12, Dp - 0.15, h - 0.10), (L - 0.12, Dp - 0.12, h - 0.04), fr)


def pedestal(m, u0, n, height):
    """Mobile drawer pedestal W426 x D550, red fronts with bar handles, 4 castors (Hope/Findel, Kaiserkraft)."""
    w, dp, c = 0.426, 0.55, 0.06
    OBST.append(rect2(m.T, u0, 0.015, u0 + w, 0.03 + dp))
    m.box((u0, 0.03, c), (u0 + w, 0.03 + dp, height), "red")
    hd = (height - c - 0.01) / n
    for i in range(n):
        z0 = c + 0.005 + i * hd
        m.box((u0 + 0.004, 0.015, z0 + 0.003), (u0 + w - 0.004, 0.03, z0 + hd - 0.003), "red")
        zh = z0 + hd - 0.045
        m.solid([((u0 + w / 2 - 0.08, -0.012, zh), (u0 + w / 2 + 0.08, -0.002, zh + 0.012)),
                 ((u0 + w / 2 - 0.08, -0.002, zh), (u0 + w / 2 - 0.07, 0.015, zh + 0.012)),
                 ((u0 + w / 2 + 0.07, -0.002, zh), (u0 + w / 2 + 0.08, 0.015, zh + 0.012))], "alu")
    if n > 1:
        m.box((u0 + w - 0.06, 0.010, height - 0.035), (u0 + w - 0.035, 0.015, height - 0.010), "alu")   # lock
    for cu in (u0 + 0.045, u0 + w - 0.045):
        for cv in (0.08, dp - 0.02):
            m.box((cu - 0.02, cv - 0.02, c - 0.012), (cu + 0.02, cv + 0.02, c), "abs_black")           # castor plate
            m.add(cyl((cu - 0.012, cv, 0.024), (cu + 0.012, cv, 0.024), 0.024, 8), "abs_black")       # wheel


def profile_frame(m, u0, u1, v0, v1, z0, z1, mi="alu", s=0.04):
    """Cube frame of 40x40 aluminium profile (item/Bosch slot 8 style), unioned into one manifold mesh."""
    bars = []
    for u in (u0, u1 - s):
        for v in (v0, v1 - s):
            bars.append(((u, v, z0), (u + s, v + s, z1)))
    for z in (z0, z1 - s):
        for v in (v0, v1 - s):
            bars.append(((u0, v, z), (u1, v + s, z + s)))
        for u in (u0, u1 - s):
            bars.append(((u, v0, z), (u + s, v1, z + s)))
    m.solid(bars, mi)


def desk(m, L, Dp, h, top, fr="steel"):
    """Lab/school desk (151011, 150435): 25 mm laminate top, welded end frames of 50 mm square tube (legs, top rail,
    floor rail), a longitudinal knee-height stretcher and a top apron, plastic glides."""
    m.box((0, 0, h - 0.025), (L, Dp, h), top)
    table(m, L, Dp, [(u, v, u + 0.05, v + 0.05) for u in (0.02, L - 0.07) for v in (0.02, Dp - 0.07)])
    for u in (0.02, L - 0.07):
        m.solid([((u, 0.02, 0.012), (u + 0.05, 0.07, h - 0.025)),
                 ((u, Dp - 0.07, 0.012), (u + 0.05, Dp - 0.02, h - 0.025)),
                 ((u + 0.005, 0.07, 0.012), (u + 0.045, Dp - 0.07, 0.052)),
                 ((u, 0.07, h - 0.085), (u + 0.05, Dp - 0.07, h - 0.025))], fr)
        for v in (0.02, Dp - 0.07):
            m.box((u + 0.004, v + 0.004, 0), (u + 0.046, v + 0.046, 0.012), "abs_black")
    m.box((0.07, Dp / 2 - 0.015, h - 0.085), (L - 0.07, Dp / 2 + 0.015, h - 0.025), fr)
    m.box((0.07, Dp / 2 - 0.015, 0.30), (L - 0.07, Dp / 2 + 0.015, 0.34), fr)


# ---------- build ----------

coll = wipe()
WALL = shared("Room_Wall", (0.85, 0.85, 0.83))
FLOOR = shared("Room_Floor", (0.55, 0.54, 0.52))
CEIL = shared("Room_Ceiling", (0.78, 0.78, 0.77))
MAT = {
    "pvc": mat(P + "PVC_White", (0.92, 0.92, 0.91), 0.35),
    "blind": mat(P + "Blind_Fabric", (0.48, 0.48, 0.47), 0.9),
    "alu": mat(P + "Aluminium", (0.80, 0.81, 0.82), 0.3, 1.0),
    "chrome": mat(P + "Chrome", (0.9, 0.9, 0.9), 0.1, 1.0),
    "white": mat(P + "Plastic_White", (0.88, 0.88, 0.87), 0.4),
    "grey": mat(P + "Plastic_Grey", (0.55, 0.56, 0.56), 0.4),
    "black": mat(P + "Plastic_Black", (0.025, 0.025, 0.025), 0.45),
    "glass": mat(P + "Glass", (0.95, 0.97, 0.97), 0.0, transmission=1.0),
    "yellow": mat(P + "Plastic_Yellow", (0.85, 0.65, 0.02), 0.4),
    "red_badge": mat(P + "Plastic_Red", (0.70, 0.02, 0.02), 0.3),
    "led": mat(P + "LED_Diffuser", (1.0, 0.95, 0.90), 0.5, emit=6.0),
    "card": mat(P + "Cardboard", (0.55, 0.40, 0.25), 0.8),
    "off": shared("TV_Screen", (0.01, 0.01, 0.012)),          # switched-off panels: room-1 TV glass (hard.py screen_off)
    "pipe": shared("Radiator_PipePaint", (0.85, 0.85, 0.83)),
    "cup": shared("Kitchen_PaperCupBrown", (0.45, 0.30, 0.18)),           # same cups / bottle as the kitchenette
    "bottle": shared("Kitchen_PET", (0.8, 0.85, 0.9)),
}
MAT.update(props.materials(P))
for n in (1, 2, 3, 5):
    MAT["board%d" % n] = props.board_material(P, n)
S = {k: k for k in MAT}                                         # props builders take slot keys


def wall_frame(wall, a, b):
    """Local window frame: u along the wall from 0 to b-a, v = 0 on the interior face, +v outward, room at v<0."""
    return frame(a, Y1, 0) if wall == "N" else frame(W, b, -90)


def r1_to_lab(wall, a, b):
    """World matrix taking room-1 window-wall geometry (interior face x=W, window centred y=R1_WIN_YC) to a lab
    window: east = shift along y, north = +90 deg about z (room-1 inward -x -> lab inward -y)."""
    c = (a + b) / 2
    if wall == "E":
        return Matrix.Translation((0, c - R1_WIN_YC, 0))
    return Matrix.Translation((c + R1_WIN_YC, Y1 - W, 0)) @ Matrix.Rotation(math.pi / 2, 4, 'Z')


# --- shell: floor, ceiling, walls (the lab side face of the partition already exists in Wall_Top) ---
m = Mesh(); m.box((-T, Y0, -0.10), (W + T_WIN, Y1 + T, 0)); obj("Floor", m, [FLOOR], coll)
m = Mesh(); m.box((-T, Y0, H), (W + T_WIN, Y1 + T, H + 0.10)); obj("Ceiling", m, [CEIL], coll)
m = Mesh(); m.box((-T, Y0, 0), (0, Y1 + T, H)); obj("Wall_Left", m, [WALL], coll)
m = Mesh()
m.solid([((0, Y1, 0), (W, Y1 + T, H))], 0, [((a, Y1, WIN_Z0), (b, Y1 + T, WIN_Z1)) for w, a, b, _ in LAB_WINDOWS if w == "N"])
obj("Wall_North", m, [WALL], coll)
m = Mesh()
m.solid([((W, Y0, 0), (W + T_WIN, Y1 + T, H))], 0, [((W, a, WIN_Z0), (W + T_WIN, b, WIN_Z1)) for w, a, b, _ in LAB_WINDOWS if w == "E"])
obj("Wall_East", m, [WALL], coll)

# --- windows: room-1 Window_Frame / Glass / Sill / Reveal instanced per opening (Room2_Window_<id> = frame, the
#     light-portal reference in render/light.py), roller blinds, MS-140 radiators (decimated room-1 Radiator) ---
rad_lod = lod(bpy.data.objects["Radiator"].data, 0.3, "LOD_Radiator")
for k in ("Window_Glass", "Window_Reveal"):
    # Fresh rebuilds: build_room.py makes no glass/reveal objects, materials/window.py (runs after this script)
    # creates them with get_obj(), which reuses an existing object + mesh of that name and writes the geometry in
    # place, so the lab instances made here pick up the real window once window.py has run.
    if k not in bpy.data.objects:
        me = bpy.data.meshes.get(k) or bpy.data.meshes.new(k)
        bpy.data.collections["Openings"].objects.link(bpy.data.objects.new(k, me))
src = {k: bpy.data.objects[k] for k in ("Window_Frame", "Window_Glass", "Window_Sill", "Window_Reveal", "Radiator")}
rb = [src["Radiator"].matrix_world @ Vector(c) for c in src["Radiator"].bound_box]
RX = (min(c.x for c in rb) + max(c.x for c in rb)) / 2                    # hub plane, near (pipe) end of the radiator
RY0 = min(c.y for c in rb)
mp = Mesh()
for wid, (wall, a, b, zb) in zip(WIN_IDS, LAB_WINDOWS):
    mw = r1_to_lab(wall, a, b)
    inst(f"Window_{wid}", src["Window_Frame"].data, mw @ src["Window_Frame"].matrix_world)
    inst(f"WinGlass_{wid}", src["Window_Glass"].data, mw @ src["Window_Glass"].matrix_world).visible_shadow = False
    inst(f"WinSill_{wid}", src["Window_Sill"].data, mw @ src["Window_Sill"].matrix_world)
    inst(f"WinReveal_{wid}", src["Window_Reveal"].data, mw @ src["Window_Reveal"].matrix_world)
    inst(f"Radiator_{wid}", rad_lod, mw @ src["Radiator"].matrix_world)
    mp.T = mw                                                              # supply/return branches + riser
    for z in (0.14, 0.64):
        mp.add(cyl((RX, RY0 + 0.01, z), (RX, RY0 - 0.18, z), 0.0134, 8), "pipe")
    mp.add(cyl((RX, RY0 - 0.18, 0.0), (RX, RY0 - 0.18, H), 0.0168, 8), "pipe")
    # roller blind: cassette on the wall above the opening, grey fabric down to zb, bottom bar
    L = b - a
    mb = Mesh()
    mb.T = wall_frame(wall, a, b)
    mb.box((-0.06, -0.10, WIN_Z1 + 0.01), (L + 0.06, 0, WIN_Z1 + 0.10), 1)
    mb.box((-0.03, -0.06, zb), (L + 0.03, -0.055, WIN_Z1 + 0.01), 0)
    mb.box((-0.03, -0.065, zb - 0.02), (L + 0.03, -0.05, zb), 1)
    obj(f"Blind_{wid}", mb, [MAT["blind"], MAT["pvc"]], coll)
mp.T = Matrix.Identity(4)
obj("Radiator_Pipes", mp, None, coll)

# --- ceiling: 600x600 LED panels in the grid, 4-way compact AC cassettes (Daikin FFA: 575 body, 620x620 panel),
#     one 2-tile linear return grille (151025, 151124) ---
# One object per panel, origin at the panel centre on the ceiling plane (lighting/Unity contract: Room2_LED_Panel_*).
# No lab lights are made here: render/light.py generates them from these panels and the Room2_Window_* objects.
for n, (i, j) in enumerate([(i, j) for i in (2, 5, 8) for j in (5, 8, 11)] + [(2, 13), (8, 13)]):
    led, h = Mesh(), CELL / 2
    led.box((-h + 0.003, -h + 0.003, -0.012), (h - 0.003, h - 0.003, 0), 1)
    led.box((-h + 0.02, -h + 0.02, -0.014), (h - 0.02, h - 0.02, -0.012), 0)
    obj(f"LED_Panel_{n + 1:02d}", led, [MAT["led"], MAT["alu"]], coll).location = (GX0 + (i + 0.5) * CELL, GY0 + (j + 0.5) * CELL, H)
ac = Mesh()
for i, j in ((4, 4), (3, 9), (6, 11)):
    ax, ay = GX0 + i * CELL + CELL / 2, GY0 + j * CELL + CELL / 2
    ac.T = Matrix.Identity(4)
    ac.box((ax - 0.31, ay - 0.31, H - 0.046), (ax + 0.31, ay + 0.31, H), 0)
    ac.box((ax - 0.16, ay - 0.16, H - 0.048), (ax + 0.16, ay + 0.16, H - 0.046), 1)            # intake grille
    for q in range(4):                                                                          # 4 louvred outlets
        ac.T = Matrix.Translation((ax, ay, 0)) @ Matrix.Rotation(q * math.pi / 2, 4, 'Z')
        ac.box((-0.20, 0.215, H - 0.048), (0.20, 0.265, H - 0.046), 2)
ac.T = Matrix.Identity(4)
gx, gy = GX0 + 3 * CELL, GY0 + 7 * CELL
ac.box((gx + 0.01, gy + 0.18, H - 0.01), (gx + 2 * CELL - 0.01, gy + 0.42, H), 0)
ac.box((gx + 0.03, gy + 0.20, H - 0.012), (gx + 2 * CELL - 0.03, gy + 0.40, H - 0.01), 2)
obj("AC_Cassettes", ac, [MAT["white"], MAT["grey"], MAT["black"]], coll)

# ---------- furniture (fm), IT + instruments (im), demo boards (bm) ----------
fm, im, bm = Mesh(), Mesh(), Mesh()


def at(*args):
    fm.T = im.T = bm.T = frame(*args)


def west(y_start, depth=0.75):        # front edge at x=depth facing +x, u along +y
    at(depth, y_start, 90)


def north(x_start, depth=0.75, gap=0.25):   # front edge facing -y, back gap left for the radiators
    at(x_start, Y1 - gap - depth, 0)


def east(y_end, depth=0.75, gap=0.25):      # front edge facing -x, u along -y from y_end
    at(W - gap - depth, y_end, -90)


def board(u0, u1, v, z0, z1, n, rects, depth=0.45):
    """Demo board n on its 40x40 profile cube: panel front at v, frame behind it (no bars in front)."""
    profile_frame(fm, u0, u1, v + 0.012, v + depth, z0 - 0.04, z1)
    props.demo_board(bm, S, u0, u1, v, z0, z1, "board%d" % n, rects, depth)


def cable(pts, r=0.0035):
    im.add(props.tube(pts, r), "abs_black")


def drape(u0, v0, u, floor):
    """Device cable from (u0, v0) on a 0.75 m desk top over the front edge at u, hanging to the floor, then `floor`."""
    cable([(u0, v0, 0.754), (u + 0.02, v0 - 0.03, 0.754), (u, 0.03, 0.754), (u, -0.006, 0.752), (u, -0.016, 0.735),
           (u + 0.005, -0.02, 0.55), (u + 0.015, -0.02, 0.30), (u + 0.03, -0.01, 0.10), (u + 0.06, 0.04, 0.012)] + floor)


# demo-board relief: (x0, y0, x1, y1, depth) photo fractions from the top-left of textures/s1_lab/board_<n>.jpg
B1 = [(0.31, 0.04, 0.70, 0.13, 0.05), (0.01, 0.31, 0.45, 0.46, 0.02), (0.0, 0.49, 0.89, 0.61, 0.055),
      (0.02, 0.66, 0.08, 0.74, 0.05), (0.27, 0.68, 0.39, 0.78, 0.015), (0.76, 0.07, 0.83, 0.15, 0.035),
      (0.86, 0.22, 0.94, 0.31, 0.03), (0.76, 0.67, 0.82, 0.80, 0.015), (0.88, 0.68, 0.94, 0.80, 0.015),
      (0.87, 0.86, 0.94, 0.97, 0.05)]
B2 = [(0.26, 0.04, 0.61, 0.18, 0.05), (0.15, 0.49, 0.66, 0.61, 0.055), (0.0, 0.50, 0.97, 0.58, 0.012),
      (0.73, 0.71, 0.81, 0.78, 0.015), (0.85, 0.70, 0.93, 0.82, 0.015)]
B3 = [(0.21, 0.09, 0.30, 0.17, 0.06), (0.17, 0.50, 0.69, 0.61, 0.055), (0.0, 0.53, 1.0, 0.57, 0.012),
      (0.04, 0.68, 0.09, 0.75, 0.05), (0.06, 0.80, 0.19, 0.92, 0.02), (0.23, 0.78, 0.29, 0.94, 0.025),
      (0.75, 0.22, 0.84, 0.33, 0.03), (0.53, 0.40, 0.58, 0.47, 0.04), (0.69, 0.38, 0.74, 0.46, 0.04),
      (0.76, 0.05, 0.82, 0.17, 0.03), (0.89, 0.22, 0.95, 0.31, 0.03)]
B5 = [(0.10, 0.53, 0.25, 0.63, 0.04), (0.50, 0.48, 1.0, 0.56, 0.05), (0.08, 0.69, 0.20, 0.77, 0.05),
      (0.20, 0.69, 0.31, 0.78, 0.04), (0.60, 0.68, 0.71, 0.80, 0.05), (0.55, 0.88, 0.71, 0.98, 0.05),
      (0.70, 0.03, 1.0, 0.10, 0.06), (0.58, 0.35, 0.97, 0.42, 0.04)]

# West wall run (151018, 151040, 122228): bench 1 with instrument shelf + lamp bar + one 3-drawer pedestal,
# bench 2 with board "5" on a 40x40 profile cube + three 4-drawer pedestals, a light grey desk with an LG
# monitor, bench with board "4" (no usable photo of its face: board 3's).
LA, DA, HA = 1.60, 0.75, 0.78
west(2.75)
bench(fm, LA, DA, HA, "laminate", "steel")
pedestal(fm, 0.14, 3, 0.62)
for u in (0.08, LA - 0.12):
    fm.box((u, DA - 0.06, HA), (u + 0.04, DA - 0.02, 1.97), "steel")
    fm.box((u, 0.30, 1.90), (u + 0.04, DA - 0.06, 1.94), "steel")
fm.box((0.0, DA - 0.36, 1.22), (LA, DA - 0.02, 1.245), "laminate")
fm.box((-0.10, 0.26, 1.88), (LA + 0.25, 0.32, 1.92), "alu")                                   # LED task light bar
fm.box((-0.08, 0.27, 1.875), (LA + 0.23, 0.31, 1.88), "white")
s = 1.245                                                                                     # shelf instruments
FULL = props.rect((0, 0, 1, 1))                                                              # fronts = photo crops
props.face_split(im, props.bx((0.15, DA - 0.33, s), (0.47, DA - 0.18, s + 0.16)), "inst_scope", "abs_white", 2, FULL)
for q, img in enumerate(("inst_dmm2", "inst_dmm1")):                                          # 2 GW Instek DMMs
    props.face_split(im, props.bx((0.52, DA - 0.33, s + q * 0.105), (0.80, DA - 0.06, s + q * 0.105 + 0.1)),
                     img, "abs_white", 2, FULL)
im.box((0.84, DA - 0.31, s), (1.04, DA - 0.11, s + 0.15), "abs_white")
im.box((1.12, DA - 0.30, s), (1.40, DA - 0.08, s + 0.07), "abs_grey")
props.lcd(im, S, 1.05, DA - 0.25, HA, 0.48, "scr_term")
fm.box((-0.02, DA - 0.25, HA), (0.06, DA - 0.02, HA + 0.55), "card")                         # upright carton
fm.box((0.10, 0.10, HA), (0.42, 0.40, HA + 0.12), "white")                                   # shoe box
fm.box((0.50, 0.20, HA), (0.80, 0.45, HA + 0.06), "card")                                    # opened parcel
im.box((0.55, DA - 0.25, HA), (0.95, DA - 0.18, HA + 0.04), "abs_white")                     # power strip

LB, HB = 1.70, 0.88
west(4.40)
bench(fm, LB, DA, HB, "laminate", "steel")
for u0 in (0.14, 0.62, 1.10):
    pedestal(fm, u0, 4, 0.80)
board(0.05, 1.30, 0.10, HB + 0.04, HB + 1.01, 5, B5)
fm.add(cyl((0.09, 0.53, HB + 0.25), (0.09, 0.30, HB + 0.98), 0.015, 6), "alu")              # diagonal brace
props.antennas(bm, S, 0.05, 1.30, 0.10, HB + 0.04, HB + 1.01, (0.125, 0.16, 0.195, 0.225), 0.36, 0.53)
fm.box((1.35, 0.30, HB), (1.65, 0.40, HB + 0.01), "white")                                   # leaflet

west(6.15, 0.70)
desk(fm, 1.40, 0.70, 0.75, "laminate")
props.lcd(im, S, 0.70, 0.40, 0.75, 0.62, "off")
props.keyboard(im, S, 0.62, 0.10, 0.75)
props.mouse(im, S, 0.98, 0.14, 0.75)
seats((0.35, 1.05))                                                                          # 2 chairs (151040)

west(7.60)
bench(fm, 1.40, DA, 0.85, "laminate", "steel")
board(0.05, 1.35, 0.15, 0.89, 1.91, 3, B3)

# North wall: desk with monitor under N1, bench with board "3" in front of N2, board "2" at the NE corner.
north(0.90, 0.70)
desk(fm, 1.40, 0.70, 0.75, "laminate")
props.lcd(im, S, 0.70, 0.40, 0.75, 0.62, "off")
props.keyboard(im, S, 0.62, 0.12, 0.75)
props.mouse(im, S, 0.98, 0.16, 0.75)
seats((0.68,))
north(2.85)
bench(fm, 1.50, DA, 0.85, "laminate", "steel")
fm.box((0.06, 0.10, 0.25), (1.44, 0.70, 0.27), "laminate")                                  # lower shelf
seats((0.75,))
board(0.02, 1.48, 0.15, 0.89, 1.91, 3, B3)
north(4.80)
bench(fm, 1.25, DA, 0.85, "laminate", "steel")
board(0.02, 1.23, 0.15, 0.89, 1.91, 2, B2)

# East wall: dual-monitor desk in front of E1 (user faces the window, 151124: left off, right spreadsheet),
# bench with board "1" beside E2.
east(8.00, 0.70)
desk(fm, 1.40, 0.70, 0.75, "laminate")
props.lcd(im, S, 0.40, 0.40, 0.75, 0.61, "off")
props.lcd(im, S, 1.02, 0.40, 0.75, 0.61, "scr_sheet")
props.keyboard(im, S, 0.42, 0.10, 0.75)
props.keyboard(im, S, 0.98, 0.08, 0.75)
props.mouse(im, S, 1.28, 0.12, 0.75)
seats((0.72,), "task")
cable(props.sag((1.02, 0.47, 0.80), (1.10, 0.68, 0.752), 0.0, 3)
      + props.sag((1.10, 0.71, 0.74), (1.15, 0.74, 0.02), 0.0, 2)[1:])
at(W - 0.45, 6.75, -90)
props.tower(im, S, 0.0, 0.0)
east(6.05)
bench(fm, 1.70, DA, 0.85, "laminate", "steel")
fm.box((0.06, 0.10, 0.25), (1.64, 0.70, 0.27), "laminate")
board(0.10, 1.60, 0.15, 0.89, 1.91, 1, B1)
seats((0.45, 1.25))                                                                          # 2 chairs (151022)

# Central cluster (151011, 151025, 151033, 150435): 2x2 red-top desks 1600x800, long axis along y, users on both
# sides. One monitor only (the old Dell with the clock screensaver, near desk of the east row), laptops, a projector,
# Dell towers on the floor, cables over the front edges.
for k, (x, y, r) in enumerate(((2.2, 5.45, -90), (2.2, 7.05, -90), (3.8, 3.85, 90), (3.8, 5.45, 90))):
    at(x, y, r)               # -90: front edge at x=2.2 facing -x (west row); 90: front at x=3.8 facing +x
    desk(fm, 1.60, 0.80, 0.75, "red_top")
    seats(((0.40, 1.15), (0.50, 1.20), (0.50, 1.18), (0.45, 1.18))[k])                     # 2 per desk (151033)
    if k == 2:
        props.dell_old(im, S, 0.50, 0.42, 0.75)
        props.keyboard(im, S, 0.50, 0.12, 0.75)
        props.mouse(im, S, 0.80, 0.16, 0.75)
        props.laptop(im, S, 1.15, 0.10, 0.75, "off")
        props.tower(im, S, 1.30, 0.42)
        drape(0.48, 0.47, 0.22, [(0.6, 0.30, 0.01), (1.22, 0.42, 0.01), (1.24, 0.43, 0.10)])
    if k == 3:
        props.projector(im, S, 1.00, 0.40, 0.75)
        props.laptop(im, S, 0.45, 0.10, 0.75, "scr_code", body="abs_grey")
        props.mouse(im, S, 0.75, 0.14, 0.75)
        im.box((1.20, 0.08, 0.75), (1.55, 0.34, 0.765), "abs_black")                    # laptop sleeve (151033)
        im.add(cyl((0.20, 0.30, 0.75), (0.20, 0.30, 0.90), 0.033, 10), "bottle")        # water bottle
    if k == 2:
        im.add(cyl((0.18, 0.28, 0.75), (0.18, 0.28, 0.86), 0.036, 10), "cup")           # paper coffee cup
    if k == 1:
        im.box((0.95, 0.30, 0.75), (1.32, 0.56, 0.765), "abs_black")                    # laptop sleeve
    if k == 0:
        props.laptop(im, S, 0.80, 0.10, 0.75, "scr_code2")
        props.tower(im, S, 1.30, 0.42)
        drape(0.66, 0.26, 0.60, [(0.8, 0.30, 0.01), (1.22, 0.42, 0.01), (1.24, 0.43, 0.10)])
    if k == 1:
        props.laptop(im, S, 0.60, 0.10, 0.75, "off")
        drape(0.46, 0.26, 0.40, [(0.35, 0.40, 0.01), (0.10, 0.55, 0.01)])

# chairs: one per workstation at its table front edge, seat facing the table with the seat front 3 cm under to
# 8 cm short of the edge, small yaw / offset jitter (Photos/3). ISO chairs = one decimated copy of the room-1
# Chair_Mesh (Nowy Styl ISO, same product as room 1; mesh +x = facing), the E1 desk has the mesh-back task chair.
chair_lod = lod(bpy.data.objects["Chair_1"].data, 0.3, "LOD_Chair")
cv = chair_lod.vertices
FX = max(v.co.x for v in cv if 0.40 < v.co.z < 0.50)                   # seat front, chair local +x
FOOT = (min(v.co.x for v in cv), min(v.co.y for v in cv), max(v.co.x for v in cv), max(v.co.y for v in cv))
rng = random.Random(7)
tc, placed = Mesh(), []
for n, (M, u, kind) in enumerate(SEATS):
    front = FX if kind == "iso" else 0.25
    C = M @ Matrix.Translation((u + rng.uniform(-0.03, 0.03), rng.uniform(-0.08, 0.03) - front, 0)) \
        @ Matrix.Rotation(math.radians(90 + rng.uniform(-7, 7)), 4, 'Z')        # chair +x -> table +v
    if kind == "iso":
        inst(f"Chair_{n + 1:02d}", chair_lod, C)
        placed.append((C, front, rect2(C, *FOOT)))
    else:
        tc.T = C @ Matrix.Rotation(math.pi / 2, 4, 'Z')                         # task chair is built facing -v
        props.task_chair(tc, S)
        placed.append((C, front, rect2(C, -0.31, -0.31, 0.31, 0.31)))
obj("Task_Chair", tc, None, coll)


def overlap(a, b):
    """2D convex polygon intersection (separating axis test)."""
    for poly in (a, b):
        for i in range(len(poly)):
            e = poly[(i + 1) % len(poly)] - poly[i]
            nrm = Vector((-e.y, e.x))
            pa, pb = [nrm.dot(p) for p in a], [nrm.dot(p) for p in b]
            if max(pa) <= min(pb) + 1e-4 or max(pb) <= min(pa) + 1e-4:
                return False
    return True


def chair_check():
    """Each chair: seat front within 0.25 m of a table front edge and facing it (dot > 0.9); its footprint
    touches no table leg / bench frame / pedestal and no other chair."""
    bad = []
    for i, (C, front, foot) in enumerate(placed):
        p = (C @ Vector((front, 0, 0))).xy
        fwd = (C.to_3x3() @ Vector((1, 0, 0))).xy
        ok = False
        for M, L in TABLES:
            a, b = (M @ Vector((0, 0, 0))).xy, (M @ Vector((L, 0, 0))).xy
            t = max(0.0, min(1.0, (p - a).dot(b - a) / (b - a).length_squared))
            nrm = (M.to_3x3() @ Vector((0, 1, 0))).xy
            ok |= (p - a.lerp(b, t)).length <= 0.25 and fwd.dot(nrm) > 0.9
        if not ok:
            bad.append("chair %d not at a table edge" % i)
        if any(overlap(foot, o) for o in OBST):
            bad.append("chair %d hits furniture" % i)
        bad += ["chairs %d/%d overlap" % (i, j) for j in range(i) if overlap(foot, placed[j][2])]
    print("ROOM2 CHAIR CHECK", "OK %d chairs" % len(placed) if not bad else "FAIL: " + "; ".join(bad))
    return not bad


chair_check()

# partition wall items seen in 151040: room thermostat + switch + notice left of the passage
fm.T = im.T = bm.T = Matrix.Identity(4)
fm.box((2.95, Y0, 1.45), (3.04, Y0 + 0.025, 1.54), "white")
fm.box((2.97, Y0, 1.02), (3.05, Y0 + 0.012, 1.10), "white")
fm.box((3.15, Y0, 1.30), (3.36, Y0 + 0.002, 1.60), "white")
obj("Furniture", fm, None, coll)
obj("IT", im, None, coll)
obj("Demo_Boards", bm, None, coll)


def tris(o):
    return sum(len(p.vertices) - 2 for p in o.data.polygons) if o.type == 'MESH' else 0


print("ROOM2 OK", len(coll.objects), "objects", sum(tris(o) for o in coll.objects), "tris")
