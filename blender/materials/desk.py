# Desk: two 120x60 office tables pushed together (window / partition corner), long sides along y.
# Rebuilds the "Desk" mesh: two laminate tops with a ~1 mm seam, round anthracite
# steel legs with plastic glides, a slim rectangular apron frame under each top.
# Footprint measured from photos 122244 / 112212 (wave 2): 1.20 x 1.20 m, seam at x 5.88,
# replaces build_room.py's assumed 1.58 x 0.78 (two 80x80). Idempotent.
import math
import bmesh
import bpy

W, D = 6.50, 2.50
# 122244: desk edge spans 448 px of the far wall vs 624 px for the 1.6 m window opening -> ~1.15-1.2 m along y;
# seam row sits midway between far/near edges -> two equal ~0.6 m tables along x.
tx0, tx1, ty0, ty1, th = W - 1.22, W - 0.02, D - 1.22, D - 0.02, 0.75
TOP_T = 0.025          # top thickness
GAP = 0.001            # seam between the two tops
STEP = 0.003           # near table sits 3 mm proud in -y, like the photo
LEG_R = 0.019          # ~38 mm tube (photos show round legs)
LEG_IN = 0.045         # leg centre inset from top edge
GLIDE_H = 0.010
RAIL_W, RAIL_H = 0.015, 0.040

LAMINATE, POWDER, GLIDE = 0, 1, 2


# ---------- materials ----------

def mat_reset(name):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    out.location = (600, 0)
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (300, 0)
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    coord = nt.nodes.new("ShaderNodeTexCoord")
    coord.location = (-1200, 0)
    return m, nt, bsdf, coord.outputs["Object"]


def noise(nt, vec, scale, detail=2.0, rough=0.5, loc=(-900, 0)):
    n = nt.nodes.new("ShaderNodeTexNoise")
    n.location = loc
    n.inputs["Scale"].default_value = scale
    n.inputs["Detail"].default_value = detail
    n.inputs["Roughness"].default_value = rough
    nt.links.new(vec, n.inputs["Vector"])
    return n.outputs["Fac"]


def map_range(nt, src, lo, hi, a=0.0, b=1.0, loc=(-600, 0)):
    r = nt.nodes.new("ShaderNodeMapRange")
    r.location = loc
    r.inputs["From Min"].default_value = a
    r.inputs["From Max"].default_value = b
    r.inputs["To Min"].default_value = lo
    r.inputs["To Max"].default_value = hi
    nt.links.new(src, r.inputs["Value"])
    return r.outputs["Result"]


def bump(nt, height, strength, distance, loc=(0, -400)):
    b = nt.nodes.new("ShaderNodeBump")
    b.location = loc
    b.inputs["Strength"].default_value = strength
    b.inputs["Distance"].default_value = distance
    nt.links.new(height, b.inputs["Height"])
    return b.outputs["Normal"]


def math_node(nt, op, a, b, loc):
    n = nt.nodes.new("ShaderNodeMath")
    n.operation = op
    n.location = loc
    for i, v in enumerate((a, b)):
        if isinstance(v, float):
            n.inputs[i].default_value = v
        else:
            nt.links.new(v, n.inputs[i])
    return n.outputs[0]


def laminate():
    # Light grey-white melamine, ~#D9D9D6, matte with a slight satin sheen.
    m, nt, bsdf, co = mat_reset("Desk_Laminate")
    base = (0.66, 0.665, 0.645, 1.0)
    # faint smudges: sparse low-frequency patches (slightly glossier, a hair darker)
    smudge_n = noise(nt, co, 2.2, 4.0, 0.6, loc=(-900, 300))
    smudge = map_range(nt, smudge_n, 0.0, 1.0, 0.58, 0.72, loc=(-600, 300))
    # micro roughness variation
    rv = noise(nt, co, 45.0, 3.0, 0.55, loc=(-900, 0))
    rough = math_node(nt, "MULTIPLY_ADD", smudge, -0.07, loc=(-350, 100))
    nt.links.new(map_range(nt, rv, 0.33, 0.42, loc=(-600, 0)), rough.node.inputs[2])
    nt.links.new(rough, bsdf.inputs["Roughness"])
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.location = (-100, 300)
    mix.inputs["A"].default_value = base
    mix.inputs["B"].default_value = (0.63, 0.635, 0.615, 1.0)
    nt.links.new(smudge, mix.inputs["Factor"])
    nt.links.new(mix.outputs["Result"], bsdf.inputs["Base Color"])
    # very fine melamine grain
    grain = noise(nt, co, 900.0, 2.0, 0.5, loc=(-900, -400))
    nt.links.new(bump(nt, grain, 0.04, 0.0002), bsdf.inputs["Normal"])
    bsdf.inputs["Specular IOR Level"].default_value = 0.5
    m.diffuse_color = (*base[:3], 1)
    return m


def powder_coat():
    # Anthracite powder-coated steel, fine orange-peel texture.
    m, nt, bsdf, co = mat_reset("Desk_PowderCoat")
    base = (0.040, 0.042, 0.046, 1.0)
    bsdf.inputs["Base Color"].default_value = base
    bsdf.inputs["Metallic"].default_value = 0.0
    rv = noise(nt, co, 30.0, 3.0, 0.5, loc=(-900, 0))
    nt.links.new(map_range(nt, rv, 0.42, 0.56), bsdf.inputs["Roughness"])
    peel = noise(nt, co, 350.0, 2.0, 0.45, loc=(-900, -400))
    nt.links.new(bump(nt, peel, 0.18, 0.0004), bsdf.inputs["Normal"])
    m.diffuse_color = base
    return m


def glide():
    m, nt, bsdf, co = mat_reset("Desk_Glide")
    base = (0.018, 0.018, 0.018, 1.0)
    bsdf.inputs["Base Color"].default_value = base
    bsdf.inputs["Roughness"].default_value = 0.6
    m.diffuse_color = base
    return m


# ---------- geometry ----------

def box(bm, lo, hi, mi):
    (x0, y0, z0), (x1, y1, z1) = lo, hi
    v = [bm.verts.new(p) for p in (
        (x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
        (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1))]
    for q in ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)):
        bm.faces.new([v[i] for i in q]).material_index = mi


def cylinder(bm, cx, cy, z0, z1, r, mi, n=16):
    ring = [(cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n)) for i in range(n)]
    lo = [bm.verts.new((x, y, z0)) for x, y in ring]
    hi = [bm.verts.new((x, y, z1)) for x, y in ring]
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((lo[i], lo[j], hi[j], hi[i])).material_index = mi
    # ponytail: caps as a quad fan (even n), both ends are hidden against top / floor
    for k in range(1, n - 1, 2):
        bm.faces.new((hi[0], hi[k], hi[k + 1], hi[(k + 2) % n])).material_index = mi
        bm.faces.new((lo[(k + 2) % n], lo[k + 1], lo[k], lo[0])).material_index = mi


def table(bm, x0, x1, y0, y1):
    zt = th - TOP_T
    box(bm, (x0, y0, zt), (x1, y1, th), LAMINATE)
    lx = (x0 + LEG_IN, x1 - LEG_IN)
    ly = (y0 + LEG_IN, y1 - LEG_IN)
    for x in lx:
        for y in ly:
            cylinder(bm, x, y, GLIDE_H, zt + 0.001, LEG_R, POWDER)  # sunk 1 mm: no coplanar faces
            cylinder(bm, x, y, 0.0, GLIDE_H + 0.001, LEG_R - 0.002, GLIDE)
    # apron frame: rails between leg centres, flush under the top
    zr, h = zt - RAIL_H, RAIL_W / 2
    for y in ly:
        box(bm, (lx[0] + LEG_R, y - h, zr), (lx[1] - LEG_R, y + h, zt + 0.001), POWDER)
    for x in lx:
        box(bm, (x - h, ly[0] + LEG_R, zr), (x + h, ly[1] - LEG_R, zt + 0.001), POWDER)


ob = bpy.data.objects["Desk"]
me = ob.data
bm = bmesh.new()
xm = (tx0 + tx1) / 2
table(bm, tx0, xm - GAP / 2, ty0 - STEP, ty1 - STEP)
table(bm, xm + GAP / 2, tx1, ty0, ty1)
for f in bm.faces:
    f.smooth = True
bm.normal_update()
me.clear_geometry()
# materials before geometry: materials.clear() would drop material_index
me.materials.clear()
for mat in (laminate(), powder_coat(), glide()):
    me.materials.append(mat)
bm.to_mesh(me)
bm.free()


bev = ob.modifiers.get("Desk_Bevel") or ob.modifiers.new("Desk_Bevel", "BEVEL")
bev.width = 0.002
bev.segments = 1
bev.use_clamp_overlap = True
bev.limit_method = "ANGLE"
bev.angle_limit = math.radians(30)
bev.harden_normals = True
