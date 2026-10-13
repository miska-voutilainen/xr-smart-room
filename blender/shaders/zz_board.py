# Owner: s2_board. Real textures for the OSB smart-home demo board (Kitchen_Board, built by materials/kitchen.py).
# Runs after kitchen.py / arch.py / hard.py and replaces, BY NAME, the board-only materials + the board's UVs:
#   Kitchen_OSB         Poly Haven "oriented_strand_board" scan (CC0), one non-repeating 0.75 m window over the
#                       whole board; edges get the same scan squashed 5x across the 12 mm thickness (strand layers)
#   Kitchen_DeviceFront NEW: front faces of the Sonoff devices, printed labels = de-lit crop of photo 122216
#   Kitchen_LampBody    NEW: black PP bodies of the two bulkhead lamps (was shared Kitchen_PlasticBlack)
#   Kitchen_LampGlass   thin-walled (2 mm shell geometry) prismatic glass, real transmission
#   Kitchen_MetalCage   galvanised / chrome wire cage (+ screws, standoffs, brackets)
#   Kitchen_QRSticker   real QR codes on matte paper (atlas in kitchen.py's tile order)
#   Kitchen_Screen, Kitchen_PCB   glossy LCD glass, blue solder mask
# Mesh topology / object names / locations are untouched (tri count unchanged); only UVs + face material indices.
# Textures: textures/s2_board/ (SOURCES.txt, _make.py).
import math
import os
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _lib as L  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEX = os.path.join(ROOT, "textures", "s2_board")

# --- kitchen.py layout constants (keep in sync with materials/kitchen.py)
TOP, K, BCX, ZTOP, PX0, PY0 = 0.90, 0.00052, 0.975, 1.66, 580, 60
OSB_Y0, YF = 0.135, 0.147
ORIGIN = Vector((BCX, 0.165, TOP))
OSB_U0, OSB_V0, OSB_WIN = BCX - 0.375, 0.915, 0.75          # world x/z of the scan window, metres
DEV_WIN = (200, 120, 950, 700)                              # crop px window of device_fronts.png (_make.py)
# (px, py, w, h, front depth) of kitchen.py's label-bearing white devices
DEVICES = [(607, 228, 0.145, 0.090, 0.020), (583, 606, 0.062, 0.062, 0.020), (260, 605, 0.043, 0.043, 0.016),
           (460, 550, 0.035, 0.039, 0.022), (862, 651, 0.074, 0.031, 0.017), (862, 607, 0.043, 0.013, 0.012)]
LAMPS = [(918, 262), (268, 855)]


def P(px, py):
    return BCX - (px - PX0) * K, ZTOP - (py - PY0) * K


def image(fn, colour=True):
    path = os.path.join(TEX, fn)
    img = bpy.data.images.get("s2b_" + fn)
    if img is None:
        img = bpy.data.images.load(path)
        img.name = "s2b_" + fn
    img.filepath = path    # s2_integrate: absolute like the other scripts; '//' paths broke in hpc/submit's temp copy
    img.colorspace_settings.name = "sRGB" if colour else "Non-Color"
    return img


def tex(nt, img, uv, interp="Linear"):
    n = nt.nodes.new("ShaderNodeTexImage")
    n.image, n.interpolation = img, interp
    nt.links.new(uv, n.inputs["Vector"])
    return n


def fresh(name):
    """Rebuild (or create) a material -> (mat, nt, principled)."""
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(b.outputs[0], out.inputs["Surface"])
    return m, nt, b


# ================================================================ materials
def mat_osb():
    m, nt, b = fresh("Kitchen_OSB")
    uv = nt.nodes.new("ShaderNodeUVMap").outputs["UV"]
    col = tex(nt, image("osb_color.jpg"), uv)
    hs = nt.nodes.new("ShaderNodeHueSaturation")         # scan is a lacquered board: photo 122216 is more orange
    hs.inputs["Hue"].default_value = 0.49
    hs.inputs["Saturation"].default_value = 1.30
    hs.inputs["Value"].default_value = 0.95
    nt.links.new(col.outputs["Color"], hs.inputs["Color"])
    nt.links.new(hs.outputs["Color"], b.inputs["Base Color"])
    rough = tex(nt, image("osb_rough.jpg", False), uv)
    L.put(nt, b.inputs["Roughness"], L.maprange(nt, rough.outputs["Color"], 0.0, 1.0, 0.55, 0.90))   # raw, unsealed
    nm = nt.nodes.new("ShaderNodeNormalMap")
    nm.inputs["Strength"].default_value = 0.8
    nt.links.new(tex(nt, image("osb_normal.jpg", False), uv).outputs["Color"], nm.inputs["Color"])
    nt.links.new(nm.outputs["Normal"], b.inputs["Normal"])
    b.inputs["Specular IOR Level"].default_value = 0.4
    m.diffuse_color = (0.55, 0.36, 0.20, 1)
    return m


def plastic_bump(nt, b, scale=2500.0, strength=0.05):
    co = nt.nodes.new("ShaderNodeTexCoord").outputs["Object"]
    L.put(nt, b.inputs["Normal"], L.bump(nt, L.noise(nt, co, scale, 2.0), strength, 0.0003))
    return co


def mat_device_front():
    m, nt, b = fresh("Kitchen_DeviceFront")
    uv = nt.nodes.new("ShaderNodeUVMap").outputs["UV"]
    L.put(nt, b.inputs["Base Color"], tex(nt, image("device_fronts.png"), uv).outputs["Color"])
    co = plastic_bump(nt, b, 2000.0, 0.04)
    L.put(nt, b.inputs["Roughness"], L.maprange(nt, L.noise(nt, co, 60.0, 3.0), 0.3, 0.7, 0.30, 0.38))
    b.inputs["IOR"].default_value = 1.53
    m.diffuse_color = (0.78, 0.78, 0.77, 1)
    return m


def mat_lamp_body():
    """Black polypropylene bulkhead body: satin, faint mould orange-peel. Its front face is white only under the
    globe (object-space stadium mask, glass outer radius 44 mm), black rim outside it as in 122216."""
    m, nt, b = fresh("Kitchen_LampBody")
    co = plastic_bump(nt, b, 900.0, 0.08)
    inside = None
    for px, py in LAMPS:
        x, z = P(px, py)
        p = nt.nodes.new("ShaderNodeVectorMath")
        p.operation = "SUBTRACT"
        nt.links.new(co, p.inputs[0])
        p.inputs[1].default_value = (x - ORIGIN.x, 0.0, z - ORIGIN.z)
        a = nt.nodes.new("ShaderNodeVectorMath")
        a.operation = "ABSOLUTE"
        nt.links.new(p.outputs[0], a.inputs[0])
        q = nt.nodes.new("ShaderNodeVectorMath")       # distance to the stadium's 80 mm centre segment, in x/z
        q.operation = "SUBTRACT"
        nt.links.new(a.outputs[0], q.inputs[0])
        q.inputs[1].default_value = (0.0, 1.0, 0.040)
        mx = nt.nodes.new("ShaderNodeVectorMath")
        mx.operation = "MAXIMUM"
        nt.links.new(q.outputs[0], mx.inputs[0])
        ln = nt.nodes.new("ShaderNodeVectorMath")
        ln.operation = "LENGTH"
        nt.links.new(mx.outputs[0], ln.inputs[0])
        f = L.math(nt, "LESS_THAN", ln.outputs["Value"], 0.0445)
        inside = f if inside is None else L.math(nt, "MAXIMUM", inside, f)
    L.put(nt, b.inputs["Base Color"], L.mix_col(nt, inside, (0.012, 0.012, 0.013), (0.62, 0.63, 0.62)))
    L.put(nt, b.inputs["Roughness"], L.maprange(nt, L.noise(nt, co, 25.0, 3.0), 0.3, 0.7, 0.28, 0.40))
    b.inputs["IOR"].default_value = 1.49
    m.diffuse_color = (0.012, 0.012, 0.013, 1)
    return m


def mat_glass():
    """Clear soda-lime glass with moulded prismatic ribs (horizontal bands, ~3 mm pitch) as in 122216."""
    m, nt, b = fresh("Kitchen_LampGlass")
    b.inputs["Base Color"].default_value = (1, 1, 1, 1)
    b.inputs["Transmission Weight"].default_value = 1.0
    b.inputs["IOR"].default_value = 1.52
    co = nt.nodes.new("ShaderNodeTexCoord").outputs["Object"]
    wv = nt.nodes.new("ShaderNodeTexWave")
    wv.bands_direction, wv.wave_profile = "Z", "SIN"
    wv.inputs["Scale"].default_value = 100.0
    nt.links.new(co, wv.inputs["Vector"])
    L.put(nt, b.inputs["Normal"], L.bump(nt, wv.outputs["Fac"], 0.10, 0.0008))
    L.put(nt, b.inputs["Roughness"], L.maprange(nt, L.noise(nt, co, 80.0, 2.0), 0.3, 0.7, 0.02, 0.06))
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")     # shadow rays pass (no caustics): lit bulb + reflector
    tr.inputs["Color"].default_value = (0.94, 0.95, 0.95, 1)
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(nt.nodes.new("ShaderNodeLightPath").outputs["Is Shadow Ray"], mix.inputs[0])
    nt.links.new(b.outputs[0], mix.inputs[1])
    nt.links.new(tr.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL").inputs["Surface"])
    m.diffuse_color = (0.9, 0.92, 0.93, 0.3)
    return m


def mat_cage():
    """Bright zinc-plated / chromed steel wire (photo: silver cage, white highlights)."""
    m, nt, b = fresh("Kitchen_MetalCage")
    b.inputs["Base Color"].default_value = (0.80, 0.82, 0.83, 1)
    b.inputs["Metallic"].default_value = 1.0
    b.inputs["Specular Tint"].default_value = (0.90, 0.95, 0.96, 1)
    co = nt.nodes.new("ShaderNodeTexCoord").outputs["Object"]
    L.put(nt, b.inputs["Roughness"], L.maprange(nt, L.noise(nt, co, 400.0, 3.0), 0.3, 0.7, 0.12, 0.26))
    m.diffuse_color = (0.80, 0.82, 0.83, 1)
    return m


def mat_qr():
    """Printed QR label on matte paper: fibre bump, ink slightly glossier than the paper."""
    m, nt, b = fresh("Kitchen_QRSticker")
    uv = nt.nodes.new("ShaderNodeUVMap").outputs["UV"]
    t = tex(nt, image("qr_atlas.png"), uv)
    co = nt.nodes.new("ShaderNodeTexCoord").outputs["Object"]
    fib = L.noise(nt, L.scale_vec(nt, co, (1.0, 1.0, 1.0)), 3000.0, 4.0, 0.7)
    L.put(nt, b.inputs["Base Color"], L.mix_col(nt, L.maprange(nt, fib, 0.3, 0.7, 0.0, 0.06),
                                               t.outputs["Color"], (0.70, 0.70, 0.66)))
    bw = nt.nodes.new("ShaderNodeRGBToBW")
    nt.links.new(t.outputs["Color"], bw.inputs["Color"])
    L.put(nt, b.inputs["Roughness"], L.maprange(nt, bw.outputs["Val"], 0.05, 0.6, 0.45, 0.72))
    L.put(nt, b.inputs["Normal"], L.bump(nt, fib, 0.06, 0.0002))
    b.inputs["Sheen Weight"].default_value = 0.2
    b.inputs["Specular IOR Level"].default_value = 0.4
    m.diffuse_color = (0.85, 0.85, 0.82, 1)
    return m


def mat_screen():
    m, nt, b = fresh("Kitchen_Screen")                    # panel off: near-black, glossy cover glass
    b.inputs["Base Color"].default_value = (0.006, 0.007, 0.008, 1)
    b.inputs["Roughness"].default_value = 0.25           # matte polariser under the glass
    b.inputs["Coat Weight"].default_value = 1.0
    b.inputs["Coat Roughness"].default_value = 0.02
    b.inputs["Coat IOR"].default_value = 1.52
    m.diffuse_color = (0.01, 0.01, 0.012, 1)
    return m


def mat_pcb():
    m, nt, b = fresh("Kitchen_PCB")                       # Waveshare blue solder mask over copper
    co = nt.nodes.new("ShaderNodeTexCoord").outputs["Object"]
    L.put(nt, b.inputs["Base Color"], L.mix_col(nt, L.maprange(nt, L.noise(nt, co, 300.0, 3.0), 0.35, 0.65, 0.0, 1.0),
                                               (0.010, 0.070, 0.260), (0.020, 0.110, 0.360)))
    b.inputs["Roughness"].default_value = 0.22
    b.inputs["Coat Weight"].default_value = 0.4
    b.inputs["Coat Roughness"].default_value = 0.1
    m.diffuse_color = (0.02, 0.10, 0.33, 1)
    return m


for f in (mat_osb, mat_device_front, mat_lamp_body, mat_glass, mat_cage, mat_qr, mat_screen, mat_pcb):
    L.tidy(f().node_tree)


# ================================================================ board UVs + face materials
ob = bpy.data.objects.get("Kitchen_Board")
if ob is not None:
    me = ob.data
    names = [s.material.name if s.material else "" for s in ob.material_slots]
    for nm in ("Kitchen_DeviceFront", "Kitchen_LampBody"):
        if nm not in names:
            me.materials.append(bpy.data.materials[nm])
            names.append(nm)
    i_osb, i_wh, i_bk = names.index("Kitchen_OSB"), names.index("Kitchen_PlasticWhite"), names.index("Kitchen_PlasticBlack")
    i_dev, i_lamp = names.index("Kitchen_DeviceFront"), names.index("Kitchen_LampBody")
    uvd = me.uv_layers["UVMap"].data
    V = [ORIGIN + v.co for v in me.vertices]                # world coords (object is unrotated, unscaled)

    def dev_uv(w):
        px, py = PX0 + (BCX - w.x) / K, PY0 + (ZTOP - w.z) / K
        x0, y0, x1, y1 = DEV_WIN
        return (px - x0) / (x1 - x0), 1.0 - (py - y0) / (y1 - y0)

    rects = []
    for px, py, w, h, d in DEVICES:
        cx, cz = P(px, py)
        rects.append((cx, cz, w / 2 + 0.001, h / 2 + 0.001, YF + d - 0.0025))
    lamp_c = [P(*p) for p in LAMPS]
    n_dev = n_lamp = 0
    for poly in me.polygons:
        c = ORIGIN + poly.center
        n = poly.normal
        loops = range(poly.loop_start, poly.loop_start + poly.loop_total)
        if poly.material_index == i_osb:
            for li in loops:
                w = V[me.loops[li].vertex_index]
                if abs(n.y) > 0.5:       # faces: one window of the scan
                    uv = ((w.x - OSB_U0) / OSB_WIN, (w.z - OSB_V0) / OSB_WIN)
                elif abs(n.x) > 0.5:     # side edges: along z, thickness squashed 5x -> layered strands
                    uv = ((w.z - OSB_V0) / OSB_WIN, 0.20 + (w.y - OSB_Y0) * 5 / OSB_WIN)
                else:                    # top / bottom edge
                    uv = ((w.x - OSB_U0) / OSB_WIN, 0.62 + (w.y - OSB_Y0) * 5 / OSB_WIN)
                uvd[li].uv = uv
        elif (poly.material_index in (i_wh, i_lamp) and n.y > 0.95 and abs(c.y - (YF + 0.032)) < 0.002
              and any(abs(c.x - lx) < 0.06 and abs(c.z - lz) < 0.10 for lx, lz in lamp_c)):
            poly.material_index = i_lamp                   # base's front face (reflector under the globe)
            n_lamp += 1
        elif poly.material_index in (i_wh, i_dev) and n.y > 0.95:
            for cx, cz, hw, hh, ymin in rects:
                if abs(c.x - cx) < hw and abs(c.z - cz) < hh and c.y > ymin:
                    poly.material_index = i_dev
                    for li in loops:
                        uvd[li].uv = dev_uv(V[me.loops[li].vertex_index])
                    n_dev += 1
                    break
        elif poly.material_index in (i_bk, i_lamp):
            # lamp base (stadium 110 x 190 mm + ears), up to 33 mm off the board
            if any(abs(c.x - lx) < 0.085 and abs(c.z - lz) < 0.10 for lx, lz in lamp_c) and c.y < YF + 0.034:
                poly.material_index = i_lamp
                n_lamp += 1
    me.update()
    tris = sum(len(p.vertices) - 2 for p in me.polygons)
    print(f"ZZ_BOARD Kitchen_Board: {tris} tris, {n_dev} device-front faces, {n_lamp} lamp-body faces")
