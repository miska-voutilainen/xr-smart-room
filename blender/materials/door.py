# Door set: Nordic painted-timber glazed door (rebated frame, flush leaf with raised glazing bead, solid
# inactive side panel), magenta satin paint, stainless lever + cylinder rose, 4 surface plate lift-off hinges,
# armoured cable loop (access control), black rebate seal, oak threshold.
# Photos 122224 / 120945 (inside), 150319 / 150325 (hinge side, leaf open): the leaf swings OUTWARD into the
# corridor (x < -0.10), ~90 deg, hinged on the low-y jamb. The hand-drawn plan shows an inward swing: deviation.
# No door closer is visible in any photo (frame head and leaf top bare on the room side) -> none modelled.
# Runs after build_room.py (via apply_materials.py). Idempotent. Touches only Door_* objects.
import math
import bpy

DOOR_Y0, DOOR_H = 1.15, 2.10                  # wall opening y 1.15..2.30, z 0..2.10 (build_room.py)
PILLAR_Y = 2.50 - 0.20
T, F = 0.10, 0.05                             # wall thickness, frame face width
FX0, FX1 = -T, -0.040                         # frame depth: set at the corridor face, 40 mm plaster reveal room side
STOP_X0, STOP_W = -0.056, 0.012               # rebate stop (room side of the leaf) and how far it overlaps the leaf
SEAL_X0 = -0.059                              # 3 mm black seal on the stop face
J0, J1 = DOOR_Y0 + F, PILLAR_Y - F            # clear inside the frame y 1.20..2.25
HEAD_Z = DOOR_H - F                           # underside of the frame head 2.05
MEET_Y = 1.95                                 # leaf / side panel meeting line (122224: leaf 75 : panel 30)

# Leaf: Door_Leaf origin = hinge pin axis (world), closed pose = rotation 0, opened by +DOOR_OPEN_DEG about +z.
AX, AY = FX0 - 0.007, J0                      # pin 7 mm proud of the corridor face, on the jamb rebate line
DOOR_OPEN_DEG = 90.0                          # photo pose (122224: room face just visible edge-on, 150325)
# Leaf-local coords: width along +y, thickness along +x (room face at +x), z = world z.
LX0, LX1 = FX0 - AX, SEAL_X0 - AX             # leaf faces 0.007 .. 0.048 (41 mm leaf)
LY0, LEAF = 0.003, MEET_Y - 0.002 - AY        # 3 mm hinge gap, lock edge at 0.748
LZ0, LZ1 = 0.015, HEAD_Z - 0.003              # 15 mm over the threshold, 3 mm under the head
LEAF_T = LX1 - LX0

GY0, GY1, GZ0, GZ1 = 0.14, LEAF - 0.14, 0.255, LZ1 - 0.13  # glass sight: stiles 14, top rail 13, bottom rail 24
HY, HZ = LEAF - 0.065, 1.05                   # lever spindle (122224: 1.05 m)
CYL_DZ = 0.075                                # cylinder rose below the lever (122224 / 150325)
HINGES_Z = (1.92, 1.73, 1.08, 0.48)           # hinge centres measured on 122224 (frame-on view)
LOOP_Z = (0.62, 1.00)                         # armoured loop: frame end / leaf end (122224, 150325)


# ---------- mesh helpers ----------

def solid_mesh(solids, holes=()):
    """Boolean-free all-quad manifold union of boxes minus holes (same as build_room.py)."""
    axes = [sorted({round(b[s][a], 4) for b in (*solids, *holes) for s in (0, 1)}) for a in range(3)]

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


def rounded_box(center, half, cuts=4, p=3.0):
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


def merge(*parts):
    verts, faces = [], []
    for v, f in parts:
        faces += [tuple(i + len(verts) for i in q) for q in f]
        verts += v
    return verts, faces


def tube(path, r, seg=8, caps=True):
    """Quad tube along a polyline (parallel-transport-free: fine for gentle bends), n-gon end caps."""
    verts, faces = [], []
    n = len(path)
    for i, p in enumerate(path):
        a, b = path[max(i - 1, 0)], path[min(i + 1, n - 1)]
        t = [b[k] - a[k] for k in range(3)]
        L = math.sqrt(sum(c * c for c in t))
        t = [c / L for c in t]
        ref = (0, 0, 1) if abs(t[2]) < 0.9 else (1, 0, 0)
        u = [t[1] * ref[2] - t[2] * ref[1], t[2] * ref[0] - t[0] * ref[2], t[0] * ref[1] - t[1] * ref[0]]
        L = math.sqrt(sum(c * c for c in u))
        u = [c / L for c in u]
        w = [t[1] * u[2] - t[2] * u[1], t[2] * u[0] - t[0] * u[2], t[0] * u[1] - t[1] * u[0]]
        for s in range(seg):
            ang = 2 * math.pi * s / seg
            verts.append(tuple(p[k] + r * (math.cos(ang) * u[k] + math.sin(ang) * w[k]) for k in range(3)))
    for i in range(n - 1):
        for s in range(seg):
            s1 = (s + 1) % seg
            faces.append((i * seg + s, i * seg + s1, (i + 1) * seg + s1, (i + 1) * seg + s))
    if caps:
        faces.append(tuple(reversed(range(seg))))
        faces.append(tuple((n - 1) * seg + s for s in range(seg)))
    return verts, faces


def cyl(c, r, h0, h1, axis=2, seg=12):
    """Closed cylinder along world axis `axis` through point c, from h0 to h1 (offsets along that axis)."""
    a = [0, 0, 0]
    a[axis] = 1
    p0 = tuple(c[k] + a[k] * h0 for k in range(3))
    p1 = tuple(c[k] + a[k] * h1 for k in range(3))
    return tube([p0, p1], r, seg)


def bezier(p0, p1, p2, p3, n=10):
    return [tuple((1 - t) ** 3 * p0[k] + 3 * (1 - t) ** 2 * t * p1[k] + 3 * (1 - t) * t * t * p2[k] + t ** 3 * p3[k]
                  for k in range(3)) for t in (i / n for i in range(n + 1))]


def set_mesh(ob, data, mat, smooth=False):
    me = ob.data
    me.clear_geometry()
    me.from_pydata(data[0], [], data[1])
    me.validate()
    me.materials.clear()
    me.materials.append(mat)
    if smooth:
        me.shade_smooth()


def bevel(ob, width, segments=2):
    mod = ob.modifiers.get("Door_Bevel") or ob.modifiers.new("Door_Bevel", "BEVEL")
    mod.width = width
    mod.segments = segments
    mod.limit_method = "ANGLE"
    mod.angle_limit = math.radians(40)
    mod.harden_normals = True
    ob.data.shade_smooth()


def helper(name, parent=None):
    ob = bpy.data.objects.get(name)
    if ob is None:
        me = bpy.data.meshes.get(name) or bpy.data.meshes.new(name)
        ob = bpy.data.objects.new(name, me)
    coll = bpy.data.collections["Openings"]
    if coll not in ob.users_collection:
        coll.objects.link(ob)
    if parent:
        ob.parent = parent
        ob.matrix_parent_inverse.identity()
        ob.location = (0, 0, 0)
        ob.rotation_euler = (0, 0, 0)
    return ob


# ---------- material helpers ----------

def new_mat(name):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    m.node_tree.nodes.clear()
    nt = m.node_tree
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    out.location = (600, 0)
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (300, 0)
    nt.links.new(bsdf.outputs[0], out.inputs["Surface"])
    return m, nt, bsdf, out


def node(nt, kind, loc=(0, 0), **inputs):
    n = nt.nodes.new(kind)
    n.location = loc
    for k, v in inputs.items():
        n.inputs[k].default_value = v
    return n


def noise(nt, src, scale, detail=2.0, loc=(0, 0), vector=None):
    n = node(nt, "ShaderNodeTexNoise", loc, Scale=scale, Detail=detail)
    nt.links.new(vector or src.outputs["Object"], n.inputs["Vector"])
    return n


def map_range(nt, sock, a, b, c, d, loc=(0, 0)):
    n = node(nt, "ShaderNodeMapRange", loc)
    n.inputs[1].default_value, n.inputs[2].default_value = a, b
    n.inputs[3].default_value, n.inputs[4].default_value = c, d
    nt.links.new(sock, n.inputs[0])
    return n


PINK = (0.56, 0.012, 0.165)   # linear; ~sRGB #C41A71 albedo, renders as the photo telemagenta under AgX


def paint_material(name, wear):
    m, nt, bsdf, out = new_mat(name)
    m.diffuse_color = (*PINK, 1)
    tc = node(nt, "ShaderNodeTexCoord", (-1400, 0))
    # very low-frequency tone drift (repainting / roller marks)
    drift = noise(nt, tc, 3.0, 3.0, (-1100, 300))
    tone = map_range(nt, drift.outputs["Fac"], 0.3, 0.7, 0.96, 1.04, (-850, 300))
    col = node(nt, "ShaderNodeMix", (-600, 300))
    col.data_type = "RGBA"
    col.blend_type = "MULTIPLY"
    col.inputs["Factor"].default_value = 1.0
    col.inputs[6].default_value = (*PINK, 1)
    nt.links.new(tone.outputs[0], col.inputs[7])
    # satin roughness with micro variation
    rn = noise(nt, tc, 60.0, 4.0, (-1100, 0))
    rough = map_range(nt, rn.outputs["Fac"], 0.3, 0.7, 0.36, 0.46, (-850, 0))
    # orange peel bump
    peel = noise(nt, tc, 450.0, 2.0, (-1100, -300))
    bump = node(nt, "ShaderNodeBump", (-300, -300), Strength=0.15, Distance=0.0004)
    nt.links.new(peel.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs[0], bsdf.inputs["Normal"])
    color_sock, rough_sock = col.outputs[2], rough.outputs[0]
    if wear:
        # scuffs only on the lock edge of the leaf, around handle height (leaf-local object coords)
        sep = node(nt, "ShaderNodeSeparateXYZ", (-1100, -650))
        nt.links.new(tc.outputs["Object"], sep.inputs[0])
        edge = map_range(nt, sep.outputs["Y"], LEAF - 0.035, LEAF - 0.002, 0.0, 1.0, (-900, -600))
        dz = node(nt, "ShaderNodeMath", (-900, -800))
        dz.inputs[1].default_value = HZ
        dz.operation = "SUBTRACT"
        nt.links.new(sep.outputs["Z"], dz.inputs[0])
        dz_abs = node(nt, "ShaderNodeMath", (-750, -800))
        dz_abs.operation = "ABSOLUTE"
        nt.links.new(dz.outputs[0], dz_abs.inputs[0])
        band = map_range(nt, dz_abs.outputs[0], 0.15, 0.40, 1.0, 0.0, (-600, -800))
        wn = noise(nt, tc, 90.0, 6.0, (-900, -1000))
        spots = map_range(nt, wn.outputs["Fac"], 0.56, 0.66, 0.0, 1.0, (-600, -1000))
        m1 = node(nt, "ShaderNodeMath", (-400, -700))
        m1.operation = "MULTIPLY"
        nt.links.new(edge.outputs[0], m1.inputs[0])
        nt.links.new(band.outputs[0], m1.inputs[1])
        mask = node(nt, "ShaderNodeMath", (-250, -700))
        mask.operation = "MULTIPLY"
        mask.use_clamp = True
        nt.links.new(m1.outputs[0], mask.inputs[0])
        nt.links.new(spots.outputs[0], mask.inputs[1])
        wc = node(nt, "ShaderNodeMix", (-100, 200))
        wc.data_type = "RGBA"
        wc.inputs[7].default_value = (0.36, 0.05, 0.14, 1)   # rubbed, dulled pink + hand grime
        nt.links.new(mask.outputs[0], wc.inputs["Factor"])
        nt.links.new(color_sock, wc.inputs[6])
        wr = node(nt, "ShaderNodeMix", (-100, 0))
        wr.inputs[3].default_value = 0.55
        nt.links.new(mask.outputs[0], wr.inputs["Factor"])
        nt.links.new(rough_sock, wr.inputs[2])
        color_sock, rough_sock = wc.outputs[2], wr.outputs[0]
    nt.links.new(color_sock, bsdf.inputs["Base Color"])
    nt.links.new(rough_sock, bsdf.inputs["Roughness"])
    return m


def steel_material():
    m, nt, bsdf, out = new_mat("Door_Steel")
    m.diffuse_color = (0.6, 0.6, 0.6, 1)
    bsdf.inputs["Metallic"].default_value = 1.0
    bsdf.inputs["Base Color"].default_value = (0.62, 0.62, 0.61, 1)
    tc = node(nt, "ShaderNodeTexCoord", (-1000, 0))
    # brushing along the lever (leaf-local y): stretch the noise across x/z
    sc = node(nt, "ShaderNodeVectorMath", (-800, 0))
    sc.operation = "MULTIPLY"
    sc.inputs[1].default_value = (300.0, 3.0, 300.0)
    nt.links.new(tc.outputs["Object"], sc.inputs[0])
    br = node(nt, "ShaderNodeTexNoise", (-600, 0), Scale=1.0, Detail=6.0)
    nt.links.new(sc.outputs[0], br.inputs["Vector"])
    rough = map_range(nt, br.outputs["Fac"], 0.3, 0.7, 0.18, 0.32, (-350, 0))
    nt.links.new(rough.outputs[0], bsdf.inputs["Roughness"])
    bump = node(nt, "ShaderNodeBump", (-300, -250), Strength=0.04, Distance=0.0002)
    nt.links.new(br.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs[0], bsdf.inputs["Normal"])
    return m


def glass_material():
    m, nt, bsdf, out = new_mat("Door_Glass")
    m.diffuse_color = (0.8, 0.9, 0.9, 0.3)
    bsdf.inputs["Base Color"].default_value = (0.93, 0.97, 0.955, 1)   # float glass, faint green
    bsdf.inputs["Roughness"].default_value = 0.0
    bsdf.inputs["IOR"].default_value = 1.52
    bsdf.inputs["Transmission Weight"].default_value = 1.0
    # let shadow rays through so the pane does not cast a black shadow (no caustics needed)
    lp = node(nt, "ShaderNodeLightPath", (0, 300))
    tr = node(nt, "ShaderNodeBsdfTransparent", (300, 200))
    tr.inputs["Color"].default_value = (0.9, 0.95, 0.93, 1)
    mix = node(nt, "ShaderNodeMixShader", (450, 100))
    nt.links.new(lp.outputs["Is Shadow Ray"], mix.inputs[0])
    nt.links.new(bsdf.outputs[0], mix.inputs[1])
    nt.links.new(tr.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    return m


def oak_material():
    m, nt, bsdf, out = new_mat("Door_Oak")
    m.diffuse_color = (0.45, 0.25, 0.10, 1)
    tc = node(nt, "ShaderNodeTexCoord", (-1200, 0))
    # grain runs along the strip (world y): squash coordinates across it
    sc = node(nt, "ShaderNodeVectorMath", (-1000, 0))
    sc.operation = "MULTIPLY"
    sc.inputs[1].default_value = (1.0, 0.06, 1.0)
    nt.links.new(tc.outputs["Object"], sc.inputs[0])
    wave = node(nt, "ShaderNodeTexWave", (-800, 0), Scale=60.0, Distortion=6.0, Detail=3.0)
    wave.bands_direction = "X"
    nt.links.new(sc.outputs[0], wave.inputs["Vector"])
    fine = noise(nt, tc, 1.0, 4.0, (-800, -250), vector=sc.outputs[0])
    fine.inputs["Scale"].default_value = 400.0
    ramp = node(nt, "ShaderNodeValToRGB", (-550, 0))
    ramp.color_ramp.elements[0].color = (0.36, 0.19, 0.075, 1)
    ramp.color_ramp.elements[1].color = (0.56, 0.33, 0.15, 1)
    mixf = node(nt, "ShaderNodeMath", (-650, 0))
    mixf.operation = "MULTIPLY_ADD"
    mixf.inputs[1].default_value = 0.6
    nt.links.new(wave.outputs["Fac"], mixf.inputs[0])
    nt.links.new(fine.outputs["Fac"], mixf.inputs[2])
    nt.links.new(mixf.outputs[0], ramp.inputs[0])
    nt.links.new(ramp.outputs[0], bsdf.inputs["Base Color"])
    rough = map_range(nt, fine.outputs["Fac"], 0.3, 0.7, 0.38, 0.55, (-300, -250))
    nt.links.new(rough.outputs[0], bsdf.inputs["Roughness"])
    bsdf.inputs["Coat Weight"].default_value = 0.25
    bsdf.inputs["Coat Roughness"].default_value = 0.3
    bump = node(nt, "ShaderNodeBump", (0, -300), Strength=0.08, Distance=0.0005)
    nt.links.new(wave.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs[0], bsdf.inputs["Normal"])
    return m




def seal_material():
    m, nt, bsdf, out = new_mat("Door_Seal")      # black EPDM rebate seal + frame screw-hole caps
    m.diffuse_color = (0.02, 0.02, 0.02, 1)
    bsdf.inputs["Base Color"].default_value = (0.018, 0.018, 0.02, 1)
    bsdf.inputs["Roughness"].default_value = 0.6
    return m


def box(lo, hi):
    (x0, y0, z0), (x1, y1, z1) = lo, hi
    v = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
         (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    return v, [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]


def to_world(p, deg=DOOR_OPEN_DEG):
    """Leaf-local point -> world, for the leaf in its open pose."""
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return (AX + p[0] * c - p[1] * s, AY + p[0] * s + p[1] * c, p[2])


# ---------- build ----------

paint = paint_material("Door_Paint", wear=False)
paint_leaf = paint_material("Door_Paint_Leaf", wear=True)
steel, glass, oak, seal = steel_material(), glass_material(), oak_material(), seal_material()

frame = bpy.data.objects["Door_Frame"]
panel = bpy.data.objects["Door_Fixed_Panel"]
leaf = bpy.data.objects["Door_Leaf"]

# Frame: rebated timber frame 50 x 60 mm set at the corridor face (the wall's 40 mm room-side reveal stays
# plaster, as in 122224 / 150319), stop 16 x 12 mm on the room side. No mullion: the leaf meets the side panel.
set_mesh(frame, solid_mesh([
    ((FX0, DOOR_Y0, 0), (FX1, J0, DOOR_H)),                                  # hinge jamb
    ((FX0, J1, 0), (FX1, PILLAR_Y, DOOR_H)),                                 # jamb at the pillar
    ((FX0, DOOR_Y0, HEAD_Z), (FX1, PILLAR_Y, DOOR_H)),                       # head
    ((STOP_X0, J0, 0.012), (FX1, J0 + STOP_W, HEAD_Z)),                     # stops
    ((STOP_X0, J1 - STOP_W, 0.012), (FX1, J1, HEAD_Z)),
    ((STOP_X0, J0, HEAD_Z - STOP_W), (FX1, J1, HEAD_Z)),
]), paint)
bevel(frame, 0.002)

# Side panel: solid flush panel in the leaf plane (an inactive leaf in practice), astragal for the active leaf.
set_mesh(panel, solid_mesh([
    ((FX0, MEET_Y + 0.002, LZ0), (SEAL_X0, J1 - 0.003, LZ1)),
    ((SEAL_X0, MEET_Y - 0.014, LZ0), (SEAL_X0 + 0.014, MEET_Y + 0.020, LZ1)),   # astragal / meeting stop
]), paint)
bevel(panel, 0.002)

# Leaf: flush slab with the glass opening and a raised 2-step glazing bead on both faces (150325).
leaf.location = (AX, AY, 0.0)
leaf.rotation_euler = (0.0, 0.0, math.radians(DOOR_OPEN_DEG))
leaf["xr_interactable"] = "hinge"
leaf["door_closed_rot_z_deg"] = 0.0              # closed pose; outward (corridor) swing = positive z rotation
leaf["door_open_deg"] = DOOR_OPEN_DEG             # pose saved in the file (photo 150325 / 122224)
hole = ((LX0 - 0.02, GY0, GZ0), (LX1 + 0.02, GY1, GZ1))
beads = []
for w, d in ((0.024, 0.004), (0.012, 0.009)):
    lo, hi = (GY0 - w, GZ0 - w), (GY1 + w, GZ1 + w)
    beads += [((LX0 - d, lo[0], lo[1]), (LX0, hi[0], hi[1])),
              ((LX1, lo[0], lo[1]), (LX1 + d, hi[0], hi[1]))]
set_mesh(leaf, solid_mesh([((LX0, LY0, LZ0), (LX1, LEAF, LZ1))] + beads, [hole]), paint_leaf)
bevel(leaf, 0.0015)   # < half the 4 mm bead step: no collapsed (zero-area) bevel faces

pane = helper("Door_Glass", leaf)
e = 0.006   # pane edges hidden in the slab
xm = (LX0 + LX1) / 2
set_mesh(pane, solid_mesh([((xm - 0.004, GY0 - e, GZ0 - e), (xm + 0.004, GY1 + e, GZ1 + e))]), glass)

# Leaf hardware: lever + rose + cylinder rose on both faces; leaf halves of the 4 plate hinges
# (Ø13 pin knuckle on the axis = local origin, 28 x 116 mm plate screwed to the leaf edge).
parts = []
for s in (1, -1):
    fx = LX1 if s > 0 else LX0
    parts += [
        rounded_box((fx + s * 0.005, HY, HZ), (0.006, 0.026, 0.026), 3, 2.0),            # rose
        rounded_box((fx + s * 0.032, HY, HZ), (0.026, 0.0085, 0.0085), 2, 2.4),          # neck
        rounded_box((fx + s * 0.058, HY - 0.055, HZ), (0.0095, 0.068, 0.0105), 3, 3.0),  # lever, points to hinge
        rounded_box((fx + s * 0.004, HY, HZ - CYL_DZ), (0.004, 0.019, 0.019), 2, 2.0),   # cylinder rose
    ]
for z in HINGES_Z:
    parts += [cyl((0, 0, z), 0.0065, 0.0, 0.05),                                         # upper knuckle
              box((0.004, LY0 - 0.001, z - 0.058), (0.032, LY0 + 0.0015, z + 0.058))]     # leaf plate
hw = helper("Door_Hardware", leaf)
set_mesh(hw, merge(*parts), steel, smooth=True)

# Static hardware on the frame: hinge frame halves + plates on the jamb rebate face, armoured cable loop.
parts = []
for z in HINGES_Z:
    parts += [cyl((AX, AY, z), 0.0065, -0.05, -0.001),                                   # lower knuckle
              cyl((AX, AY, z), 0.0035, -0.058, -0.05, seg=8),                            # pin tip
              box((AX + 0.004, J0 - 0.0015, z - 0.058), (AX + 0.032, J0 + 0.001, z + 0.058))]
hwf = helper("Door_Hinges_Frame")
set_mesh(hwf, merge(*parts), steel, smooth=True)

# Armoured door loop (400 mm stainless hose Ø10, two end caps) between jamb and leaf edge, posed for the
# photographed ~90 deg opening. Static: it does not follow the leaf in Unity.
fc = (FX0 + 0.022, J0 + 0.006)                                     # frame cap centre (x, y)
lc = to_world((0.028, LY0 - 0.006, 0))                             # leaf cap centre, on the leaf edge
p0 = (fc[0], fc[1], LOOP_Z[0] + 0.035)
p3 = (lc[0], lc[1], LOOP_Z[1] - 0.035)
loop = merge(
    rounded_box((fc[0], fc[1], LOOP_Z[0]), (0.008, 0.006, 0.035), 2, 4.0),
    rounded_box((lc[0], lc[1], LOOP_Z[1]), (0.006, 0.008, 0.035), 2, 4.0),
    tube(bezier(p0, (p0[0] + 0.03, p0[1], p0[2] + 0.13), (p3[0] + 0.03, p3[1], p3[2] - 0.13), p3, 12), 0.005, 8))
lp = helper("Door_CableLoop")
set_mesh(lp, loop, steel, smooth=True)

# Black rebate seal on the stop faces + screw-hole caps on the jamb rebate faces (150325 / 122224).
parts = [box((SEAL_X0, J0, LZ0), (STOP_X0, J0 + STOP_W - 0.002, HEAD_Z)),
         box((SEAL_X0, J1 - STOP_W + 0.002, LZ0), (STOP_X0, J1, HEAD_Z)),
         box((SEAL_X0, J0, HEAD_Z - STOP_W + 0.002), (STOP_X0, J1, HEAD_Z))]
for z in (0.25, 0.80, 1.40, 2.00):
    parts.append(cyl((FX0 + 0.024, J0, z), 0.005, 0.0, 0.0008, axis=1, seg=8))
    parts.append(cyl((FX0 + 0.024, J1, z), 0.005, -0.0008, 0.0, axis=1, seg=8))
sl = helper("Door_Seal")
set_mesh(sl, merge(*parts), seal)

# Oak threshold strip across the whole opening between the jambs, flush with the room-side wall face.
th = helper("Door_Threshold")
set_mesh(th, solid_mesh([((FX0 + 0.002, J0, 0.0), (-0.002, J1, 0.012))]), oak)
bevel(th, 0.002)

print("DOOR MATERIALS OK")
