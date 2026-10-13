# Architectural trim of room 1: stepped metal-look skirting swept along all wall runs (mitred), the pilaster
# at the window wall, white 2-compartment cable trunking with double sockets + RJ45, the light switch at the door,
# and the ceiling: T24 grid + wall angle, LED panel frames, smoke detector, sensor, square vent diffuser.
# Runs after build_room.py and room.py (via apply_materials.py). Standalone, idempotent. Touches only Trim_* objects.
import math
import os
import re

import bmesh
import bpy

W, D, H = 6.50, 2.50, 2.90                    # mirror of build_room.py
T_TOP = 0.12
DOOR_Y0, PILLAR_Y, PILLAR_X = 1.15, D - 0.20, 0.25
PASS_X0, PASS_X1 = 1.00, 2.50

# Ceiling grid: read room.py so the frames always sit where its LED lights and painted T-lines are.
CELL, GX0, GY0, LED_CELLS = 0.60, 0.25, 0.35, (3, 6, 9)
try:
    src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "room.py")).read()
    GX0, GY0 = (float(v) for v in re.search(r"^GX0, GY0 = ([\d.]+), ([\d.]+)", src, re.M).groups())
    LED_CELLS = tuple(int(v) for v in re.search(r"^LED_CELLS = \(([\d, ]+)\)", src, re.M).group(1).split(","))
except (OSError, NameError, AttributeError):   # ponytail: falls back to the values above
    pass

PIL_P, PIL_W = 0.13, 0.20                     # pilaster projection (agreed with g1_radiator, photos 150354/150359) / width (plan y 0..0.2)
PIL_X = W - PIL_P                             # pilaster front face x = 6.42

# Skirting profile (d from wall face, z): 12 mm proud face, chamfer, two small stair steps back to the wall.
SKIRT = [(0, 0), (0.012, 0), (0.012, 0.056), (0.0105, 0.0595), (0.007, 0.0605), (0.007, 0.065),
         (0.0055, 0.0668), (0.003, 0.067), (0.003, 0.0705), (0, 0.0705)]

# Legrand DLP 50x130, 2 compartments (lower data 57 mm, upper power 73 mm), cover split groove.
TR_Z0, TR_H, TR_D = 0.98, 0.13, 0.05
TRUNK = [(0, 0), (0.048, 0), (0.05, 0.002), (0.05, 0.0555), (0.0475, 0.0565), (0.0475, 0.0585), (0.05, 0.0595),
         (0.05, 0.128), (0.048, 0.13), (0, 0.13)]
TRUNK = [(d, z + TR_Z0) for d, z in TRUNK]
SOCKET_X = (2.48, 3.73, 4.79, 6.01)           # double Schuko + double RJ45 below (122216, 120939; last two 150354 back-projected)
SW_Y, SW_Z = 2.40, 0.92                       # light switch on the pillar's room face x=0.25 (122224)

# Ceiling devices (cells per 150430 / 122209)
VENT_CELL = (5, 1)                            # door end: LED, -, vent, LED, -, -, LED (cells 3..9)
SMOKE_XY = (GX0 + 2.5 * CELL, GY0 + 2.5 * CELL)  # 150430: (1.74, 2.01)
SENSOR_XY = (3.94, 2.20)                      # 122209 / 150430 back-projected: (3.91, 2.13) / (3.97, 2.24)

TB_W, TB_Z = 0.024, H - 0.003                 # T24 flange width, flange underside (3 mm under the tile face)


# ---------- mesh accumulator ----------

class M:
    def __init__(self):
        self.v, self.f, self.m = [], [], []

    def face(self, idx, mat):
        self.f.append(tuple(idx))
        self.m.append(mat)

    def box(self, lo, hi, mat=0):
        (x0, y0, z0), (x1, y1, z1) = lo, hi
        b = len(self.v)
        self.v += [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
                   (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
        for q in ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)):
            self.face([b + i for i in q], mat)

    def sweep(self, path, prof, closed=False, mat=0):
        """Sweep a closed (d, z) profile along a 2D wall path; the wall is on the RIGHT of the walk direction,
        d grows to the left (into the room). Mitred joints, flat caps on open ends."""
        n = len(path)
        dirs = []
        for i in range(n if closed else n - 1):
            (ax, ay), (bx, by) = path[i], path[(i + 1) % n]
            L = math.hypot(bx - ax, by - ay)
            dirs.append(((bx - ax) / L, (by - ay) / L))
        b = len(self.v)
        for i, (px, py) in enumerate(path):
            ins = [dirs[i - 1]] if (closed or i > 0) else []
            ins += [dirs[i % len(dirs)]] if (closed or i < n - 1) else []
            nx = sum(-d[1] for d in ins) / len(ins)
            ny = sum(d[0] for d in ins) / len(ins)
            k = nx * nx + ny * ny                       # mitre: offset vector scaled by 1/cos^2(half angle)
            nx, ny = nx / k, ny / k
            self.v += [(px + nx * d, py + ny * d, z) for d, z in prof]
        P = len(prof)
        for i in range(n if closed else n - 1):
            r0, r1 = b + i * P, b + ((i + 1) % n) * P
            for j in range(P):
                j1 = (j + 1) % P
                self.face((r0 + j, r0 + j1, r1 + j1, r1 + j), mat)
        if not closed:
            self.face([b + j for j in range(P)], mat)
            self.face([b + (n - 1) * P + j for j in range(P)], mat)

    def lathe(self, c, axis, prof, seg=24, mat=0):
        """Revolve (r, h) points around axis ('x','y','-z') through c; first and last points get n-gon caps."""
        ux, uy, uz = {"x": ((0, 1, 0), (0, 0, 1), (1, 0, 0)), "y": ((1, 0, 0), (0, 0, 1), (0, 1, 0)),
                      "-z": ((1, 0, 0), (0, 1, 0), (0, 0, -1))}[axis]
        b = len(self.v)
        for r, h in prof:
            for s in range(seg):
                a = 2 * math.pi * s / seg
                ca, sa = math.cos(a) * r, math.sin(a) * r
                self.v.append(tuple(c[i] + ux[i] * ca + uy[i] * sa + uz[i] * h for i in range(3)))
        for j in range(len(prof) - 1):
            for s in range(seg):
                s1 = (s + 1) % seg
                self.face((b + j * seg + s, b + j * seg + s1, b + (j + 1) * seg + s1, b + (j + 1) * seg + s), mat)
        self.face([b + s for s in range(seg)], mat)
        self.face([b + (len(prof) - 1) * seg + s for s in range(seg)], mat)


# ---------- materials (simple placeholders; group 2 overrides by name) ----------

def mat(name, rgb, rough, metal=0.0):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    m.diffuse_color = (*rgb, 1)
    nt = m.node_tree
    nt.nodes.clear()
    b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    b.inputs["Base Color"].default_value = (*rgb, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    out.location = (300, 0)
    nt.links.new(b.outputs[0], out.inputs[0])
    return m, b, nt


def perforated_mat():
    m, b, nt = mat("Trim_Vent_Perf", (0.80, 0.80, 0.79), 0.45)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    vor = nt.nodes.new("ShaderNodeTexVoronoi")       # ponytail: a square-ish 6 mm hole field via Voronoi F1 on a grid
    vor.inputs["Scale"].default_value = 160.0
    vor.inputs["Randomness"].default_value = 0.0
    nt.links.new(tc.outputs["Object"], vor.inputs["Vector"])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.28
    ramp.color_ramp.elements[0].color = (0.02, 0.02, 0.02, 1)
    ramp.color_ramp.elements[1].position = 0.30
    ramp.color_ramp.elements[1].color = (0.80, 0.80, 0.79, 1)
    nt.links.new(vor.outputs["Distance"], ramp.inputs[0])
    nt.links.new(ramp.outputs[0], b.inputs["Base Color"])
    return m


# ---------- cleanup (idempotent) ----------

for ob in [o for o in bpy.data.objects if o.name.startswith("Trim_")]:
    bpy.data.objects.remove(ob, do_unlink=True)
for me in [m for m in bpy.data.meshes if m.name.startswith("Trim_") and m.users == 0]:
    bpy.data.meshes.remove(me)
coll = bpy.data.collections.get("Trim") or bpy.data.collections.new("Trim")
if coll.name not in bpy.context.scene.collection.children:
    bpy.context.scene.collection.children.link(coll)

SKIRT_M = mat("Trim_Skirting", (0.07, 0.072, 0.075), 0.32, 0.7)[0]   # dark titanium-anodised look (150439)
PVC = mat("Trim_PVC_White", (0.82, 0.82, 0.80), 0.35)[0]              # trunking, plates
DARK = mat("Trim_Dark", (0.02, 0.02, 0.02), 0.6)[0]                    # socket holes, RJ45 ports
GRID = mat("Trim_Ceiling_Grid", (0.85, 0.85, 0.84), 0.4, 0.0)[0]       # white painted steel T24
LEDF = mat("Trim_LED_Frame", (0.88, 0.88, 0.88), 0.3, 0.0)[0]
DEV = mat("Trim_Device_White", (0.86, 0.86, 0.85), 0.4)[0]            # smoke detector, sensor, vent frame
PERF = perforated_mat()
WALL = bpy.data.materials.get("Room_Wall") or bpy.data.materials.get("Wall")


def multi(name, parts):
    """Join (M, material) parts; material index stored per face and re-applied after triangulation."""
    acc, mats = M(), []
    for mm, mt in parts:
        b = len(acc.v)
        acc.v += mm.v
        acc.f += [tuple(i + b for i in f) for f in mm.f]
        acc.m += [len(mats)] * len(mm.f)
        mats.append(mt)
    me = bpy.data.meshes.new(name)
    me.from_pydata(acc.v, [], acc.f)
    me.validate()
    me.polygons.foreach_set("material_index", acc.m)
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4], ngon_method='EAR_CLIP')
    bm.to_mesh(me)                                   # material_index is kept per face by bmesh
    bm.free()
    for mt in mats:
        me.materials.append(mt)
    ob = bpy.data.objects.new(name, me)
    coll.objects.link(ob)
    return ob


# ---------- pilaster ----------

p = M()
p.box((PIL_X, 0, 0), (W, PIL_W, H))
multi("Trim_Pilaster", [(p, WALL)])

# ---------- skirting: two open runs, wall on the right ----------

run_a = [(0, DOOR_Y0), (0, 0), (PIL_X, 0), (PIL_X, PIL_W), (W, PIL_W), (W, D), (PASS_X1, D), (PASS_X1, D + T_TOP)]
run_b = [(PASS_X0, D + T_TOP), (PASS_X0, D), (PILLAR_X, D), (PILLAR_X, PILLAR_Y), (0, PILLAR_Y)]
s = M()
s.sweep(run_a, SKIRT)
s.sweep(run_b, SKIRT)
multi("Trim_Skirting", [(s, SKIRT_M)])

# ---------- cable trunking + sockets ----------

t = M()
t.sweep([(0, 0), (PIL_X, 0)], TRUNK)                              # walking +x keeps the wall (y<0) on the right
t.box((0.01, 0, 0.30), (0.09, 0.04, TR_Z0))                       # vertical drop at the door-end corner (122216)

pl, holes = M(), M()


def schuko(cx, cy0, cz, axis="y"):
    """One Schuko insert on a plate front at y=cy0: raised ring with a 9 mm well and two pin holes."""
    pl.lathe((cx, cy0, cz), axis, [(0.0195, 0), (0.0195, 0.008), (0.018, 0.0095), (0.0165, 0.0095),
                                   (0.0165, 0.002)], seg=20)
    for dx in (-0.0095, 0.0095):
        holes.box((cx + dx - 0.002, cy0 + 0.002, cz - 0.002), (cx + dx + 0.002, cy0 + 0.0028, cz + 0.002))


for x in SOCKET_X:
    zc = TR_Z0 + 0.0595 + 0.035
    pl.box((x - 0.052, TR_D, zc - 0.028), (x + 0.052, TR_D + 0.006, zc + 0.028))   # 2-gang frame
    for dx in (-0.0245, 0.0245):
        schuko(x + dx, TR_D + 0.006, zc)
    zr = TR_Z0 + 0.028                                                            # RJ45 2-port plate
    pl.box((x - 0.023, TR_D, zr - 0.022), (x + 0.023, TR_D + 0.005, zr + 0.022))
    for dx in (-0.01, 0.01):
        holes.box((x + dx - 0.006, TR_D + 0.005, zr - 0.006), (x + dx + 0.006, TR_D + 0.0058, zr + 0.004))
pl.box((0.015, 0.04, 0.44), (0.085, 0.046, 0.51))                                 # single socket in the drop
schuko(0.05, 0.046, 0.475)
multi("Trim_Trunking", [(t, PVC)])
multi("Trim_Sockets", [(pl, PVC), (holes, DARK)])

# ---------- light switch on the pillar face (x = 0.25, facing +x) ----------

sw = M()
sw.box((PILLAR_X, SW_Y - 0.04, SW_Z - 0.04), (PILLAR_X + 0.009, SW_Y + 0.04, SW_Z + 0.04))            # plate
sw.box((PILLAR_X + 0.009, SW_Y - 0.028, SW_Z - 0.028), (PILLAR_X + 0.013, SW_Y - 0.0005, SW_Z + 0.028))  # 2 rockers
sw.box((PILLAR_X + 0.009, SW_Y + 0.0005, SW_Z - 0.028), (PILLAR_X + 0.013, SW_Y + 0.028, SW_Z + 0.028))
multi("Trim_Switch", [(sw, PVC)])

# ---------- ceiling: T24 grid + wall angle ----------

g = M()
perim = [(0, 0), (PIL_X, 0), (PIL_X, PIL_W), (W, PIL_W), (W, D), (PILLAR_X, D), (PILLAR_X, PILLAR_Y), (0, PILLAR_Y)]
ANGLE = [(0, H - 0.024), (0.0012, H - 0.024), (0.0012, TB_Z), (TB_W, TB_Z), (TB_W, H), (0, H)]
g.sweep(perim, ANGLE, closed=True)                    # walking the loop with walls on the right
xs = [GX0 + k * CELL for k in range(20) if 0 < GX0 + k * CELL < W]
ys = [GY0 + k * CELL for k in range(10) if 0 < GY0 + k * CELL < D]
h = TB_W / 2
for y in ys:                                          # main runners along x, continuous wall to wall
    g.box((TB_W, y - h, TB_Z), (W - TB_W, y + h, H))
for x in xs:                                          # cross tees between the mains
    y_end = PILLAR_Y if x - h < PILLAR_X else D
    stops = [TB_W] + [v for y in ys for v in (y - h, y + h)] + [y_end - TB_W]
    for a, b in zip(stops[::2], stops[1::2]):
        g.box((x - h, a, TB_Z), (x + h, b, H))
multi("Trim_Ceiling_Grid", [(g, GRID)])

# ---------- LED panel frames: 10 mm alu rim; clips ~8 mm of room.py's 570 mm emitter edge (better: light 0.555) ----------

lf = M()
for k in LED_CELLS:
    cx, cy = GX0 + (k + 0.5) * CELL, GY0 + 1.5 * CELL
    o, i, z0 = (CELL - TB_W) / 2, 0.278, H - 0.007    # outer = clear T opening, 10 mm visible rim (150430)
    for lo, hi in (((cx - o, cy - o), (cx + o, cy - i)), ((cx - o, cy + i), (cx + o, cy + o)),
                   ((cx - o, cy - i), (cx - i, cy + i)), ((cx + i, cy - i), (cx + o, cy + i))):
        lf.box((lo[0], lo[1], z0), (hi[0], hi[1], H))
multi("Trim_LED_Frames", [(lf, LEDF)])

# ---------- smoke detector, small sensor ----------

sd = M()
sd.lathe((*SMOKE_XY, H), "-z", [(0.055, 0), (0.055, 0.026), (0.052, 0.034), (0.040, 0.040), (0.018, 0.043)], 32)
sd.lathe((SMOKE_XY[0] + 0.012, SMOKE_XY[1], H - 0.043), "-z", [(0.0025, 0), (0.0025, 0.0015)], 8)  # LED lens
multi("Trim_Smoke_Detector", [(sd, DEV)])
se = M()
se.lathe((*SENSOR_XY, H), "-z", [(0.03, 0), (0.03, 0.012), (0.024, 0.022), (0.012, 0.028)], 16)
multi("Trim_Sensor", [(se, DEV)])

# ---------- square ceiling diffuser in one cell: sloped frame + perforated face (150430) ----------

v_fr, v_pf = M(), M()
cx, cy = GX0 + (VENT_CELL[0] + 0.5) * CELL, GY0 + (VENT_CELL[1] + 0.5) * CELL
o, i, fz, pz = (CELL - TB_W) / 2, 0.235, H - 0.022, H - 0.018
# frame: sloped square ring from the tile plane (outer) down to the face level (inner); d grows outward
ring = [(cx - i, cy - i), (cx - i, cy + i), (cx + i, cy + i), (cx + i, cy - i)]  # walls (outside) on the right
v_fr.sweep(ring, [(0, fz), (o - i, H - 0.004), (o - i, H), (0, H)], closed=True)
v_pf.box((cx - i - 0.001, cy - i - 0.001, pz), (cx + i + 0.001, cy + i + 0.001, H - 0.004))
multi("Trim_Vent", [(v_fr, DEV), (v_pf, PERF)])

n_tris = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in coll.objects)
print("TRIM OK", len(coll.objects), "objects,", n_tris, "tris; pilaster x", PIL_X, "..", W, "y 0 ..", PIL_W)
