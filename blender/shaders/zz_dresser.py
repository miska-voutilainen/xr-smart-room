# Cabinet (black kitchenette sideboard) final looks, owner s2_dresser. Sorts after hard.py, so it wins over its
# Cabinet_* entries. Rebuilds the six Cabinet_* materials with CC0 image maps (textures/s2_dresser/, see SOURCES.txt)
# on the "UVMap" layer made by materials/cabinet.py (world metres, U = x = brush direction; on fronts
# V = z - front top edge, used as the "near the handle" mask for fingerprints).
# Metal constants (linear F0 / F82 edge tint): https://physicallybased.info ("Aluminum", "Stainless Steel"),
# clear anodising dulls aluminium F0 by ~10 % (same values as hard.py ANODISED).
# Bake-friendly: no view-dependent nodes upstream of Base Color / Roughness / Normal.
import os
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import _lib as L  # noqa: E402

TEX = os.path.join(os.path.dirname(HERE), "textures", "s2_dresser")
UV = "UVMap"
ANODISED = ((0.80, 0.805, 0.81), (0.95, 0.95, 0.95))
STAINLESS = ((0.669, 0.639, 0.598), (0.804, 0.791, 0.714))


def image(nt, uvsock, fname, tile, color=False):
    """Image map tiled every `tile` metres (non-square images keep square texels)."""
    img = bpy.data.images.load(os.path.join(TEX, fname), check_existing=True)
    img.colorspace_settings.name = "sRGB" if color else "Non-Color"
    w, h = img.size
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (1.0 / tile, w / (h * tile), 1.0)
    nt.links.new(uvsock, mp.inputs["Vector"])
    t = nt.nodes.new("ShaderNodeTexImage")
    t.image = img
    nt.links.new(mp.outputs[0], t.inputs["Vector"])
    return t.outputs["Color"]


def bw(nt, col):
    n = nt.nodes.new("ShaderNodeRGBToBW")
    nt.links.new(col, n.inputs[0])
    return n.outputs[0]


def normal_map(nt, col, strength):
    n = nt.nodes.new("ShaderNodeNormalMap")
    n.space, n.uv_map = "TANGENT", UV
    n.inputs["Strength"].default_value = strength
    nt.links.new(col, n.inputs["Color"])
    return n.outputs[0]


def start(name):
    r = L.reset(name)
    if r is None:
        return None
    m, nt, b, co = r
    uvn = nt.nodes.new("ShaderNodeUVMap")
    uvn.uv_map = UV
    return m, nt, b, co, uvn.outputs["UV"]


def sparse(nt, co, scale, lo, hi):
    """Large blotchy 0..1 mask: where on a surface people actually touch/scratch."""
    return L.maprange(nt, L.noise(nt, co, scale, 3.0, 0.55), lo, hi, 0.0, 1.0)


def metal(name, f0, f82, rough, tile, aniso, scratch, prints, slots=None):
    r = start(name)
    if r is None:
        return
    m, nt, b, co, uv = r
    b.inputs["Metallic"].default_value = 1.0
    L.put(nt, b.inputs["Specular Tint"], f82)
    # brushing: Metal009 roughness streaks around `rough`, plus Scratches005 (rougher) and Fingerprints002 (grease is
    # smoother than the brushed finish), both gated by blotchy masks so they cluster instead of tiling evenly
    brush = bw(nt, image(nt, uv, "Metal009_2K-JPG_Roughness.jpg", tile))                       # mean ~0.47
    rr = L.math(nt, "MULTIPLY_ADD", brush, 0.35, rough - 0.165)
    sc = bw(nt, image(nt, uv, "Scratches005_2K-JPG_Opacity.jpg", 0.35))                    # already sparse
    rr = L.math(nt, "MULTIPLY_ADD", sc, scratch, rr)
    fp = L.math(nt, "MULTIPLY", bw(nt, image(nt, uv, "Fingerprints002_2K-JPG_Opacity.jpg", 0.12)), sparse(nt, co, 6.0, 0.52, 0.72))
    rr = L.math(nt, "MULTIPLY_ADD", fp, -prints, rr, clamp=True)
    L.put(nt, b.inputs["Roughness"], rr)
    # slightly darker where scratched / greasy (oxide + oil films lower the visible F0 a touch)
    L.put(nt, b.inputs["Base Color"], L.mix_col(nt, L.math(nt, "ADD", L.math(nt, "MULTIPLY", sc, 0.4), L.math(nt, "MULTIPLY", fp, 0.12)),
                                                f0, tuple(c * 0.85 for c in f0)))
    # anisotropy: tangent = U = brush direction; rotation 0.25 puts the long axis of the lobe across the grooves
    tg = nt.nodes.new("ShaderNodeTangent")
    tg.direction_type, tg.uv_map = "UV_MAP", UV
    nt.links.new(tg.outputs[0], b.inputs["Tangent"])
    b.inputs["Anisotropic"].default_value = aniso
    b.inputs["Anisotropic Rotation"].default_value = 0.25
    nrm = normal_map(nt, image(nt, uv, "Metal009_2K-JPG_NormalGL.jpg", tile, color=False), 0.15)
    if slots:  # fridge vent: slot grid (Brick texture, no stagger); bricks = slots, mortar = steel web
        fx0, fz1, px, pz = slots
        K = 1.3
        sx = nt.nodes.new("ShaderNodeSeparateXYZ")
        nt.links.new(co, sx.inputs[0])
        cx = nt.nodes.new("ShaderNodeCombineXYZ")
        L.put(nt, cx.inputs["X"], L.math(nt, "SUBTRACT", sx.outputs["X"], fx0))
        L.put(nt, cx.inputs["Y"], L.math(nt, "MULTIPLY_ADD", sx.outputs["Z"], -K, fz1 * K))
        br = nt.nodes.new("ShaderNodeTexBrick")
        br.offset, br.squash = 0.0, 1.0
        for k, v in {"Scale": 1.0, "Mortar Size": 0.00275, "Mortar Smooth": 0.35, "Bias": 0.0,
                     "Brick Width": px, "Row Height": pz * K}.items():
            br.inputs[k].default_value = v
        nt.links.new(cx.outputs[0], br.inputs["Vector"])
        web = br.outputs["Fac"]                                                             # 1 steel, 0 slot
        L.put(nt, b.inputs["Base Color"], L.mix_col(nt, web, (0.004, 0.004, 0.004), b.inputs["Base Color"].links[0].from_socket))
        L.put(nt, b.inputs["Metallic"], web)
        nrm = L.bump(nt, web, 0.6, 0.002, nrm)
    L.put(nt, b.inputs["Normal"], nrm)
    m.diffuse_color = (*f0, 1)
    L.tidy(nt)


def laminate(name, color, rough, var, tile, nstrength, grip=0.0, smear=0.0):
    """Melamine / HPL / ABS: Plastic010 micro texture (roughness + normal), optional fingerprints near the handle
    (UV V = z - front top edge, 0..-0.12 m) and optional broad wipe smears (worktop)."""
    r = start(name)
    if r is None:
        return
    m, nt, b, co, uv = r
    b.inputs["IOR"].default_value = 1.5
    pr = bw(nt, image(nt, uv, "Plastic010_2K-JPG_Roughness.jpg", tile))                       # mean ~0.36
    rr = L.math(nt, "MULTIPLY_ADD", pr, var / 0.035, rough - 0.365 * var / 0.035)
    tone = L.maprange(nt, L.noise(nt, co, 3.0, 3.0), 0.3, 0.7, 0.94, 1.06)                    # slow albedo drift
    col = L.mix_col(nt, tone, tuple(c * 0.94 for c in color), tuple(c * 1.06 for c in color))
    if grip:
        sep = nt.nodes.new("ShaderNodeSeparateXYZ")
        nt.links.new(uv, sep.inputs[0])
        near = L.maprange(nt, sep.outputs["Y"], -0.12, 0.0, 0.0, 1.0)                        # 1 at the handle
        fp = bw(nt, image(nt, uv, "Fingerprints002_2K-JPG_Opacity.jpg", 0.11))
        fp = L.math(nt, "MULTIPLY", L.math(nt, "MULTIPLY", fp, near), sparse(nt, co, 5.0, 0.35, 0.6))
        rr = L.math(nt, "MULTIPLY_ADD", fp, -grip, rr)                                       # skin oil = glossier
        col = L.mix_col(nt, fp, col, tuple(c * 1.8 for c in color))
    if smear:
        sm = bw(nt, image(nt, uv, "Smear004_2K-JPG_Roughness.jpg", 0.9))
        rr = L.math(nt, "MULTIPLY_ADD", L.math(nt, "MULTIPLY", sm, sparse(nt, co, 1.5, 0.35, 0.65)), -smear, rr)
    L.put(nt, b.inputs["Roughness"], L.math(nt, "MAXIMUM", rr, 0.08))
    L.put(nt, b.inputs["Base Color"], col)
    if nstrength:
        L.put(nt, b.inputs["Normal"], normal_map(nt, image(nt, uv, "Plastic010_2K-JPG_NormalGL.jpg", tile), nstrength))
    m.diffuse_color = (*color, 1)
    L.tidy(nt)


ob = bpy.data.objects.get("Cabinet")
vent = tuple(ob[k] for k in ("vent_fx0", "vent_fz1", "vent_px", "vent_pz")) if ob and "vent_px" in ob else None

# fronts: matte black melamine/HPL, decor-paper micro texture; photo 150448 reads warm near-black
laminate("Cabinet_Front", (0.019, 0.018, 0.017), 0.55, 0.05, 0.35, 0.25, grip=0.8)
laminate("Cabinet_Edge", (0.021, 0.020, 0.019), 0.38, 0.03, 0.35, 0.0, grip=0.4)          # 1 mm ABS banding
laminate("Cabinet_Worktop", (0.075, 0.064, 0.057), 0.40, 0.04, 0.25, 0.2, smear=0.10)      # compact laminate
metal("Cabinet_Aluminium", *ANODISED, 0.36, 0.12, 0.6, 0.5, 0.12)
metal("Cabinet_Steel", *STAINLESS, 0.34, 0.15, 0.5, 0.4, 0.1)
if vent:
    metal("Cabinet_Vent", *STAINLESS, 0.36, 0.15, 0.5, 0.15, 0.04, slots=vent)
print("ZZ_DRESSER: Cabinet materials rebuilt")
