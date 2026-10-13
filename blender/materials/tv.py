# TV: Samsung 55" LED set (H-series class, switched off) on a slim VESA wall mount in the Wall_Top niche, facing -y.
# Rebuilds the TV mesh (bezel shell + recessed screen + back casing + silver bottom lip + wall bracket)
# and assigns TV_* materials. Idempotent.
# Size: Samsung UE55H6640/H6740 spec, 1230.6 x 715.5 x 64 mm without stand, VESA 400x400 (tvsfaq.com).
# 64 mm body + ~20 mm slim bracket > 60 mm niche: the set stands ~2.4 cm proud of the wall, as in 122244.
import bpy
import bmesh

# ---------- geometry (metres, world coords; niche back wall is at y = 2.56) ----------
CX, CZ = 4.772, 1.438          # 150338 gaps: left 0.18, right 0.20, top/bottom 0.15 (niche x 4.07..5.50, z .98..1.89)
TW, TH = 1.050, 0.600          # s3_geo: 150338 TV/niche px ratio x niche 0.91 m high (112212/122244) -> 46" class, not 55"
Y_WALL, BRACKET, DEPTH = 2.56, 0.020, 0.064
Y_BACK = Y_WALL - BRACKET      # back of casing
Y_FRONT = Y_BACK - DEPTH       # front face (~2.476)
SHELL_D = 0.030                # depth of the slim outer frame; the electronics bulge makes up the rest
BEZ, BEZ_BOT = 0.009, 0.017    # bezel width top/sides, bottom
INSET = 0.002                  # screen recessed behind the bezel lip
LIP_H = 0.005                  # silver strip under the bottom bezel
VESA = 0.40

x0, x1 = CX - TW / 2, CX + TW / 2
z0, z1 = CZ - TH / 2, CZ + TH / 2
zs = z0 + LIP_H                # shell bottom (lip sits below it)
yf, yb = Y_FRONT, Y_FRONT + SHELL_D

BEZEL, SCREEN, BACK, TRIM = range(4)

bm = bmesh.new()


def quad(vs, mat):
    f = bm.faces.new(vs)
    f.material_index = mat


def box(lo, hi, mat):
    (a0, b0, c0), (a1, b1, c1) = lo, hi
    v = [bm.verts.new(p) for p in ((a0, b0, c0), (a1, b0, c0), (a1, b1, c0), (a0, b1, c0),
                                   (a0, b0, c1), (a1, b0, c1), (a1, b1, c1), (a0, b1, c1))]
    for q in ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)):
        quad([v[i] for i in q], mat)


def rect(ax0, az0, ax1, az1, y):
    return [bm.verts.new(p) for p in ((ax0, y, az0), (ax1, y, az0), (ax1, y, az1), (ax0, y, az1))]


# Front shell: outer box whose front face is a bezel ring around a recessed screen.
o = rect(x0, zs, x1, z1, yf)
b = rect(x0, zs, x1, z1, yb)
i = rect(x0 + BEZ, z0 + BEZ_BOT, x1 - BEZ, z1 - BEZ, yf)
# 45 deg chamfer into the panel: below the bevel's 60 deg limit, so the bevel skips it (no degenerate faces)
r = rect(x0 + BEZ + INSET, z0 + BEZ_BOT + INSET, x1 - BEZ - INSET, z1 - BEZ - INSET, yf + INSET)
quad(b, BACK)
quad(r, SCREEN)
for k in range(4):
    n = (k + 1) % 4
    quad([o[k], o[n], b[n], b[k]], BEZEL)   # outer edge
    quad([o[k], o[n], i[n], i[k]], BEZEL)   # bezel ring
    quad([i[k], i[n], r[n], r[k]], BEZEL)   # recess wall

# Back casing (thicker electronics bulge) and the silver lip under the bottom bezel.
box((x0 + 0.06, yb, z0 + 0.06), (x1 - 0.06, Y_BACK, z1 - 0.06), BACK)
# Slim VESA 400x400 mount: two vertical arms on the casing, two horizontal rails on the wall plate.
for dx in (-VESA / 2, VESA / 2):
    box((CX + dx - 0.015, Y_BACK - 0.001, CZ - 0.23), (CX + dx + 0.015, Y_BACK + 0.009, CZ + 0.23), BACK)
for dz in (-0.17, 0.17):
    box((CX - 0.25, Y_BACK + 0.0085, CZ + dz - 0.02), (CX + 0.25, Y_WALL - 0.0005, CZ + dz + 0.02), BACK)
box((x0 + 0.002, yf - 0.001, z0), (x1 - 0.002, yf + 0.009, zs - 0.0002), TRIM)  # no coplanar faces with the shell

bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
for f in bm.faces:
    f.smooth = True   # harden_normals on the bevel needs smooth shading

# ---------- materials ----------

def new_mat(name):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return m, nt, bsdf


def noise(nt, scale, detail=4.0):
    tc = nt.nodes.new("ShaderNodeTexCoord")
    n = nt.nodes.new("ShaderNodeTexNoise")
    n.inputs["Scale"].default_value = scale
    n.inputs["Detail"].default_value = detail
    nt.links.new(tc.outputs["Object"], n.inputs["Vector"])
    return n


def vary(nt, src, lo, hi, dst):
    """Map a 0..1 noise output to lo..hi into a socket."""
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value = 0.3
    mr.inputs["From Max"].default_value = 0.7
    mr.inputs["To Min"].default_value = lo
    mr.inputs["To Max"].default_value = hi
    nt.links.new(src, mr.inputs["Value"])
    nt.links.new(mr.outputs["Result"], dst)


def bump(nt, src, strength, dist, bsdf):
    bp = nt.nodes.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = strength
    bp.inputs["Distance"].default_value = dist
    nt.links.new(src, bp.inputs["Height"])
    nt.links.new(bp.outputs["Normal"], bsdf.inputs["Normal"])


def principled(bsdf, color, rough, metallic=0.0, spec=0.5):
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Specular IOR Level"].default_value = spec


# Screen: near-black panel under an anti-glare film. Slightly hazy reflections,
# barely visible smudges/dust as roughness variation.
m_screen, nt, bsdf = new_mat("TV_Screen")
principled(bsdf, (0.004, 0.0045, 0.005), 0.16)
bsdf.inputs["IOR"].default_value = 1.5
bsdf.inputs["Coat Weight"].default_value = 0.15
bsdf.inputs["Coat Roughness"].default_value = 0.22
bsdf.inputs["Coat IOR"].default_value = 1.45
smudge = noise(nt, 6.0, 3.0)
vary(nt, smudge.outputs["Fac"], 0.13, 0.21, bsdf.inputs["Roughness"])
bump(nt, noise(nt, 1800.0, 2.0).outputs["Fac"], 0.02, 0.0005, bsdf)

# Bezel: satin black plastic with fine moulding texture.
m_bezel, nt, bsdf = new_mat("TV_Bezel")
principled(bsdf, (0.012, 0.012, 0.013), 0.4)
vary(nt, noise(nt, 40.0).outputs["Fac"], 0.36, 0.46, bsdf.inputs["Roughness"])
bump(nt, noise(nt, 2500.0, 2.0).outputs["Fac"], 0.08, 0.0003, bsdf)

# Back casing: matte textured black plastic.
m_back, nt, bsdf = new_mat("TV_Back")
principled(bsdf, (0.008, 0.008, 0.009), 0.62, spec=0.4)
bump(nt, noise(nt, 1500.0, 2.0).outputs["Fac"], 0.25, 0.0005, bsdf)

# Bottom lip: silver-grey painted/brushed plastic strip.
m_trim, nt, bsdf = new_mat("TV_Trim")
principled(bsdf, (0.6, 0.6, 0.61), 0.35, metallic=0.5)
bsdf.inputs["Anisotropic"].default_value = 0.4
vary(nt, noise(nt, 300.0).outputs["Fac"], 0.28, 0.36, bsdf.inputs["Roughness"])

# Slots must exist before to_mesh, or face material indices get clamped to 0.
ob = bpy.data.objects["TV"]
ob.data.materials.clear()
for m in (m_bezel, m_screen, m_back, m_trim):   # order = BEZEL, SCREEN, BACK, TRIM
    ob.data.materials.append(m)

bm.to_mesh(ob.data)
bm.free()
ob.data.update()

mod = ob.modifiers.get("TV_Bevel") or ob.modifiers.new("TV_Bevel", "BEVEL")
mod.width = 0.0012
mod.segments = 1
mod.use_clamp_overlap = True
mod.angle_limit = 1.0472
mod.limit_method = "ANGLE"
mod.harden_normals = True


