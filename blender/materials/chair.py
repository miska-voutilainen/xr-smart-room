# Chairs: Nowy Styl "ISO CR" stacking visitor chair (chrome flat-oval frame, black upholstered seat/back,
# black plastic covers). Rebuilds Chair_1 / Chair_2 from one shared mesh "Chair_Mesh".
# Dimensions from the Nowy Styl technical sheet (ISO CR: overall W545 D560 H820, seat H470, seat W470 D410-425,
# back W480 H330, feet 425 apart front-to-back) and retailer data (frame tube 30x15x2 mm flat oval).
# Origin: centre of the four feet on the floor, local +x = facing direction.
import math
import bpy
import bmesh
from mathutils import Vector, Matrix

# ponytail: real chairs are 545 wide, so the plan's 0.46 m spacing overlapped and Chair_2 hit the TV partition (y 2.5).
CHAIRS = {"Chair_1": (5.10, 1.60), "Chair_2": (5.10, 2.15)}  # integrator: fit desk 1.2x1.2 (x 5.28..6.48)
FRAME_Y = 0.2575          # side frame centreline (outer width 545)
OVAL = (0.015, 0.0075)    # flat-oval tube half sizes: lateral, in-plane (30 x 15 mm)

# ---------------- geometry ----------------


def axis_samples(h, r, inner):
    a = h - r
    t = r * math.tan(math.radians(22.5))
    mid = [-a + 2 * a * i / inner for i in range(inner + 1)] if a > 1e-6 else [0.0]
    return [-h, -a - t] + mid + [a + t, h]


def rounded_box(half, r, inner, puff=0.0):
    """Quad-only rounded box (cube grid projected onto an inflated inner box).
    Returns verts, faces, face centroids (before any later deformation)."""
    S = [axis_samples(half[i], r, inner[i]) for i in range(3)]
    A = [half[i] - r for i in range(3)]
    n = [len(s) for s in S]
    index, verts, faces = {}, [], []

    def vid(i, j, k):
        key = (i, j, k)
        if key not in index:
            p = Vector((S[0][i], S[1][j], S[2][k]))
            c = Vector([max(-A[d], min(A[d], p[d])) for d in range(3)])
            d = p - c
            q = c + d.normalized() * r if d.length > 1e-9 else c
            if puff and q.z > 0:
                q.z += puff * (1 - (q.x / half[0]) ** 2) * (1 - (q.y / half[1]) ** 2) * (q.z / half[2])
            index[key] = len(verts)
            verts.append(q)
        return index[key]

    for ax in range(3):
        b, c = (ax + 1) % 3, (ax + 2) % 3
        for side in (0, n[ax] - 1):
            for u in range(n[b] - 1):
                for v in range(n[c] - 1):
                    quad = []
                    for du, dv in ((0, 0), (1, 0), (1, 1), (0, 1)):
                        idx = [0, 0, 0]
                        idx[ax], idx[b], idx[c] = side, u + du, v + dv
                        quad.append(vid(*idx))
                    if side == 0:
                        quad.reverse()
                    faces.append(quad)
    cents = [sum((verts[i] for i in f), Vector()) / 4 for f in faces]
    return verts, faces, cents


def round_corners(v, hu, hv, rc, iu, iv, side=0):
    """Round the silhouette corners of a box in the (iu, iv) axis plane (square -> quarter disc).
    side=+1/-1 limits it to the corners at +iv / -iv."""
    for p in v:
        if side and p[iv] * side <= 0:
            continue
        cu, cv = math.copysign(hu - rc, p[iu]), math.copysign(hv - rc, p[iv])
        du, dv = p[iu] - cu, p[iv] - cv
        if du * cu > 0 and dv * cv > 0:
            k = max(abs(du), abs(dv)) / math.hypot(du, dv)
            p[iu], p[iv] = cu + du * k, cv + dv * k


def fillet(pts, R, steps=5):
    pts = [Vector(p) for p in pts]
    out = [pts[0]]
    for A, P, B in zip(pts, pts[1:], pts[2:]):
        dA, dB = (A - P).normalized(), (B - P).normalized()
        theta = dA.angle(dB)
        if theta > math.pi - 1e-3:
            out.append(P)
            continue
        t = min(R / math.tan(theta / 2), 0.45 * (A - P).length, 0.45 * (B - P).length)
        rr = t * math.tan(theta / 2)
        C = P + (dA + dB).normalized() * (rr / math.sin(theta / 2))
        u, v = P + dA * t - C, P + dB * t - C
        phi = u.angle(v)
        for s in range(steps + 1):
            f = s / steps
            out.append(C + (u * math.sin((1 - f) * phi) + v * math.sin(f * phi)) / math.sin(phi))
    out.append(pts[-1])
    return out


def tube(path, r, sides=8):
    """Swept round tube with quad caps (an octagon split into 3 quads)."""
    tans = []
    for i in range(len(path)):
        a, b = path[max(i - 1, 0)], path[min(i + 1, len(path) - 1)]
        tans.append((b - a).normalized())
    N = tans[0].orthogonal().normalized()
    verts, faces = [], []
    for i, (p, T) in enumerate(zip(path, tans)):
        if i:
            N = tans[i - 1].rotation_difference(T) @ N
        Bn = T.cross(N)
        for s in range(sides):
            ang = 2 * math.pi * s / sides
            verts.append(p + (N * math.cos(ang) + Bn * math.sin(ang)) * r)
    for i in range(len(path) - 1):
        for s in range(sides):
            a, b = i * sides + s, i * sides + (s + 1) % sides
            faces.append([a, b, b + sides, a + sides])
    last = (len(path) - 1) * sides
    faces += [[3, 2, 1, 0], [7, 6, 5, 4], [7, 4, 3, 0]]
    faces += [[last + q for q in f] for f in ([0, 1, 2, 3], [4, 5, 6, 7], [0, 3, 4, 7])]
    return verts, faces


def stadium(a, b, n=6):
    """Flat-oval section: two half circles (radius b) joined by flats; u lateral, v in-plane."""
    pts = []
    for sgn in (1, -1):
        for k in range(n):
            t = -math.pi / 2 + math.pi * k / (n - 1)
            pts.append((sgn * (a - b + b * math.cos(t)), sgn * b * math.sin(t)))
    return pts


def chamfer_rect(a, b, c):
    return [(a, -b + c), (a, b - c), (a - c, b), (-a + c, b), (-a, b - c), (-a, -b + c), (-a + c, -b), (a - c, -b)]


def sweep_xz(path, y, prof, flat_ends=()):
    """Sweep a section along a path lying in the plane y = const (u axis = lateral +y).
    flat_ends: (ring index, z) pairs; that ring is slid along the tube so it lies flat at height z."""
    n = len(prof)
    tans = [(path[min(i + 1, len(path) - 1)] - path[max(i - 1, 0)]).normalized() for i in range(len(path))]
    verts, faces = [], []
    for p, T in zip(path, tans):
        N = Vector((T.z, 0.0, -T.x))
        verts += [Vector((p.x, y, p.z)) + Vector((0, u, 0)) + N * v for u, v in prof]
    for ring, z in flat_ends:
        T = tans[ring]
        for k in range(ring * n, ring * n + n):
            verts[k] = verts[k] + T * ((z - verts[k].z) / T.z)
    for i in range(len(path) - 1):
        for k in range(n):
            a, b = i * n + k, i * n + (k + 1) % n
            faces.append([a, b, b + n, a + n])
    cap = [[0, k, k + 1, k + 2] for k in range(1, n - 2, 2)]
    last = (len(path) - 1) * n
    faces += [list(reversed(f)) for f in cap] + [[last + q for q in f] for f in cap]
    return verts, faces


def build_mesh(me):
    bm = bmesh.new()
    # material indices: 0 chrome, 1 fabric, 2 shell (black plastic)

    def add(verts, faces, mat_of_face):
        vs = [bm.verts.new(v) for v in verts]
        for fi, f in enumerate(faces):
            face = bm.faces.new([vs[i] for i in f])
            face.material_index = mat_of_face(fi)
            face.smooth = True

    # Seat: 470 wide x 427 deep, sits BETWEEN the side frames; dished across (sides 20 mm higher than the
    # centre, centre top at 470) and a front waterfall rolled down ~45 mm. Black plastic cover underneath.
    hx, hy, hz, x0, R, zc = 0.2135, 0.235, 0.025, 0.16, 0.13, 0.465
    v, f, nr = rounded_box((hx, hy, hz), 0.018, (8, 6, 1), puff=0.008)
    round_corners(v, hx, hy, 0.05, 0, 1)
    sv = []
    for p in v:
        x, y, dz = p.x + 0.0595, p.y, p.z
        if x > x0:  # roll the front edge down around an axis R below the seat mid-plane
            th = (x - x0) / R
            x, dz = x0 + (R + dz) * math.sin(th), (R + dz) * math.cos(th) - R
        sv.append(Vector((x, y, zc + dz - 0.02 * (1 - (y / hy) ** 2))))
    add(sv, f, lambda i: 2 if nr[i].z < -0.015 else 1)

    # Back: 480 x 330, curved in plan, arched top, reclined 12.5 deg; plastic cover on the rear with a raised
    # moulded panel (140 wide, 6 mm proud, lower 60 % of the back) as in the photos and the side drawing.
    rot = Matrix.Rotation(math.radians(-12.5), 3, "Y")
    ctr = Vector((-0.231, 0, 0.652))

    def place_back(p, front_pad):
        q = Vector((p.x + 0.4 * p.y * p.y, p.y, p.z))
        q.z += 0.008 * (1 - (p.y / 0.24) ** 2) * max(0.0, (p.z + 0.165) / 0.33)  # arched top edge
        if front_pad:
            q.x += 0.006 * (1 - (p.y / 0.24) ** 2) * max(p.x, 0) / 0.0225
        return rot @ q + ctr

    v, f, nr = rounded_box((0.0225, 0.24, 0.165), 0.018, (1, 8, 6))
    round_corners(v, 0.24, 0.165, 0.022, 1, 2)
    round_corners(v, 0.24, 0.165, 0.065, 1, 2, side=1)
    add([place_back(p, True) for p in v], f, lambda i: 2 if nr[i].x < -0.012 else 1)
    v, f, _ = rounded_box((0.006, 0.07, 0.10), 0.004, (1, 1, 2))
    add([place_back(p + Vector((-0.0225, 0, -0.04)), False) for p in v], f, lambda i: 2)

    # Side frames: one bent flat-oval tube per side: rear foot -> rear leg (splayed back) -> top rail at seat
    # level -> front leg (splayed forward) -> front foot. Black plastic glides on the feet.
    prof = stadium(*OVAL)
    rear_foot, rear_top = Vector((-0.205, 0, 0)), Vector((-0.122, 0, 0.483))
    front_foot, front_top = Vector((0.206, 0, 0)), Vector((0.128, 0, 0.483))
    path = fillet([rear_foot, rear_foot.lerp(rear_top, 0.015 / 0.483), rear_top, front_top,
                   front_foot.lerp(front_top, 0.015 / 0.483), front_foot], 0.03, steps=6)
    nring, nseg = len(prof), len(path) - 1
    for sy in (-1, 1):
        add(*sweep_xz(path, sy * FRAME_Y, prof, ((0, 0.0), (1, 0.015), (nseg - 1, 0.015), (nseg, 0.0))),
            lambda i: 2 if i < nring or nseg - 1 <= i // nring < nseg or i >= nseg * nring else 0)

    # Back supports: two flat chrome bars (25 x 8) bolted under the seat, bent up behind it into the back.
    bar = fillet([Vector((-0.02, 0, 0.433)), Vector((-0.162, 0, 0.433)), Vector((-0.1765, 0, 0.50)),
                  Vector((-0.2025, 0, 0.617))], 0.035, steps=6)
    for sy in (-1, 1):
        add(*sweep_xz(bar, sy * 0.215, chamfer_rect(0.0125, 0.004, 0.0025)), lambda i: 0)

    # Black stacking buffers on the inner face of each leg, just under the rail (circles in the side drawing).
    for sy in (-1, 1):
        for lx in (-0.1328, 0.1382):
            yi = sy * (FRAME_Y - OVAL[0])
            add(*tube([Vector((lx, yi + sy * 0.004, 0.42)), Vector((lx, yi - sy * 0.016, 0.42))], 0.007),
                lambda i: 2)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    me.update()


# ---------------- materials ----------------


def new_mat(name):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(bsdf.outputs[0], out.inputs["Surface"])
    coord = nt.nodes.new("ShaderNodeTexCoord")
    return m, nt, bsdf, coord


def node(nt, kind, **inputs):
    n = nt.nodes.new(kind)
    for k, val in inputs.items():
        if k.startswith("_"):
            setattr(n, k[1:], val)
        else:
            n.inputs[k].default_value = val
    return n


def math_node(nt, op, a, b=None, clamp=False):
    n = nt.nodes.new("ShaderNodeMath")
    n.operation = op
    n.use_clamp = clamp
    for i, x in enumerate((a, b)):
        if x is None:
            continue
        if isinstance(x, (int, float)):
            n.inputs[i].default_value = x
        else:
            nt.links.new(x, n.inputs[i])
    return n.outputs[0]


def maprange(nt, src, a, b, c, d):
    n = node(nt, "ShaderNodeMapRange")
    n.inputs["From Min"].default_value, n.inputs["From Max"].default_value = a, b
    n.inputs["To Min"].default_value, n.inputs["To Max"].default_value = c, d
    nt.links.new(src, n.inputs["Value"])
    return n.outputs[0]


def chrome():
    m, nt, bsdf, co = new_mat("Chair_Chrome")
    bsdf.inputs["Base Color"].default_value = (0.78, 0.78, 0.80, 1)
    bsdf.inputs["Metallic"].default_value = 1.0
    # Fine wipe marks / micro scratches: stretched noise drives roughness 0.06..0.16.
    mp = node(nt, "ShaderNodeMapping", Scale=(1.0, 1.0, 12.0))
    nt.links.new(co.outputs["Object"], mp.inputs["Vector"])
    scr = node(nt, "ShaderNodeTexNoise", Scale=90.0, Detail=6.0, Roughness=0.65)
    nt.links.new(mp.outputs[0], scr.inputs["Vector"])
    blot = node(nt, "ShaderNodeTexNoise", Scale=18.0, Detail=3.0)
    nt.links.new(co.outputs["Object"], blot.inputs["Vector"])
    r = math_node(nt, "ADD", maprange(nt, scr.outputs["Fac"], 0.45, 0.75, 0.0, 0.06),
                  maprange(nt, blot.outputs["Fac"], 0.35, 0.7, 0.06, 0.10))
    nt.links.new(r, bsdf.inputs["Roughness"])
    bump = node(nt, "ShaderNodeBump", Strength=0.04, Distance=0.0005)
    nt.links.new(scr.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs[0], bsdf.inputs["Normal"])
    return m


def fabric():
    m, nt, bsdf, co = new_mat("Chair_Fabric")
    bsdf.inputs["Roughness"].default_value = 0.72
    bsdf.inputs["Sheen Weight"].default_value = 0.2
    bsdf.inputs["Sheen Roughness"].default_value = 0.35
    bsdf.inputs["Sheen Tint"].default_value = (0.25, 0.25, 0.27, 1)
    bsdf.inputs["Specular IOR Level"].default_value = 0.35
    # Fine plain weave (~1.2 mm pitch) from two crossed band waves.
    weave = []
    for axis in ("X", "Z", "Y"):
        w = node(nt, "ShaderNodeTexWave", Scale=420.0, Distortion=1.5, _bands_direction=axis)
        w.inputs["Detail"].default_value = 1.0
        nt.links.new(co.outputs["Object"], w.inputs["Vector"])
        weave.append(w.outputs["Fac"])
    h = math_node(nt, "MULTIPLY", math_node(nt, "MAXIMUM", weave[0], weave[1]), weave[2])
    fuzz = node(nt, "ShaderNodeTexNoise", Scale=900.0, Detail=2.0)
    nt.links.new(co.outputs["Object"], fuzz.inputs["Vector"])
    h = math_node(nt, "ADD", h, math_node(nt, "MULTIPLY", fuzz.outputs["Fac"], 0.5))
    bump = node(nt, "ShaderNodeBump", Strength=0.35, Distance=0.0004)
    nt.links.new(h, bump.inputs["Height"])
    # Slightly uneven black (dust, sitting wear), plus a faint weave darkening.
    mott = node(nt, "ShaderNodeTexNoise", Scale=9.0, Detail=4.0)
    nt.links.new(co.outputs["Object"], mott.inputs["Vector"])
    v = math_node(nt, "MULTIPLY", maprange(nt, mott.outputs["Fac"], 0.3, 0.7, 0.014, 0.024),
                  maprange(nt, h, 0.0, 1.5, 0.85, 1.1))
    col = node(nt, "ShaderNodeCombineColor")
    for i in range(3):
        nt.links.new(v, col.inputs[i])
    nt.links.new(col.outputs[0], bsdf.inputs["Base Color"])
    nt.links.new(maprange(nt, mott.outputs["Fac"], 0.3, 0.7, 0.68, 0.78), bsdf.inputs["Roughness"])
    nt.links.new(bump.outputs[0], bsdf.inputs["Normal"])
    return m


def shell():
    m, nt, bsdf, co = new_mat("Chair_Shell")
    bsdf.inputs["Base Color"].default_value = (0.018, 0.018, 0.019, 1)
    sep = node(nt, "ShaderNodeSeparateXYZ")
    nt.links.new(co.outputs["Object"], sep.inputs[0])
    y, z = sep.outputs["Y"], sep.outputs["Z"]
    # Vertical ribs inside the raised back panel (panel itself is geometry; coords match build_mesh).
    def box1d(c, lo, hi, soft=0.006):
        a = maprange(nt, c, lo - soft, lo + soft, 0, 1)
        b = maprange(nt, c, hi - soft, hi + soft, 1, 0)
        return math_node(nt, "MINIMUM", a, b)
    panel = math_node(nt, "MULTIPLY", box1d(y, -0.07, 0.07), box1d(z, 0.515, 0.71))
    ribs = math_node(nt, "SINE", math_node(nt, "MULTIPLY", y, 2 * math.pi / 0.03))
    ribs = math_node(nt, "MULTIPLY", math_node(nt, "ABSOLUTE", ribs), 0.4)
    inner = math_node(nt, "MULTIPLY", box1d(y, -0.055, 0.055), box1d(z, 0.53, 0.695))
    emboss = math_node(nt, "SUBTRACT", panel, math_node(nt, "MULTIPLY", inner, math_node(nt, "SUBTRACT", 0.6, ribs)))
    # Fine moulded grain.
    grain = node(nt, "ShaderNodeTexNoise", Scale=1400.0, Detail=2.0)
    nt.links.new(co.outputs["Object"], grain.inputs["Vector"])
    bump = node(nt, "ShaderNodeBump", Strength=0.8, Distance=0.002)
    nt.links.new(emboss, bump.inputs["Height"])
    bump2 = node(nt, "ShaderNodeBump", Strength=0.25, Distance=0.0002)
    nt.links.new(grain.outputs["Fac"], bump2.inputs["Height"])
    nt.links.new(bump.outputs[0], bump2.inputs["Normal"])
    nt.links.new(bump2.outputs[0], bsdf.inputs["Normal"])
    scuff = node(nt, "ShaderNodeTexNoise", Scale=25.0, Detail=5.0)
    nt.links.new(co.outputs["Object"], scuff.inputs["Vector"])
    nt.links.new(maprange(nt, scuff.outputs["Fac"], 0.3, 0.7, 0.42, 0.58), bsdf.inputs["Roughness"])
    return m


# ---------------- apply ----------------

me = bpy.data.meshes.get("Chair_Mesh") or bpy.data.meshes.new("Chair_Mesh")
me.materials.clear()  # must precede build_mesh: clearing slots resets face material indices
for mat in (chrome(), fabric(), shell()):
    me.materials.append(mat)
build_mesh(me)

for name, (cx, cy) in CHAIRS.items():
    ob = bpy.data.objects.get(name)
    if ob is None:
        continue
    old = ob.data
    ob.data = me
    ob.location = (cx, cy, 0.0)
    ob.rotation_euler = (0, 0, 0)
    for mod in list(ob.modifiers):
        ob.modifiers.remove(mod)
    if old is not me and old.users == 0:
        bpy.data.meshes.remove(old)
