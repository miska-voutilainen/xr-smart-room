# Procedural PBR library for "hard" surfaces: metals, plastics, paints, glass, screens, laminates, rubber, fabric.
# Runs after materials/*.py. Overrides EXISTING materials by name only: never creates materials, never touches
# meshes or slots. Two modes per name:
#   rebuild: the whole node tree is replaced by a recipe below.
#   patch:   the tree from materials/<part>.py encodes geometry-coupled masks (stickers, vent slots, wear zones,
#            emboss); it is kept, PBR scalars are corrected, a fine bump is chained in, and AO grime is gated.
# Coordinates: Object (= world metres for most objects; Chair_* and Door_Leaf are object-local).
# Bake-friendly: nothing view-dependent upstream of Base Color/Roughness/Metallic/Normal.
# AO grime is multiplied through a Value node "Hard_Dirt" (set to 0 for Unity bakes, see _lib.DIRT).
# Reference values (linear F0 / albedo, roughness, IOR): https://physicallybased.info (api.physicallybased.info/materials),
# Blender manual Principled BSDF: https://docs.blender.org/manual/en/latest/render/shader_nodes/shader/principled.html
import importlib
import os
import sys

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _lib as L  # noqa: E402

importlib.reload(L)

PATCH_TAG = "Hard_Patched"


# ---------------------------------------------------------------- recipes

def tone_mul(nt, color, t):
    """color * t (t is a float socket) using a Multiply colour mix."""
    n = nt.nodes.new("ShaderNodeMix")
    n.data_type, n.blend_type = "RGBA", "MULTIPLY"
    n.inputs[0].default_value = 1.0
    L.put(nt, n.inputs[6], color)
    c = nt.nodes.new("ShaderNodeCombineColor")
    for i in range(3):
        L.put(nt, c.inputs[i], t)
    nt.links.new(c.outputs[0], n.inputs[7])
    return n.outputs[2]


def albedo(nt, co, color, tone, tone_scale=4.0):
    t = L.maprange(nt, L.noise(nt, co, tone_scale, 3.0), 0.3, 0.7, 1.0 - tone, 1.0 + tone)
    return tone_mul(nt, color, t)


def rough_var(nt, co, rough, var, scale=30.0, smudge=0.0, vec=None):
    """Micro roughness variation +-var around rough, plus optional sparse smudges (fingerprints/wipes)."""
    r = L.maprange(nt, L.noise(nt, vec or co, scale, 4.0, 0.55), 0.3, 0.7, rough - var, rough + var)
    if smudge:
        s = L.maprange(nt, L.noise(nt, co, 3.0, 5.0, 0.6, 0.4), 0.55, 0.75, 0.0, smudge)
        r = L.math(nt, "ADD", r, s, clamp=True)
    return r


def dielectric(name, color, rough, var=0.04, rscale=30.0, tone=0.04, tex=(1500.0, 0.05, 0.0003),
               ior=1.5, spec=0.5, smudge=0.0, coat=0.0, coat_rough=0.05, sheen=0.0):
    """Plastics, laminates, paints, rubber. tex = (noise scale per metre, bump strength, bump distance m)."""
    r = L.reset(name)
    if r is None:
        return None
    m, nt, b, co = r
    b.inputs["IOR"].default_value = ior
    b.inputs["Specular IOR Level"].default_value = spec
    L.put(nt, b.inputs["Base Color"], albedo(nt, co, color, tone))
    L.put(nt, b.inputs["Roughness"], rough_var(nt, co, rough, var, rscale, smudge))
    nrm = None
    if tex:
        nrm = L.bump(nt, L.noise(nt, co, tex[0], 2.0), tex[1], tex[2])
        L.put(nt, b.inputs["Normal"], nrm)
    if coat:
        b.inputs["Coat Weight"].default_value = coat
        b.inputs["Coat Roughness"].default_value = coat_rough
    if sheen:
        b.inputs["Sheen Weight"].default_value = sheen
    m.diffuse_color = (*color, 1)
    return m, nt, b, co


def metal(name, f0, f82, rough, var, streak=None, scratch=0.0, tone=0.02):
    """Conductor: Base Color = F0 (linear), Specular Tint = F82 edge tint. streak = coord stretch for brushing."""
    r = L.reset(name)
    if r is None:
        return None
    m, nt, b, co = r
    b.inputs["Metallic"].default_value = 1.0
    L.put(nt, b.inputs["Specular Tint"], f82)
    L.put(nt, b.inputs["Base Color"], albedo(nt, co, f0, tone, 8.0))
    vec = L.scale_vec(nt, co, streak) if streak else None
    rr = rough_var(nt, co, rough, var, 1.0 if streak else 6.0, smudge=0.05, vec=vec)  # broad: fine mottling reads as glitter
    h = L.noise(nt, vec or co, 1.0 if streak else 2500.0, 6.0, 0.6)
    if scratch:  # sparse fine scratches: thin ridges of a stretched noise, rougher than the polish
        s = L.maprange(nt, L.noise(nt, L.scale_vec(nt, co, (60.0, 2000.0, 60.0)), 1.0, 2.0), 0.62, 0.66, 0.0, scratch)
        rr = L.math(nt, "ADD", rr, s, clamp=True)
    L.put(nt, b.inputs["Roughness"], rr)
    L.put(nt, b.inputs["Normal"], L.bump(nt, h, 0.03 if streak else 0.008, 0.0002))  # unbrushed: avoid glitter
    m.diffuse_color = (*f0, 1)
    return m, nt, b, co


def glass(name, tint=(0.96, 0.985, 0.97), ior=1.52):
    """Soda-lime float glass. Shadow rays pass through a tinted Transparent BSDF so panes don't block daylight
    (no caustics needed); camera/reflection rays see real refraction. Faint smudges/dust as roughness."""
    r = L.reset(name)
    if r is None:
        return None
    m, nt, b, co = r
    out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
    L.put(nt, b.inputs["Base Color"], tint)
    b.inputs["IOR"].default_value = ior
    b.inputs["Transmission Weight"].default_value = 1.0
    L.put(nt, b.inputs["Roughness"], L.maprange(nt, L.noise(nt, co, 4.0, 5.0, 0.6, 0.5), 0.55, 0.8, 0.0, 0.025))
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    tr.inputs["Color"].default_value = (*tint, 1)
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(nt.nodes.new("ShaderNodeLightPath").outputs["Is Shadow Ray"], mix.inputs[0])
    nt.links.new(b.outputs[0], mix.inputs[1])
    nt.links.new(tr.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    m.diffuse_color = (*tint, 0.25)
    return m, nt, b, co


def screen(name, rough=0.2):
    """Switched-off LCD: near-black panel (no emission) behind an anti-glare/AR polariser film. The film reflects
    ~2 % at normal incidence (photo 112212: screen ~2 % of the wall luminance), i.e. Specular IOR Level 0.25
    (0.5 = 4 % F0 for IOR 1.5). Smudges in roughness."""
    return dielectric(name, (0.004, 0.0042, 0.0048), rough, 0.03, 8.0, 0.1, (3000.0, 0.01, 0.0002),
                      ior=1.5, spec=0.25, smudge=0.08)


def fabric(name, color, rough=0.8):
    """Woven polyester upholstery: plain weave (~1.2 mm pitch) bump, sheen for the fibre fuzz, mottled wear."""
    r = L.reset(name)
    if r is None:
        return None
    m, nt, b, co = r
    w = []
    for axis in ("X", "Y", "Z"):
        n = nt.nodes.new("ShaderNodeTexWave")
        n.bands_direction = axis
        n.inputs["Scale"].default_value = 420.0
        n.inputs["Distortion"].default_value = 1.5
        L.put(nt, n.inputs["Vector"], co)
        w.append(n.outputs["Fac"])
    weave = L.math(nt, "MULTIPLY", L.math(nt, "MAXIMUM", w[0], w[1]), w[2])
    h = L.math(nt, "MULTIPLY_ADD", L.noise(nt, co, 900.0, 2.0), 0.5, weave)  # weave + 0.5 * fuzz
    L.put(nt, b.inputs["Normal"], L.bump(nt, h, 0.35, 0.0004))
    mott = L.noise(nt, co, 9.0, 4.0)
    shade = L.math(nt, "MULTIPLY", L.maprange(nt, mott, 0.3, 0.7, 0.85, 1.15), L.maprange(nt, h, 0.0, 1.5, 0.85, 1.1))
    L.put(nt, b.inputs["Base Color"], tone_mul(nt, color, shade))
    L.put(nt, b.inputs["Roughness"], L.maprange(nt, mott, 0.3, 0.7, rough - 0.05, rough + 0.05))
    b.inputs["Sheen Weight"].default_value = 0.35
    b.inputs["Sheen Roughness"].default_value = 0.4
    b.inputs["Sheen Tint"].default_value = (0.5, 0.5, 0.52, 1)
    b.inputs["Specular IOR Level"].default_value = 0.35
    m.diffuse_color = (*color, 1)
    return m, nt, b, co


def patch(name, bump=None, rough=None, tone=0.04, **scalars):
    """Keep the part's own tree; set Principled scalars, give unlinked Roughness micro variation (rough=(lo, hi)),
    chain a fine bump (scale, strength, dist) after any existing normal, gate every AO node through Hard_Dirt."""
    m = bpy.data.materials.get(name)
    if m is None or not m.use_nodes:
        return None
    nt = m.node_tree
    if nt.nodes.get(PATCH_TAG):
        return m  # already patched (idempotent when hard.py is run twice without materials/ in between)
    nt.nodes.new("NodeFrame").name = PATCH_TAG
    co = nt.nodes.new("ShaderNodeTexCoord").outputs["Object"]
    for b in [n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"]:
        for k, v in scalars.items():
            L.put(nt, b.inputs[k.replace("_", " ")], v)
        if tone:  # +-tone albedo drift on top of whatever feeds Base Color (masks kept)
            bc = b.inputs["Base Color"]
            src = bc.links[0].from_socket if bc.is_linked else tuple(bc.default_value)
            L.put(nt, bc, albedo(nt, co, src, tone))
        if rough and not b.inputs["Roughness"].is_linked:
            L.put(nt, b.inputs["Roughness"], rough_var(nt, co, (rough[0] + rough[1]) / 2, (rough[1] - rough[0]) / 2))
        if bump:
            old = b.inputs["Normal"].links[0].from_socket if b.inputs["Normal"].is_linked else None
            nrm = L.bump(nt, L.noise(nt, co, bump[0], 2.0), bump[1], bump[2], old)
            for s in ("Normal", "Coat Normal"):
                if s == "Normal" or (old and b.inputs[s].is_linked and b.inputs[s].links[0].from_socket == old):
                    nt.links.new(nrm, b.inputs[s])
    for ao in [n for n in nt.nodes if n.type == "AMBIENT_OCCLUSION"]:
        for sock in ao.outputs:
            for lk in list(sock.links):
                nt.links.new(L.gate_ao(nt, sock), lk.to_socket)
    return m


# ---------------------------------------------------------------- physically based constants (linear)
CHROMIUM = ((0.654, 0.685, 0.701), (0.591, 0.675, 0.703))      # physicallybased.info "Chromium" color / specularColor
ALUMINIUM = ((0.916, 0.923, 0.924), (0.989, 0.989, 0.972))     # "Aluminum"
STAINLESS = ((0.669, 0.639, 0.598), (0.804, 0.791, 0.714))     # "Stainless Steel"
ZINC = ((0.808, 0.844, 0.865), (0.854, 0.922, 0.923))          # "Zinc" (zinc-plated steel hardware)
ANODISED = ((0.80, 0.805, 0.81), (0.95, 0.95, 0.95))           # clear-anodised Al: oxide layer dulls F0 ~10 %
PINK = (0.56, 0.012, 0.165)                                    # door.py telemagenta (photo-matched by g1)

# Looks, by preset key. Each entry: fn(material_name) -> rebuilt material or None.
BRUSH_X = (2.0, 800.0, 800.0)        # streaks along world x
PRESETS = {
    # metals
    "chrome": lambda n: metal(n, *CHROMIUM, 0.05, 0.02, scratch=0.12),
    "alu_anodised_brushed_x": lambda n: metal(n, *ANODISED, 0.30, 0.05, streak=BRUSH_X),
    "alu_satin_plinth": lambda n: metal(n, *ANODISED, 0.42, 0.06, streak=BRUSH_X),            # 122216 kick plate
    "alu_extrusion": lambda n: metal(n, *ANODISED, 0.38, 0.05),                              # lab frames (151018)
    "stainless_brushed_leaf_y": lambda n: metal(n, *STAINLESS, 0.24, 0.06, streak=(300.0, 3.0, 300.0)),
    "stainless_brushed_x": lambda n: metal(n, *STAINLESS, 0.28, 0.06, streak=BRUSH_X),
    "steel_zinc": lambda n: metal(n, *ZINC, 0.32, 0.06),                                      # hinges, screws, brackets
    "silver_plastic_lip": lambda n: metal(n, (0.42, 0.42, 0.43), (0.8, 0.8, 0.82), 0.36, 0.04, streak=BRUSH_X),
    # plastics (ABS IOR ~1.53, PVC 1.54, PP 1.49: physicallybased.info "Plastic (*)")
    "abs_black_satin": lambda n: dielectric(n, (0.012, 0.012, 0.013), 0.36, 0.05, 40.0, 0.06, (2500.0, 0.06, 0.0003), ior=1.53),
    "abs_black_matte": lambda n: dielectric(n, (0.010, 0.010, 0.011), 0.60, 0.05, 30.0, 0.06, (1500.0, 0.25, 0.0005), ior=1.53),
    "abs_black_textured": lambda n: dielectric(n, (0.012, 0.012, 0.013), 0.42, 0.05, 40.0, 0.06, (2000.0, 0.10, 0.0004), ior=1.53, smudge=0.06),
    "abs_white": lambda n: dielectric(n, (0.78, 0.785, 0.77), 0.32, 0.05, 40.0, 0.02, (2000.0, 0.04, 0.0003), ior=1.53, smudge=0.06),
    "pp_black_glide": lambda n: dielectric(n, (0.018, 0.018, 0.018), 0.58, 0.06, 60.0, 0.08, (3000.0, 0.15, 0.0003), ior=1.49),
    "pvc_white_window": lambda n: dielectric(n, (0.80, 0.805, 0.79), 0.30, 0.04, 20.0, 0.015, (350.0, 0.04, 0.0005), ior=1.54, smudge=0.05),
    "pvc_white_sill": lambda n: dielectric(n, (0.79, 0.795, 0.78), 0.22, 0.05, 15.0, 0.02, (250.0, 0.02, 0.0005), ior=1.54, smudge=0.08),
    # rubber (EPDM): physicallybased.info "Tire" 0.023 albedo, roughness 0.7
    "rubber_epdm": lambda n: dielectric(n, (0.03, 0.031, 0.033), 0.68, 0.06, 80.0, 0.08, (2500.0, 0.10, 0.0002), ior=1.52),
    # paints / powder coat (powder coat: semi-gloss, orange peel 2-4 mm)
    "powder_anthracite": lambda n: dielectric(n, (0.042, 0.044, 0.048), 0.40, 0.05, 30.0, 0.05, (300.0, 0.18, 0.0004)),
    "powder_ral7035": lambda n: dielectric(n, (0.58, 0.60, 0.59), 0.38, 0.05, 30.0, 0.02, (300.0, 0.15, 0.0004)),  # lab frames 151022
    "paint_red_drawer": lambda n: dielectric(n, (0.32, 0.035, 0.045), 0.35, 0.05, 30.0, 0.04, (300.0, 0.12, 0.0004), smudge=0.06),  # 151018 pedestals
    # laminates (melamine / HPL), photo-derived albedo (white-balanced against the wall)
    "melamine_white_grey": lambda n: dielectric(n, (0.66, 0.665, 0.645), 0.40, 0.04, 45.0, 0.025, (900.0, 0.04, 0.0002), smudge=0.08),
    "laminate_black_matte": lambda n: dielectric(n, (0.017, 0.016, 0.015), 0.52, 0.05, 25.0, 0.08, (900.0, 0.04, 0.0003), smudge=0.08),
    "laminate_dark_worktop": lambda n: dielectric(n, (0.072, 0.061, 0.055), 0.42, 0.05, 25.0, 0.10, (1500.0, 0.05, 0.0003), smudge=0.1),
    "hpl_red_desktop": lambda n: dielectric(n, (0.42, 0.03, 0.035), 0.33, 0.05, 25.0, 0.04, (1200.0, 0.04, 0.0003), smudge=0.1),  # 151022
    "laminate_grey_bench": lambda n: dielectric(n, (0.36, 0.36, 0.35), 0.40, 0.05, 25.0, 0.04, (1200.0, 0.04, 0.0003), smudge=0.1),  # 151018
    "panel_white_board": lambda n: dielectric(n, (0.78, 0.79, 0.78), 0.30, 0.04, 20.0, 0.015, (800.0, 0.02, 0.0003), smudge=0.05),
    # glass, screens, fabric
    "glass_window": lambda n: glass(n, (0.955, 0.975, 0.965)),
    "glass_door": lambda n: glass(n, (0.93, 0.97, 0.955)),
    "screen_off": lambda n: screen(n),
    "fabric_black": lambda n: fabric(n, (0.019, 0.019, 0.02)),
    "mesh_black": lambda n: fabric(n, (0.012, 0.012, 0.013), 0.6),     # office-chair mesh back (opaque: bake-safe)
    "fabric_green": lambda n: fabric(n, (0.10, 0.15, 0.05)),
    # phase 2 additions
    "alu_dark_anodised": lambda n: metal(n, (0.16, 0.16, 0.17), (0.5, 0.5, 0.52), 0.35, 0.05, streak=BRUSH_X),  # skirting 150439
    "abs_grey": lambda n: dielectric(n, (0.30, 0.305, 0.31), 0.38, 0.05, 40.0, 0.03, (2000.0, 0.05, 0.0003), ior=1.53),
    "abs_dark": lambda n: dielectric(n, (0.05, 0.05, 0.052), 0.45, 0.05, 40.0, 0.05, (2000.0, 0.06, 0.0003), ior=1.53),
    "abs_yellow": lambda n: dielectric(n, (0.80, 0.55, 0.01), 0.35, 0.05, 40.0, 0.03, (2000.0, 0.04, 0.0003), ior=1.53),
    "abs_red": lambda n: dielectric(n, (0.60, 0.015, 0.015), 0.30, 0.05, 40.0, 0.03, (2000.0, 0.04, 0.0003), ior=1.53),
    "powder_white": lambda n: dielectric(n, (0.80, 0.80, 0.79), 0.35, 0.05, 30.0, 0.015, (300.0, 0.10, 0.0004)),
    "enamel_white": lambda n: dielectric(n, (0.78, 0.77, 0.72), 0.28, 0.05, 25.0, 0.03, (600.0, 0.08, 0.0004)),
    "paint_pink": lambda n: dielectric(n, PINK, 0.40, 0.05, 60.0, 0.04, (450.0, 0.15, 0.0004)),
}

# material name -> preset key. Missing names are skipped silently (scene may not have them yet).
REBUILD = {
    "Chair_Chrome": "chrome",
    "Cabinet_Aluminium": "alu_anodised_brushed_x",
    "Cabinet_Steel": "alu_satin_plinth",
    "Door_Steel": "stainless_brushed_leaf_y",
    "TV_Trim": "silver_plastic_lip",
    "TV_Bezel": "abs_black_satin",
    "TV_Back": "abs_black_matte",
    "Monitor_Back": "abs_black_textured",
    "Desk_Glide": "pp_black_glide",
    "Window_PVC": "pvc_white_window",
    "Window_SillBoard": "pvc_white_sill",
    "Window_Gasket": "rubber_epdm",
    "Desk_PowderCoat": "powder_anthracite",
    "Desk_Laminate": "melamine_white_grey",
    "Cabinet_Front": "laminate_black_matte",
    "Cabinet_Worktop": "laminate_dark_worktop",
    "Window_Glass": "glass_window",
    "Door_Glass": "glass_door",
    "TV_Screen": "screen_off",
    "Chair_Fabric": "fabric_black",
    # phase 2: lab (room2.py)
    "Room2_PVC_White": "pvc_white_window", "Room2_Glass": "glass_window", "Room2_Radiator_Paint": "enamel_white",
    "Room2_Laminate_Grey": "laminate_grey_bench", "Room2_Laminate_Red": "hpl_red_desktop",
    "Room2_Steel_Grey": "powder_ral7035", "Room2_Drawer_Red": "paint_red_drawer", "Room2_Aluminium": "alu_extrusion",
    "Room2_Chrome": "chrome", "Room2_Plastic_White": "abs_white", "Room2_Plastic_Grey": "abs_grey",
    "Room2_Plastic_Black": "abs_black_satin", "Room2_Plastic_Yellow": "abs_yellow", "Room2_Plastic_Red": "abs_red",
    "Room2_Fabric_Black": "fabric_black", "Room2_Door_Pink": "paint_pink", "Room2_Sofa_Green": "fabric_green",
    # trim.py
    "Trim_Skirting": "alu_dark_anodised", "Trim_PVC_White": "pvc_white_window", "Trim_Trunking": "pvc_white_window",
    "Trim_Dark": "abs_dark", "Trim_Ceiling_Grid": "powder_white", "Trim_LED_Frame": "powder_white",
    "Trim_LED_Frames": "powder_white", "Trim_Vent_Perf": "powder_white", "Trim_Vent": "powder_white",
    "Trim_Device_White": "abs_white", "Trim_Sockets": "abs_white", "Trim_Switch": "abs_white",
    "Trim_Smoke_Detector": "abs_white", "Trim_Sensor": "abs_white",
    # doorend.py / door.py
    "Doorend_Duct_PVC": "pvc_white_window", "Doorend_Duct_Corner": "pvc_white_window",
    "Doorend_Enclosure_White": "powder_white", "Doorend_PIR": "abs_white",
    "Door_Seal": "rubber_epdm", "Door_Hinges_Frame": "steel_zinc",
    # deskprops.py
    "Deskprops_PowerStrip": "abs_white", "Deskprops_WhitePlastic": "abs_white", "Deskprops_StripWhite": "abs_white",
    "Deskprops_CamBase": "abs_white", "Deskprops_Camera": "abs_white", "Deskprops_Remote": "abs_black_satin",
    "Deskprops_CableBlack": "abs_black_matte", "Deskprops_CableTV": "abs_black_matte", "Deskprops_CableWhite": "abs_white",
    # kitchen.py (Kitchen_LEDStrip / QR / QRSticker / Screen / PCB keep their own UV/image trees)
    "Kitchen_PlasticBlack": "abs_black_satin", "Kitchen_PlasticGrey": "abs_grey", "Kitchen_PlasticWhite": "abs_white",
    "Kitchen_BlackBox": "abs_black_matte", "Kitchen_LampGlass": "glass_door", "Kitchen_PoESwitch": "abs_black_textured",
    "Kitchen_CableBlack": "abs_black_matte", "Kitchen_CableWhite": "abs_white",
}

# name -> patch kwargs (geometry-coupled trees owned by materials/<part>.py)
PATCH = {
    "Chair_Shell": dict(IOR=1.49, Specular_IOR_Level=0.5),                       # PP shell; emboss panel/ribs kept
    "Monitor_Bezel": dict(bump=(3000.0, 0.01, 0.0002)),                           # UV stickers + logo kept
    "Monitor_Rim": dict(bump=(2000.0, 0.05, 0.0003)),
    "Monitor_Screen": dict(bump=(3000.0, 0.01, 0.0002), tone=0.0),                          # UV emission gradient kept
    "Cabinet_Vent": dict(Specular_Tint=STAINLESS[1]),                             # slot grid kept
    "Door_Paint": dict(IOR=1.5, Specular_IOR_Level=0.5),                          # same builder as the leaf: keep pair identical
    "Door_Paint_Leaf": dict(IOR=1.5, Specular_IOR_Level=0.5),                     # lock-edge wear kept
    "Radiator_Paint": dict(IOR=1.5, Specular_IOR_Level=0.5),                      # drips/chips kept, AO grime gated
    "Radiator_PipePaint": dict(IOR=1.5, Specular_IOR_Level=0.5),
}

done = []
for name, key in REBUILD.items():
    m0 = bpy.data.materials.get(name)
    if m0 and m0.node_tree and any(n.type in ("TEX_IMAGE", "UVMAP") for n in m0.node_tree.nodes):
        continue  # printed labels / UV-driven trees keep their own look
    if PRESETS[key](name) is not None:
        L.tidy(bpy.data.materials[name].node_tree)
        done.append(name)
for name, kw in PATCH.items():
    if patch(name, **kw) is not None:
        done.append(name + "(patch)")
print("HARD shaders:", len(done), ", ".join(done))
