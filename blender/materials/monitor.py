# Monitor: Hanns.G-style 24" touch display leaning back on the desk (photos 112212, 122244).
# Rebuilds the Monitor mesh as a tilted slab (black glass front, thin light rim, black back),
# adds a Monitor_Stand kickstand helper, and builds the Monitor_* materials.
import math
import bpy
import bmesh
from mathutils import Matrix, Vector

# ---------- geometry ----------
Y0, Y1 = 1.86, 2.46          # 122244: left end almost at the partition, covers ~half the desk's far edge
X_FRONT, Z_DESK = 6.20, 0.75
H, T = 0.375, 0.035          # panel height (slanted), thickness
TILT = math.radians(12)      # leans back toward the window
B_SIDE, B_TOP, B_CHIN = 0.022, 0.020, 0.052   # glass border widths

# local frame: x = thickness (front face at x=0, facing -x), y = world y, z = up the panel.
# pivot at the bottom-back edge so nothing dips below the desk.
M = (Matrix.Translation((X_FRONT + T, 0, Z_DESK)) @ Matrix.Rotation(TILT, 4, 'Y')
     @ Matrix.Translation((-T, 0, 0)))


def slab(bm, lo, hi):
    (x0, y0, z0), (x1, y1, z1) = lo, hi
    v = [bm.verts.new(p) for p in ((x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
                                   (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1))]
    for q in ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)):
        bm.faces.new([v[i] for i in q])
    return v


def get_obj(name, coll):
    ob = bpy.data.objects.get(name)
    if ob is None:
        ob = bpy.data.objects.new(name, bpy.data.meshes.new(name))
    if ob.name not in coll.objects:
        coll.objects.link(ob)
    return ob


mon = bpy.data.objects["Monitor"]
coll = mon.users_collection[0]

# Monitor panel
bm = bmesh.new()
slab(bm, (0, Y0, 0), (T, Y1, H))
bm.normal_update()
front = next(f for f in bm.faces if f.normal.x < -0.5)
bmesh.ops.inset_individual(bm, faces=[front], thickness=B_SIDE)
for v in front.verts:                       # front is now the inner (screen) face
    v.co.z = B_CHIN if v.co.z < H / 2 else H - B_TOP
    v.co.y = Y0 + B_SIDE if v.co.y < (Y0 + Y1) / 2 else Y1 - B_SIDE
bm.normal_update()
uv = bm.loops.layers.uv.new("UVMap")       # UVs in metres across the panel face
for f in bm.faces:
    n = f.normal
    f.material_index = 3 if f is front else 2 if n.x < -0.5 else 0 if n.x > 0.5 else 1
    f.smooth = True
    for lp in f.loops:
        # front/back: u runs left->right as seen from the room; sides: u = depth from the glass
        lp[uv].uv = (lp.vert.co.x, 0) if f.material_index == 1 else (Y1 - lp.vert.co.y, lp.vert.co.z)
bmesh.ops.transform(bm, matrix=M, verts=bm.verts)
bm.to_mesh(mon.data)
bm.free()
face_mats = [p.material_index for p in mon.data.polygons]   # materials.clear() below resets these

# Kickstand: hinged on the panel back, foot on the desk behind it.
hinge = M @ Vector((T - 0.002, 0, 0.13))
foot = Vector((hinge.x + 0.075, 0, Z_DESK))
d = (foot - hinge).normalized()
n = Vector((d.z, 0, -d.x)) * -1           # points away from the panel (+x side)
bm = bmesh.new()
pts = [hinge, foot, foot + n * 0.006, hinge + n * 0.006]
YM = (Y0 + Y1) / 2
ring0 = [bm.verts.new((p.x, YM - 0.10, p.z)) for p in pts]
ring1 = [bm.verts.new((p.x, YM + 0.10, p.z)) for p in pts]
for i in range(4):
    j = (i + 1) % 4
    bm.faces.new((ring0[i], ring0[j], ring1[j], ring1[i]))
bm.faces.new(ring0[::-1])
bm.faces.new(ring1)
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
for f in bm.faces:
    f.smooth = True
stand = get_obj("Monitor_Stand", coll)
bm.to_mesh(stand.data)
bm.free()

for ob in (mon, stand):
    mod = ob.modifiers.get("Monitor_Bevel") or ob.modifiers.new("Monitor_Bevel", 'BEVEL')
    mod.width, mod.segments, mod.limit_method = 0.0015, 1, 'ANGLE'
    mod.use_clamp_overlap = True
    mod.angle_limit = math.radians(30)
    mod.harden_normals = True


# ---------- materials ----------
def new_mat(name):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(bsdf.outputs[0], out.inputs[0])
    return m, nt, bsdf


def node(nt, kind, *inputs, op=None, **props):
    """Create a node; inputs are sockets (linked) or numbers (set), in input order."""
    nd = nt.nodes.new(kind)
    if op:
        nd.operation = op
    for k, v in props.items():
        setattr(nd, k, v)
    for i, val in enumerate(inputs):
        if val is None:
            continue
        if hasattr(val, "is_output"):
            nt.links.new(val, nd.inputs[i])
        else:
            nd.inputs[i].default_value = val
    return nd.outputs[0]


def math_(nt, op, a, b=0.0):
    return node(nt, "ShaderNodeMath", a, b, op=op)


def box_mask(nt, u, v, u0, u1, v0, v1):
    """1 inside the uv rectangle, else 0."""
    m = math_(nt, 'MULTIPLY', math_(nt, 'GREATER_THAN', u, u0), math_(nt, 'LESS_THAN', u, u1))
    m = math_(nt, 'MULTIPLY', m, math_(nt, 'GREATER_THAN', v, v0))
    return math_(nt, 'MULTIPLY', m, math_(nt, 'LESS_THAN', v, v1))


def uv_split(nt):
    uvn = nt.nodes.new("ShaderNodeUVMap")
    uvn.uv_map = "UVMap"
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(uvn.outputs[0], sep.inputs[0])
    return sep.outputs[0], sep.outputs[1]


def micro(nt, scale, lo, hi):
    """Low-contrast noise mapped to lo..hi (roughness variation)."""
    tc = nt.nodes.new("ShaderNodeTexCoord")
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = scale
    nz.inputs["Detail"].default_value = 6
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    return node(nt, "ShaderNodeMapRange", nz.outputs[0], 0.3, 0.7, lo, hi), nz.outputs[0]


def glass_front(bsdf, nt):
    bsdf.inputs["Coat Weight"].default_value = 1.0
    bsdf.inputs["Coat Roughness"].default_value = 0.02
    bsdf.inputs["Coat IOR"].default_value = 1.52
    bsdf.inputs["Specular IOR Level"].default_value = 0.15   # matte layer under the glass; coat does the gloss
    r, _ = micro(nt, 180, 0.012, 0.03)       # faint smudges on the glass
    nt.links.new(r, bsdf.inputs["Coat Roughness"])


# Back housing + stand: black satin plastic, fine texture.
m_back, nt, bsdf = new_mat("Monitor_Back")
bsdf.inputs["Base Color"].default_value = (0.012, 0.012, 0.013, 1)
r, nz = micro(nt, 400, 0.38, 0.5)
nt.links.new(r, bsdf.inputs["Roughness"])
bump = nt.nodes.new("ShaderNodeBump")
bump.inputs["Strength"].default_value = 0.08
bump.inputs["Distance"].default_value = 0.0005
nt.links.new(nz, bump.inputs["Height"])
nt.links.new(bump.outputs[0], bsdf.inputs["Normal"])

# Panel sides: thin light-grey trim behind the glass (visible right/bottom in 112212), rest black plastic.
m_rim, nt, bsdf = new_mat("Monitor_Rim")
u, _ = uv_split(nt)
trim = math_(nt, 'LESS_THAN', u, 0.007)
rc = nt.nodes.new("ShaderNodeMix")
rc.data_type = 'RGBA'
rc.inputs[6].default_value = (0.012, 0.012, 0.013, 1)
rc.inputs[7].default_value = (0.42, 0.43, 0.44, 1)
nt.links.new(trim, rc.inputs[0])
nt.links.new(rc.outputs[2], bsdf.inputs["Base Color"])
nt.links.new(math_(nt, 'MULTIPLY', trim, 0.5), bsdf.inputs["Metallic"])
r, _ = micro(nt, 300, 0.3, 0.42)
nt.links.new(r, bsdf.inputs["Roughness"])

# Glass border: black glass with feature stickers bottom-left on the chin and a grey logo bottom-right.
m_bez, nt, bsdf = new_mat("Monitor_Bezel")
glass_front(bsdf, nt)
bsdf.inputs["Roughness"].default_value = 0.3
u, v = uv_split(nt)
N, PITCH, SW, SH, U0, VC = 13, 0.0225, 0.0185, 0.017, 0.030, 0.026
cell = math_(nt, 'DIVIDE', math_(nt, 'SUBTRACT', u, U0), PITCH)
idx = math_(nt, 'FLOOR', cell)
fx = math_(nt, 'MULTIPLY', math_(nt, 'SUBTRACT', cell, idx), PITCH)      # metres inside the cell
dv = math_(nt, 'SUBTRACT', v, VC)
row = box_mask(nt, idx, dv, -0.5, N - 0.5, -SH / 2, SH / 2)
sticker = math_(nt, 'MULTIPLY', row, box_mask(nt, fx, dv, 0, SW, -1, 1))
glyph = math_(nt, 'MULTIPLY', sticker, box_mask(nt, fx, dv, SW * 0.2, SW * 0.8, -SH * 0.28, SH * 0.3))
# per-sticker colour, sampled from 122244 (mostly white labels, a few coloured ones)
ramp_in = math_(nt, 'DIVIDE', math_(nt, 'ADD', idx, 0.5), N)
cr = nt.nodes.new("ShaderNodeValToRGB")
cr.color_ramp.interpolation = 'CONSTANT'
cols = [(0.62, 0.62, 0.6)] * 7 + [(0.45, 0.17, 0.04), (0.62, 0.62, 0.6), (0.55, 0.56, 0.5),
                                  (0.6, 0.62, 0.64), (0.08, 0.36, 0.65), (0.66, 0.66, 0.66)]
el = cr.color_ramp.elements
while len(el) < N:
    el.new(0.5)
for i, c in enumerate(cols):
    el[i].position = i / N
    el[i].color = (*c, 1)
nt.links.new(ramp_in, cr.inputs[0])
glyph_col = (0.06, 0.06, 0.07, 1)
mix = nt.nodes.new("ShaderNodeMix")
mix.data_type = 'RGBA'
mix.inputs[6].default_value = (0.004, 0.004, 0.005, 1)        # black glass
nt.links.new(sticker, mix.inputs[0])
nt.links.new(cr.outputs[0], mix.inputs[7])
mix2 = nt.nodes.new("ShaderNodeMix")
mix2.data_type = 'RGBA'
nt.links.new(math_(nt, 'MULTIPLY', glyph, 0.75), mix2.inputs[0])
nt.links.new(mix.outputs[2], mix2.inputs[6])
mix2.inputs[7].default_value = glyph_col
# logo strip bottom-right on the chin
logo = box_mask(nt, u, v, 0.60 - 0.10, 0.60 - 0.045, VC - 0.0025, VC + 0.0025)
mix3 = nt.nodes.new("ShaderNodeMix")
mix3.data_type = 'RGBA'
nt.links.new(math_(nt, 'MULTIPLY', logo, 0.6), mix3.inputs[0])
nt.links.new(mix2.outputs[2], mix3.inputs[6])
mix3.inputs[7].default_value = (0.05, 0.05, 0.055, 1)
nt.links.new(mix3.outputs[2], bsdf.inputs["Base Color"])
# paper stickers are matte under the glass coat
nt.links.new(node(nt, "ShaderNodeMapRange", sticker, 0, 1, 0.3, 0.7), bsdf.inputs["Roughness"])

# Screen: standby-dark desktop under the glass, very low emission.
m_scr, nt, bsdf = new_mat("Monitor_Screen")
glass_front(bsdf, nt)
bsdf.inputs["Base Color"].default_value = (0.012, 0.012, 0.013, 1)
bsdf.inputs["Roughness"].default_value = 0.35
u, v = uv_split(nt)
grad = node(nt, "ShaderNodeMapRange", v, B_CHIN, H - B_TOP, 1.0, 0.8)   # slightly brighter low down
emc = nt.nodes.new("ShaderNodeMix")
emc.data_type = 'RGBA'
emc.inputs[6].default_value = (0, 0, 0, 1)
emc.inputs[7].default_value = (0.016, 0.017, 0.02, 1)
nt.links.new(grad, emc.inputs[0])
nt.links.new(emc.outputs[2], bsdf.inputs["Emission Color"])
bsdf.inputs["Emission Strength"].default_value = 1.5

mon.data.materials.clear()
for m in (m_back, m_rim, m_bez, m_scr):
    mon.data.materials.append(m)
mon.data.polygons.foreach_set("material_index", face_mats)
mon.data.update()
stand.data.materials.clear()
stand.data.materials.append(m_back)
