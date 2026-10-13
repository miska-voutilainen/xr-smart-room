# Cabinet: black kitchenette sideboard on the y=0 wall, fronts face +y.
# Rebuilds the "Cabinet" mesh (2.44 m, wider than build_room.py's box, see X0/X1) as carcass + end panels,
# individual fronts with 3 mm gaps, aluminium J-profile handles, worktop, recessed
# stainless plinth and the fridge vent grille. Bays from low x (door end) to high x:
# fridge, 3 drawers, tall door, 3 drawers (checked against photos 122216 / 122250).
import bpy
import bmesh

X0, X1, CD = 0.62, 3.06, 0.60          # 4 x 600 mm modules + 2 x 19 mm end panels; x0 from a PnP solve of 122216
                                       # (EXIF 25 mm eq., 4.5 px rms). Deviates from build_room.py's guessed 0.50..2.70.
TOP, WT = 0.90, 0.04                   # worktop top / thickness (photo reads ~40 mm)
END = 0.019                            # end panels, full height to the floor
YF, FT, G = CD, 0.019, 0.003           # front face y, front thickness, gap between fronts
PL_H, PL_SET = 0.125, 0.04             # plinth height, plinth setback from the fronts
FRIDGE_W, FRIDGE_Z0 = 0.60, 0.095      # fridge bay width, fridge door bottom (~3 cm below the drawers, 122216)
FRIDGE_DROP = 0.015                    # fridge door top sits ~15 mm below the other fronts (122216)
XA, XB = X0 + END, X1 - END            # inner span between the end panels
ZW = TOP - WT                          # worktop underside

FRONT, WORKTOP, ALU, STEEL, VENT, EDGE = range(6)
NO_GRIP = 10.0                         # UV v reference for faces that are not fronts (v = z - ref, see UVs)

# ---------- geometry ----------
verts, faces, mats, vref = [], [], [], []


def box(lo, hi, m, edge=(), ref=NO_GRIP):
    """edge: face indices (0 -z, 1 +z, 2 -y, 3 +x, 4 +y, 5 -x) that get the edge-banding material."""
    (x0, y0, z0), (x1, y1, z1) = lo, hi
    b = len(verts)
    verts.extend([(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
                  (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)])
    for k, q in enumerate(((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7))):
        faces.append(tuple(b + i for i in q))
        mats.append(EDGE if k in edge else m)
        vref.append(ref)


def handle(x0, x1, ztop):
    """J-pull profile sitting on the front's top edge, extruded along x (quads only)."""
    y0, y1, t, tf, h = YF - FT, YF + 0.018, 0.002, 0.0025, 0.016
    ring = [(y0, ztop), (y1 - tf, ztop), (y1, ztop), (y1, ztop - t),
            (y1, ztop - h), (y1 - tf, ztop - h), (y1 - tf, ztop - t), (y0, ztop - t)]
    b = len(verts)
    for x in (x0, x1):
        verts.extend((x, y, z) for y, z in ring)
    n = len(ring)
    for i in range(n):
        j = (i + 1) % n
        faces.append((b + i, b + j, b + n + j, b + n + i))
        mats.append(ALU)
        vref.append(NO_GRIP)
    for q in ((0, 1, 6, 7), (1, 2, 3, 6), (6, 3, 4, 5)):
        faces.append(tuple(b + i for i in reversed(q)))
        faces.append(tuple(b + n + i for i in q))
        mats.extend((ALU, ALU))
        vref.extend((NO_GRIP, NO_GRIP))


def front(x0, x1, z0, z1):
    """Front cell -> laminate panel + handle, shrunk by half a gap on each side."""
    x0, x1, z0, z1 = x0 + G / 2, x1 - G / 2, z0 + G / 2, z1 - G / 2
    box((x0, YF - FT, z0), (x1, YF, z1 - 0.002), FRONT, edge=(0, 1, 3, 5), ref=z1)   # ABS banding on the 4 edges
    handle(x0 + 0.001, x1 - 0.001, z1)


box((X0 - 0.02, 0, ZW), (X1 + 0.02, CD + 0.02, TOP), WORKTOP)
box((X0, 0, 0), (XA, YF, ZW), FRONT, edge=(4,))                        # end panels, banded front edge
box((XB, 0, 0), (X1, YF, ZW), FRONT, edge=(4,))
box((XA, 0, PL_H), (XB, YF - FT - 0.001, ZW), FRONT)                   # carcass body behind the fronts
box((XA, 0.02, 0), (XB, YF - PL_SET, PL_H), STEEL)                     # recessed kick plate

zt = ZW + G / 2 - 0.0015                                               # cell top: 3 mm under the worktop
bay = (XB - XA - FRIDGE_W) / 3
edges = [XA, XA + FRIDGE_W, XA + FRIDGE_W + bay, XA + FRIDGE_W + 2 * bay, XB]
end_gap = [G / 2, 0, 0, 0, -G / 2]                                     # full gap against the end panels
edges = [e + d for e, d in zip(edges, end_gap)]

front(edges[0], edges[1], FRIDGE_Z0, zt - FRIDGE_DROP)                 # under-counter fridge door
front(edges[2], edges[3], PL_H, zt)                                    # tall door
for a, b in ((edges[1], edges[2]), (edges[3], edges[4])):              # drawer stacks, photo ratios
    z = zt
    for frac in (0.19, 0.337, 0.473):
        zb = z - frac * (zt - PL_H)
        front(a, b, zb, z)
        z = zb

# fridge vent grille in the plinth: stainless frame plate + slotted field (slots in the shader)
gx = (edges[0] + edges[1]) / 2
yp = YF - PL_SET
box((gx - 0.2275, yp, 0.020), (gx + 0.2275, yp + 0.0025, 0.093), STEEL)
SLOT_PX, SLOT_PZ, SLOT_NX, SLOT_NZ = 0.0305, 0.0084, 14, 7
fx0, fz1 = gx - SLOT_PX * SLOT_NX / 2, 0.0565 + SLOT_PZ * SLOT_NZ / 2
box((fx0, yp, fz1 - SLOT_PZ * SLOT_NZ), (fx0 + SLOT_PX * SLOT_NX, yp + 0.003, fz1), VENT)

# ---------- materials ----------


def node(nt, kind, loc, **inputs):
    nd = nt.nodes.new(kind)
    nd.location = loc
    for k, v in inputs.items():
        nd.inputs[k].default_value = v
    return nd


def new_material(name):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    if m.node_tree is None:
        m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = node(nt, "ShaderNodeOutputMaterial", (600, 0))
    bsdf = node(nt, "ShaderNodeBsdfPrincipled", (300, 0))
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    co = node(nt, "ShaderNodeTexCoord", (-900, 0))
    return m, nt, bsdf, co


def sock(socks, ident):
    """Mix node sockets share names across types; pick by identifier."""
    return next(s for s in socks if s.identifier == ident)


def ramp_value(nt, src, lo, hi, loc):
    """Map a 0..1 noise to lo..hi."""
    mr = node(nt, "ShaderNodeMapRange", loc, **{"To Min": lo, "To Max": hi})
    nt.links.new(src, mr.inputs["Value"])
    return mr.outputs["Result"]


def bump(nt, height, strength, distance, loc):
    bp = node(nt, "ShaderNodeBump", loc, Strength=strength, Distance=distance)
    nt.links.new(height, bp.inputs["Height"])
    return bp.outputs["Normal"]


def laminate(name, rgb, rough, rough_var, grain, grain_amt, peel):
    m, nt, bsdf, co = new_material(name)
    m.diffuse_color = (*rgb, 1)
    # fine speckle in the decor paper + slow cloudy roughness variation + orange-peel bump
    speck = node(nt, "ShaderNodeTexNoise", (-600, 300), Scale=grain, Detail=2.0)
    cloud = node(nt, "ShaderNodeTexNoise", (-600, 0), Scale=3.0, Detail=3.0)
    peel_n = node(nt, "ShaderNodeTexNoise", (-600, -300), Scale=peel, Detail=1.0)
    for t in (speck, cloud, peel_n):
        nt.links.new(co.outputs["Object"], t.inputs["Vector"])
    mix = node(nt, "ShaderNodeMix", (0, 300))
    mix.data_type = "RGBA"
    sock(mix.inputs, "A_Color").default_value = tuple(c * (1 - grain_amt) for c in rgb) + (1,)
    sock(mix.inputs, "B_Color").default_value = tuple(c * (1 + grain_amt) for c in rgb) + (1,)
    nt.links.new(speck.outputs["Fac"], mix.inputs["Factor"])
    nt.links.new(sock(mix.outputs, "Result_Color"), bsdf.inputs["Base Color"])
    nt.links.new(ramp_value(nt, cloud.outputs["Fac"], rough - rough_var, rough + rough_var, (0, 0)),
                 bsdf.inputs["Roughness"])
    nt.links.new(bump(nt, peel_n.outputs["Fac"], 0.025, 0.001, (0, -300)), bsdf.inputs["Normal"])
    bsdf.inputs["Specular IOR Level"].default_value = 0.5
    return m


def brushed(name, rgb, rough, stretch, vent=False):
    """Metal brushed along x: noise squashed in y/z, drives roughness + bump."""
    m, nt, bsdf, co = new_material(name)
    m.diffuse_color = (*rgb, 1)
    mp = node(nt, "ShaderNodeMapping", (-700, 0), Scale=(2.0, stretch, stretch))
    nt.links.new(co.outputs["Object"], mp.inputs["Vector"])
    nz = node(nt, "ShaderNodeTexNoise", (-500, 0), Scale=1.0, Detail=4.0, Roughness=0.6)
    nt.links.new(mp.outputs["Vector"], nz.inputs["Vector"])
    bsdf.inputs["Metallic"].default_value = 1.0
    bsdf.inputs["Base Color"].default_value = (*rgb, 1)
    nt.links.new(ramp_value(nt, nz.outputs["Fac"], rough - 0.06, rough + 0.06, (-200, 100)),
                 bsdf.inputs["Roughness"])
    nrm = bump(nt, nz.outputs["Fac"], 0.08, 0.0005, (-200, -200))
    if vent:
        # slot grid: Brick texture without stagger; bricks = slots, mortar = steel web.
        # Cell edges land on the slot-field edges, so the border is a half web.
        K = 1.3
        sx = node(nt, "ShaderNodeSeparateXYZ", (-700, -400))
        nt.links.new(co.outputs["Object"], sx.inputs["Vector"])
        u = node(nt, "ShaderNodeMath", (-500, -350))
        u.operation = "SUBTRACT"
        nt.links.new(sx.outputs["X"], u.inputs[0])
        u.inputs[1].default_value = fx0
        v = node(nt, "ShaderNodeMath", (-500, -500))           # (fz1 - z) * K: stretch rows so the
        v.operation = "MULTIPLY_ADD"                            # uniform mortar gives thinner
        v.inputs[1].default_value = -K                          # horizontal webs than vertical ones
        v.inputs[2].default_value = fz1 * K
        nt.links.new(sx.outputs["Z"], v.inputs[0])
        cx = node(nt, "ShaderNodeCombineXYZ", (-300, -400))
        nt.links.new(u.outputs[0], cx.inputs["X"])
        nt.links.new(v.outputs[0], cx.inputs["Y"])
        br = node(nt, "ShaderNodeTexBrick", (-100, -400), Scale=1.0, **{
            "Mortar Size": 0.00275, "Mortar Smooth": 0.35, "Bias": 0.0,
            "Brick Width": SLOT_PX, "Row Height": SLOT_PZ * K})
        br.offset, br.squash = 0.0, 1.0
        nt.links.new(cx.outputs["Vector"], br.inputs["Vector"])
        web = br.outputs["Fac"]                                        # 1 on steel, 0 in a slot
        col = node(nt, "ShaderNodeMix", (100, 200))
        col.data_type = "RGBA"
        sock(col.inputs, "A_Color").default_value = (0.004, 0.004, 0.004, 1)       # dark cavity behind the slots
        sock(col.inputs, "B_Color").default_value = (*rgb, 1)
        nt.links.new(web, col.inputs["Factor"])
        nt.links.new(sock(col.outputs, "Result_Color"), bsdf.inputs["Base Color"])
        nt.links.new(web, bsdf.inputs["Metallic"])
        bp = node(nt, "ShaderNodeBump", (100, -300), Strength=0.6, Distance=0.002)
        nt.links.new(web, bp.inputs["Height"])
        nt.links.new(nrm, bp.inputs["Normal"])
        nrm = bp.outputs["Normal"]
    nt.links.new(nrm, bsdf.inputs["Normal"])
    return m


materials = [                                                          # slot order = FRONT .. EDGE
    laminate("Cabinet_Front", (0.016, 0.015, 0.014), 0.50, 0.05, 900.0, 0.04, 350.0),
    laminate("Cabinet_Worktop", (0.085, 0.072, 0.064), 0.45, 0.06, 1500.0, 0.10, 500.0),
    brushed("Cabinet_Aluminium", (0.80, 0.80, 0.80), 0.32, 900.0),
    brushed("Cabinet_Steel", (0.62, 0.61, 0.59), 0.30, 700.0),
    brushed("Cabinet_Vent", (0.62, 0.61, 0.59), 0.32, 700.0, vent=True),
    laminate("Cabinet_Edge", (0.018, 0.017, 0.016), 0.38, 0.04, 900.0, 0.04, 350.0),     # ABS edge banding
]
# final looks (image textures, anisotropic metals) are built in shaders/zz_dresser.py

# ---------- object ----------
ob = bpy.data.objects["Cabinet"]
old = ob.data
me = bpy.data.meshes.new("Cabinet")
me.from_pydata(verts, [], faces)
for poly, mi in zip(me.polygons, mats):
    poly.material_index = mi
bm = bmesh.new()
bm.from_mesh(me)
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
bm.to_mesh(me)
bm.free()
me.validate()
# UVs: world-metre box projection, U = x on every face whose normal is y or z (brush direction of the metals
# and the decor-paper direction). V = z - ref on vertical faces: ref = the front's top edge for fronts (so the
# shader reads "distance below the handle" for fingerprints) and NO_GRIP (10 m) elsewhere.
uv = me.uv_layers.new(name="UVMap").data
for poly, ref in zip(me.polygons, vref):
    nx, ny, nz = (abs(c) for c in poly.normal)
    for li in poly.loop_indices:
        x, y, z = me.vertices[me.loops[li].vertex_index].co
        uv[li].uv = (x, y) if nz >= max(nx, ny) else (x, z - ref) if ny >= nx else (y, z - ref)
for m in materials:
    me.materials.append(m)
ob.data = me
if old.users == 0:
    bpy.data.meshes.remove(old)
me.name = "Cabinet"

bev = ob.modifiers.get("Cabinet_Bevel") or ob.modifiers.new("Cabinet_Bevel", "BEVEL")
bev.width = 0.0008
bev.segments = 1
bev.limit_method = "ANGLE"
bev.harden_normals = True                       # custom normals: smooth shading reads as flat faces + soft edges
me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
ob["vent_fx0"], ob["vent_fz1"] = fx0, fz1                 # slot grid for shaders/zz_dresser.py
ob["vent_px"], ob["vent_pz"] = SLOT_PX, SLOT_PZ
print("CABINET rebuilt", len(me.polygons), "faces")
