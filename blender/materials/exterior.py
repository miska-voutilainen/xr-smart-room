# Exterior seen through the room-1 window (x > 6.6) and the lab windows on the same facade:
# multi-stem box-elder / ash clumps right in front of the facade (yellow pinnate leaves, bare whips on top),
# a plain lawn plane far below and the outer reveal of our own facade. NOT sky / fog / sun (render/).
# v2 cull (s1_cull): neighbouring buildings, TV mast, street, far trees, conifers and rain streaks removed
# (user: no buildings in the windows; the rest was hit by a handful of probe rays or sub-pixel). Trees are
# low-poly: open tubes, leaf-cluster cards (1 quad, 8-10 leaves each), twigs are leaf emitters only.
# Standalone + idempotent: every Ext_* object is rebuilt each run; materials / node group get-or-create,
# Ext_* materials / images / node groups left without users are deleted at the end.
# Assumptions (from photo measurements, see report): room floor z=0 is ~7 m above street level.
import math
import random

import bpy
from mathutils import Quaternion, Vector

G = -10.0                     # ground level: room floor ~10 m up (lab windows look DOWN onto the slate roof of
                              # the 3-storey block behind, 151022; pale block eave ~ eye level in 150359)
FACADE_X = 6.60               # outer face of the window wall (build_room W + T_WIN)
REVEAL = 0.12                 # outer reveal depth beyond the frame wall (white jamb visible in 150359)
WIN_Y0, WIN_Y1, WIN_Z0, WIN_Z1 = 0.20, 1.80, 0.85, 2.87   # build_room.py WIN_*
COLL = "Exterior"
XLIM = FACADE_X + REVEAL + 0.5   # branches stay this far out from the facade
LEAF_S = 0.80                 # leaf-cluster card size (m)
LEAF_DMAX = 6000.0            # leaf cards per m2 of twig surface at leafy=1


# ---------- infrastructure ----------

def coll():
    c = bpy.data.collections.get(COLL) or bpy.data.collections.new(COLL)
    if c.name not in bpy.context.scene.collection.children:
        bpy.context.scene.collection.children.link(c)
    return c


def purge():
    """Remove all Ext_* objects and their meshes so every run starts clean (no .001 duplicates)."""
    for ob in [o for o in bpy.data.objects if o.name.startswith("Ext_")]:
        data = ob.data
        bpy.data.objects.remove(ob, do_unlink=True)
        if isinstance(data, bpy.types.Mesh) and data.users == 0:
            bpy.data.meshes.remove(data)
    for me in [m for m in bpy.data.meshes if m.name.startswith("Ext_") and m.users == 0]:
        bpy.data.meshes.remove(me)


def material(name, color, rough=0.8, **extra):
    """Get-or-create placeholder Principled material (group 2 overrides by name)."""
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    out.location = (300, 0)
    nt.links.new(b.outputs["BSDF"], out.inputs["Surface"])
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    for k, v in extra.items():
        b.inputs[k].default_value = v
    m.diffuse_color = (*color, 1)
    return m


class Mesh:
    """verts / faces / per-face material index (+ optional per-face float attributes)."""
    def __init__(self):
        self.v, self.f, self.m, self.attr = [], [], [], {}

    def add(self, verts, faces, mat=0, **attrs):
        base = len(self.v)
        self.v += [tuple(p) for p in verts]
        self.f += [tuple(i + base for i in q) for q in faces]
        self.m += [mat] * len(faces)
        for k, val in attrs.items():
            self.attr.setdefault(k, [0.0] * (len(self.f) - len(faces)))
        for k in self.attr:
            self.attr[k] += [attrs.get(k, 0.0)] * len(faces)

    def box(self, lo, hi, mat=0):
        (x0, y0, z0), (x1, y1, z1) = lo, hi
        v = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
             (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
        self.add(v, [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)], mat)

    def obj(self, name, mats, smooth=False):
        me = bpy.data.meshes.new(name)
        me.from_pydata(self.v, [], self.f)
        assert len(me.polygons) == len(self.f)
        for p, mi in zip(me.polygons, self.m):
            p.material_index = mi
            p.use_smooth = smooth
        for k, vals in self.attr.items():
            me.attributes.new(k, "FLOAT", "FACE").data.foreach_set("value", vals)
        for mt in mats:
            me.materials.append(mt)
        ob = bpy.data.objects.new(name, me)
        coll().objects.link(ob)
        return ob


def solid_mesh(solids, holes=()):
    """Boolean-free union of boxes minus holes -> manifold all-quad mesh (same as build_room.py)."""
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


def tube(M, pts, radii, k, mat=0, **attrs):
    """Open swept tube (parallel-transport frames), quads only: ends are a 2 mm tip or buried in the ground."""
    n = len(pts)
    verts, nrm = [], None
    for i, p in enumerate(pts):
        t = (pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]).normalized()
        nrm = t.orthogonal().normalized() if nrm is None else (nrm - t * nrm.dot(t)).normalized()
        b = t.cross(nrm)
        for j in range(k):
            a = 2 * math.pi * j / k
            verts.append(p + (nrm * math.cos(a) + b * math.sin(a)) * radii[i])
    faces = [(i * k + j, i * k + (j + 1) % k, (i + 1) * k + (j + 1) % k, (i + 1) * k + j)
             for i in range(n - 1) for j in range(k)]
    M.add(verts, faces, mat, **attrs)


# ---------- materials (placeholders; names are the contract for shaders/arch.py) ----------

def leaf_image(n=512):
    """Procedural RGBA leaf cluster: a twig with 5 sprays of 3 box-elder / ash compound leaves (3-5 lanceolate
    leaflets each), packed. v = 0 is the twig end (card base). Painted with numpy: no external file, Unity-bakeable."""
    import numpy as np
    img = bpy.data.images.get("Ext_LeafSpray")
    if img is None or tuple(img.size) != (n, n):
        if img:
            bpy.data.images.remove(img)
        img = bpy.data.images.new("Ext_LeafSpray", n, n, alpha=True)
    vv, uu = (np.mgrid[0:n, 0:n] + 0.5) / n
    rgb = np.zeros((n, n, 3))
    alpha = np.zeros((n, n))
    rnd = random.Random(5)

    def stroke(x0, y0, ang, ln, wd, col, taper=True):
        c, s_ = math.cos(ang), math.sin(ang)
        du, dv = uu - x0, vv - y0
        t = (du * c + dv * s_) / ln                      # 0..1 along the leaflet
        w = (-du * s_ + dv * c) / wd                     # -1..1 across
        prof = np.sqrt(np.clip(t * (1 - t), 0, None)) * 2 * (1.15 - 0.45 * t if taper else 1)
        m = (t > 0) & (t < 1) & (np.abs(w) < prof)
        shade = 0.82 + 0.18 * np.clip(np.abs(w) / np.maximum(prof, 1e-3) * 3, 0, 1)   # darker midrib
        edge = np.clip((np.abs(w) / np.maximum(prof, 1e-3) - 0.75) * 4, 0, 1)        # browning rim
        cc = np.array(col)[None, None, :] * shade[..., None]
        cc = cc * (1 - 0.35 * edge[..., None]) + np.array((0.35, 0.18, 0.05)) * 0.35 * edge[..., None]
        rgb[m] = cc[m]
        alpha[m] = 1.0

    def spray(x0, y0, a0, sc):
        """3 compound leaves fanned around direction a0 from (x0, y0), scaled by sc (1 = whole card)."""
        for da in (-30, 0, 28):
            ang = a0 + math.radians(da + rnd.uniform(-8, 8))
            rl = (0.48 + rnd.uniform(-0.04, 0.06)) * sc
            tint = rnd.uniform(-0.08, 0.08)
            base = (0.86 + tint, 0.70 + tint * 1.5, 0.30)
            stroke(x0, y0, ang, rl, 0.008 * sc, (0.45, 0.36, 0.18), taper=False)   # rachis
            ex, ey = x0 + math.cos(ang) * rl, y0 + math.sin(ang) * rl
            pairs = 2 if rnd.random() < 0.6 else 1
            for k in range(pairs):
                t = 0.45 + 0.3 * k
                px, py = x0 + math.cos(ang) * rl * t, y0 + math.sin(ang) * rl * t
                for side in (-1, 1):
                    stroke(px, py, ang + side * math.radians(rnd.uniform(45, 60)),
                           (0.17 + rnd.uniform(-0.02, 0.03)) * sc, 0.045 * sc, base)
            stroke(ex - math.cos(ang) * 0.02 * sc, ey - math.sin(ang) * 0.02 * sc, ang + rnd.uniform(-0.15, 0.15),
                   0.21 * sc, 0.05 * sc, base)

    stroke(0.5, 0.0, math.radians(90), 0.80, 0.006, (0.30, 0.26, 0.20), taper=False)     # twig
    for t, side in ((0.10, -1), (0.28, 1), (0.45, -1), (0.62, 1)):
        spray(0.5, t, math.radians(90 + side * rnd.uniform(35, 55)), 0.46 + rnd.uniform(-0.04, 0.04))
    spray(0.5, 0.78, math.radians(90 + rnd.uniform(-10, 10)), 0.42)                       # terminal spray
    px = np.dstack([rgb, alpha]).astype(np.float32)
    img.pixels.foreach_set(px.ravel())
    img.pack()
    return img


def leaf_material():
    """Alpha-cutout leaf card. Per-instance colour shift (Object Info Random) from yellow to orange-brown."""
    m = material("Ext_Leaf", (0.72, 0.55, 0.18), 0.55)
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = leaf_image()
    tex.interpolation = "Linear"
    info = nt.nodes.new("ShaderNodeObjectInfo")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    els = ramp.color_ramp.elements
    els[0].position, els[0].color = 0.0, (0.72, 0.48, 0.32, 1)     # orange-brown (few)
    els[1].position, els[1].color = 1.0, (1.0, 1.0, 0.95, 1)       # texture as painted (yellow)
    e = els.new(0.22)
    e.color = (0.92, 0.80, 0.62, 1)
    mul = nt.nodes.new("ShaderNodeMix")
    mul.data_type, mul.blend_type = "RGBA", "MULTIPLY"
    mul.inputs["Factor"].default_value = 1.0
    nt.links.new(info.outputs["Random"], ramp.inputs["Fac"])
    nt.links.new(tex.outputs["Color"], mul.inputs["A"])
    nt.links.new(ramp.outputs["Color"], mul.inputs["B"])
    nt.links.new(mul.outputs["Result"], b.inputs["Base Color"])
    nt.links.new(tex.outputs["Alpha"], b.inputs["Alpha"])
    b.inputs["Subsurface Weight"].default_value = 0.0
    m.surface_render_method = "DITHERED"
    return m


MAT = dict(
    bark=material("Ext_Bark", (0.16, 0.15, 0.13), 0.85),
    leaf=leaf_material(),
    grass=material("Ext_Grass", (0.12, 0.17, 0.07), 0.9),
    reveal=material("Ext_Reveal_White", (0.80, 0.80, 0.78), 0.9),      # peeling white outer jamb
    tin=material("Ext_Sill_Metal", (0.45, 0.46, 0.47), 0.35, **{"Metallic": 1.0}),
    canopy=material("Ext_Canopy_Far", (0.55, 0.38, 0.05), 0.8),       # arch.py `leaves` (no UV -> opaque)
)


# ---------- leaves: leaf-cluster card + GN scatter on twigs ----------

def leaf_object():
    """Leaf cluster card: one quad, LEAF_S x LEAF_S, base at origin, growing along +Z."""
    S = LEAF_S
    M = Mesh()
    M.add([(-S / 2, 0, 0), (S / 2, 0, 0), (S / 2, 0, S), (-S / 2, 0, S)], [(0, 1, 2, 3)])
    ob = M.obj("Ext_Leaf", [MAT["leaf"]])
    ob.location = (FACADE_X + 2.0, -3.0, G - 1.0)     # parked below ground; render-hidden source
    ob.hide_render = True
    me = ob.data
    uv = me.uv_layers.new(name="UVMap")
    for loop in me.loops:
        co = me.vertices[loop.vertex_index].co
        uv.data[loop.index].uv = (co.x / S + 0.5, co.z / S)
    return ob


def sock(socks, name, typ):
    """Random Value has one socket per data type under the same name; pick by type."""
    return next(s for s in socks if s.name == name and s.type == typ)


def leaf_scatter_group():
    ng = bpy.data.node_groups.get("Ext_LeafScatter") or bpy.data.node_groups.new("Ext_LeafScatter",
                                                                                  "GeometryNodeTree")
    ng.nodes.clear()
    ng.interface.clear()
    ng.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    ng.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    N, L = ng.nodes, ng.links
    gi, go = N.new("NodeGroupInput"), N.new("NodeGroupOutput")
    leafy = N.new("GeometryNodeInputNamedAttribute")
    leafy.data_type = "FLOAT"
    leafy.inputs["Name"].default_value = "leafy"
    dist = N.new("GeometryNodeDistributePointsOnFaces")
    dist.distribute_method = "POISSON"
    dist.inputs["Distance Min"].default_value = 0.0
    info = N.new("GeometryNodeObjectInfo")
    info.transform_space = "ORIGINAL"
    rnd_rot = N.new("FunctionNodeRandomValue")
    rnd_rot.data_type = "FLOAT_VECTOR"
    rnd_rot.inputs["Min"].default_value = (-0.5, -0.5, -math.pi)
    rnd_rot.inputs["Max"].default_value = (0.9, 0.5, math.pi)
    rot = N.new("FunctionNodeRotateRotation")
    rot.rotation_space = "LOCAL"
    rnd_scl = N.new("FunctionNodeRandomValue")
    rnd_scl.data_type = "FLOAT"
    sock(rnd_scl.inputs, "Min", "VALUE").default_value = 0.7
    sock(rnd_scl.inputs, "Max", "VALUE").default_value = 1.25
    inst = N.new("GeometryNodeInstanceOnPoints")
    join = N.new("GeometryNodeJoinGeometry")
    # twigs only carry leaves: their faces are dropped from the rendered / exported mesh
    twig = N.new("GeometryNodeInputNamedAttribute")
    twig.data_type = "FLOAT"
    twig.inputs["Name"].default_value = "twig"
    cmp = N.new("FunctionNodeCompare")
    cmp.data_type, cmp.operation = "FLOAT", "GREATER_THAN"
    cmp.inputs["B"].default_value = 0.5
    drop = N.new("GeometryNodeDeleteGeometry")
    drop.domain = "FACE"
    L.new(twig.outputs["Attribute"], cmp.inputs["A"])
    L.new(gi.outputs["Geometry"], drop.inputs["Geometry"])
    L.new(cmp.outputs["Result"], drop.inputs["Selection"])
    L.new(gi.outputs["Geometry"], dist.inputs["Mesh"])
    dist.inputs["Density Max"].default_value = LEAF_DMAX
    L.new(leafy.outputs["Attribute"], dist.inputs["Density Factor"])
    info.inputs["Object"].default_value = LEAF_OB
    L.new(dist.outputs["Rotation"], rot.inputs["Rotation"])
    L.new(rnd_rot.outputs["Value"], rot.inputs["Rotate By"])
    L.new(dist.outputs["Points"], inst.inputs["Points"])
    L.new(info.outputs["Geometry"], inst.inputs["Instance"])
    L.new(rot.outputs["Rotation"], inst.inputs["Rotation"])
    L.new(sock(rnd_scl.outputs, "Value", "VALUE"), inst.inputs["Scale"])
    L.new(drop.outputs["Geometry"], join.inputs["Geometry"])
    L.new(inst.outputs["Instances"], join.inputs["Geometry"])
    L.new(join.outputs["Geometry"], go.inputs["Geometry"])
    return ng


# ---------- trees ----------

def grow(start, d, length, r0, seg, curv, up, rnd, taper=0.85):
    n = max(2, int(length / seg + 0.5))
    pts, p = [start.copy()], start.copy()
    for _ in range(n):
        d = (d + Vector((rnd.gauss(0, curv), rnd.gauss(0, curv), rnd.gauss(0, curv) + up))).normalized()
        p = p + d * (length / n)
        if p.x < XLIM:                       # never grow into our own building: bounce off the facade
            d.x = abs(d.x)
            p.x = 2 * XLIM - p.x
        pts.append(p)
    radii = [max(r0 * (1 - taper * i / n), 0.002) for i in range(n + 1)]
    return pts, radii


def outward(d, ang, rnd):
    """Direction rotated `ang` away from d around a random azimuth."""
    perp = d.orthogonal().normalized()
    perp.rotate(Quaternion(d, rnd.uniform(0, 2 * math.pi)))
    return (d * math.cos(ang) + perp * math.sin(ang)).normalized()


def tree_clump(name, x, y, height, seed, stems=(5, 8), sides=(5, 3, 3), leaves=700,
               lean=(0.05, 0.30), lat_every=0.75, lat_start=0.38, bare_top=0.80):
    """Multi-stem box elder / ash clump (`leaves` = leaf-cluster cards). Laterals only from lat_start (the
    lower trunk is bare and out of view from the windows); leafy crown up to bare_top, bare whips above.
    Twig tubes (twig=1) only emit leaves; the GN modifier deletes them from the rendered mesh."""
    rnd = random.Random(seed)
    M = Mesh()
    base = Vector((x, y, G))
    top_z = G + height
    for s in range(rnd.randint(*stems)):
        sb = base + Vector((rnd.uniform(-0.35, 0.35), rnd.uniform(-0.35, 0.35), 0))
        az = rnd.uniform(0, 2 * math.pi)
        th = rnd.uniform(*lean)
        d = Vector((math.cos(az) * math.sin(th), math.sin(az) * math.sin(th), math.cos(th)))
        L = height * rnd.uniform(0.72, 1.0) / max(d.z, 0.5)
        r0 = rnd.uniform(0.035, 0.08) * (L / 10.0)
        pts, radii = grow(sb, d, L, r0, 1.3, 0.05, 0.03, rnd, 0.9)
        tube(M, pts, radii, sides[0], 0, leafy=0.0)
        # laterals
        h = L * lat_start + rnd.uniform(0, 0.6)
        seglen = L / (len(pts) - 1)
        while h < L * 0.97:
            i = min(int(h / seglen), len(pts) - 2)
            frac = h / L
            p0 = pts[i].lerp(pts[i + 1], h / seglen - i)
            sd = (pts[i + 1] - pts[i]).normalized()
            ld = outward(sd, rnd.uniform(0.45, 0.85), rnd)
            ll = L * rnd.uniform(0.10, 0.26) * (1.15 - 0.7 * frac)
            lr = max(radii[i] * 0.45, 0.008)
            up = 0.05
            lp, lrad = grow(p0, ld, ll, lr, 0.9, 0.10, up, rnd)
            zrel = (p0.z - G) / height
            bare_branch = rnd.random() < 0.22
            leafy = 0.0 if bare_branch else max(0.08, min(1.0, (bare_top - zrel) / 0.12 + 1.0))
            tube(M, lp, lrad, sides[1], 0, leafy=0.25 * leafy)
            # twigs off the lateral
            for _ in range(rnd.randint(2, 4)):
                t = rnd.uniform(0.25, 0.95)
                j = min(int(t * (len(lp) - 1)), len(lp) - 2)
                q0 = lp[j].lerp(lp[j + 1], t * (len(lp) - 1) - j)
                td = outward((lp[j + 1] - lp[j]).normalized(), rnd.uniform(0.3, 0.8), rnd)
                tp, trad = grow(q0, td, rnd.uniform(0.3, 0.8), 0.006, 0.4, 0.15, up * 2, rnd, 0.6)
                tube(M, tp, trad, sides[2], 0, leafy=leafy, twig=1.0)
            h += lat_every * rnd.uniform(0.6, 1.4)
        # bare whip tops: a few thin shoots near the stem tip
        for _ in range(rnd.randint(1, 3)):
            p0 = pts[-2].lerp(pts[-1], rnd.random())
            wp, wr = grow(p0, outward(d, rnd.uniform(0.1, 0.4), rnd), rnd.uniform(0.6, 1.5), 0.008, 0.7,
                          0.06, 0.04, rnd, 0.7)
            tube(M, wp, wr, sides[2], 0, leafy=0.04 if pts[-1].z < top_z - 1 else 0.0)
    ob = M.obj(name, [MAT["bark"]], smooth=True)
    # leaf density so that the expected leaf count ~= `leaves`: baked into the leafy attribute
    # (GN density = LEAF_DMAX * leafy), so the modifier needs no per-object inputs.
    me = ob.data
    area = [p.area for p in me.polygons]
    lf = [0.0] * len(me.polygons)
    me.attributes["leafy"].data.foreach_get("value", lf)
    weighted = sum(a * w for a, w in zip(area, lf)) or 1.0
    k = min(leaves / weighted / LEAF_DMAX, 1.0 / max(lf + [1e-6]))
    me.attributes["leafy"].data.foreach_set("value", [w * k for w in lf])
    ob.modifiers.new("Ext_Leaves", "NODES").node_group = LEAF_NG
    return ob


def build_far_trees(seed=21):
    """Haze depth cue (s2_atmos request): opaque low-poly crown blobs 20-150 m out, in front of the room-1 /
    lab east windows (+x) and the lab north windows (+y). One mesh, ~36 tris per blob, no trunks."""
    rnd = random.Random(seed)
    M = Mesh()
    n, rings = 6, 4

    def blob(cx, cy, cz, rx, rz):
        verts = [(cx, cy, cz - rz)]
        for i in range(1, rings):
            a = math.pi * i / rings
            for k in range(n):
                t = 2 * math.pi * (k + 0.5 * (i % 2)) / n
                j = rnd.uniform(0.8, 1.15)
                verts.append((cx + rx * j * math.sin(a) * math.cos(t), cy + rx * j * math.sin(a) * math.sin(t),
                              cz - rz * math.cos(a)))
        verts.append((cx, cy, cz + rz))
        top = len(verts) - 1
        faces = [(0, 1 + (k + 1) % n, 1 + k) for k in range(n)]
        for i in range(rings - 2):
            for k in range(n):
                a_, b_ = 1 + i * n + k, 1 + i * n + (k + 1) % n
                faces.append((a_, b_, b_ + n, a_ + n))
        last = 1 + (rings - 2) * n
        faces += [(last + k, last + (k + 1) % n, top) for k in range(n)]
        M.add(verts, faces)

    spots = [(rnd.uniform(25, 150), rnd.uniform(-70, 70)) for _ in range(11)]      # east (+x)
    spots += [(rnd.uniform(-40, 60), rnd.uniform(30, 150)) for _ in range(6)]       # north (+y)
    for x, y in spots:
        h = rnd.uniform(9, 15)
        for _ in range(rnd.randint(2, 3)):
            r = h * rnd.uniform(0.25, 0.38)
            blob(x + rnd.uniform(-3, 3), y + rnd.uniform(-3, 3), G + h - r * rnd.uniform(0.8, 1.1), r, r * 1.2)
    M.obj("Ext_TreeFar", [MAT["canopy"]], smooth=True)


# ---------- ground, own facade ----------

def build_ground():
    """Plain lawn plane far below (seen when looking down through the windows); fog does the rest."""
    M = Mesh()
    S = 400.0
    n = 1                                       # flat: one quad is enough
    verts = [(-S + 2 * S * i / n + FACADE_X, -S + 2 * S * j / n, G) for j in range(n + 1) for i in range(n + 1)]
    faces = [(j * (n + 1) + i, j * (n + 1) + i + 1, (j + 1) * (n + 1) + i + 1, (j + 1) * (n + 1) + i)
             for j in range(n) for i in range(n)]
    M.add(verts, faces, 0)
    M.obj("Ext_Ground", [MAT["grass"]])


def build_own_facade():
    """Outer reveal of the room-1 window: the 12 cm white jamb faces (seen at the pane edges in 150359 /
    112212) + galvanised drip sill. The outer plaster skin was never hit by the visibility probe: dropped."""
    M = Mesh()
    v, f = solid_mesh([((FACADE_X, -0.5, -0.5), (FACADE_X + REVEAL, 2.56, 3.3))],
                      [((FACADE_X - 1, WIN_Y0, WIN_Z0), (FACADE_X + 1, WIN_Y1, WIN_Z1))])

    def jamb(q):                                # face centre inside the opening
        c = [sum(v[i][a] for i in q) / len(q) for a in range(3)]
        return WIN_Y0 - 1e-4 <= c[1] <= WIN_Y1 + 1e-4 and WIN_Z0 - 1e-4 <= c[2] <= WIN_Z1 + 1e-4

    M.add(v, [q for q in f if jamb(q)], 0)
    M.obj("Ext_Facade", [MAT["reveal"]])
    # drip sill as a proper closed wedge: top slope + drip nose (8 quads)
    M = Mesh()
    xi, xo = FACADE_X - 0.015, FACADE_X + REVEAL + 0.05
    zi, zo, zn = WIN_Z0 + 0.025, WIN_Z0 + 0.003, WIN_Z0 - 0.035
    prof = [(xi, zi), (xo, zo), (xo, zn), (xo - 0.008, zn), (xo - 0.008, zo - 0.002), (xi, zi - 0.002)]
    n = len(prof)
    verts = [(x, y, z) for y in (WIN_Y0 + 0.002, WIN_Y1 - 0.002) for x, z in prof]
    faces = [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
    faces += [tuple(reversed(range(n))), tuple(n + i for i in range(n))]
    M.add(verts, faces, 0)
    M.obj("Ext_Sill_Out", [MAT["tin"]])


# ---------- build ----------

def purge_orphans():
    """Drop Ext_* materials / images / node groups nothing uses any more (e.g. from older builds)."""
    for coll_ in (bpy.data.materials, bpy.data.node_groups, bpy.data.images):
        for d in [d for d in coll_ if d.name.startswith("Ext_") and d.users == 0]:
            coll_.remove(d)


purge()
LEAF_OB = leaf_object()
LEAF_NG = leaf_scatter_group()

# Near clumps right in front of room 1 + along the lab facade (y > 2.62).
# (x, y, height, seed, leaf-cluster cards): densest right in front of the room-1 window (y 0.2..1.8).
NEAR = [(9.0, -1.0, 13.6, 101, 1300), (11.0, 1.8, 14.0, 102, 1300), (8.6, 4.4, 13.2, 103, 1100),
        (13.0, -4.2, 14.4, 104, 700), (12.2, 7.6, 13.6, 105, 700), (9.4, 11.0, 13.0, 106, 650),
        (13.5, 14.5, 13.8, 108, 500)]
for i, (x, y, h, s, n) in enumerate(NEAR):
    tree_clump(f"Ext_Tree_{i + 1:02d}", x, y, h, s, leaves=n)

build_far_trees()
build_ground()
# s2_integrate: materials/window.py's Window_Reveal (60 cm wall lining + steel drip sill) now owns the outer reveal;
# these jambs were coplanar with it (rendered as black strips at the pane edges) and the sill doubled up. Switchable.
OWN_FACADE = False
if OWN_FACADE:
    build_own_facade()
else:
    for n in ("Ext_Facade", "Ext_Sill_Out"):
        if n in bpy.data.objects:
            bpy.data.objects.remove(bpy.data.objects[n], do_unlink=True)
purge_orphans()
print("EXTERIOR OK")
