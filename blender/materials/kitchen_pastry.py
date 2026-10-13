# Kitchen pastry trays (s3_polish): two black polystyrene catering platters with croissants / buns on the
# worktop, left of the cups. Photos 122216 (x along the worktop), 122209 (depth), 120945 (tray shape, earlier layout).
# Each tray + its pastries = one object (Kitchen_Pastry_A / _B), collection Kitchen, real scale, origin bottom centre.
# Positions back-projected from Cam_122216 / Cam_122209 onto the worktop (z 0.90), kept >= 1 cm from the existing
# Kitchen_* props (PlateStack, TeaBox, Bottle). Standalone + idempotent.
import math
import random

import bmesh
import bpy
from mathutils import Matrix, Vector

TOP = 0.90
# name: (centre x, centre y, yaw, half length, half width, pastry kind, count)
TRAYS = {
    "Kitchen_Pastry_A": (2.78, 0.19, 0.04, 0.23, 0.15, "croissant", 7),
    "Kitchen_Pastry_B": (2.30, 0.165, -0.06, 0.18, 0.135, "bun", 6),
}


def mat(name, build):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    o = nt.nodes.new("ShaderNodeOutputMaterial")
    b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(b.outputs[0], o.inputs[0])
    build(m, nt, b)
    return m


def tray_ps(m, nt, b):
    """Black thermoformed PS: deep black, glossy with a slightly orange-peel surface."""
    b.inputs["Base Color"].default_value = (0.012, 0.012, 0.013, 1)
    b.inputs["Roughness"].default_value = 0.12
    b.inputs["Specular IOR Level"].default_value = 0.5
    n = nt.nodes.new("ShaderNodeTexNoise")
    n.inputs["Scale"].default_value = 180.0
    bp = nt.nodes.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = 0.08
    nt.links.new(nt.nodes.new("ShaderNodeTexCoord").outputs["Object"], n.inputs[0])
    nt.links.new(n.outputs["Fac"], bp.inputs["Height"])
    nt.links.new(bp.outputs[0], b.inputs["Normal"])
    m.diffuse_color = (0.012, 0.012, 0.013, 1)


def baked(m, nt, b):
    """Egg-washed baked dough: golden-brown tops, pale undersides, darker blotches; light SSS, satin gloss."""
    L = nt.links
    co = nt.nodes.new("ShaderNodeTexCoord").outputs["Object"]
    nz = nt.nodes.new("ShaderNodeSeparateXYZ")
    L.new(nt.nodes.new("ShaderNodeNewGeometry").outputs["Normal"], nz.inputs[0])
    blot = nt.nodes.new("ShaderNodeTexNoise")
    blot.inputs["Scale"].default_value = 40.0
    blot.inputs["Detail"].default_value = 6.0
    L.new(co, blot.inputs[0])
    # browning = up-facing + blotch noise
    add = nt.nodes.new("ShaderNodeMath")
    add.operation = 'MULTIPLY_ADD'
    L.new(nz.outputs[2], add.inputs[0])
    add.inputs[1].default_value = 0.45
    L.new(blot.outputs["Fac"], add.inputs[2])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    L.new(add.outputs[0], ramp.inputs[0])
    e = ramp.color_ramp.elements
    e[0].position, e[0].color = 0.15, (0.55, 0.36, 0.14, 1)    # pale crumb-side dough
    e[1].position, e[1].color = 0.95, (0.30, 0.13, 0.035, 1)  # deep bake
    mid = e.new(0.6)
    mid.color = (0.42, 0.20, 0.05, 1)                          # golden
    L.new(ramp.outputs[0], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.42
    b.inputs["Subsurface Weight"].default_value = 0.08
    b.inputs["Subsurface Radius"].default_value = (0.01, 0.006, 0.003)
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.35
    fine = nt.nodes.new("ShaderNodeTexNoise")
    fine.inputs["Scale"].default_value = 260.0
    L.new(co, fine.inputs[0])
    L.new(fine.outputs["Fac"], bump.inputs["Height"])
    L.new(bump.outputs[0], b.inputs["Normal"])
    m.diffuse_color = (0.40, 0.19, 0.05, 1)


def octagon(hx, hy, c):
    return [(hx - c, -hy), (hx, -hy + c), (hx, hy - c), (hx - c, hy), (-hx + c, hy), (-hx, hy - c), (-hx, -hy + c),
            (-hx + c, -hy)]


def build_tray(bm, hx, hy):
    """Thermoformed platter: flat floor on two low steps, flared 2 cm wall, flat 8 mm lip. 1 mm sheet."""
    c = min(hx, hy) * 0.35
    prof = [(-0.040, 0.000), (-0.032, 0.003), (-0.020, 0.004), (-0.010, 0.020), (0.0, 0.022)]   # (inset, z)
    rings = [[bm.verts.new((x * (1 + d / hx), y * (1 + d / hy), z)) for x, y in octagon(hx, hy, c)] for d, z in prof]
    floor = bm.faces.new(rings[0][::-1])
    faces = [floor]
    for r0, r1 in zip(rings, rings[1:]):
        for k in range(8):
            faces.append(bm.faces.new((r0[k], r0[(k + 1) % 8], r1[(k + 1) % 8], r1[k])))
    bmesh.ops.triangulate(bm, faces=[floor])
    bmesh.ops.solidify(bm, geom=list(bm.faces), thickness=0.001)
    return 0.004  # floor top z


def croissant(bm, T, L, R):
    """Crescent: tube along an arc, swelling to R in the middle, ridged, flattened underside."""
    segs, sides, rows = 10, 8, []
    for i in range(segs + 1):
        t = i / segs
        a = (t - 0.5) * 2.0
        cx, cy = math.sin(a) * L * 0.5, (1 - math.cos(a)) * L * 0.35
        r = R * (0.25 + 0.75 * math.sin(math.pi * t) ** 0.8) * (1 + 0.08 * math.cos(t * 6 * math.pi))
        tx, ty = math.cos(a), math.sin(a)              # tangent direction (normalised)
        ring = []
        for k in range(sides):
            ph = 2 * math.pi * k / sides
            u, w = math.cos(ph) * r, math.sin(ph) * r
            w = w * 0.75 if w > 0 else w * 0.25         # flat-ish underside
            ring.append(bm.verts.new(T @ Vector((cx - ty * u, cy + tx * u, w + r * 0.25))))
        rows.append(ring)
    for r0, r1 in zip(rows, rows[1:]):
        for k in range(sides):
            bm.faces.new((r0[k], r0[(k + 1) % sides], r1[(k + 1) % sides], r1[k])).smooth = True
    bm.faces.new(rows[0][::-1]).smooth = True
    bm.faces.new(rows[-1]).smooth = True


def bun(bm, T, rx, ry, h):
    """Oval glazed bun / turnover: half-flattened UV sphere."""
    res = bmesh.ops.create_uvsphere(bm, u_segments=10, v_segments=6, radius=1.0)
    for v in res["verts"]:
        x, y, z = v.co
        z = z * h if z > 0 else z * h * 0.2
        v.co = T @ Vector((x * rx, y * ry, z + h * 0.2))
    for f in {f for v in res["verts"] for f in v.link_faces}:
        f.smooth = True


def make(name, cx, cy, yaw, hx, hy, kind, count):
    rnd = random.Random(name)
    bm = bmesh.new()
    floor_z = build_tray(bm, hx, hy)
    for f in bm.faces:
        f.material_index = 0
    n_tray = len(bm.faces)
    # pastries in two staggered rows along x
    per = (count + 1) // 2
    for i in range(count):
        row, col = i % 2, i // 2
        px = -hx * 0.70 + (col + 0.5 * row) * (1.4 * hx / max(per - 0.5, 1))
        py = (row - 0.5) * hy * 0.85 + rnd.uniform(-0.01, 0.01)
        T = Matrix.Translation((px, py, floor_z)) @ Matrix.Rotation(rnd.uniform(-0.5, 0.5) + row * math.pi, 4, 'Z')
        if kind == "croissant":
            croissant(bm, T, rnd.uniform(0.14, 0.16), rnd.uniform(0.03, 0.035))
        else:
            bun(bm, T, rnd.uniform(0.055, 0.065), rnd.uniform(0.04, 0.047), rnd.uniform(0.03, 0.036))
    for f in list(bm.faces)[n_tray:]:
        f.material_index = 1
    # UVs: planar top projection in metres (procedural materials; Unity bake only needs non-degenerate UVs)
    uv = bm.loops.layers.uv.new("UVMap")
    for f in bm.faces:
        for lp in f.loops:
            co = lp.vert.co
            lp[uv].uv = (co.x * 2 + 0.5 + co.z, co.y * 2 + 0.5 + co.z)
    bmesh.ops.triangulate(bm, faces=list(bm.faces))   # report true tri count
    me = bpy.data.meshes.get(name) or bpy.data.meshes.new(name)
    me.materials.clear()        # before to_mesh: clear() zeroes the face material indices
    me.materials.append(TRAY)
    me.materials.append(DOUGH)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.get(name) or bpy.data.objects.new(name, me)
    ob.data = me
    ob.location = (cx, cy, TOP)
    ob.rotation_euler = (0, 0, yaw)
    col = bpy.data.collections.get("Kitchen") or bpy.context.scene.collection
    for c in list(ob.users_collection):
        c.objects.unlink(ob)
    col.objects.link(ob)
    return len(me.polygons)


TRAY = mat("Kitchen_PastryTray_PS", tray_ps)
DOUGH = mat("Kitchen_Pastry_Baked", baked)
tris = {n: make(n, *p) for n, p in TRAYS.items()}
print("KITCHEN PASTRY", tris, "total tris", sum(tris.values()))
