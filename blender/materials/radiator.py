# Radiator: MS-140-500 cast-iron sectional radiator (9 sections) + its supply/return branches.
# Standalone and idempotent; runs after build_room.py (via apply_materials.py).
#
# Hydronic scheme (Soviet-era one-pipe vertical riser, as in photos 122244 / 120939 / 150354):
#   * Photos 150354 / 150359: both branches run straight into the pilaster's +y side face, no vertical pipe
#     is visible and nothing runs above the supply, so the riser is concealed in the pilaster (boxed in during
#     the renovation), together with its bypass / closing section (zamykayushchiy uchastok) between the tees.
#     ASSUMED top distribution (riser flows down), not verifiable from the photos; the radiator node is the
#     same for a bottom-fed riser (one-sided, top-in / bottom-out; the offset bypass handles the flow split).
#   * One-sided connection, both branches on the near (pilaster) end, y = Y0:
#       SUPPLY = upper branch -> top hub; RETURN = lower branch <- bottom hub.
#     Water enters the top hub channel, spreads along the sections, falls through both channels of every
#     section (hot water rises, so top-in / bottom-out is the stable flow direction), collects in the bottom
#     hub and goes back to the riser. 9 sections is far below the 25-section limit for one-sided connection.
#   * Branches are DN20 (3/4", OD 26.8 mm) steel, 0.45 m visible (one-pipe short branch L <= 0.5 m); the last
#     third is the thicker DN25 tee stub coming out of the pilaster, as in the photos. Short
#     branches on one-pipe vertical risers are laid WITHOUT slope (NCFU heating manual), so the supply is level.
#     The return has an offset bend ("utka") dropping ~35 mm toward the riser tee, as in the photos.
#   * Joints: near end = two through-plugs (1 1/4" -> 3/4" reducers), each followed by a "sgon" (long-thread
#     nipple + locknut + coupling); the supply has one more coupling mid-run. Far end = two blind plugs,
#     the TOP one carries the Mayevsky air vent (highest point on the end opposite the connections).
#     No valves: original flow-through one-pipe node, none visible in the photos.
#   * Mounting per the MS-140 installation drawing: >= 60 mm floor clearance (tips at 90 mm), >= 50 mm under
#     the sill, >= 25 mm off the wall (30 mm). Four wall hooks between the end sections (top + bottom).
# MS-140-500 section: height 588, hub centre distance 500, depth 140, build length 93 mm, 1 1/4" nipples.
# Sources: https://www.tproekt.com/tehniceskie-harakteristiki-cugunnogo-radiatora-ms-140-500/ (spec table),
#   https://www.tproekt.com/wp-content/uploads/2/1/0/2102d6b4428e83c7ad6e79676c2e4a95.jpg (section + mounting drawing),
#   https://www.tproekt.com/wp-content/uploads/5/b/5/5b58f3a8373d9041bc60ed17daf620ae.jpg (dimension scheme),
#   https://www.tproekt.com/wp-content/uploads/3/5/3/3537cebcd3cdc7474332d09aace39308.jpg (hub close-up),
#   https://sveden.ncfu.ru/sveden/files/ric/37_Metod_Otoplen_2026.pdf (one-pipe nodes, branch length / slope).
#
# Pipes end INSIDE the pilaster: centre line x = X_HUB (6.40), supply z = Z_HUB_HI, return z = Z_RET,
# they cross the pilaster's +y face at y = 0.20 and run on to y = PIPE_END_Y, buried in the y = 0 wall
# (the pilaster must project >= 0.125, front face x <= 6.375, for them to enter its side face as photographed).
# Low poly: direct lofted quad shells with smooth shading (no subdivision), hex nuts flat shaded.
import math
import bpy
import bmesh
from mathutils import Vector

W = 6.50                       # window wall (interior face)
N, PITCH = 7, 0.093            # sections, build length per section (MS-140-500)
Y0 = 0.60                      # near (pipe) end; 0.45 m branches to the pilaster face at y = 0.20
Y1 = Y0 + N * PITCH
X_BACK = W - 0.030             # 30 mm off the wall
X_FRONT = X_BACK - 0.140       # 140 mm deep
X_HUB = (X_FRONT + X_BACK) / 2
Z_BOT = 0.09                   # leg tips
Z_HUB_LO, Z_HUB_HI = Z_BOT + 0.050, Z_BOT + 0.550   # 500 mm hub centre distance
Z_TOP = Z_BOT + 0.588
PIPE_R = 0.0134                # DN20 steel, OD 26.8 mm
Z_RET = Z_HUB_LO - 0.035       # return drops through the offset bend before the riser
Y_PIL, PIPE_END_Y = 0.20, -0.02


def ring_shape(k):
    return [(math.cos(2 * math.pi * (i + 0.5) / k), math.sin(2 * math.pi * (i + 0.5) / k)) for i in range(k)]


def cap(bm, ring, smooth):
    """Fill a convex ring with quads (fan of quads), one triangle if the count is odd."""
    k = len(ring)
    for i in range(1, k - 2, 2):
        f = bm.faces.new((ring[0], ring[i], ring[i + 1], ring[i + 2]))
        f.smooth = smooth
    if k % 2 == 1:
        f = bm.faces.new((ring[0], ring[-2], ring[-1]))
        f.smooth = smooth


def loft(bm, pts, sizes, shape, smooth=True, caps=(True, True)):
    """Closed tube through pts; sizes[i] = (half size along u, along v). u = t x Z (or t x X for vertical t)."""
    rings = []
    n = len(pts)
    for i, p in enumerate(pts):
        t = (pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]).normalized()
        ref = Vector((0, 0, 1)) if abs(t.z) < 0.9 else Vector((1, 0, 0))
        u = t.cross(ref).normalized()
        v = u.cross(t)
        su, sv = sizes[i]
        rings.append([bm.verts.new(p + u * (a * su) + v * (b * sv)) for a, b in shape])
    k = len(shape)
    for r0, r1 in zip(rings, rings[1:]):
        for j in range(k):
            f = bm.faces.new((r0[j], r0[(j + 1) % k], r1[(j + 1) % k], r1[j]))
            f.smooth = smooth
    if caps[0]:
        cap(bm, rings[0][::-1], smooth)
    if caps[1]:
        cap(bm, rings[-1], smooth)


C8, C10, C12, HEX = ring_shape(8), ring_shape(10), ring_shape(12), ring_shape(6)
# Front column cross-section (u = +y width, v = +x depth): cast ridge pointing into the room (-v).
FRONT = [(1, 0), (0.92, 0.55), (0.6, 0.9), (0, 1), (-0.6, 0.9), (-0.92, 0.55), (-1, 0),
         (-0.97, -0.7), (-0.55, -1.05), (0, -1.35), (0.55, -1.05), (0.97, -0.7)]
# (z, half width y, half depth x): pencil-point leg at the bottom, rounded crest above the top hub
COLUMN = [(Z_BOT, 0.004, 0.006), (Z_BOT + 0.012, 0.012, 0.012), (Z_BOT + 0.030, 0.022, 0.018),
          (Z_HUB_LO, 0.035, 0.022), (Z_HUB_LO + 0.035, 0.032, 0.022), (Z_HUB_LO + 0.070, 0.027, 0.022),
          (Z_HUB_HI - 0.060, 0.027, 0.022), (Z_HUB_HI - 0.025, 0.034, 0.022), (Z_HUB_HI + 0.010, 0.033, 0.022),
          (Z_TOP - 0.012, 0.029, 0.019), (Z_TOP, 0.006, 0.009)]
X_COL_F = X_FRONT + 0.022 * 1.35     # ridge tip lands on X_FRONT
X_COL_B = X_BACK - 0.020
R_BOSS = 0.034                       # hub boss around the 1 1/4" nipple
BOSS_X = 1.5                         # header barrel is oval: reaches almost to the column fronts (continuous band in photos)


def radiator_cage(bm):
    for s in range(N):
        yc = Y0 + (s + 0.5) * PITCH
        loft(bm, [Vector((X_COL_F, yc, z)) for z, _, _ in COLUMN], [(w, d) for _, w, d in COLUMN], FRONT)
        loft(bm, [Vector((X_COL_B, yc, z)) for z, _, _ in COLUMN], [(w, d * 0.9) for _, w, d in COLUMN], C8)
        for zc in (Z_HUB_LO, Z_HUB_HI):
            # boss along y; joint faces of neighbouring sections touch -> a fine seam groove at each nipple
            ys = (-PITCH / 2, -PITCH / 2 + 0.005, PITCH / 2 - 0.005, PITCH / 2)
            rs = (R_BOSS - 0.003, R_BOSS, R_BOSS, R_BOSS - 0.003)
            loft(bm, [Vector((X_HUB, yc + d, zc)) for d in ys], [(r * BOSS_X, r) for r in rs], C12)
            # bridge along x joining the front and rear channel through the hub
            xs = (X_COL_F, X_HUB, X_COL_B)
            loft(bm, [Vector((x, yc, zc)) for x in xs], [(0.024, 0.030)] * 3, C8)
        # web between the channels (hidden from the front, closes the top view)
        loft(bm, [Vector((X_HUB, yc, z)) for z in (Z_HUB_LO, Z_HUB_HI)],
             [(0.005, (X_COL_B - X_COL_F) / 2)] * 2, [(1, 1), (-1, 1), (-1, -1), (1, -1)], smooth=False)
    # far end: two 1 1/4" blind plugs (gasket flange + hex), the top one with the Mayevsky air vent
    for zc in (Z_HUB_LO, Z_HUB_HI):
        loft(bm, [Vector((X_HUB, Y1 + d, zc)) for d in (-0.002, 0.004)], [(0.029, 0.029)] * 2, C12)
        loft(bm, [Vector((X_HUB, Y1 + d, zc)) for d in (0.003, 0.014)], [(0.019, 0.019)] * 2, HEX, smooth=False)
    loft(bm, [Vector((X_HUB, Y1 + d, Z_HUB_HI)) for d in (0.013, 0.024, 0.027)],
         [(0.0075, 0.0075), (0.0075, 0.0075), (0.004, 0.004)], C8)          # brass body + cone screw
    loft(bm, [Vector((X_HUB, Y1 + 0.019, Z_HUB_HI + d)) for d in (0.004, 0.012)],
         [(0.002, 0.002)] * 2, HEX, smooth=False)                                 # vent spout, pointing up
    # wall hooks in the necks between the end sections, under the top and bottom hubs
    for yb in (Y0 + PITCH, Y1 - PITCH):
        for zc in (Z_HUB_LO, Z_HUB_HI):
            zh = zc - R_BOSS - 0.004
            path = [Vector((W + 0.04, yb, zh)), Vector((X_HUB + 0.01, yb, zh)),
                    Vector((X_HUB - 0.012, yb, zh + 0.006)), Vector((X_HUB - 0.018, yb, zh + 0.018))]
            loft(bm, path, [(0.005, 0.005)] * len(path), C8)


def fittings(bm, zc, coupling_at):
    """Near-end through-plug (1 1/4" -> 3/4" reducer) + sgon: locknut and coupling(s)."""
    loft(bm, [Vector((X_HUB, Y0 + d, zc)) for d in (0.002, -0.004)], [(0.029, 0.029)] * 2, C12)
    loft(bm, [Vector((X_HUB, Y0 - d, zc)) for d in (0.003, 0.014)], [(0.021, 0.021)] * 2, HEX, smooth=False)
    loft(bm, [Vector((X_HUB, Y0 - d, zc)) for d in (0.013, 0.020)], [(0.016, 0.016)] * 2, C10)
    for i, dy in enumerate(coupling_at):
        y = Y0 - dy
        if i == 0:   # sgon locknut first, then the coupling
            loft(bm, [Vector((X_HUB, y + d, zc)) for d in (0.006, 0.0)], [(0.0195, 0.0195)] * 2, HEX, smooth=False)
            y -= 0.001
        loft(bm, [Vector((X_HUB, y - d, zc)) for d in (0.0, 0.003, 0.033, 0.036)],
             [(0.0165, 0.0165), (0.018, 0.018), (0.018, 0.018), (0.0165, 0.0165)], C10)


def pipe_cage(bm):
    r, r_stub = PIPE_R, 0.0158          # DN20 branch; DN25 tee stub out of the pilaster (thicker end piece in photos)
    run = Y0 - Y_PIL
    y_stub = Y0 - 0.65 * run

    def stub(z):
        loft(bm, [Vector((X_HUB, y, z)) for y in (y_stub + 0.004, y_stub, PIPE_END_Y)],
             [(r * 1.02, r * 1.02), (r_stub, r_stub), (r_stub, r_stub)], C10)

    # supply: level, straight into the pilaster
    fittings(bm, Z_HUB_HI, (0.05, 0.17))
    loft(bm, [Vector((X_HUB, y, Z_HUB_HI)) for y in (Y0 - 0.015, y_stub + 0.002)], [(r, r)] * 2, C10)
    stub(Z_HUB_HI)
    # return: sgon, then an offset bend ("utka") dropping toward the riser tee, then into the pilaster
    fittings(bm, Z_HUB_LO, (0.05,))
    y_a, y_b = Y0 - 0.35 * run, Y0 - 0.53 * run
    path = [Vector((X_HUB, Y0 - 0.015, Z_HUB_LO)), Vector((X_HUB, y_a + 0.015, Z_HUB_LO))]
    for i in range(1, 6):
        t = i / 6
        path.append(Vector((X_HUB, y_a - (y_a - y_b) * t, Z_HUB_LO - (Z_HUB_LO - Z_RET) * (1 - math.cos(math.pi * t)) / 2)))
    path += [Vector((X_HUB, y_b - 0.015, Z_RET)), Vector((X_HUB, y_stub + 0.002, Z_RET))]
    loft(bm, path, [(r, r)] * len(path), C10)
    stub(Z_RET)


def build_mesh(name, build):
    bm = bmesh.new()
    build(bm)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    return me


def set_mesh(ob, me, name):
    old = ob.data
    ob.data = me
    if old.users == 0:
        bpy.data.meshes.remove(old)
    me.name = name


# ---------- materials ----------

def mat_reset(name):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    m.node_tree.nodes.clear()
    return m, m.node_tree.nodes, m.node_tree.links


def mix(nodes, links, fac, a, b):
    n = nodes.new("ShaderNodeMix")
    n.data_type = "RGBA"
    for sock, val in ((n.inputs[0], fac), (n.inputs[6], a), (n.inputs[7], b)):
        if isinstance(val, bpy.types.NodeSocket):
            links.new(val, sock)
        else:
            sock.default_value = val
    return n.outputs[2]


def noise(nodes, links, vec, scale, detail=4.0, rough=0.5):
    n = nodes.new("ShaderNodeTexNoise")
    n.inputs["Scale"].default_value = scale
    n.inputs["Detail"].default_value = detail
    n.inputs["Roughness"].default_value = rough
    links.new(vec, n.inputs["Vector"])
    return n.outputs["Fac"]


def ramp(nodes, links, fac, a, b, ca=(0, 0, 0, 1), cb=(1, 1, 1, 1)):
    n = nodes.new("ShaderNodeValToRGB")
    e = n.color_ramp.elements
    e[0].position, e[0].color = a, ca
    e[1].position, e[1].color = b, cb
    links.new(fac, n.inputs["Fac"])
    return n.outputs["Color"]


def bump(nodes, links, height, strength, dist, normal=None, invert=False):
    n = nodes.new("ShaderNodeBump")
    n.invert = invert
    n.inputs["Strength"].default_value = strength
    n.inputs["Distance"].default_value = dist
    links.new(height, n.inputs["Height"])
    if normal is not None:
        links.new(normal, n.inputs["Normal"])
    return n.outputs["Normal"]


def paint_material(name, base, heavy):
    """Glossy enamel. heavy=True: many coats on cast iron (drips, cast pits, chips, grime in crevices)."""
    m, nodes, links = mat_reset(name)
    out = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    co = nodes.new("ShaderNodeTexCoord").outputs["Object"]

    # gentle yellowing / uneven coat thickness
    tint = noise(nodes, links, co, 6.0, 3.0)
    col = mix(nodes, links, ramp(nodes, links, tint, 0.35, 0.75), base,
              tuple(c * k for c, k in zip(base, (0.97, 0.95, 0.88))) + (1,))
    peel = noise(nodes, links, co, 900.0 if heavy else 1400.0, 2.0)
    rough = ramp(nodes, links, noise(nodes, links, co, 25.0, 3.0), 0.3, 0.7,
                 (0.24, 0.24, 0.24, 1), (0.34, 0.34, 0.34, 1))

    if heavy:
        # vertical drips/sags: noise squashed along z
        sq = nodes.new("ShaderNodeVectorMath")
        sq.operation = "MULTIPLY"
        sq.inputs[1].default_value = (1.0, 1.0, 0.3)
        links.new(co, sq.inputs[0])
        drips = ramp(nodes, links, noise(nodes, links, sq.outputs[0], 45.0, 2.0), 0.62, 0.72)
        cast = noise(nodes, links, co, 100.0, 6.0, 0.65)
        h = nodes.new("ShaderNodeMath")
        h.operation = "MULTIPLY_ADD"
        links.new(drips, h.inputs[0])
        h.inputs[1].default_value = 0.7
        links.new(cast, h.inputs[2])
        nrm = bump(nodes, links, h.outputs[0], 0.7, 0.0025)
        # a few chips showing dark iron
        chip = ramp(nodes, links, noise(nodes, links, co, 55.0, 6.0, 0.6), 0.735, 0.745)
        chip_f = nodes.new("ShaderNodeSeparateColor")
        links.new(chip, chip_f.inputs[0])
        chip_f = chip_f.outputs[0]
        nrm = bump(nodes, links, chip_f, 0.6, 0.0006, nrm, invert=True)
        col = mix(nodes, links, chip_f, col, (0.05, 0.045, 0.04, 1))
        # grime in the gaps between sections and under the hubs
        ao = nodes.new("ShaderNodeAmbientOcclusion")
        ao.samples = 8
        ao.only_local = True
        ao.inputs["Distance"].default_value = 0.12
        dirt = ramp(nodes, links, ao.outputs["AO"], 0.5, 0.95)
        dirt_f = nodes.new("ShaderNodeSeparateColor")
        links.new(dirt, dirt_f.inputs[0])
        xyz = nodes.new("ShaderNodeSeparateXYZ")
        links.new(co, xyz.inputs[0])
        deep = nodes.new("ShaderNodeMapRange")
        deep.inputs["From Min"].default_value = X_FRONT + 0.035
        deep.inputs["From Max"].default_value = X_FRONT + 0.075
        deep.inputs["To Min"].default_value = 1.0
        deep.inputs["To Max"].default_value = 0.45
        links.new(xyz.outputs["X"], deep.inputs["Value"])
        both = nodes.new("ShaderNodeMath")
        both.operation = "MINIMUM"
        links.new(dirt_f.outputs[0], both.inputs[0])
        links.new(deep.outputs[0], both.inputs[1])
        dirt_f = both
        col = mix(nodes, links, dirt_f.outputs[0], (0.12, 0.11, 0.095, 1), col)
        rough = mix(nodes, links, dirt_f.outputs[0], (0.6, 0.6, 0.6, 1), rough)
    else:
        nrm = None
    nrm = bump(nodes, links, peel, 0.12 if heavy else 0.06, 0.0004, nrm)

    links.new(col, bsdf.inputs["Base Color"])
    links.new(rough, bsdf.inputs["Roughness"])
    links.new(nrm, bsdf.inputs["Normal"])
    bsdf.inputs["Coat Weight"].default_value = 0.2
    bsdf.inputs["Coat Roughness"].default_value = 0.2
    links.new(nrm, bsdf.inputs["Coat Normal"])
    m.diffuse_color = base
    return m


# ---------- apply ----------

rad = bpy.data.objects["Radiator"]
coll = rad.users_collection[0]
set_mesh(rad, build_mesh("Radiator", radiator_cage), "Radiator")

pipe = bpy.data.objects.get("Radiator_Pipes")
if pipe is None:
    pipe = bpy.data.objects.new("Radiator_Pipes", bpy.data.meshes.new("Radiator_Pipes"))
    coll.objects.link(pipe)
set_mesh(pipe, build_mesh("Radiator_Pipes", pipe_cage), "Radiator_Pipes")

paint = paint_material("Radiator_Paint", (0.74, 0.72, 0.65, 1), heavy=True)
pipe_paint = paint_material("Radiator_PipePaint", (0.78, 0.77, 0.72, 1), heavy=False)
for ob, m in ((rad, paint), (pipe, pipe_paint)):
    ob.data.materials.clear()
    ob.data.materials.append(m)
