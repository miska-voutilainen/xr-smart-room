# Room 3: the hall beyond the pink ENTRANCE door of room 1 (our door in the x=0 wall, y 1.15..2.30).
# Standalone + idempotent (runs after build_room.py / room.py / room2.py via apply_materials.py).
# Objects Room3_* (+ window portals Light_Portal_Hall_*), collection Room3. Wipes its own objects and any leftover
# Room2_Corridor_* (old stub in room2.py).
#
# Rebuilt by s3_hall from Photos/5/hall_01..05 (EXIF, 4.69 mm / 25 mm equiv.). Layout from a joint bundle adjustment of
# the five photos (5 cameras + ~45 layout unknowns, ~130 point/line picks, anchored on our door frame and room-1 walls;
# reprojection mostly 3..10 px at 1400 px, our door frame 25..35 px: the real opening reads ~10 % wider than the
# modelled 1.15 m, see report). Cameras: Cam_hall_01..05 (render/cameras.py, owner s3_cams).
#   hall_01  from x=-5 in the corridor looking EAST at our door (room-1 window visible through it), teal block right
#   hall_02  from the corridor's east end looking WEST: 405 (north wall), booth, play area left, glass offices
#   hall_03/04 from inside room 1 through our door (WNW / NW): catering table against the north wall, 405
#   hall_05  from near our door looking WSW: play area, south-facade window + radiator, glass offices, booth
# Plan (metres, world): the corridor runs WEST from our door. North wall y=YN (405, posters, booth, prints, doors) to
# the far end x=XFAR. East end: our wall x=XE; a solid block (teal west face, x XB..XE) south of the door bay.
# South of the corridor: play area (dark blue vinyl zone) x XC..XB down to the south facade y=YSF (windows +
# radiators), then the glass office row x XFAR..XC, y YSF..YC (white alu frames, blinds, lid at 2.80).
# Old painted ceiling CH with a moulded cornice on every wall, exposed white spiral ducts + AC cassette, conduits,
# surface LED fittings along y=1.40. Unseen in every photo (assumed): rooms behind the doors, the corridor ceiling
# east of x=-5 (no fitting placed there), windows other than the one in hall_05 (3.3 m rhythm).
# Units metres; all meshes world-space verts, origin 0; every face gets world-metre box UVs ("UVMap"), pictures 0..1.
import math
import os

import bpy
from mathutils import Matrix, Vector

P = "Room3_"
H1 = 2.90                                  # room-1 / lab ceiling (build_room.py H)
CH = 3.20                                  # hall ceiling (BA 3.19..3.21)
ZK, DK = 2.945, 0.19                       # cornice: bottom edge on the wall / projection at the ceiling
XE = -0.10                                 # corridor face of the room-1 / lab wall line (door wall)
YN, TN = 2.96, 0.33                        # corridor north wall face / thickness (= 405 reveal depth)
XB, YK = -1.17, 0.41                       # teal block: west face x / north face y
YSF, TS = -4.76, 0.60                      # south facade inner face / thickness (old brick)
XC, YC = -9.30, 0.26                       # glass offices: east face x / north face y (NE corner post)
XFAR = -24.24                              # corridor far end wall
ZOT, ZOM = 2.80, 2.07                      # glass offices: top (lid) / transom
YBL, XBL = 1.06, -2.15                     # dark blue vinyl zone: north edge y, east edge x (west edge = offices)
X4W, X4E, Z4 = -4.07, -2.65, 2.13          # door 405 opening (wall plane), head
WIN_Z0, WIN_Z1, WIN_W = 0.88, 2.80, 1.65   # facade windows (hall_05: x -8.87..-7.22, sill 0.89)
WIN_XC = (-4.75, -8.05, -11.35, -14.65, -17.95, -21.25)   # only -8.05 is photographed; 3.3 m rhythm assumed
LIN_Y = 1.40                               # line of ceiling fittings over the corridor (hall_02 / hall_05)

LM_PER_W = 683.0                           # render/light.py convention
LED_K = 4000.0

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEX = os.path.join(ROOT, "textures", "s1_entrance")
TEX3 = os.path.join(ROOT, "textures", "s3_hall")


# ---------- mesh helpers ----------

def box(lo, hi):
    (x0, y0, z0), (x1, y1, z1) = lo, hi
    v = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
         (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    f = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    return v, f


def solid_mesh(solids, holes=()):
    """Boolean-free union of boxes minus holes -> one manifold all-quad mesh (same as build_room.py)."""
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


def cyl(p0, p1, r, n=8):
    """Closed cylinder p0->p1, n even; caps split into quads (all-quad, no n-gons)."""
    p0, p1 = Vector(p0), Vector(p1)
    t = (p1 - p0).normalized()
    u = t.cross(Vector((0, 0, 1)) if abs(t.z) < 0.9 else Vector((1, 0, 0))).normalized()
    w = t.cross(u)
    ring = [u * math.cos(2 * math.pi * i / n) + w * math.sin(2 * math.pi * i / n) for i in range(n)]
    v = [tuple(p0 + q * r) for q in ring] + [tuple(p1 + q * r) for q in ring]
    f = [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
    for k in range(n // 2 - 1):
        a, b, c, d = k, k + 1, n - 2 - k, n - 1 - k
        f.append((d, c, b, a))
        f.append((n + a, n + b, n + c, n + d))
    return v, f


class Mesh:
    """Parts with a material slot; T = local->world for the next adds; uv: None = world box UVs, else per-loop list."""
    def __init__(self):
        self.v, self.f, self.m, self.uv = [], [], [], []
        self.T = Matrix.Identity(4)

    def add(self, vf, mi=0):
        v, f = vf
        b = len(self.v)
        self.v += [tuple(self.T @ Vector(p)) for p in v]
        self.f += [tuple(i + b for i in q) for q in f]
        self.m += [mi] * len(f)
        self.uv += [None] * len(f)

    def box(self, lo, hi, mi=0):
        self.add(box(lo, hi), mi)

    def solid(self, boxes, mi=0, holes=()):
        self.add(solid_mesh(boxes, holes), mi)

    def quad(self, pts, mi=0):
        """Picture quad (4 world-ish points in T, CCW seen from the front), UV 0..1."""
        b = len(self.v)
        self.v += [tuple(self.T @ Vector(p)) for p in pts]
        self.f.append((b, b + 1, b + 2, b + 3))
        self.m.append(mi)
        self.uv.append(((0, 0), (1, 0), (1, 1), (0, 1)))

    def face(self, pts, uv=None, mi=0):
        """One polygon (points in T), optional per-loop UVs."""
        b = len(self.v)
        self.v += [tuple(self.T @ Vector(p)) for p in pts]
        self.f.append(tuple(range(b, b + len(pts))))
        self.m.append(mi)
        self.uv.append(uv)


def frame(x, y, rz_deg=0.0, z=0.0):
    return Matrix.Translation((x, y, z)) @ Matrix.Rotation(math.radians(rz_deg), 4, 'Z')


def lathe(m, prof, n=16, mi=0, cap_top=True, cap_bot=True):
    """Surface of revolution about local z: prof = [(r, z), ...] bottom -> top. n-gon caps on open ends."""
    ring = [(math.cos(2 * math.pi * i / n), math.sin(2 * math.pi * i / n)) for i in range(n)]
    v = [(r * c, r * s, z) for r, z in prof for c, s in ring]
    f = [(k * n + i, k * n + (i + 1) % n, (k + 1) * n + (i + 1) % n, (k + 1) * n + i)
         for k in range(len(prof) - 1) for i in range(n)]
    if cap_bot and prof[0][0] > 0:
        f.append(tuple(range(n))[::-1])
    if cap_top and prof[-1][0] > 0:
        k = len(prof) - 1
        f.append(tuple(k * n + i for i in range(n)))
    m.add((v, f), mi)


def duct(m, p0, p1, r, mi, n=16, pitch=0.137):
    """Spiral-seam duct: open tube p0->p1 with UV (u = turns, v = metres/pitch) for the helix seam shader."""
    p0, p1 = Vector(p0), Vector(p1)
    t = (p1 - p0)
    L = t.length
    t.normalize()
    u = t.cross(Vector((0, 0, 1)) if abs(t.z) < 0.9 else Vector((1, 0, 0))).normalized()
    w = t.cross(u)
    for i in range(n):
        a0, a1 = 2 * math.pi * i / n, 2 * math.pi * (i + 1) / n
        q0, q1 = u * math.cos(a0) + w * math.sin(a0), u * math.cos(a1) + w * math.sin(a1)
        pts = [p0 + q0 * r, p0 + q1 * r, p1 + q1 * r, p1 + q0 * r]
        uv = [(i / n, 0), ((i + 1) / n, 0), ((i + 1) / n, L / pitch), (i / n, L / pitch)]
        m.face(pts, uv, mi)


def extrude(m, path, prof, mi=0, closed=False):
    """Cornice: profile [(d into the room, z), ...] swept along a wall-root polyline [(x, y), ...] whose room side is
    on the LEFT of the walking direction; mitred corners. Faces oriented toward the room."""
    n = len(path)
    P2 = [Vector((x, y, 0)) for x, y in path]

    def left(a, b):
        d = (b - a).normalized()
        return Vector((-d.y, d.x, 0))
    offs = []
    for i in range(n):
        ns = []
        if closed or i > 0:
            ns.append(left(P2[i - 1], P2[i]))
        if closed or i < n - 1:
            ns.append(left(P2[i], P2[(i + 1) % n]))
        mv = sum(ns, Vector()).normalized()
        offs.append(mv / mv.dot(ns[0]))
    k = len(prof)
    b = len(m.v)
    for i in range(n):
        for d, z in prof:
            p = P2[i] + offs[i] * d
            m.v.append((p.x, p.y, z))
    segs = range(n) if closed else range(n - 1)
    for i in segs:
        j = (i + 1) % n
        for q in range(k - 1):
            m.f.append((b + i * k + q, b + j * k + q, b + j * k + q + 1, b + i * k + q + 1))
            m.m.append(mi)
            m.uv.append(None)


def drape(m, x0, x1, y0, y1, top, over, mi, step=0.055, r=0.012, amp=0.014, flen=0.13):
    """Sculpted tablecloth: flat sheet (table + overhang) laid over the top, wrapped round the edge (radius r) and
    hanging; corners fall as cones (lowest points), soft folds grow toward the hem."""
    nx, ny = round((x1 - x0 + 2 * over) / step), round((y1 - y0 + 2 * over) / step)
    b = len(m.v)
    for j in range(ny + 1):
        for i in range(nx + 1):
            u, v = x0 - over + (x1 - x0 + 2 * over) * i / nx, y0 - over + (y1 - y0 + 2 * over) * j / ny
            cx, cy = min(max(u, x0), x1), min(max(v, y0), y1)
            dx, dy = u - cx, v - cy
            d = math.hypot(dx, dy)
            if d < 1e-6:
                m.v.append((u, v, top))
                continue
            nxv, nyv = dx / d, dy / d
            if d < math.pi * r / 2:
                ph = d / r
                h, z = r * math.sin(ph), top - r * (1 - math.cos(ph))
            else:
                s = d - math.pi * r / 2
                wv = min(1.0, s / over) ** 1.3
                h = r + amp * wv * math.sin((cx + cy + 0.25 * math.atan2(dy, dx)) / flen * 2 * math.pi)
                z = max(top - r - s, 0.03)
            m.v.append((cx + nxv * h, cy + nyv * h, z))
    for j in range(ny):
        for i in range(nx):
            a = b + j * (nx + 1) + i
            m.f.append((a, a + 1, a + nx + 2, a + nx + 1))
            m.m.append(mi)
            m.uv.append(None)


# ---------- scene helpers ----------

def wipe():
    for o in [o for o in bpy.data.objects if o.name.startswith(("Room2_Corridor_", P, "Light_Portal_Hall_"))]:
        bpy.data.objects.remove(o, do_unlink=True)
    c = bpy.data.collections.get("Room3")
    if c is None:
        c = bpy.data.collections.new("Room3")
        bpy.context.scene.collection.children.link(c)
    for coll in (bpy.data.meshes, bpy.data.lights):
        for d in list(coll):
            if d.name.startswith((P, "Room2_Corridor_", "Light_Portal_Hall_")) and d.users == 0:
                coll.remove(d)
    for m in list(bpy.data.materials):
        if m.name.startswith(("Room2_Corridor_", "Room2_Partition_Blinds", "Room2_Tablecloth", "Room2_Fabric_Yellow",
                              P)) and m.users == 0:
            bpy.data.materials.remove(m)
    return c


def obj(name, mesh, mats, coll, bevel=0.0):
    me = bpy.data.meshes.new(P + name)
    me.from_pydata(mesh.v, [], mesh.f)
    for m in mats:
        me.materials.append(m)
    me.polygons.foreach_set("material_index", mesh.m)
    uvl = me.uv_layers.new(name="UVMap")
    for poly, uv in zip(me.polygons, mesh.uv):
        if uv is None:                         # world box projection, metres
            ax = max(range(3), key=lambda a: abs(poly.normal[a]))
            a, b = [(1, 2), (0, 2), (0, 1)][ax]
            for li in poly.loop_indices:
                co = me.vertices[me.loops[li].vertex_index].co
                uvl.data[li].uv = (co[a], co[b])
        else:
            for li, q in zip(poly.loop_indices, uv):
                uvl.data[li].uv = q
    me.validate()
    ob = bpy.data.objects.new(P + name, me)
    coll.objects.link(ob)
    if bevel:                                  # upholstery: rounded edges (Unity export applies modifiers)
        bv = ob.modifiers.new("Bevel", 'BEVEL')
        bv.width, bv.segments, bv.limit_method = bevel, 2, 'ANGLE'
        bv.angle_limit = math.radians(40)
        bv.harden_normals = False
        for p in me.polygons:
            p.use_smooth = True
    return ob


# ---------- materials (Principled + CC0 image maps, textures/s1_entrance + textures/s3_hall SOURCES.txt) ----------

def img(fname, color=True):
    path = os.path.join(TEX3 if os.path.exists(os.path.join(TEX3, fname)) else TEX, fname)
    im = bpy.data.images.load(path, check_existing=True)
    im.colorspace_settings.name = 'sRGB' if color else 'Non-Color'
    return im


def pbr(name, rgb=(0.8, 0.8, 0.8), rough=0.5, metal=0.0, cmap=None, crange=None, rmap=None, rrange=(0.0, 1.0),
        nmap=None, nstr=0.2, size=1.0, transmission=0.0, ior=1.5, coat=0.0):
    """cmap with crange=(lo, hi, a, b): grey-level of the map remapped lo..hi -> a..b, times rgb (keeps the CC0 map's
    texture but sets a measured albedo); cmap without crange: map colour times rgb. size = metres per texture tile."""
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.diffuse_color = (*rgb, 1)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    N, L = nt.nodes.new, nt.links.new
    bsdf = N("ShaderNodeBsdfPrincipled")
    L(bsdf.outputs[0], N("ShaderNodeOutputMaterial").inputs[0])
    bsdf.inputs["Base Color"].default_value = (*rgb, 1)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    bsdf.inputs["IOR"].default_value = ior
    bsdf.inputs["Transmission Weight"].default_value = transmission
    bsdf.inputs["Coat Weight"].default_value = coat
    if not (cmap or rmap or nmap):
        return m
    uv = N("ShaderNodeTexCoord").outputs["UV"]
    mp = N("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (1 / size, 1 / size, 1)
    L(uv, mp.inputs["Vector"])

    def tex(f, color):
        t = N("ShaderNodeTexImage")
        t.image = img(f, color)
        L(mp.outputs[0], t.inputs["Vector"])
        return t

    if cmap:
        t = tex(cmap, True)
        col = t.outputs["Color"]
        if crange:
            bw = N("ShaderNodeRGBToBW")
            L(col, bw.inputs[0])
            mr = N("ShaderNodeMapRange")
            mr.inputs[1].default_value, mr.inputs[2].default_value = crange[0], crange[1]
            mr.inputs[3].default_value, mr.inputs[4].default_value = crange[2], crange[3]
            L(bw.outputs[0], mr.inputs[0])
            col = mr.outputs[0]
        mul = N("ShaderNodeMix")
        mul.data_type, mul.blend_type = 'RGBA', 'MULTIPLY'
        mul.inputs["Factor"].default_value = 1.0
        L(col, mul.inputs["A"])
        mul.inputs["B"].default_value = (*rgb, 1)
        L(mul.outputs["Result"], bsdf.inputs["Base Color"])
    if rmap:
        t = tex(rmap, False)
        mr = N("ShaderNodeMapRange")
        mr.inputs[3].default_value, mr.inputs[4].default_value = rrange
        L(t.outputs["Color"], mr.inputs[0])
        L(mr.outputs[0], bsdf.inputs["Roughness"])
    if nmap:
        t = tex(nmap, False)
        nm = N("ShaderNodeNormalMap")
        nm.inputs["Strength"].default_value = nstr
        L(t.outputs["Color"], nm.inputs["Color"])
        L(nm.outputs[0], bsdf.inputs["Normal"])
    return m


def first_mat(obname, *fallback_names):
    ob = bpy.data.objects.get(obname)
    if ob and ob.active_material:
        return ob.active_material
    for n in fallback_names:
        if bpy.data.materials.get(n):
            return bpy.data.materials[n]
    return None


def picture(name, fname, rough=0.35, alpha=False):
    """Printed matter: photo crop as base colour on UV 0..1 (alpha = cut-out shape)."""
    m = pbr(name, (1, 1, 1), rough)
    nt = m.node_tree
    t = nt.nodes.new("ShaderNodeTexImage")
    t.image = img(fname, True)
    t.extension = 'EXTEND'
    nt.links.new(nt.nodes.new("ShaderNodeTexCoord").outputs["UV"], t.inputs["Vector"])
    bsdf = nt.nodes["Principled BSDF"]
    nt.links.new(t.outputs["Color"], bsdf.inputs["Base Color"])
    if alpha:
        nt.links.new(t.outputs["Alpha"], bsdf.inputs["Alpha"])
    return m


def emissive(name, rgb, strength):
    m = pbr(name, rgb, 0.4)
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Emission Color"].default_value = (*rgb, 1)
    b.inputs["Emission Strength"].default_value = strength
    return m


def spiral_duct_mat(name):
    """White painted spiral-seam duct: lock seam = helix fract(u + v) as a bump ridge (UV from duct())."""
    m = pbr(name, (0.78, 0.78, 0.77), 0.45, metal=0.0)
    nt = m.node_tree
    N, L = nt.nodes.new, nt.links.new
    sep = N("ShaderNodeSeparateXYZ")
    L(N("ShaderNodeTexCoord").outputs["UV"], sep.inputs[0])
    add = N("ShaderNodeMath"); add.operation = 'ADD'
    L(sep.outputs[0], add.inputs[0]); L(sep.outputs[1], add.inputs[1])
    fr = N("ShaderNodeMath"); fr.operation = 'FRACT'
    L(add.outputs[0], fr.inputs[0])
    dist = N("ShaderNodeMath"); dist.operation = 'PINGPONG'; dist.inputs[1].default_value = 0.5
    L(fr.outputs[0], dist.inputs[0])
    mr = N("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value, mr.inputs["From Max"].default_value = 0.0, 0.06
    mr.inputs["To Min"].default_value, mr.inputs["To Max"].default_value = 1.0, 0.0
    L(dist.outputs[0], mr.inputs["Value"])
    bump = N("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.6; bump.inputs["Distance"].default_value = 0.003
    L(mr.outputs[0], bump.inputs["Height"])
    L(bump.outputs[0], nt.nodes["Principled BSDF"].inputs["Normal"])
    return m


def led_light(ob):
    """As render/light.py led_light(): the area light only lights (diffuse/volume); camera, reflections and
    refractions see the Room3_LED_<n> diffuser mesh instead (no double count, real fitting shape in the vinyl)."""
    ob.visible_camera = ob.visible_glossy = ob.visible_transmission = False


NLED = [0]


def fitting(coll, name, x, y, sx, sy, zc=CH, body=0.065):
    """Surface-mounted LED fitting: white body on the ceiling, Room3_LED_<n> diffuser underneath (render/light.py
    rebuilds Room3_LED_Diffuser), Room3_<name> area light of the diffuser's size (re-rated by light.py
    make_entrance from its area)."""
    m = Mesh()
    m.box((x - sx / 2 - 0.02, y - sy / 2 - 0.02, zc - body), (x + sx / 2 + 0.02, y + sy / 2 + 0.02, zc))
    FIT_BODIES.append(m)
    z = zc - body - 0.002
    k = NLED[0]
    NLED[0] += 1
    d = Mesh()
    d.v, d.f, d.m, d.uv = [(x - sx / 2, y - sy / 2, z), (x + sx / 2, y - sy / 2, z), (x + sx / 2, y + sy / 2, z),
                           (x - sx / 2, y + sy / 2, z)], [(3, 2, 1, 0)], [0], [None]
    ob = obj(f"LED_{k:02d}", d, [LED_MAT], coll)
    ob.visible_diffuse = ob.visible_volume_scatter = ob.visible_shadow = False
    li = bpy.data.lights.new(P + name, 'AREA')
    li.shape, li.size, li.size_y = 'RECTANGLE', sx, sy
    li.energy = 3600.0 * sx * sy / 0.555 ** 2 / LM_PER_W        # placeholder: light.py make_entrance re-rates
    li.use_temperature, li.temperature, li.spread = True, LED_K, math.radians(150)
    lo = bpy.data.objects.new(P + name, li)
    lo.location = (x, y, z - 0.001)
    led_light(lo)
    coll.objects.link(lo)


def portal(coll, k, xc, w, z0, z1):
    """Cycles portal on the outer face of a south-facade window, emitting into the hall (+y)."""
    li = bpy.data.lights.new(f"Light_Portal_Hall_{k}", 'AREA')
    li.shape, li.size, li.size_y = 'RECTANGLE', w, z1 - z0
    li.cycles.is_portal = True
    ob = bpy.data.objects.new(f"Light_Portal_Hall_{k}", li)
    ob.location = (xc, YSF - TS - 0.005, (z0 + z1) / 2)
    ob.rotation_euler = (math.pi / 2, 0, 0)
    coll.objects.link(ob)


# ---------- build ----------
coll = wipe()
FIT_BODIES = []

WALL = bpy.data.materials.get("Room_Wall") or pbr(P + "Wall_Paint", (0.775, 0.765, 0.735), 0.9,
                                                    nmap="plaster001_normal.jpg", nstr=0.08, size=1.5)
PINK = (bpy.data.materials.get("Door_Paint") or first_mat("Door_Frame", "Door_Pink")
        or pbr(P + "Pink_Paint", (0.56, 0.012, 0.165), 0.4))
REVEAL = pbr(P + "Reveal_Pink", (0.58, 0.36, 0.34), 0.85, nmap="plaster001_normal.jpg", nstr=0.05, size=1.5)
TEAL = pbr(P + "Paint_Teal", (0.006, 0.13, 0.21), 0.8, nmap="plaster001_normal.jpg", nstr=0.05, size=1.5)
# sheet vinyl (Tarkett iQ-type), polished: grey corridor, dark blue play zone (hall_05: blue ~ grey x (0.7, 0.9, 1.4))
VINYL = pbr(P + "Vinyl_Grey", (0.12, 0.122, 0.125), cmap="rubber004_color.jpg", crange=(0.009, 0.037, 0.88, 1.12),
            rmap="rubber004_rough.jpg", rrange=(0.10, 0.30), nmap="rubber004_normal.jpg", nstr=0.03, size=0.8)
VINYL_B = pbr(P + "Vinyl_Blue", (0.042, 0.052, 0.075), cmap="rubber004_color.jpg", crange=(0.009, 0.037, 0.85, 1.15),
              rmap="rubber004_rough.jpg", rrange=(0.12, 0.32), nmap="rubber004_normal.jpg", nstr=0.03, size=0.8)
# aged lime-white ceiling (warm): photo ceiling R/G 1.00 B/G 0.97, the blue-floor bounce tints it cyan
CEIL = pbr(P + "Ceiling_Paint", (0.86, 0.82, 0.75), 0.92, nmap="plaster001_normal.jpg", nstr=0.06, size=1.5)
CORN = pbr(P + "Cornice_Plaster", (0.86, 0.82, 0.75), 0.85)
SKIRT = pbr(P + "Skirting", (0.08, 0.08, 0.085), 0.5)               # arch.py "skirt" rule -> vinyl skirting
POWDER = pbr(P + "Powder_White", (0.80, 0.80, 0.79), 0.35)
GLASS = pbr(P + "Glass", (0.96, 0.985, 0.97), 0.0, transmission=1.0, ior=1.52)
_nt = GLASS.node_tree                      # as shaders/hard.py glass(): shadow rays pass a tinted Transparent BSDF
_mix, _tr = _nt.nodes.new("ShaderNodeMixShader"), _nt.nodes.new("ShaderNodeBsdfTransparent")
_tr.inputs["Color"].default_value = (0.96, 0.985, 0.97, 1)
_nt.links.new(_nt.nodes.new("ShaderNodeLightPath").outputs["Is Shadow Ray"], _mix.inputs[0])
_nt.links.new(_nt.nodes["Principled BSDF"].outputs[0], _mix.inputs[1])
_nt.links.new(_tr.outputs[0], _mix.inputs[2])
_nt.links.new(_mix.outputs[0], _nt.nodes["Material Output"].inputs["Surface"])
BLIND = pbr(P + "Blind_Slats", (1.0, 1.0, 1.0), 0.6, cmap="blind_slats.png", size=0.1)
BLIND.node_tree.nodes["Principled BSDF"].inputs["Alpha"].default_value = 0.55   # slats half open
DUCT = spiral_duct_mat(P + "Duct_Spiral")
CHROME = pbr(P + "Chrome", (0.90, 0.90, 0.90), 0.08, metal=1.0)
STEEL = pbr(P + "Steel_Brushed", (0.85, 0.85, 0.84), 0.22, metal=1.0)
BLACK = pbr(P + "Plastic_Black", (0.03, 0.03, 0.03), 0.45)
GREY = pbr(P + "Powder_Graphite", (0.09, 0.095, 0.10), 0.4)
SOFA = pbr(P + "Fabric_Green", (0.12, 0.19, 0.02), cmap="fabric030_color.jpg", crange=(0.045, 0.223, 0.7, 1.3),
           rmap="fabric030_rough.jpg", rrange=(0.75, 0.95), nmap="fabric030_normal.jpg", nstr=0.4, size=0.25)
SEAT = pbr(P + "Fabric_Charcoal", (0.03, 0.032, 0.035), cmap="fabric030_color.jpg", crange=(0.045, 0.223, 0.7, 1.3),
           rmap="fabric030_rough.jpg", rrange=(0.75, 0.95), nmap="fabric030_normal.jpg", nstr=0.4, size=0.25)
CLOTH = pbr(P + "Tablecloth", (0.80, 0.80, 0.78), cmap="fabric036_color.jpg", crange=(0.42, 0.59, 0.92, 1.08),
            rmap="fabric036_rough.jpg", rrange=(0.7, 0.9), nmap="fabric036_normal.jpg", nstr=0.3, size=0.3)
BIRCH = pbr(P + "Birch_Veneer", (1.25, 1.20, 1.10), cmap="wood090a_color.jpg", rmap="wood090a_rough.jpg",
            rrange=(0.35, 0.55), nmap="wood090a_normal.jpg", nstr=0.15, size=1.0)
MAHOG = pbr(P + "Laminate_Mahogany", (0.20, 0.09, 0.08), cmap="wood090a_color.jpg", rmap="wood090a_rough.jpg",
            rrange=(0.25, 0.40), nmap="wood090a_normal.jpg", nstr=0.1, size=1.0)
DOOR_BROWN = pbr(P + "Door_Laminate_Brown", (0.13, 0.07, 0.065), cmap="wood090a_color.jpg", rmap="wood090a_rough.jpg",
                 rrange=(0.35, 0.5), size=1.0)
PALE_PINK = pbr(P + "Door_Paint_PalePink", (0.62, 0.40, 0.42), 0.4)
YELLOW = pbr(P + "Fabric_Yellow", (0.62, 0.42, 0.02), cmap="fabric030_color.jpg", crange=(0.045, 0.223, 0.8, 1.2),
             rmap="fabric030_rough.jpg", rrange=(0.75, 0.95), nmap="fabric030_normal.jpg", nstr=0.4, size=0.25)
BLUE_BIKE = pbr(P + "Paint_Bike_Blue", (0.02, 0.04, 0.35), 0.3, coat=0.5)
RED = pbr(P + "Plastic_Red", (0.50, 0.03, 0.03), 0.35)
STICKER = pbr(P + "Sticker_Yellow", (0.75, 0.55, 0.02), 0.4)
WHITE_PL = pbr(P + "Plastic_White", (0.82, 0.82, 0.80), 0.35)
PAPER = pbr(P + "Paper_Plate", (0.80, 0.80, 0.78), 0.6)
EXIT = emissive(P + "Exit_Sign", (0.05, 0.60, 0.20), 0.7)      # ~150 cd/m2 (= 0.22 W/m2/sr x pi)
EXIT.cycles.emission_sampling = 'NONE'
READER = emissive(P + "Reader_LED", (0.1, 1.0, 0.3), 4.0)
LED_MAT = emissive(P + "LED_Diffuser", (1.0, 0.94, 0.87), 16.0)   # placeholder: render/light.py rebuilds it
LED_MAT.cycles.emission_sampling = 'NONE'
PG = picture(P + "Poster_GoodPractice", "poster_pg.jpg")
A3 = picture(P + "Poster_A3", "poster_a3.jpg")
SIGN405 = picture(P + "Sign_405", "sign_405.jpg", 0.3)
PRINT = picture(P + "Print_Pink", "print_pink.jpg", 0.1)
CUTOUT = picture(P + "Cutout_Board", "cutout.png", 0.4, alpha=True)
UNIQUE = picture(P + "Box_Unique", "unique_box.jpg", 0.5)

# --- floor: grey vinyl, dark blue play zone (x XC..XBL, y YSF..YBL; hall_01 / hall_02 / hall_05); top z=0 ---
m = Mesh()
FL = ((XFAR - 0.25, YSF - TS, -0.10), (XE, YN + TN, 0))
BZ = ((XC, YSF, -0.10), (XBL, YBL, 0))
m.solid([FL], 0, [BZ])
m.box(*BZ, 1)
obj("Floor", m, [VINYL, VINYL_B], coll)

# --- ceiling slab ---
m = Mesh()
m.box((XFAR - 0.25, YSF - TS, CH), (0.0, YN + TN, CH + 0.12))
obj("Ceiling", m, [CEIL], coll)

# --- walls: north wall with 405 / doors, south facade with windows, far wall, teal block, east lining + bulkhead ---
DW = (-10.86, -9.77, 2.10)          # dark laminate door west of the booth (hall_02 / hall_05)
LPD = (-17.55, -16.65, 2.11)        # pale pink door further west (hall_02)
FARD = (1.95, 2.85, 2.15)           # open pink-framed doorway in the far wall (hall_02 / hall_05), y range + head
m = Mesh()
m.solid([((XFAR - 0.25, YN, 0), (XE, YN + TN, CH))], 0,
        [((X4W, YN - 0.01, 0), (X4E, YN + TN + 0.01, Z4)), ((DW[0], YN - 0.01, 0), (DW[1], YN + TN + 0.01, DW[2])),
         ((LPD[0], YN - 0.01, 0), (LPD[1], YN + TN + 0.01, LPD[2]))])
m.solid([((XFAR - 0.25, YSF - TS, 0), (XB, YSF, CH))], 0,
        [((xc - WIN_W / 2, YSF - TS - 0.01, WIN_Z0), (xc + WIN_W / 2, YSF + 0.01, WIN_Z1)) for xc in WIN_XC])
m.solid([((XFAR - 0.25, YSF, 0), (XFAR, YN, CH))], 0, [((XFAR - 0.26, FARD[0], 0), (XFAR + 0.01, FARD[1], FARD[2]))])
m.solid([((XFAR - 1.35, FARD[0] - 0.1, 0), (XFAR - 0.25, FARD[1] + 0.1, CH))], 0,
        [((XFAR - 1.25, FARD[0], 0), (XFAR - 0.24, FARD[1], 2.60))])           # white niche behind the far doorway
m.box((XB, YSF, 0), (XE, YK, CH))                                               # block south of the door bay
m.box((-0.105, 2.30, 0), (XE, YN, H1 - 0.12))                                   # lining of the room-1 / lab wall line
                                                                                 # (stops where the bulkhead starts: no coplanar overlap)
m.box((-0.105, YK, H1 - 0.12), (0.0, YN, CH))                                   # bulkhead over room 1 / lab ceilings
                                                                                 # (5 mm proud: room ceiling slabs end flush at x=-0.10)
obj("Walls", m, [WALL], coll)

# 405 reveal (pink-painted jambs + soffit), teal paint on the block's west face (hall_01: y -2.2 .. YK)
m = Mesh()
e = 0.003
m.box((X4W, YN, 0), (X4W + e, YN + TN - 0.05, Z4), 0)
m.box((X4E - e, YN, 0), (X4E, YN + TN - 0.05, Z4), 0)
m.box((X4W, YN, Z4 - e), (X4E, YN + TN - 0.05, Z4), 0)
m.box((XB - e, -2.20, 0.06), (XB, YK, ZK), 1)
obj("Paint_Accents", m, [REVEAL, TEAL], coll)

# --- cornice (old moulded plaster cove, ~255 x 190 mm) round every wall of the hall ---
COV = [(0.0, ZK), (0.014, ZK + 0.006), (0.014, ZK + 0.028), (0.032, ZK + 0.040), (0.032, ZK + 0.055)]
for k in range(1, 6):                                                           # quarter-circle cove r = 0.135
    a = math.pi / 2 * k / 5
    COV.append((0.032 + 0.135 * (1 - math.cos(a)), ZK + 0.055 + 0.135 * math.sin(a)))
COV += [(0.172, CH - 0.055), (0.172, CH - 0.030), (0.183, CH - 0.022), (DK, CH - 0.010), (DK, CH)]
m = Mesh()
extrude(m, [(XFAR, YSF), (XB, YSF), (XB, YK), (XE, YK), (XE, YN), (XFAR, YN)], COV, closed=True)
obj("Cornice", m, [CORN], coll)

# --- skirting 60 mm dark grey (hall_02: blue-grey vinyl skirting on the north wall) ---
m = Mesh()
sk, st = 0.06, 0.012
runs = [((X4E, YN - st, 0), (XE, YN, sk)), ((DW[1], YN - st, 0), (X4W, YN, sk)), ((LPD[1], YN - st, 0), (DW[0], YN, sk)),
        ((XFAR, YN - st, 0), (LPD[0], YN, sk)), ((XFAR, YSF, 0), (XFAR + st, YN, sk)),
        ((XC, YSF, 0), (XB, YSF + st, sk)), ((XB - st, YSF, 0), (XB, YK, sk)), ((XB, YK, 0), (XE, YK + st, sk)),
        ((XE - st, YK, 0), (XE, 1.15, sk)), ((XE - st, 2.30, 0), (XE, YN, sk))]
for lo, hi in runs:
    m.box(lo, hi, 0)
obj("Skirting", m, [SKIRT], coll)

# --- door 405 (hall_02 / 03 / 04): pink frame at the room side of the 330 mm reveal, leaf with
#     the room sign, one wide leaf hinged west and ajar 15 deg (room visible at its east edge); card reader on the west jamb ---
m = Mesh()
fy0, fy1, f = YN + TN - 0.05, YN + TN, 0.05
m.solid([((X4W, fy0, 0), (X4W + f, fy1, Z4)), ((X4E - f, fy0, 0), (X4E, fy1, Z4)), ((X4W, fy0, Z4 - f), (X4E, fy1, Z4))], 0)
hx, hy = X4W + f, fy0 + 0.02
m.T = frame(hx, hy, 15)                                                          # leaf, hinge at the west jamb
LW = X4E - X4W - 2 * f - 0.006
m.box((0.003, -0.02, 0.01), (LW, 0.02, Z4 - f - 0.004), 0)
m.quad([(0.66, -0.0205, 1.42), (0.80, -0.0205, 1.42), (0.80, -0.0205, 1.68), (0.66, -0.0205, 1.68)], 3)
m.add(cyl((LW - 0.07, -0.02, 1.05), (LW - 0.07, -0.075, 1.05), 0.010, 8), 1)
m.add(cyl((LW - 0.07, -0.075, 1.05), (LW - 0.21, -0.075, 1.05), 0.010, 8), 1)
m.add(cyl((LW - 0.07, -0.02, 0.975), (LW - 0.07, -0.03, 0.975), 0.018, 8), 1)
m.T = Matrix.Identity(4)
m.box((X4W, YN + 0.08, 1.18), (X4W + 0.03, YN + 0.15, 1.32), 2)                  # card reader on the west jamb
m.box((X4W + 0.03, YN + 0.105, 1.28), (X4W + 0.032, YN + 0.125, 1.30), 4)
obj("Door_405", m, [PINK, CHROME, BLACK, SIGN405, READER], coll)

# room 405 behind it (glimpsed in hall_02 / hall_04: white room, bright north window): shell + one panel light
m = Mesh()
RX0, RX1, RY0, RY1 = -6.10, -1.25, YN + TN, 8.90
m.solid([((RX0 - 0.1, RY0, -0.1), (RX1 + 0.1, RY1 + 0.25, CH + 0.1))], 0,
        [((RX0, RY0 - 0.01, 0), (RX1, RY1, CH)), ((-3.80, RY1 - 0.01, 0.85), (-2.20, RY1 + 0.26, 2.75))])
m.box((RX0, RY0, 0), (RX1, RY1, 0.001), 1)
m.box((-3.80, RY1 + 0.10, 0.85), (-2.20, RY1 + 0.11, 2.75), 2)
obj("Room405", m, [WALL, BIRCH, GLASS], coll)
fitting(coll, "R405_Panel", (RX0 + RX1) / 2, (RY0 + RY1) / 2, 0.555, 0.555)

# --- other doors on the north wall: dark laminate (west of the booth) + pale pink (further west), far doorway ---
m = Mesh()
for (x0, x1, h), mat in ((DW, 1), (LPD, 2)):
    m.solid([((x0, YN + 0.17, 0), (x0 + 0.04, YN + 0.23, h)), ((x1 - 0.04, YN + 0.17, 0), (x1, YN + 0.23, h)),
             ((x0, YN + 0.17, h - 0.04), (x1, YN + 0.23, h))], 0)                         # frames
    m.box((x0 + 0.04, YN + 0.19, 0.01), (x1 - 0.04, YN + 0.23, h - 0.044), mat)
    m.add(cyl((x1 - 0.12, YN + 0.19, 1.05), (x1 - 0.12, YN + 0.13, 1.05), 0.010, 8), 3)
    m.add(cyl((x1 - 0.12, YN + 0.13, 1.05), (x1 - 0.26, YN + 0.13, 1.05), 0.010, 8), 3)
m.box((DW[1] + 0.10, YN - 0.025, 1.18), (DW[1] + 0.17, YN, 1.32), 4)                # card reader east of it
m.solid([((XFAR, FARD[0] - 0.06, 0), (XFAR + 0.02, FARD[0], FARD[2] + 0.06)),
         ((XFAR, FARD[1], 0), (XFAR + 0.02, FARD[1] + 0.06, FARD[2] + 0.06)),
         ((XFAR, FARD[0] - 0.06, FARD[2]), (XFAR + 0.02, FARD[1] + 0.06, FARD[2] + 0.06))], 0)   # pink casing
obj("Doors_North", m, [PINK, DOOR_BROWN, PALE_PINK, CHROME, BLACK], coll)

# --- windows on the south facade (hall_05: white uPVC, 3 lower + 3 upper lights, transom, sill board) + radiators ---
m = Mesh()
FRY = YSF - 0.30                                                                 # frame plane in the 600 mm wall
for k, xc in enumerate(WIN_XC):
    x0, x1 = xc - WIN_W / 2, xc + WIN_W / 2
    zt = 2.15
    bars = [((x0, FRY, WIN_Z0), (x0 + 0.06, FRY + 0.07, WIN_Z1)), ((x1 - 0.06, FRY, WIN_Z0), (x1, FRY + 0.07, WIN_Z1)),
            ((x0, FRY, WIN_Z0), (x1, FRY + 0.07, WIN_Z0 + 0.07)), ((x0, FRY, WIN_Z1 - 0.06), (x1, FRY + 0.07, WIN_Z1)),
            ((x0, FRY, zt - 0.035), (x1, FRY + 0.07, zt + 0.035))]
    for q in (1, 2):
        xm = x0 + (x1 - x0) * q / 3
        bars.append(((xm - 0.04, FRY, WIN_Z0), (xm + 0.04, FRY + 0.07, WIN_Z1)))
    m.solid(bars, 0)
    m.box((x0 + 0.05, FRY + 0.03, WIN_Z0 + 0.05), (x1 - 0.05, FRY + 0.034, WIN_Z1 - 0.05), 1)           # glazing
    m.box((x0 - 0.04, YSF - 0.23, WIN_Z0 - 0.02), (x1 + 0.04, YSF + 0.04, WIN_Z0 + 0.0), 0)          # sill board
    # cast-iron column radiator under it (hall_05), 0.95 x 0.10 x 0.55, 10 sections
    ry = YSF + 0.05
    for s_ in range(10):
        sx = xc - 0.475 + s_ * 0.095
        m.box((sx + 0.006, ry, 0.16), (sx + 0.089, ry + 0.10, 0.71), 2)
    m.add(cyl((xc - 0.49, ry + 0.05, 0.66), (xc + 0.49, ry + 0.05, 0.66), 0.022, 6), 2)
    m.add(cyl((xc - 0.49, ry + 0.05, 0.21), (xc + 0.49, ry + 0.05, 0.21), 0.022, 6), 2)
    portal(coll, k, xc, WIN_W, WIN_Z0, WIN_Z1)
obj("Windows", m, [pbr(P + "PVC_White", (0.85, 0.85, 0.83), 0.3), GLASS, pbr(P + "Radiator_Paint", (0.78, 0.78, 0.76), 0.45)], coll)

# backdrop outside the south facade (hall_05 window: autumn birch/maple crowns over a lawn; exterior.py only covers
# the east / north facades): one vertical card of procedural crowns 9 m out + a lawn plane at the street (z -10)
m = Mesh()
YBD = YSF - TS - 9.0
m.face([(XFAR - 12, YBD, -10.0), (6.0, YBD, -10.0), (6.0, YBD, 9.0), (XFAR - 12, YBD, 9.0)], None, 0)
m.face([(XFAR - 12, YSF - TS - 0.2, -10.0), (XFAR - 12, YBD - 40, -10.0), (6.0, YBD - 40, -10.0), (6.0, YSF - TS - 0.2, -10.0)], None, 1)
TREES = pbr(P + "Ext_Treeline", (1, 1, 1), 0.85)
_n, _l = TREES.node_tree.nodes.new, TREES.node_tree.links.new
_pos = _n("ShaderNodeNewGeometry").outputs["Position"]
_nz = _n("ShaderNodeTexNoise"); _nz.inputs["Scale"].default_value = 0.9; _nz.inputs["Detail"].default_value = 12.0
_nz.inputs["Roughness"].default_value = 0.65
_l(_pos, _nz.inputs["Vector"])
_cr = _n("ShaderNodeValToRGB")                                                   # dark gaps -> green -> autumn yellow
_cr.color_ramp.elements[0].position, _cr.color_ramp.elements[0].color = 0.35, (0.025, 0.03, 0.015, 1)
_cr.color_ramp.elements[1].position, _cr.color_ramp.elements[1].color = 0.68, (0.36, 0.30, 0.06, 1)
_e = _cr.color_ramp.elements.new(0.52); _e.color = (0.08, 0.11, 0.03, 1)
_l(_nz.outputs["Fac"], _cr.inputs["Fac"])
_l(_cr.outputs["Color"], TREES.node_tree.nodes["Principled BSDF"].inputs["Base Color"])
_sep = _n("ShaderNodeSeparateXYZ"); _l(_pos, _sep.inputs[0])
_n2 = _n("ShaderNodeTexNoise"); _n2.inputs["Scale"].default_value = 0.25; _n2.inputs["Detail"].default_value = 4.0
_l(_pos, _n2.inputs["Vector"])
_top = _n("ShaderNodeMath"); _top.operation = 'MULTIPLY_ADD'                    # crown line z ~ 2..8 m (floor = 0)
_l(_n2.outputs["Fac"], _top.inputs[0]); _top.inputs[1].default_value = 12.0; _top.inputs[2].default_value = -1.0
_d = _n("ShaderNodeMath"); _d.operation = 'SUBTRACT'
_l(_top.outputs[0], _d.inputs[0]); _l(_sep.outputs["Z"], _d.inputs[1])
_hole = _n("ShaderNodeMath"); _hole.operation = 'MULTIPLY_ADD'                  # ragged edge from the leaf noise
_l(_nz.outputs["Fac"], _hole.inputs[0]); _hole.inputs[1].default_value = 3.0; _l(_d.outputs[0], _hole.inputs[2])
_a = _n("ShaderNodeMath"); _a.operation = 'SUBTRACT'; _a.use_clamp = True
_l(_hole.outputs[0], _a.inputs[0]); _a.inputs[1].default_value = 1.2
_l(_a.outputs[0], TREES.node_tree.nodes["Principled BSDF"].inputs["Alpha"])
LAWN = pbr(P + "Ext_Lawn", (0.06, 0.09, 0.03), 0.9)
ob = obj("Ext_Backdrop", m, [TREES, LAWN], coll)
ob.visible_shadow = False

# --- glass offices (hall_02 / hall_05): 50 mm white profiles, frosted lower panes with blinds, clear upper panes,
#     transom ZOM, lid ZOT; yellow glass-marking triangles at 1.55 ---
def glass_wall(m, a, b, fixed, along_x, n, side):
    """side = +1/-1: office interior on the +/- side of the glass line."""
    posts = [a + (b - a) * k / n for k in range(n + 1)]

    def bx(u0, u1, v0, v1, z0, z1):
        return ((u0, v0, z0), (u1, v1, z1)) if along_x else ((v0, u0, z0), (v1, u1, z1))
    bars = [bx(u - 0.025, u + 0.025, fixed - 0.025, fixed + 0.025, 0, ZOT) for u in posts]
    bars += [bx(posts[0] - 0.025, posts[-1] + 0.025, fixed - 0.025, fixed + 0.025, z0, z1)
             for z0, z1 in ((0.0, 0.06), (ZOM - 0.03, ZOM + 0.03), (ZOT - 0.05, ZOT))]
    m.solid(bars, 0)
    for p, q in zip(posts, posts[1:]):
        for z0, z1 in ((0.06, ZOM - 0.03), (ZOM + 0.03, ZOT - 0.05)):
            m.box(*bx(p + 0.025, q - 0.025, fixed - 0.004, fixed + 0.004, z0, z1), 1)
        v = fixed + side * 0.04
        m.box(*bx(p + 0.03, q - 0.03, v - 0.002, v + 0.002, 0.10, ZOM - 0.06), 2)          # blind, inside
        c = (p + q) / 2                                                         # glass-marking sticker, outside
        m.box(*bx(c - 0.045, c + 0.045, fixed - side * 0.0065, fixed - side * 0.0045, 1.50, 1.58), 3)


m = Mesh()
glass_wall(m, YSF, YC, XC, False, 4, -1)                                         # east face (x = XC), 4 bays
glass_wall(m, XFAR, XC, YC, True, 12, -1)                                        # north face (y = YC), 12 bays
m.box((XFAR, YSF, ZOT), (XC + 0.025, YC + 0.025, ZOT + 0.03), 0)                 # lid
for x in (-13.0, -16.75, -20.5):                                                 # office partitions (assumed)
    m.box((x - 0.05, YSF, 0), (x + 0.05, YC - 0.03, ZOT), 4)
obj("Glass_Offices", m, [POWDER, GLASS, BLIND, STICKER, WALL], coll)
fitting(coll, "Office_1", -10.42, -2.06, 1.20, 0.18, zc=ZOT)
fitting(coll, "Office_2", -14.9, -2.06, 1.20, 0.18, zc=ZOT)

# --- services: spiral ducts (hall_02 / hall_05), AC cassette, conduits, CCTV, Wi-Fi APs, exit sign ---
m = Mesh()
AX, AY = -6.37, -2.04                                                            # AC cassette (hall_05)
ZD, RD = 2.97, 0.16                    # spiral duct (hall_02 reads y -1.3, hall_05 runs it out of the AC box: y -1.7)
YD = -1.70
duct(m, (XC, YD, ZD), (AX - 0.40, YD, ZD), RD, 0)
for x in (-8.5, -7.2):
    m.add(cyl((x, YD, ZD + RD), (x, YD, CH), 0.004, 6), 1)
m.box((AX - 0.40, AY - 0.40, 2.78), (AX + 0.40, YD + 0.25, CH), 2)              # plenum / fan-coil box
m.box((AX - 0.36, AY - 0.36, 2.72), (AX + 0.36, AY + 0.36, 2.78), 2)            # cassette fascia
m.box((AX - 0.25, AY - 0.25, 2.719), (AX + 0.25, AY + 0.25, 2.72), 3)           # grille
for y, z in ((YN - 0.03, 2.905), (YN - 0.05, 2.925), (YN - 0.07, 2.945)):          # conduits along the cornice
    m.add(cyl((XFAR, y, z), (XE, y, z), 0.010, 6), 2)
for y in (0.95, 2.05):                                                            # conduits on the ceiling
    m.add(cyl((XFAR, y, CH - 0.013), (XE, y, CH - 0.013), 0.012, 6), 2)
for x in (-2.64, -9.75, -17.1):                                                  # Wi-Fi APs at the cornice (hall_04 / 02)
    m.box((x - 0.12, YN - 0.32, CH - 0.06), (x + 0.12, YN - 0.08, CH), 2)
m.T = Matrix.Translation((-2.37, YN - 0.12, 2.86))                               # CCTV dome (hall_04)
lathe(m, [(0.075, 0.0), (0.075, 0.03), (0.0001, 0.03)], 12, 2)
lathe(m, [(0.068, 0.0), (0.06, -0.035), (0.035, -0.06), (0.0001, -0.068)], 12, 4, cap_bot=False)
m.T = Matrix.Identity(4)
m.box((XFAR + 0.30, 1.18, 2.72), (XFAR + 0.36, 1.52, 2.88), 2)                    # exit sign (hall_02)
m.box((XFAR + 0.36, 1.20, 2.74), (XFAR + 0.361, 1.50, 2.86), 5)
obj("Services", m, [DUCT, CHROME, WHITE_PL, pbr(P + "Grille_Grey", (0.55, 0.55, 0.55), 0.5), BLACK, EXIT], coll)

# --- ceiling LED fittings (seen: linear over the corridor at x -7.84 and over the play zone at -7.42, small
#     squares at -13.8 / -19.8 / -23.3 on y = LIN_Y; none seen over the door bay) ---
fitting(coll, "Lin_01", -7.84, LIN_Y, 1.20, 0.18)
fitting(coll, "Lin_02", -7.42, -2.80, 1.20, 0.18)
fitting(coll, "Sq_01", -13.80, 1.43, 0.28, 0.28)
fitting(coll, "Sq_02", -19.80, 1.49, 0.28, 0.28)
fitting(coll, "Sq_03", -23.30, 1.50, 0.28, 0.28)
fitting(coll, "Far_Niche", XFAR - 0.75, (FARD[0] + FARD[1]) / 2, 0.555, 0.555, zc=2.60)   # bright room beyond the far doorway (hall_02: far end ~1.5 stops brighter than lit by the corridor alone)
m = Mesh()
for fm in FIT_BODIES:
    b = len(m.v)
    m.v += fm.v
    m.f += [tuple(i + b for i in q) for q in fm.f]
    m.m += fm.m
    m.uv += fm.uv
obj("Fitting_Bodies", m, [POWDER], coll)

# --- posters / prints / cut-out ---
m = Mesh()
y = YN - 0.002
m.quad([(-4.88, y, 1.13), (-5.40, y, 1.13), (-5.40, y, 1.91), (-4.88, y, 1.91)], 0)          # "Good practice" (pink)
m.quad([(-6.10, y, 1.40), (-6.45, y, 1.40), (-6.45, y, 1.90), (-6.10, y, 1.90)], 1)          # white A3-ish poster
m.box((-6.42, y - 0.002, 1.25), (-6.13, y, 1.34), 2)                                          # red sign below it
w, g = 0.61, 0.12                                                                             # framed print series
for k in range(7):
    x1 = -11.07 - k * (w + g)
    m.solid([((x1 - w, YN - 0.035, 1.00), (x1, YN, 1.87))], 3, [((x1 - w + 0.02, YN - 0.036, 1.02), (x1 - 0.02, YN + 0.01, 1.85))])
    m.quad([(x1 - 0.02, YN - 0.012, 1.02), (x1 - w + 0.02, YN - 0.012, 1.02), (x1 - w + 0.02, YN - 0.012, 1.85),
            (x1 - 0.02, YN - 0.012, 1.85)], 4)
    m.box((x1 - w + 0.02, YN - 0.032, 1.02), (x1 - 0.02, YN - 0.030, 1.85), 5)                 # glazing
x = XB - 0.012
m.quad([(x, -0.06, 1.25), (x, -0.73, 1.25), (x, -0.73, 1.82), (x, -0.06, 1.82)], 6)          # cut-out board (hall_01)
obj("Posters", m, [PG, A3, pbr(P + "Sign_Red", (0.45, 0.03, 0.05), 0.4), pbr(P + "Frame_Silver", (0.6, 0.6, 0.6), 0.3, 1.0),
                   PRINT, GLASS, CUTOUT], coll)


# --- furniture ---
def sofa(m, T, W=0.94, Dp=0.75):
    """High-back booth sofa (hall_02 / 03 / 05), local: seat front at x=0 facing -x, back at x=Dp, width along +y.
    Green plinth + arms, charcoal seat, two-tier upholstered back (lower cushion, chrome bar, upper panel), chrome feet."""
    m.T = T
    m.box((0.04, 0.02, 0.10), (Dp - 0.02, W - 0.02, 0.40), 0)
    m.box((0.0, 0.07, 0.40), (Dp - 0.19, W - 0.07, 0.50), 1)
    m.box((Dp - 0.19, 0.0, 0.10), (Dp, W, 0.95), 0)
    m.box((Dp - 0.15, 0.0, 0.99), (Dp, W, 1.40), 0)
    for yy in (0.0, W - 0.07):
        m.box((0.03, yy, 0.10), (Dp - 0.19, yy + 0.07, 0.64), 0)
    m.add(cyl((Dp - 0.08, 0.02, 0.97), (Dp - 0.08, W - 0.02, 0.97), 0.012, 8), 2)
    for xx in (0.08, Dp - 0.06):
        for yy in (0.06, W - 0.06):
            m.add(cyl((xx, yy, 0.0), (xx, yy, 0.10), 0.012, 8), 2)
    m.T = Matrix.Identity(4)


m = Mesh()
sofa(m, frame(-6.25, 2.00, 0))                   # B: back toward the folding table (east), seat faces west
sofa(m, frame(-6.90, 2.94, 180))                 # A: facing B across the booth
sofa(m, frame(-22.85, 2.94, 180))                # far end of the corridor (hall_02), facing east
obj("Booth", m, [SOFA, SEAT, CHROME], coll, bevel=0.025)


def folding_legs(m, x, y0, y1, h, mi):
    """Folding-table T-leg: two chrome tubes on a floor bar along y, top bracket."""
    for yy in (y0 + 0.12, y1 - 0.12):
        m.add(cyl((x, yy, 0.03), (x, yy, h - 0.03), 0.014, 8), mi)
    m.add(cyl((x, y0 + 0.02, 0.016), (x, y1 - 0.02, 0.016), 0.016, 8), mi)
    m.add(cyl((x, y0 + 0.10, h - 0.05), (x, y1 - 0.10, h - 0.05), 0.012, 8), mi)


m = Mesh()
# catering table (hall_01 / 03 / 04): 1.70 x 0.70 banquet table, white damask cloth draped 0.32 m, urns, sugar box ...
TX0, TX1, TY0, TY1, TH = -2.82, -1.20, 2.32, 2.90, 0.74
m.box((TX0, TY0, TH - 0.03), (TX1, TY1, TH - 0.004), 1)
for x in (TX0 + 0.20, TX1 - 0.20):
    folding_legs(m, x, TY0 + 0.05, TY1 - 0.05, TH - 0.03, 2)
drape(m, TX0, TX1, TY0, TY1, TH, 0.28, 0)
for ux, uy in ((-2.19, 2.72), (-1.69, 2.70)):                                    # stainless insulated urns
    m.T = Matrix.Translation((ux, uy, TH + 0.06))
    lathe(m, [(0.118, 0.0), (0.122, 0.02), (0.122, 0.33), (0.112, 0.35)], 16, 3, cap_bot=True, cap_top=False)
    lathe(m, [(0.112, 0.35), (0.105, 0.37), (0.06, 0.39), (0.035, 0.40), (0.035, 0.43), (0.0001, 0.435)], 16, 4,
          cap_bot=False)
    for a in (90, 210, 330):
        c, s = math.cos(math.radians(a)), math.sin(math.radians(a))
        m.add(cyl((0.09 * c, 0.09 * s, 0.0), (0.105 * c, 0.105 * s, -0.06), 0.008, 6), 4)
    m.box((-0.02, -0.17, 0.0), (0.02, -0.12, 0.06), 4)                          # tap
    m.add(cyl((0, -0.122, 0.04), (0, -0.15, 0.04), 0.012, 6), 4)
    m.T = Matrix.Identity(4)
m.T = frame(-2.52, 2.60, -12, TH)                                                # UNIQUE sugar-stick box
m.box((-0.06, -0.045, 0), (0.06, 0.045, 0.075), 6)
m.quad([(-0.06, -0.0455, 0.0), (0.06, -0.0455, 0.0), (0.06, -0.0455, 0.075), (-0.06, -0.0455, 0.075)], 7)
m.T = Matrix.Identity(4)
for (px, py, r, h) in ((-2.02, 2.42, 0.11, 0.025), (-1.80, 2.38, 0.09, 0.05), (-2.30, 2.40, 0.10, 0.02)):
    m.T = Matrix.Translation((px, py, TH))
    lathe(m, [(r * 0.7, 0.0), (r, h), (r * 0.95, h)], 14, 5, cap_top=False)
    m.T = Matrix.Identity(4)
for (px, py) in ((-1.46, 2.52), (-1.33, 2.36)):                                  # black octagonal trays
    m.T = Matrix.Translation((px, py, TH))
    lathe(m, [(0.12, 0.0), (0.15, 0.02)], 8, 4, cap_top=False)
    m.T = Matrix.Identity(4)
m.T = Matrix.Translation((-2.33, 2.52, TH))                                      # paper cup
lathe(m, [(0.03, 0.0), (0.042, 0.10)], 10, 5, cap_top=False)
m.T = Matrix.Identity(4)
# dark folding table east of the booth (hall_02 / 03): 1.40 x 0.58, mahogany laminate, chrome T-legs, a plate
FX0_, FX1_ = -5.45, -4.05
m.box((FX0_, YN - 0.58, 0.715), (FX1_, YN - 0.01, 0.74), 8)
for x in (FX0_ + 0.22, FX1_ - 0.22):
    folding_legs(m, x, YN - 0.56, YN - 0.03, 0.715, 2)
m.T = Matrix.Translation((-4.55, YN - 0.30, 0.74))
lathe(m, [(0.08, 0.0), (0.11, 0.015), (0.105, 0.015)], 14, 5, cap_top=False)
m.T = Matrix.Identity(4)
obj("Tables", m, [CLOTH, POWDER, CHROME, STEEL, BLACK, PAPER, WHITE_PL, UNIQUE, MAHOG], coll)

# --- play area (hall_02 / hall_05): foosball "ESPAK", air hockey, birch tray table on X legs, yellow ottoman ---
m = Mesh()
m.T = frame(-6.41, -0.25, 54)                       # foosball: long axis (goal to goal) local x; legs from the BA
m.solid([((-0.66, -0.36, 0.66), (0.66, 0.36, 0.90))], 0, [((-0.62, -0.32, 0.70), (0.62, 0.32, 0.91))])
m.box((-0.62, -0.32, 0.70), (0.62, 0.32, 0.705), 3)                              # pitch
for u in (-0.595, 0.595):
    for v in (-0.245, 0.245):
        m.box((u - 0.03, v - 0.03, 0.0), (u + 0.03, v + 0.03, 0.66), 0)
    m.box((u - 0.02, -0.245, 0.20), (u + 0.02, 0.245, 0.25), 0)
for q in range(8):
    x = -0.525 + q * 0.15
    side = 1 if q in (0, 1, 3, 5) else -1
    m.add(cyl((x, -0.52, 0.85), (x, 0.52, 0.85), 0.008, 6), 1)
    m.add(cyl((x, 0.52 * side, 0.85), (x, 0.65 * side, 0.85), 0.018, 6), 2)
    n = (1, 2, 5, 3, 3, 5, 2, 1)[q]
    for k in range(n):
        yy = (k - (n - 1) / 2) * (0.56 / max(n, 2))
        m.box((x - 0.012, yy - 0.015, 0.74), (x + 0.012, yy + 0.015, 0.88), 4 if side > 0 else 5)
m.T = Matrix.Identity(4)
m.T = frame(-8.66, -3.27, 90)                       # air hockey: 2.13 x 1.10, long axis along y
m.box((-1.065, -0.55, 0.65), (1.065, 0.55, 0.78), 6)
m.box((-1.04, -0.525, 0.78), (1.04, 0.525, 0.785), 7)
m.solid([((-1.065, -0.55, 0.78), (1.065, 0.55, 0.81))], 8, [((-1.04, -0.525, 0.78), (1.04, 0.525, 0.82))])
for u in (-0.85, 0.85):                             # arched pedestals
    m.box((u - 0.10, -0.35, 0.0), (u + 0.10, 0.35, 0.06), 6)
    m.box((u - 0.07, -0.18, 0.06), (u + 0.07, 0.18, 0.65), 6)
for u in (-0.6, 0.6):
    m.T = frame(-8.66, -3.27, 90) @ Matrix.Translation((u, 0.0, 0.785))
    lathe(m, [(0.045, 0.0), (0.045, 0.02), (0.02, 0.03), (0.02, 0.07), (0.0001, 0.075)], 12, 4, cap_bot=False)
m.T = Matrix.Identity(4)
m.T = frame(-6.35, -3.15, 120)                      # birch tray table on black X legs, 1.20 x 0.85
m.box((-0.60, -0.425, 0.70), (0.60, 0.425, 0.72), 9)
m.solid([((-0.60, -0.425, 0.72), (0.60, 0.425, 0.75))], 9, [((-0.57, -0.395, 0.72), (0.57, 0.395, 0.76))])
for v in (-0.36, 0.36):
    for s_ in (-1, 1):
        m.add(cyl((-0.45 * s_, v, 0.02), (0.45 * s_, v, 0.69), 0.016, 6), 0)
    m.add(cyl((-0.46, v, 0.02), (0.46, v, 0.02), 0.015, 6), 0)
m.add(cyl((0.0, -0.36, 0.35), (0.0, 0.36, 0.35), 0.012, 6), 0)
m.T = Matrix.Identity(4)
m.box((-9.01, -0.92, 0.30), (-8.59, 0.08, 0.42), 10)                             # yellow ottoman, chrome legs
for x in (-8.96, -8.64):
    for y in (-0.86, 0.02):
        m.add(cyl((x, y, 0.0), (x, y, 0.30), 0.012, 6), 1)
obj("Play", m, [GREY, CHROME, BLACK, pbr(P + "Foosball_Pitch", (0.10, 0.30, 0.10), 0.5), RED,
                pbr(P + "Plastic_YellowPlayer", (0.70, 0.55, 0.02), 0.35), BLACK, WHITE_PL,
                pbr(P + "Aluminium_Rim", (0.75, 0.75, 0.76), 0.25, 1.0), BIRCH, YELLOW], coll)

# --- exercise-bike trainer in front of the teal wall (hall_01), a camera pole beside it ---
m = Mesh()
BX = XB - 0.30
for yc in (-1.25, -0.20):                                                        # wheels: 16-gon rim tubes
    for i in range(16):
        a0, a1 = 2 * math.pi * i / 16, 2 * math.pi * (i + 1) / 16
        m.add(cyl((BX, yc + 0.33 * math.cos(a0), 0.36 + 0.33 * math.sin(a0)),
                  (BX, yc + 0.33 * math.cos(a1), 0.36 + 0.33 * math.sin(a1)), 0.018, 4), 1)
    m.add(cyl((BX - 0.05, yc, 0.36), (BX + 0.05, yc, 0.36), 0.03, 8), 2)
for a, b in (((-1.25, 0.36), (-0.78, 0.30)), ((-0.78, 0.30), (-0.95, 0.88)), ((-0.95, 0.88), (-1.25, 0.36)),
             ((-0.78, 0.30), (-0.36, 0.86)), ((-0.95, 0.80), (-0.38, 0.80)), ((-0.36, 0.86), (-0.20, 0.36)),
             ((-0.36, 0.86), (-0.40, 1.00))):
    m.add(cyl((BX, a[0], a[1]), (BX, b[0], b[1]), 0.022, 8), 0)
m.add(cyl((BX - 0.28, -0.40, 1.00), (BX + 0.28, -0.40, 1.00), 0.012, 8), 1)      # handlebar
m.box((BX - 0.07, -1.06, 0.88), (BX + 0.07, -0.84, 0.94), 2)                     # saddle
m.box((BX - 0.30, -1.55, 0.0), (BX + 0.30, -0.95, 0.03), 2)                      # trainer base
m.add(cyl((BX - 0.25, -1.40, 0.03), (BX - 0.05, -1.25, 0.36), 0.02, 6), 0)
m.add(cyl((BX + 0.25, -1.40, 0.03), (BX + 0.05, -1.25, 0.36), 0.02, 6), 0)
m.box((BX - 0.15, -0.30, 0.0), (BX + 0.15, -0.10, 0.04), 1)                      # front-wheel block
m.add(cyl((XB - 0.20, 0.08, 0.0), (XB - 0.20, 0.08, 1.30), 0.012, 6), 3)          # pole + device
m.box((XB - 0.24, 0.05, 1.30), (XB - 0.16, 0.11, 1.42), 1)
obj("Bike", m, [BLUE_BIKE, BLACK, WHITE_PL, CHROME], coll)

dg = bpy.context.evaluated_depsgraph_get()
tris = 0
for o in coll.objects:
    if o.type == 'MESH':
        me = o.evaluated_get(dg).to_mesh()
        tris += sum(len(p.vertices) - 2 for p in me.polygons)
        o.evaluated_get(dg).to_mesh_clear()
print("ROOM3 OK", len(coll.objects), "objects", tris, "tris")
