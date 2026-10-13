# Window: white uPVC tilt-and-turn window modelled on a 70 mm, 5-chamber system (VEKA Softline 70 AD / Rehau
# Euro-Design 70 class): frame + transom + mullions, glazing beads, 4-16-4 double glazing with spacer bars,
# dry glazing gaskets (room + exterior side), one opening sash (middle bottom, as photographed)
# proud of the frame with stop gasket, round-rosette lever handle, stay/corner hinge caps, exterior drainage caps.
# Also: deep plastered reveal (old ~60 cm brick wall), interior PVC sill board, exterior steel drip sill,
# rain droplets/streaks as bump on the OUTER glass face only (separate material slot).
# Runs after build_room.py. Idempotent: rebuilds meshes in place, get-or-create objects/materials.
import bmesh
import bpy

W = 6.50
T_WIN = 0.10                                              # build_room.py wall slab (frozen)
WIN_Y0, WIN_Y1, WIN_Z0, WIN_Z1 = 0.20, 1.80, 0.85, 2.87   # build_room.py WIN_* (opening = plaster edges)
WALL_T = 0.60          # real wall: Stalin-era brick, 60-70 cm; build_room models only 10 cm -> lining outside
REVEAL = 0.26          # interior wall face -> frame room face (photos 150359 / 122244 / 112212)
SILL_T, SILL_OH, SILL_EAR = 0.020, 0.040, 0.040            # sill board thickness, overhang past wall, side ears
RAIN = False           # s2_integrate: droplet bump read as dark specks against the exterior head (150359); photos show none

FX0 = W + REVEAL       # frame room face
FX1 = FX0 + 0.070      # 70 mm system depth
FY0, FY1 = WIN_Y0, WIN_Y1
FZ0, FZ1 = WIN_Z0 + SILL_T, WIN_Z1                         # frame stands on the sill board / adapter profile
m1 = WIN_Y0 + (WIN_Y1 - WIN_Y0) / 3
m2 = WIN_Y0 + 2 * (WIN_Y1 - WIN_Y0) / 3
TRC = 2.20             # transom centre (122244: 2.17..2.23 on the frame face)
FB, TB, DB = 0.042, 0.050, 0.020   # body widths: outer frame, transom/mullion, top glazing bars
BEAD, BEAD_D = 0.022, 0.006        # glazing bead width (sight line); narrow bead at the top-row bars
GX0, GX1 = FX0 + 0.040, FX0 + 0.064                        # fixed IGU 4-16-4 (24 mm)
OV, SFACE = 0.008, 0.056           # sash lip overlap onto frame; sash face width (outer edge -> bead)
SX0 = FX0 - 0.012                  # sash room face (12 mm proud)
SGX0, SGX1 = FX0 + 0.030, FX0 + 0.054                      # sash IGU


# ---------- mesh helpers (same approach as build_room.py) ----------

def box_faces(lo, hi, base=0):
    (x0, y0, z0), (x1, y1, z1) = lo, hi
    v = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
         (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    f = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    return v, [tuple(i + base for i in q) for q in f]


def solid_mesh(solids, holes=()):
    """Boolean-free union of boxes minus holes -> manifold all-quad mesh (copied from build_room.py)."""
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


def prism(pts, axis, a0, a1):
    """Closed prism: 2D outline pts (CCW in the (axis+1, axis+2) plane) extruded along axis a0..a1.
    Quad sides, one n-gon cap per end (caps are the only non-quads)."""
    n = len(pts)
    u, v = (axis + 1) % 3, (axis + 2) % 3
    verts = []
    for a in (a0, a1):
        for pu, pv in pts:
            p = [0, 0, 0]
            p[axis], p[u], p[v] = a, pu, pv
            verts.append(tuple(p))
    faces = [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
    faces += [tuple(reversed(range(n))), tuple(range(n, 2 * n))]
    return verts, faces


def rrect(cu, cv, hu, hv, r, seg=3):
    """CCW rounded rectangle outline (r = hu = hv gives a circle, r = hu < hv a stadium)."""
    import math
    out = []
    for k, (sx, sy) in enumerate(((1, 1), (-1, 1), (-1, -1), (1, -1))):
        ccx, ccy = cu + sx * (hu - r), cv + sy * (hv - r)
        for i in range(seg + 1):
            a = math.pi / 2 * (k + i / seg)
            q = (ccx + r * math.cos(a), ccy + r * math.sin(a))
            if not out or math.dist(q, out[-1]) > 1e-7:      # r == hu/hv: arcs share end points
                out.append(q)
    return out[:-1] if math.dist(out[0], out[-1]) < 1e-7 else out


class Parts:
    """Collects islands (verts, faces, material index or per-face list) into one mesh."""
    def __init__(self):
        self.verts, self.faces, self.mats = [], [], []

    def add(self, mesh, mat=0):
        v, f = mesh
        base = len(self.verts)
        self.verts += v
        self.faces += [tuple(i + base for i in q) for q in f]
        self.mats += mat if isinstance(mat, list) else [mat] * len(f)

    def write(self, me, smooth=True):
        me.clear_geometry()
        me.from_pydata(self.verts, [], self.faces)
        me.validate()
        assert len(me.polygons) == len(self.mats), "validate() dropped faces"
        for p, mi in zip(me.polygons, self.mats):
            p.material_index = mi
            p.use_smooth = smooth


def ring(x0, x1, rect, inset_out, inset_in):
    """Rectangular ring in the y/z plane: rect inset by inset_out (outer) and inset_in (inner).
    inset_in may be a tuple (y0 side, y1 side, z0 side, z1 side). Mitred, 16 quads."""
    (y0, z0), (y1, z1) = rect
    a, b, c, d = inset_in if isinstance(inset_in, tuple) else (inset_in,) * 4
    o = inset_out
    outer = [(y0 + o, z0 + o), (y1 - o, z0 + o), (y1 - o, z1 - o), (y0 + o, z1 - o)]   # CCW in y/z
    inn = [(y0 + a, z0 + c), (y1 - b, z0 + c), (y1 - b, z1 - d), (y0 + a, z1 - d)]
    v = [(x, y, z) for x in (x0, x1) for loop in (outer, inn) for y, z in loop]
    Of, If, Ob, Ib = (list(range(k, k + 4)) for k in (0, 4, 8, 12))
    f = []
    for i in range(4):
        j = (i + 1) % 4
        f += [(Of[i], Of[j], Ob[j], Ob[i]), (If[j], If[i], Ib[i], Ib[j]),
              (Of[i], If[i], If[j], Of[j]), (Ob[i], Ob[j], Ib[j], Ib[i])]
    return v, f


def grow(rect, d):
    (y0, z0), (y1, z1) = rect
    return (y0 - d, z0 - d), (y1 + d, z1 + d)


# ---------- materials ----------

def new_mat(name):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    out.location, bsdf.location = (400, 0), (100, 0)
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return m, nt, bsdf


def micro(nt, bsdf, rough, rough_var, bump_scale, bump_strength, detail_scale=6.0):
    """Roughness variation (large blotches) + fine orange-peel bump, object coords (= world metres)."""
    tc = nt.nodes.new("ShaderNodeTexCoord")
    n1 = nt.nodes.new("ShaderNodeTexNoise")
    n1.inputs["Scale"].default_value = detail_scale
    n1.inputs["Detail"].default_value = 4.0
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["To Min"].default_value = rough - rough_var
    mr.inputs["To Max"].default_value = rough + rough_var
    mr.inputs["From Min"].default_value = 0.3
    mr.inputs["From Max"].default_value = 0.7
    n2 = nt.nodes.new("ShaderNodeTexNoise")
    n2.inputs["Scale"].default_value = bump_scale
    n2.inputs["Detail"].default_value = 2.0
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = bump_strength
    bump.inputs["Distance"].default_value = 0.0005
    nt.links.new(tc.outputs["Object"], n1.inputs["Vector"])
    nt.links.new(tc.outputs["Object"], n2.inputs["Vector"])
    nt.links.new(n1.outputs["Fac"], mr.inputs["Value"])
    nt.links.new(mr.outputs["Result"], bsdf.inputs["Roughness"])
    nt.links.new(n2.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    for i, n in enumerate((tc, n1, n2, mr, bump)):
        n.location = (-700 + 150 * (i // 2), 300 - 250 * (i % 2))


def glass_bsdf(b):
    b.inputs["Base Color"].default_value = (0.965, 0.99, 0.975, 1)   # faint green edge tint
    b.inputs["Roughness"].default_value = 0.0
    b.inputs["IOR"].default_value = 1.5
    b.inputs["Transmission Weight"].default_value = 1.0


def rain_bump(nt, bsdf):
    """Droplets (sparse random-radius domes) + a few vertical run-off streaks, as a bump on the outer pane face.
    Object coords = world metres; the pane lies in the y/z plane."""
    N, L = nt.nodes.new, nt.links.new

    def math(op, a, b=None, c=None):
        m = N("ShaderNodeMath")
        m.operation = op
        for i, v in enumerate((a, b, c)):
            if v is None:
                continue
            L(v, m.inputs[i]) if isinstance(v, bpy.types.NodeSocket) else setattr(m.inputs[i], "default_value", v)
        return m.outputs[0]

    co = N("ShaderNodeTexCoord").outputs["Object"]

    def drops(scale, keep, rmin, rmax, stretch=1.0):
        vec = co
        if stretch != 1.0:
            mp = N("ShaderNodeMapping")
            mp.inputs["Scale"].default_value = (1.0, 1.0, stretch)
            L(co, mp.inputs["Vector"])
            vec = mp.outputs[0]
        vo = N("ShaderNodeTexVoronoi")
        vo.inputs["Scale"].default_value = scale
        vo.inputs["Randomness"].default_value = 1.0
        L(vec, vo.inputs["Vector"])
        sep = N("ShaderNodeSeparateColor")
        L(vo.outputs["Color"], sep.inputs[0])
        r = math('MULTIPLY_ADD', sep.outputs[0], rmax - rmin, rmin)          # per-cell radius (cell units)
        dome = math('SQRT', math('MAXIMUM', math('SUBTRACT', 1.0, math('POWER', math('DIVIDE', vo.outputs["Distance"], r), 2.0)), 0.0))
        on = math('GREATER_THAN', sep.outputs[1], 1.0 - keep)               # only some cells carry a drop
        return math('MULTIPLY', math('MULTIPLY', dome, on), math('MULTIPLY', r, 2.5))

    h = math('MAXIMUM', drops(220.0, 0.55, 0.10, 0.32), drops(70.0, 0.35, 0.12, 0.30))  # small + large drops
    h = math('MAXIMUM', h, math('MULTIPLY', drops(60.0, 0.12, 0.05, 0.09, stretch=0.06), 0.5))  # streaks
    bump = N("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 1.0
    bump.inputs["Distance"].default_value = 0.0012
    L(h, bump.inputs["Height"])
    L(bump.outputs["Normal"], bsdf.inputs["Normal"])


pvc, nt, b = new_mat("Window_PVC")
b.inputs["Base Color"].default_value = (0.86, 0.865, 0.85, 1)
b.inputs["Specular IOR Level"].default_value = 0.45
micro(nt, b, 0.36, 0.04, 350.0, 0.04)
pvc.diffuse_color = (0.86, 0.865, 0.85, 1)

gasket, nt, b = new_mat("Window_Gasket")
b.inputs["Base Color"].default_value = (0.035, 0.036, 0.038, 1)
b.inputs["Roughness"].default_value = 0.6
gasket.diffuse_color = (0.035, 0.036, 0.038, 1)

spacer, nt, b = new_mat("Window_Spacer")          # dark grey warm-edge spacer (photos: dark line at glass edges)
b.inputs["Base Color"].default_value = (0.07, 0.072, 0.075, 1)
b.inputs["Roughness"].default_value = 0.45
spacer.diffuse_color = (0.07, 0.072, 0.075, 1)

glass, nt, b = new_mat("Window_Glass")
glass_bsdf(b)
glass.diffuse_color = (0.8, 0.88, 0.88, 0.2)

rain, nt, b = new_mat("Window_GlassRain")         # outer face of the outer pane only
glass_bsdf(b)
if RAIN:
    rain_bump(nt, b)
rain.diffuse_color = (0.8, 0.88, 0.88, 0.2)

sill_mat, nt, b = new_mat("Window_SillBoard")
b.inputs["Base Color"].default_value = (0.84, 0.845, 0.83, 1)
b.inputs["Coat Weight"].default_value = 0.15
b.inputs["Coat Roughness"].default_value = 0.15
micro(nt, b, 0.24, 0.05, 250.0, 0.02, detail_scale=4.0)
sill_mat.diffuse_color = (0.84, 0.845, 0.83, 1)

flash, nt, b = new_mat("Window_Flashing")         # exterior powder-coated steel drip sill (wet)
b.inputs["Base Color"].default_value = (0.55, 0.56, 0.56, 1)
b.inputs["Metallic"].default_value = 0.6
b.inputs["Roughness"].default_value = 0.25
flash.diffuse_color = (0.55, 0.56, 0.56, 1)

wall_mat = bpy.data.materials.get("Room_Wall") or bpy.data.materials.get("Wall")


def bevel(ob, width, segments, pvc_only=False):
    """pvc_only: bevel only sharp edges whose faces are all slot 0 (white PVC) via edge bevel weights,
    so 2 mm gaskets / spacers / drip sill stay unbevelled (no clamped zero-area faces, fewer tris)."""
    mod = ob.modifiers.get("Window_Bevel") or ob.modifiers.new("Window_Bevel", "BEVEL")
    mod.width = width
    mod.segments = segments
    mod.limit_method = "ANGLE"
    if pvc_only:
        me = ob.data
        bm = bmesh.new()
        bm.from_mesh(me)
        wts = [1.0 if all(f.material_index == 0 for f in e.link_faces) and e.calc_face_angle(0.0) > 0.5 else 0.0
               for e in bm.edges]
        bm.free()
        at = me.attributes.get("bevel_weight_edge") or me.attributes.new("bevel_weight_edge", "FLOAT", "EDGE")
        at.data.foreach_set("value", wts)
        mod.limit_method = "WEIGHT"
    mod.harden_normals = True
    mod.use_clamp_overlap = True


def set_mats(ob, mats):
    ob.data.materials.clear()
    for m in mats:
        ob.data.materials.append(m)


def get_obj(name, coll):
    me = bpy.data.meshes.get(name) or bpy.data.meshes.new(name)
    ob = bpy.data.objects.get(name) or bpy.data.objects.new(name, me)
    ob.data = me
    if coll not in ob.users_collection:
        coll.objects.link(ob)
    return ob


# ---------- frame ----------

frame = bpy.data.objects["Window_Frame"]
openings = frame.users_collection[0]
PV, GK, SP = 0, 1, 2
P = Parts()

# Outer frame + transom + mullions (bottom row) + glazing bars (top row), one welded body.
P.add(solid_mesh([
    ((FX0, FY0, FZ0), (FX1, FY1, FZ0 + FB)),
    ((FX0, FY0, FZ1 - FB), (FX1, FY1, FZ1)),
    ((FX0, FY0, FZ0), (FX1, FY0 + FB, FZ1)),
    ((FX0, FY1 - FB, FZ0), (FX1, FY1, FZ1)),
    ((FX0, FY0, TRC - TB / 2), (FX1, FY1, TRC + TB / 2)),
    ((FX0, m1 - TB / 2, FZ0), (FX1, m1 + TB / 2, TRC)),
    ((FX0, m2 - TB / 2, FZ0), (FX1, m2 + TB / 2, TRC)),
    ((FX0, m1 - DB / 2, TRC), (FX1, m1 + DB / 2, FZ1)),
    ((FX0, m2 - DB / 2, TRC), (FX1, m2 + DB / 2, FZ1)),
]))
# Sill adapter profile under the frame, behind the sill board (VEKA "Fensterbankanschluss").
P.add(box_faces((FX0 + 0.012, FY0, WIN_Z0), (FX1, FY1, FZ0)))

# Cells = openings between frame bodies (y/z rects). Looking from the room, +y is on the left.
bz = (FZ0 + FB, TRC - TB / 2)
tz = (TRC + TB / 2, FZ1 - FB)
cell_sash = ((m1 + TB / 2, bz[0]), (m2 - TB / 2, bz[1]))           # middle bottom: the only opening sash
cells_fixed = [
    (((FY0 + FB, bz[0]), (m1 - TB / 2, bz[1])), BEAD),              # bottom right (seen from room)
    (((m2 + TB / 2, bz[0]), (FY1 - FB, bz[1])), BEAD),              # bottom left
    (((FY0 + FB, tz[0]), (m1 - DB / 2, tz[1])), (BEAD, BEAD_D, BEAD, BEAD)),   # top row: narrow beads at bars
    (((m1 + DB / 2, tz[0]), (m2 - DB / 2, tz[1])), (BEAD_D, BEAD_D, BEAD, BEAD)),
    (((m2 + DB / 2, tz[0]), (FY1 - FB, tz[1])), (BEAD_D, BEAD, BEAD, BEAD)),
]


def sight(inset, d):
    return tuple(i + d for i in inset) if isinstance(inset, tuple) else inset + d


def glazing(rect, bead, gx0, gx1, bx0, lip_x1):
    """Room bead + gaskets (room/exterior) + exterior lip + spacer bar & secondary seal for one IGU."""
    P.add(ring(bx0, gx0 - 0.0005, rect, 0.0, bead))                            # glazing bead
    P.add(ring(gx0 - 0.0025, gx0 - 0.0005, rect, 0.010, sight(bead, -0.001)), GK)   # room-side gasket lip
    P.add(ring(gx1 + 0.0005, gx1 + 0.0025, rect, 0.010, sight(bead, -0.001)), GK)   # exterior gasket lip
    P.add(ring(gx1 + 0.0025, lip_x1, rect, 0.0, bead))                         # exterior rebate lip
    P.add(ring(gx0 + 0.004, gx1 - 0.004, rect, 0.012, sight(bead, 0.0015)), SP)    # spacer bar (just visible)


for c, bead in cells_fixed:
    glazing(c, bead, GX0, GX1, FX0 + 0.003, FX1)

# Opening sash: lip 12 mm proud (2 mm stop-gasket gap), overlapping the frame by OV; body inside the frame rebate.
sash_out = grow(cell_sash, OV)
(sy0, sz0), (sy1, sz1) = sash_out
inner = grow(cell_sash, -(SFACE - OV))                             # sash opening (glass zone)
(iy0, iz0), (iy1, iz1) = inner
P.add(solid_mesh(
    [((SX0, sy0, sz0), (FX0 - 0.002, sy1, sz1)),
     ((FX0 - 0.002, cell_sash[0][0] + 0.003, cell_sash[0][1] + 0.003), (FX0 + 0.066, cell_sash[1][0] - 0.003, cell_sash[1][1] - 0.003))],
    [((SX0 - 1, iy0, iz0), (FX1 + 1, iy1, iz1))]))
P.add(ring(FX0 - 0.002, FX0, sash_out, 0.002, OV + 0.001), GK)     # stop gasket (dark line around the sash)
SBEAD = 0.022
glazing(inner, SBEAD, SGX0, SGX1, SX0 + 0.004, FX0 + 0.066)

# Handle: round-ended rosette 31 x 68 x 16 mm, round neck, lever 125 mm down (Hoppe Atlanta class),
# centred on the +y stile and on the sash height (150359 / 122244).
hy, hz = sy1 - SFACE / 2, (sz0 + sz1) / 2
P.add(prism(rrect(hy, hz - 0.006, 0.0155, 0.034, 0.0155, 4), 0, SX0 - 0.016, SX0))       # rosette
P.add(prism(rrect(hy, hz, 0.012, 0.012, 0.012, 3), 0, SX0 - 0.040, SX0 - 0.016))         # neck / boss
P.add(prism(rrect(SX0 - 0.031, hy, 0.007, 0.009, 0.005, 2), 2, hz - 0.125, hz - 0.004))  # lever

# Hinges on the -y side (hinge_top / hinge_bot crops): top stay-bearing cap, bottom corner-hinge cap.
by, bx = sy0 - 0.002, SX0 - 0.002
for z0, z1 in ((sz1 - 0.070, sz1 + 0.004), (sz0 - 0.004, sz0 + 0.048)):
    P.add(prism(rrect(bx, by, 0.009, 0.009, 0.009, 2), 2, z0, z1))                       # barrel cap
    P.add(box_faces((bx - 0.004, by - 0.016, z0 + 0.004), (FX0 - 0.0005, by, z1 - 0.004)))  # leaf on the frame
P.add(box_faces((bx - 0.005, by - 0.005, sz0 - 0.008), (bx + 0.005, by + 0.005, sz0 - 0.004)), GK)  # pivot tip

# Drainage slot caps on the exterior face of the bottom frame rail, 40 x 11 x 6 mm, two per bottom light.
for (y0, _), (y1, _) in [cell_sash] + [c for c, _ in cells_fixed[:2]]:
    for t in (0.2, 0.8):
        yc = y0 + (y1 - y0) * t
        P.add(box_faces((FX1, yc - 0.020, FZ0 + 0.008), (FX1 + 0.006, yc + 0.020, FZ0 + 0.019)))

set_mats(frame, [pvc, gasket, spacer])   # before write: clearing slots resets material indices
P.write(frame.data)
bevel(frame, 0.0012, 1, pvc_only=True)

# ---------- glass (helper object): 2 x 4 mm panes per light; outer face of the outer pane = rain slot ----------

gob = get_obj("Window_Glass", openings)
G = Parts()
for rect, gx0, gx1 in [(inner, SGX0, SGX1)] + [(c, GX0, GX1) for c, _ in cells_fixed]:
    (y0, z0), (y1, z1) = grow(rect, -0.005)
    G.add(box_faces((gx0, y0, z0), (gx0 + 0.004, y1, z1)))
    G.add(box_faces((gx1 - 0.004, y0, z0), (gx1, y1, z1)), [0, 0, 0, 1, 0, 0])   # face 3 = +x (outside)
set_mats(gob, [glass, rain])
G.write(gob.data, smooth=False)
gob.visible_shadow = False   # panes must not block sun/sky light entering the room

# ---------- reveal: lining that thickens the 10 cm wall slab to the real wall around the opening ----------

rev = get_obj("Window_Reveal", openings)
R = Parts()
RX0, RX1, RM = W + T_WIN, W + WALL_T, 0.15
R.add(solid_mesh([((RX0, WIN_Y0 - RM, WIN_Z0 - RM), (RX1, WIN_Y1 + RM, WIN_Z1 + RM))],
                 [((RX0 - 1, WIN_Y0, WIN_Z0), (RX1 + 1, WIN_Y1, WIN_Z1))]))
# exterior drip sill: 1.5 mm steel, falls 25 mm outward, 30 mm drip nose past the facade
fz, oz, ox = FZ0 - 0.003, WIN_Z0 - 0.005, RX1 + 0.035
v = [(FX1, WIN_Y0, fz - 0.0015), (ox, WIN_Y0, oz - 0.0015), (ox, WIN_Y1, oz - 0.0015), (FX1, WIN_Y1, fz - 0.0015),
     (FX1, WIN_Y0, fz), (ox, WIN_Y0, oz), (ox, WIN_Y1, oz), (FX1, WIN_Y1, fz)]
f = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
R.add((v, f), 1)
R.add(box_faces((ox, WIN_Y0, oz - 0.030), (ox + 0.0015, WIN_Y1, oz - 0.0015)), 1)
set_mats(rev, [wall_mat, flash])
R.write(rev.data, smooth=False)

# ---------- sill board ----------

sill = bpy.data.objects["Window_Sill"]
S = Parts()
# Board overhangs the wall face by SILL_OH with a SILL_EAR ear past the +y reveal, runs 12 mm under the frame.
# -y side: no ear, the board butts g1_trim's pilaster (x 6.37..6.5, y 0..0.20).
S.add(solid_mesh([((W - SILL_OH, WIN_Y0, WIN_Z0), (W, WIN_Y1 + SILL_EAR, WIN_Z0 + SILL_T)),
                  ((W, WIN_Y0, WIN_Z0), (FX0 + 0.012, WIN_Y1, WIN_Z0 + SILL_T))]))
set_mats(sill, [sill_mat])
S.write(sill.data)
bevel(sill, 0.006, 2)
