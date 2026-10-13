# Desk corner props (photos 112212, 122244, 150338): objects Deskprops_*, materials Deskprops_*.
#   Deskprops_Remote      Samsung TV remote on the niche ledge (XR grab object, origin = geometric centre)
#   Deskprops_Camera      Aqara Camera Hub G3 with silicone cat ears on the desk (XR grab object, origin = bottom centre)
#   Deskprops_PowerStrip  white 3-way Schuko strip standing in the niche corner + black TV plug + USB charger
#   Deskprops_CableTV / _CableStrip / _CableUSB   swept tube cables (TV power, strip cord, camera USB with coil)
# Real dimensions:
#   Aqara G3: 123.4 x 85.1 x 67.8 mm (H x W x D), ears are removable silicone (vesternet.com, eftm.com).
#   Samsung AA59-00741A class remote: 178 x 45 x 24 mm (galaxus.it).
#   Brennenstuhl Eco-Line class 3-way strip: ~205 mm long; 48 x 40 mm section scaled from the remote in tvside 122244.
# Standalone + idempotent: objects are reused by name, meshes rebuilt, materials rebuilt.
import math

import bmesh
import bpy
from mathutils import Matrix, Vector

LEDGE_Z, NICHE_BACK, NICHE_FRONT, NICHE_RX = 0.98, 2.56, 2.50, 5.50   # build_room.py niche
DESK_Z = 0.75


# ---------- helpers ----------

def get_obj(name, coll):
    ob = bpy.data.objects.get(name)
    if ob is None:
        ob = bpy.data.objects.new(name, bpy.data.meshes.new(name))
    if ob.name not in coll.objects:
        coll.objects.link(ob)
    return ob


def finish(ob, bm, mats, smooth=True):
    """bmesh -> object mesh with material slots (slots first, or indices get clamped)."""
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for f in bm.faces:
        f.smooth = smooth
    me = ob.data
    me.clear_geometry()
    me.materials.clear()
    for m in mats:
        me.materials.append(m)
    bm.to_mesh(me)
    bm.free()
    me.update()


def ring_loft(bm, rings, mi, cap=True):
    """Quads between consecutive vertex rings (lists of Vectors), n-gon caps at both ends."""
    vs = [[bm.verts.new(p) for p in r] for r in rings]
    n = len(rings[0])
    for a, b in zip(vs, vs[1:]):
        for k in range(n):
            bm.faces.new((a[k], a[(k + 1) % n], b[(k + 1) % n], b[k])).material_index = mi
    if cap:
        bm.faces.new(vs[0][::-1]).material_index = mi
        bm.faces.new(vs[-1]).material_index = mi
    return vs


def circle(c, r, n, axis="z", phase=0.0):
    out = []
    for i in range(n):
        a = 2 * math.pi * i / n + phase
        u, v = r * math.cos(a), r * math.sin(a)
        out.append(c + (Vector((u, v, 0)) if axis == "z" else Vector((u, 0, v)) if axis == "y" else Vector((0, u, v))))
    return out


def cyl(bm, c, r, h, n, mi, axis="z", r2=None):
    """Closed cylinder/cone frustum from c along +axis by h."""
    d = {"x": Vector((1, 0, 0)), "y": Vector((0, 1, 0)), "z": Vector((0, 0, 1))}[axis]
    return ring_loft(bm, [circle(c, r, n, axis), circle(c + d * h, r if r2 is None else r2, n, axis)], mi)


def box(bm, lo, hi, mi):
    (x0, y0, z0), (x1, y1, z1) = lo, hi
    v = [bm.verts.new(p) for p in ((x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
                                   (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1))]
    for q in ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)):
        bm.faces.new([v[i] for i in q]).material_index = mi


def rounded_rect(hw, hh, r, per=3):
    """Rounded rectangle (half sizes hw, hh) as 2D points, counter-clockwise, 4*per+4 points."""
    pts = []
    for cx, cy, a0 in ((hw - r, hh - r, 0), (-hw + r, hh - r, 90), (-hw + r, -hh + r, 180), (hw - r, -hh + r, 270)):
        for i in range(per + 2):
            a = math.radians(a0 + 90 * i / (per + 1))
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def catmull(ctrl, step=0.006):
    """Uniform Catmull-Rom through control points, resampled ~every `step` metres."""
    P = [Vector(p) for p in ctrl]
    P = [P[0] * 2 - P[1]] + P + [P[-1] * 2 - P[-2]]
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        m = max(2, int((p2 - p1).length / step))
        for j in range(m):
            t = j / m
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t
                              + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    out.append(P[-2])
    return out


def sweep(bm, pts, r, sides, mi):
    """Tube along a polyline, parallel-transport frames, capped ends."""
    n = len(pts)
    T = [(pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]).normalized() for i in range(n)]
    N = T[0].cross(Vector((0, 0, 1)) if abs(T[0].z) < 0.9 else Vector((1, 0, 0))).normalized()
    rings = []
    for i in range(n):
        N = (N - T[i] * N.dot(T[i])).normalized()
        B = T[i].cross(N)
        rings.append([pts[i] + (N * math.cos(a) + B * math.sin(a)) * r
                      for a in (2 * math.pi * k / sides for k in range(sides))])
    ring_loft(bm, rings, mi)


# ---------- materials ----------

def new_mat(name, color, rough, metallic=0.0, spec=0.5):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Specular IOR Level"].default_value = spec
    m.diffuse_color = (*color, 1)
    return m, nt, bsdf


def mnode(nt, op, a, b=0.0, c=0.0):
    n = nt.nodes.new("ShaderNodeMath")
    n.operation = op
    for i, v in enumerate((a, b, c)):
        if isinstance(v, (int, float)):
            n.inputs[i].default_value = v
        else:
            nt.links.new(v, n.inputs[i])
    return n.outputs[0]


def box_mask(nt, u, v, uc, vc, hu, hv):
    """1 inside |u-uc|<hu and |v-vc|<hv."""
    a = mnode(nt, "LESS_THAN", mnode(nt, "ABSOLUTE", mnode(nt, "SUBTRACT", u, uc)), hu)
    b = mnode(nt, "LESS_THAN", mnode(nt, "ABSOLUTE", mnode(nt, "SUBTRACT", v, vc)), hv)
    return mnode(nt, "MULTIPLY", a, b)


def disc_mask(nt, u, v, uc, vc, r):
    du, dv = mnode(nt, "SUBTRACT", u, uc), mnode(nt, "SUBTRACT", v, vc)
    d2 = mnode(nt, "ADD", mnode(nt, "MULTIPLY", du, du), mnode(nt, "MULTIPLY", dv, dv))
    return mnode(nt, "LESS_THAN", d2, r * r)


def local_xyz(nt):
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Object"], sep.inputs[0])
    return sep.outputs[0], sep.outputs[1], sep.outputs[2]


def mix_col(nt, fac, a, col):
    """Mix socket/colour a toward colour col by fac."""
    mx = nt.nodes.new("ShaderNodeMix")
    mx.data_type = "RGBA"
    nt.links.new(fac, mx.inputs[0])
    if isinstance(a, tuple):
        mx.inputs[6].default_value = (*a, 1)
    else:
        nt.links.new(a, mx.inputs[6])
    mx.inputs[7].default_value = (*col, 1)
    return mx.outputs[2]


def remote_mat():
    # Black satin body; rubber keys printed only (geometry stays a smooth shell for the tri budget).
    m, nt, bsdf = new_mat("Deskprops_Remote", (0.012, 0.012, 0.013), 0.42)
    x, y, z = local_xyz(nt)
    top = mnode(nt, "GREATER_THAN", z, 0.0)
    # key grid: 3 columns, rows along x, skipping the d-pad zone
    wx = mnode(nt, "WRAP", mnode(nt, "SUBTRACT", x, -0.062), 0.0045, -0.0045)
    wy = mnode(nt, "WRAP", y, 0.00575, -0.00575)
    grid = box_mask(nt, wx, wy, 0.0, 0.0, 0.0029, 0.0042)
    zone = mnode(nt, "ADD", box_mask(nt, x, y, -0.046, 0.0, 0.020, 0.017), box_mask(nt, x, y, 0.030, 0.0, 0.022, 0.017))
    keys = mnode(nt, "MULTIPLY", grid, mnode(nt, "MINIMUM", zone, 1.0))
    ring = mnode(nt, "SUBTRACT", disc_mask(nt, x, y, -0.008, 0.0, 0.0105), disc_mask(nt, x, y, -0.008, 0.0, 0.0055))
    keys = mnode(nt, "MAXIMUM", keys, ring)
    col = mix_col(nt, mnode(nt, "MULTIPLY", keys, top), (0.012, 0.012, 0.013), (0.16, 0.16, 0.17))   # keys read light grey (white print)
    power = mnode(nt, "MULTIPLY", disc_mask(nt, x, y, -0.077, -0.011, 0.0042), top)
    col = mix_col(nt, power, col, (0.45, 0.02, 0.02))
    for i, c in enumerate(((0.35, 0.03, 0.03), (0.04, 0.3, 0.05), (0.45, 0.38, 0.02), (0.03, 0.12, 0.45))):
        k = mnode(nt, "MULTIPLY", box_mask(nt, x, y, 0.060, -0.0135 + i * 0.009, 0.0022, 0.0032), top)
        col = mix_col(nt, k, col, c)
    nt.links.new(col, bsdf.inputs["Base Color"])
    # rubber keys rougher than the shell
    nt.links.new(mnode(nt, "ADD", mnode(nt, "MULTIPLY", keys, 0.25), 0.42), bsdf.inputs["Roughness"])
    return m


def strip_mat():
    # Off-white strip, Schuko recesses + pin holes printed on the socket face (local -x).
    m, nt, bsdf = new_mat("Deskprops_StripWhite", (0.70, 0.69, 0.64), 0.5)
    x, y, z = local_xyz(nt)
    face = mnode(nt, "LESS_THAN", x, -0.0195)
    zz = mnode(nt, "WRAP", mnode(nt, "SUBTRACT", z, 0.040), 0.0275, -0.0275)
    band = mnode(nt, "LESS_THAN", z, 0.180)
    rec = mnode(nt, "MULTIPLY", mnode(nt, "MULTIPLY", disc_mask(nt, y, zz, 0, 0, 0.0185), face), band)
    holes = mnode(nt, "ADD", disc_mask(nt, y, zz, 0.0095, 0, 0.0025), disc_mask(nt, y, zz, -0.0095, 0, 0.0025))
    col = mix_col(nt, rec, (0.70, 0.69, 0.64), (0.55, 0.54, 0.50))
    col = mix_col(nt, mnode(nt, "MULTIPLY", holes, rec), col, (0.02, 0.02, 0.02))
    nt.links.new(col, bsdf.inputs["Base Color"])
    return m


M_WHITE = new_mat("Deskprops_WhitePlastic", (0.78, 0.78, 0.76), 0.38)[0]
M_BASE = new_mat("Deskprops_CamBase", (0.50, 0.51, 0.52), 0.35)[0]
m_face, nt, bsdf = new_mat("Deskprops_CamFace", (0.006, 0.006, 0.007), 0.06, spec=0.6)
bsdf.inputs["Coat Weight"].default_value = 0.6
M_FACE = m_face
M_LENS = new_mat("Deskprops_CamLens", (0.003, 0.003, 0.004), 0.03, metallic=0.2)[0]
M_BLACK = new_mat("Deskprops_CableBlack", (0.015, 0.015, 0.016), 0.45)[0]
M_CWHITE = new_mat("Deskprops_CableWhite", (0.80, 0.80, 0.79), 0.35)[0]
M_REMOTE = remote_mat()
M_STRIP = strip_mat()

coll = bpy.data.objects["Desk"].users_collection[0]


# ---------- remote: Samsung AA59-00741A class, 178 x 45 x 22 mm ----------
RL, RW, RT = 0.178, 0.045, 0.022
bm = bmesh.new()
rings = []
stations = [(-RL / 2, 0.86), (-RL / 2 + 0.004, 0.97), (-RL / 2 + 0.012, 1.0), (-0.02, 1.0), (0.04, 1.0),
            (RL / 2 - 0.012, 1.0), (RL / 2 - 0.004, 0.97), (RL / 2, 0.86)]
for sx, k in stations:
    u = (sx + RL / 2) / RL                  # 0 at the power end
    t = RT * (1.0 - 0.22 * u)               # thicker at the top (power) end, thinner toward the bottom
    w = RW * (1.0 - 0.06 * u)
    hh = t / 2 * k
    zc = -RT / 2 + hh                       # flat bottom on the ledge
    prof = rounded_rect(w / 2 * k, hh, min(0.0065, hh * 0.9), per=2)
    rings.append([Vector((sx, py, zc + pz)) for py, pz in prof])
ring_loft(bm, rings, 0)
remote = get_obj("Deskprops_Remote", coll)
finish(remote, bm, [M_REMOTE])
# 150338: lying on the ledge front, under the TV's right half, power key toward the TV centre
remote.location = (5.16, 2.5255, LEDGE_Z + RT / 2 + 0.0002)
remote.rotation_euler = (0, 0, math.radians(1.5))


# ---------- camera: Aqara Camera Hub G3 (123.4 x 85.1 x 67.8 mm) + silicone cat ears ----------
F_WHITE, F_BASE, F_FACE, F_LENS = range(4)
bm = bmesh.new()
cyl(bm, Vector((0, 0, 0)), 0.0325, 0.009, 24, F_BASE)                                 # base disc
cyl(bm, Vector((0, 0, 0.008)), 0.0300, 0.058, 20, F_WHITE, r2=0.0265)                  # neck body
cyl(bm, Vector((0, -0.0275, 0.036)), 0.0055, -0.003, 12, F_BASE, axis="y")             # ring-light button
# head: superellipsoid "rounded box", face toward -y
HC, HA, HB, HH = 0.0925, 0.04255, 0.0339, 0.031
res = bmesh.ops.create_uvsphere(bm, u_segments=24, v_segments=12, radius=1.0)
head_v = res["verts"]
for v in head_v:
    n = v.co.copy()
    v.co = Vector((math.copysign(abs(n.x) ** 0.85, n.x) * HA, math.copysign(abs(n.y) ** 0.85, n.y) * HB,
                   math.copysign(abs(n.z) ** 0.85, n.z) * HH + HC))
for f in {f for v in head_v for f in v.link_faces}:
    f.material_index = F_WHITE
# black visor: elliptic glossy dome a few mm proud of the head front
VZ = HC + 0.002
ring_loft(bm, [[Vector((0.031 * k * math.cos(t), y, VZ + 0.025 * k * math.sin(t)))
                for t in (2 * math.pi * i / 20 for i in range(20))]
               for k, y in ((0.97, -0.022), (1.0, -HB + 0.001), (0.93, -HB - 0.0022), (0.6, -HB - 0.0038))], F_FACE)
cyl(bm, Vector((0.0, -0.030, VZ + 0.003)), 0.0095, -0.0085, 16, F_LENS, axis="y")      # lens behind the visor dome
for s in (-1, 1):                                                                     # ears, tilted outward
    ear = cyl(bm, Vector((0, 0, 0)), 0.0115, 0.017, 8, F_WHITE, r2=0.0035)   # soft silicone cat ear, flattened
    vs = [v for r in ear for v in r]
    bmesh.ops.transform(bm, verts=vs, matrix=Matrix.Translation((s * 0.024, 0.002, HC + HH - 0.007))
                        @ Matrix.Rotation(math.radians(14 * s), 4, "Y") @ Matrix.Diagonal((1.0, 0.55, 1.0, 1.0)))
camera = get_obj("Deskprops_Camera", coll)
finish(camera, bm, [M_WHITE, M_BASE, M_FACE, M_LENS])
# 112212 / 122244: on the near table, left of the monitor, ~20 cm from the partition, looking into the room
CAM_POS, CAM_YAW = Vector((5.47, 2.30, DESK_Z)), math.radians(-20)
camera.location = CAM_POS
camera.rotation_euler = (0, 0, CAM_YAW)


# ---------- power strip (local: length +z from the bottom, sockets face -x) ----------
SL, SD, SW = 0.205, 0.040, 0.048
SOCK = (0.040, 0.095, 0.150)                      # socket centres from the bottom end (cord at the top)
P_STRIP, P_BLACK = 0, 1
bm = bmesh.new()
prof = rounded_rect(SD / 2, SW / 2, 0.008, per=2)
rings = []
for z, k in ((0.0, 0.88), (0.004, 0.97), (0.010, 1.0), (SL - 0.010, 1.0), (SL - 0.004, 0.97), (SL, 0.88)):
    rings.append([Vector((px * k, py * k, z)) for px, py in prof])
ring_loft(bm, rings, P_STRIP)
cyl(bm, Vector((0, 0, SL - 0.002)), 0.0065, 0.016, 10, P_STRIP, r2=0.0045)              # cord strain relief
# TV plug (angled Schuko, black) in the top socket; cable leaves it downward
cyl(bm, Vector((-0.019, 0, SOCK[2])), 0.0180, -0.010, 16, P_BLACK, axis="x")
box(bm, (-0.044, -0.009, SOCK[2] - 0.026), (-0.0285, 0.009, SOCK[2] + 0.014), P_BLACK)
# USB charger in the bottom socket (white cube, USB-A lead out of its far end)
box(bm, (-0.066, -0.0145, SOCK[0] - 0.016), (-0.0195, 0.0145, SOCK[0] + 0.016), P_STRIP)
box(bm, (-0.074, -0.006, SOCK[0] - 0.0025), (-0.0655, 0.006, SOCK[0] + 0.0055), P_STRIP)
strip = get_obj("Deskprops_PowerStrip", coll)
finish(strip, bm, [M_STRIP, M_BLACK])
bev = strip.modifiers.get("Deskprops_Bevel") or strip.modifiers.new("Deskprops_Bevel", "BEVEL")
bev.width, bev.segments, bev.limit_method = 0.0015, 2, "ANGLE"
bev.angle_limit = math.radians(50)
bev.harden_normals = True
# standing on end in the niche's right corner, top leaning toward the TV, sockets turned to the room (150338, 122244)
PIVOT_L = Vector((-SD / 2, 0, 0))                  # rests on its socket-side bottom edge
PIVOT_W = Vector((NICHE_RX - 0.080, 2.528, LEDGE_Z))       # s3_geo: 150338 strip ~3 cm in from the corner
S_M = (Matrix.Translation(PIVOT_W) @ Matrix.Rotation(math.radians(10), 4, "Z")
       @ Matrix.Rotation(math.radians(-8), 4, "Y") @ Matrix.Translation(-PIVOT_L))
strip.matrix_world = S_M


def sw(x, y, z):
    """Strip-local point -> world."""
    return S_M @ Vector((x, y, z))


# ---------- cables ----------
R_TV, R_STRIP, R_USB = 0.0028, 0.0036, 0.0017

# TV power cord: out of the set's bottom, sags onto the ledge behind the remote, rises to the plug.
bm = bmesh.new()
pe = sw(-0.036, 0.0, SOCK[2] - 0.026)
tv_cord = [Vector((4.83, 2.512, 1.149)), Vector((4.835, 2.513, 1.124)), Vector((4.87, 2.52, 1.084)),
           Vector((4.93, 2.535, 1.056)), Vector((5.00, 2.553, LEDGE_Z + R_TV + 0.0004)),
           Vector((5.15, 2.555, LEDGE_Z + R_TV + 0.0004)), Vector((5.30, 2.555, LEDGE_Z + R_TV + 0.0004)),
           Vector((5.40, 2.555, LEDGE_Z + R_TV + 0.004)), Vector((pe.x + 0.004, 2.554, LEDGE_Z + 0.05)),
           Vector((pe.x, 2.548, pe.z - 0.03)), pe + Vector((0, 0, 0.004))]
sweep(bm, catmull(tv_cord, 0.012), R_TV, 6, 0)
cab_tv = get_obj("Deskprops_CableTV", coll)
finish(cab_tv, bm, [M_BLACK])

# Strip's own cord: up from the strip top, round the TV's right edge into the bracket gap (wall socket behind the set).
bm = bmesh.new()
st = sw(0, 0, SL + 0.012)
strip_cord = [st, sw(0, 0, SL + 0.03), Vector((st.x - 0.012, 2.546, st.z + 0.05)), Vector((5.39, 2.552, 1.288)),
              Vector((5.32, 2.5535, 1.303)), Vector((5.22, 2.5535, 1.308)), Vector((5.10, 2.5535, 1.308))]
sweep(bm, catmull(strip_cord, 0.012), R_STRIP, 6, 0)
cab_st = get_obj("Deskprops_CableStrip", coll)
finish(cab_st, bm, [M_CWHITE])

# USB cable: charger -> over the ledge front -> down the wall -> onto the desk -> coil -> camera back.
bm = bmesh.new()
u0 = sw(-0.0735, 0, SOCK[0] + 0.0015)
ZL, ZD = LEDGE_Z + R_USB + 0.0006, DESK_Z + R_USB + 0.0006
yw = NICHE_FRONT - R_USB - 0.0008                   # against the wall face below the niche
cam_m = Matrix.Translation(CAM_POS) @ Matrix.Rotation(CAM_YAW, 4, "Z")
port = cam_m @ Vector((0, 0.029, 0.013))
port_out = cam_m @ Vector((0, 0.045, ZD - DESK_Z))
usb = [u0, u0 + Vector((-0.012, -0.004, -0.010)), Vector((u0.x - 0.022, 2.515, ZL + 0.002)), Vector((u0.x - 0.026, 2.505, ZL)),
       Vector((u0.x - 0.024, NICHE_FRONT - 0.001, LEDGE_Z - 0.002)), Vector((u0.x - 0.018, yw, 0.948)),
       Vector((u0.x - 0.004, yw, 0.896)), Vector((u0.x - 0.016, yw, 0.845)), Vector((u0.x - 0.008, yw, 0.787)),
       Vector((u0.x - 0.012, 2.489, 0.762)), Vector((u0.x - 0.016, 2.470, ZD)),
       Vector((CAM_POS.x + 0.16, 2.455, ZD)), Vector((CAM_POS.x + 0.08, 2.44, ZD))]
# flat coil of the spare length, a little behind the camera
cc, rc = Vector((CAM_POS.x + 0.035, CAM_POS.y + 0.085, ZD)), 0.021
a0 = math.atan2(usb[-1].y - cc.y, usb[-1].x - cc.x)
usb.append(cc + Vector((math.cos(a0) * rc * 1.6, math.sin(a0) * rc * 1.6, 0)))
for i in range(1, 3 * 8 + 1):                      # 3 loops, 8 points each, rising one cable diameter per loop
    a = a0 + 2 * math.pi * i / 8
    rr = rc * (1.0 + 0.08 * math.sin(i * 1.7))
    usb.append(cc + Vector((math.cos(a) * rr, math.sin(a) * rr, min(i / 8, 2) * 2 * R_USB)))
usb += [port_out, port]
sweep(bm, catmull(usb, 0.008), R_USB, 6, 0)
# black twist tie across the coil
tie_c = cc + Vector((math.cos(a0 + 2.2) * rc, math.sin(a0 + 2.2) * rc, 0))
box(bm, (tie_c.x - 0.0015, tie_c.y - 0.009, ZD - R_USB), (tie_c.x + 0.0015, tie_c.y + 0.009, ZD + 5 * R_USB), 1)
box(bm, (tie_c.x - 0.009, tie_c.y - 0.0012, ZD - R_USB - 0.0002), (tie_c.x + 0.009, tie_c.y + 0.0012, ZD - R_USB + 0.0014), 1)
cab_usb = get_obj("Deskprops_CableUSB", coll)
finish(cab_usb, bm, [M_CWHITE, M_BLACK])
