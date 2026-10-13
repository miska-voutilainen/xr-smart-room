# Architectural + exterior procedural material library (g2_shaders_arch).
# Runs after materials/*.py (apply_materials.py) and REBUILDS the node trees of existing
# materials matched BY NAME (RULES below). Never creates materials or objects, never touches geometry.
# Physically based albedos (linear), real-world scale in metres via Object coords
# (objects here keep origins at 0 with world-space verts, so Object coords = metres).
# Bake-friendly: no view-dependent nodes in Base Color; AO dirt only via AO_DIRT (0 = off for baking).
import math
import os
import re

import bpy

AO_DIRT = 1.0            # 0.0 disables the AO contact-dirt term everywhere (use 0 when baking for Unity)
CEILING_PROC_GRID = False  # painted T-grid + LED cells in the shader; off: Trim_Ceiling_Grid geometry exists
CELL, GX0, GY0 = 0.60, 0.25, 0.35      # ceiling grid, from materials/room.py
LED_CELLS = (4, 7)


# ---------- node helpers ----------

class G:
    """Tiny node-graph builder. n(kind, *positional_inputs, i={name_or_index: value}, **node_props)."""

    def __init__(self, nt):
        self.nt, self.k = nt, 0

    def n(self, kind, *ins, i=None, **props):
        node = self.nt.nodes.new("ShaderNode" + kind)
        self.k += 1
        node.location = (self.k * 40 % 2400 - 1600, -(self.k // 60) * 300)
        for key, v in props.items():
            setattr(node, key, v)
        for idx, v in list(enumerate(ins)) + list((i or {}).items()):
            if v is not None:
                self.put(node.inputs[idx], v)
        return node

    def put(self, sock, v):
        if isinstance(v, bpy.types.NodeSocket):
            self.nt.links.new(v, sock)
        else:
            sock.default_value = v

    def math(self, op, a, b=0.0, c=0.0, clamp=False):
        return self.n("Math", a, b, c, operation=op, use_clamp=clamp).outputs[0]

    def vmath(self, op, a, b=(0, 0, 0)):
        return self.n("VectorMath", a, b, operation=op).outputs[0]

    def fmix(self, fac, a, b):
        return self.n("Mix", fac, None, a, b, data_type='FLOAT').outputs[0]

    def mix(self, fac, a, b, blend='MIX'):
        m = self.n("Mix", data_type='RGBA', blend_type=blend)
        self.put(m.inputs[0], fac)
        self.put(m.inputs[6], a if isinstance(a, bpy.types.NodeSocket) or len(a) == 4 else (*a, 1))
        self.put(m.inputs[7], b if isinstance(b, bpy.types.NodeSocket) or len(b) == 4 else (*b, 1))
        return m.outputs[2]

    def ramp(self, fac, stops, interp='LINEAR'):
        r = self.n("ValToRGB")
        self.put(r.inputs[0], fac)
        cr = r.color_ramp
        cr.interpolation = interp
        while len(cr.elements) > 1:
            cr.elements.remove(cr.elements[-1])
        for k, (p, c) in enumerate(stops):
            e = cr.elements[0] if k == 0 else cr.elements.new(p)
            e.position = p
            e.color = (*c, 1) if len(c) == 3 else c
        return r.outputs[0]

    def noise(self, vec, scale, detail=2.0, rough=0.5, distortion=0.0, out=0):
        return self.n("TexNoise", vec, i={"Scale": scale, "Detail": detail, "Roughness": rough,
                                          "Distortion": distortion}).outputs[out]

    def voronoi(self, vec, scale, feature='F1', randomness=1.0):
        return self.n("TexVoronoi", vec, i={"Scale": scale, "Randomness": randomness}, feature=feature)

    def maprange(self, v, a, b, c, d, clamp=True):
        return self.n("MapRange", v, a, b, c, d, clamp=clamp).outputs[0]

    def bump(self, height, strength=1.0, normal=None):
        return self.n("Bump", i={"Strength": strength, "Distance": 1.0, "Height": height,
                                 "Normal": normal}).outputs[0]     # height in metres

    def scale_vec(self, vec, s):
        return self.vmath('MULTIPLY', vec, s)


TEX = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "textures")


def image(g, rel, vec, scale, rot=0.0, off=(0.0, 0.0, 0.0)):
    """Greyscale Non-Color map from textures/<rel>, tiled every `scale` metres of Object coords (planar xy)."""
    img = bpy.data.images.load(os.path.join(TEX, rel), check_existing=True)
    img.colorspace_settings.name = 'Non-Color'
    mp = g.n("Mapping", vec, i={"Location": off, "Rotation": (0.0, 0.0, rot), "Scale": (1 / scale,) * 3})
    t = g.n("TexImage", mp.outputs[0], interpolation='Linear', extension='REPEAT')
    t.image = img
    return t.outputs["Color"]


def reset(m):
    m.use_nodes = True
    m.node_tree.nodes.clear()
    return G(m.node_tree)


def coords(g):
    return g.n("TexCoord").outputs["Object"]


def dirt(g, color, dist=0.15, amount=0.18):
    """Multiply colour by AO contact dirt; switch off globally with AO_DIRT = 0."""
    if AO_DIRT <= 0:
        return color
    ao = g.n("AmbientOcclusion", i={"Distance": dist}, samples=8).outputs["AO"]
    k = g.math('MULTIPLY_ADD', g.math('SUBTRACT', 1.0, ao), -amount * AO_DIRT, 1.0)
    return g.mix(1.0, color, g.n("CombineColor", k, k, k).outputs[0], 'MULTIPLY')


def out(g, m, color, rough, normal=None, shader=None, **extra):
    b = g.n("BsdfPrincipled")
    g.put(b.inputs["Base Color"], color)
    g.put(b.inputs["Roughness"], rough)
    if normal is not None:
        g.put(b.inputs["Normal"], normal)
    for k, v in extra.items():
        g.put(b.inputs[k.replace("_", " ")], v)
    o = g.n("OutputMaterial")
    g.nt.links.new((shader(b) if shader else b.outputs[0]), o.inputs[0])
    if not isinstance(color, bpy.types.NodeSocket):
        m.diffuse_color = (*color[:3], 1)
    return b


def users_of(m):
    return [o for o in bpy.data.objects if o.type == 'MESH' and any(s.material == m for s in o.material_slots)]


def long_axis(m):
    """0 = x, 1 = y, 2 = z: the longest world extent of the objects using m (wood grain direction)."""
    ext = [0.0, 0.0, 0.0]
    for o in users_of(m):
        for a in range(3):
            ext[a] = max(ext[a], o.dimensions[a] * 1.0)
    return max(range(3), key=lambda a: ext[a])


def stretch(g, co, axis, along, across):
    """Scale coords so features become long along `axis` (along < across)."""
    s = [across] * 3
    s[axis] = along
    return g.scale_vec(co, tuple(s))


# ---------- interior ----------

def plaster_paint(m, base=(0.775, 0.765, 0.735)):
    """Matt emulsion on plaster, roller stipple. LRV ~0.78 typical off-white. No skirting mask:
    real skirting geometry comes from materials/trim.py."""
    g = reset(m)
    co = coords(g)
    stip = g.noise(co, 260.0, 4.0, 0.6)
    blot = g.noise(co, 1.6, 3.0, 0.55)
    lo = tuple(c * 0.975 for c in base)
    hi = tuple(min(1.0, c * 1.025) for c in base)
    color = dirt(g, g.ramp(blot, [(0.3, lo), (0.7, hi)]), 0.25, 0.12)
    # matt emulsion (60 deg gloss < 5 GU): R ~0.85-0.95; vertical roller laps (~23 cm wide strokes, long in z)
    # and a finer 1-2 mm nap stipple shift roughness a little so grazing light shows a faint uneven sheen.
    lap = g.noise(g.scale_vec(co, (4.5, 4.5, 0.35)), 1.0, 2.0, 0.5)
    nap = g.noise(co, 900.0, 2.0, 0.6)
    rough = g.math('MULTIPLY_ADD', stip, 0.08, g.maprange(lap, 0.3, 0.7, 0.84, 0.92))
    rough = g.math('MULTIPLY_ADD', nap, 0.04, rough)
    hgt = g.math('MULTIPLY_ADD', stip, 0.00035, g.math('MULTIPLY', nap, 0.00008))
    out(g, m, color, rough, g.bump(hgt))
    m.diffuse_color = (*base, 1)


def ceppo_floor(m):
    """Ceppo-di-Gre look rectified matt porcelain, 600x1200 mm, ~2 mm joints, long side along x.
    Grey cloudy matrix, angular chips in three size bands + grit, per-tile print offset."""
    g = reset(m)
    co = coords(g)
    # tiles: joint mask only
    br = g.n("TexBrick", co, (0, 0, 0, 1), (1, 1, 1, 1), (0, 0, 0, 1),
             i={"Scale": 1.0, "Mortar Size": 0.0012, "Mortar Smooth": 0.6, "Bias": 0.0,
                "Brick Width": 1.2, "Row Height": 0.6}, offset=0.5, offset_frequency=2)
    joint = br.outputs["Fac"]
    # s3_polish: one continuous print across tiles (photo 122209 reads as a monolithic terrazzo; per-tile
    # print offset + tone made a checkerboard).
    tc = co
    warp = g.n("TexNoise", tc, i={"Scale": 30.0, "Detail": 2.0}).outputs["Color"]
    tw = g.vmath('ADD', tc, g.vmath('MULTIPLY', g.vmath('SUBTRACT', warp, (0.5, 0.5, 0.5)), (0.012, 0.012, 0.0)))

    # matrix: mid grey cement with soft cloudy patches + fine sand
    cloud = g.noise(tc, 4.0, 4.0, 0.6)
    sand = g.noise(tc, 700.0, 2.0, 0.6)
    mat_col = g.ramp(g.math('MULTIPLY_ADD', cloud, 0.85, g.math('MULTIPLY', sand, 0.15)),
                     [(0.30, (0.258, 0.245, 0.228)), (0.52, (0.318, 0.303, 0.283)), (0.72, (0.358, 0.343, 0.322))])
    color = mat_col

    # soft "ghost" stones (printed, blurred edges) 6-12 cm, low contrast
    gv = g.voronoi(tw, 9.0, 'DISTANCE_TO_EDGE').outputs["Distance"]
    gc = g.n("SeparateColor", g.voronoi(tw, 9.0, 'F1').outputs["Color"]).outputs
    ghost = g.math('MULTIPLY', g.math('GREATER_THAN', gc[0], 0.72), g.maprange(gv, 0.05, 0.25, 0.0, 1.0))
    color = g.mix(g.math('MULTIPLY', ghost, 0.68), color,                      # 150439: big grey stones read clearly
                  g.ramp(gc[1], [(0.0, (0.17, 0.168, 0.165)), (0.5, (0.24, 0.235, 0.228)), (1.0, (0.40, 0.395, 0.38))]))

    palette = [(0.00, (0.47, 0.46, 0.44)),    # near-white limestone (rarer: 150439 close-up, s2_reflect)
               (0.08, (0.40, 0.392, 0.378)),  # light grey
               (0.25, (0.35, 0.342, 0.33)),   # grey close to the matrix
               (0.42, (0.24, 0.235, 0.228)),  # mid grey     } 122209: many mid/dark grey stones
               (0.65, (0.15, 0.148, 0.145)),  # dark grey    }
               (0.86, (0.085, 0.084, 0.086)),  # charcoal
               (0.97, (0.30, 0.26, 0.22))]    # rare warm brown
    taken = None

    def chips(scale, keep, edge0, edge1, opacity):
        """Sub-angular pebbles: voronoi cell inset (angular) AND warped disc (rounds the corners).
        Present where cell random < keep; inset jittered per cell -> size spread. Smaller bands
        never print over bigger stones (a stone is one stone)."""
        nonlocal color, taken
        f1 = g.voronoi(tw, scale, 'F1')
        de = g.voronoi(tw, scale, 'DISTANCE_TO_EDGE').outputs["Distance"]
        r = g.n("SeparateColor", f1.outputs["Color"]).outputs
        thr = g.math('MULTIPLY_ADD', r[2], edge1 - edge0, edge0)
        rad = g.math('MULTIPLY_ADD', r[2], -0.15, 0.62)   # wide disc: only clips the sharpest corners
        soft = g.math('MULTIPLY', g.maprange(g.math('SUBTRACT', de, thr), 0.0, 0.035, 0.0, 1.0),
                      g.maprange(g.math('SUBTRACT', rad, f1.outputs["Distance"]), 0.0, 0.05, 0.0, 1.0))
        shape = soft                                   # slightly soft edge, like the printed stones
        mask = g.math('MULTIPLY', g.math('LESS_THAN', r[0], keep), shape)
        if taken is not None:
            mask = g.math('MULTIPLY', mask, g.math('SUBTRACT', 1.0, taken))
        taken = mask if taken is None else g.math('MAXIMUM', taken, mask)
        stone = g.ramp(r[1], palette, 'CONSTANT')
        vein = g.maprange(g.noise(tw, scale * 6.0, 3.0, 0.6), 0.3, 0.7, 0.9, 1.1)   # texture inside a stone
        stone = g.mix(1.0, stone, g.n("CombineColor", vein, vein, vein).outputs[0], 'MULTIPLY')
        color = g.mix(g.math('MULTIPLY', mask, opacity), color, stone)
        return mask

    big = chips(14.0, 0.30, 0.08, 0.22, 0.92)     # 3-6 cm
    med = chips(30.0, 0.50, 0.06, 0.20, 0.90)     # 1.5-3 cm aggregate, dense (122209)
    chips(90.0, 0.50, 0.06, 0.18, 0.75)           # 4-10 mm
    chips(350.0, 0.30, 0.08, 0.18, 0.25)          # 1-2 mm grit, barely visible

    # s2_reflect: floor/wall luminance in photo 122209 = 0.51, render was 0.70 (0.62 after a first x0.74 step)
    # -> overall x0.60 of the old palette, a touch warmer (photo floor r/g 1.13, b/g 0.83)
    color = g.mix(1.0, color, (0.63, 0.60, 0.565), 'MULTIPLY')
    color = g.mix(g.math('MULTIPLY', joint, 0.25), color, (0.17, 0.162, 0.152))  # grout: thin, matrix-coloured
    color = dirt(g, color, 0.2, 0.15)
    # Lappato (semi-polished) porcelain + maintenance wax (s2_reflect). Lappato = irregular grinding of the glaze:
    # a mix of polished highs and matt lows, so window/LED reflections are soft and broken, never a mirror.
    # Two lobes: base = matt-ish glaze micro-relief (R ~0.4, specular cut to ~3 %), coat = polished/waxed film
    # (IOR 1.5, weight 0.33-0.58, R 0.11-0.28) whose weight and roughness follow a scanned mop/wipe haze map (ambientCG
    # SurfaceImperfections008, CC0), two tilings rotated against each other so no repeat reads.
    w1 = image(g, "s2_reflect/floor_wipe_SurfaceImperfections008.jpg", co, 1.7, 0.0)
    w2 = image(g, "s2_reflect/floor_wipe_SurfaceImperfections008.jpg", co, 2.9, 1.1, (0.37, 0.71, 0.0))
    haze = g.maprange(g.math('MULTIPLY_ADD', w1, 0.6, g.math('MULTIPLY', w2, 0.4)), 0.24, 0.48, 0.0, 1.0)
    traffic = g.maprange(g.noise(co, 0.45, 2.0, 0.5), 0.35, 0.65, 0.0, 0.35)   # broad walked/dull zones
    haze = g.math('ADD', haze, traffic, clamp=True)
    stone = g.math('MAXIMUM', big, med)
    rn = g.noise(co, 9.0, 3.0, 0.6)
    rough = g.math('MULTIPLY_ADD', rn, 0.08, g.math('MULTIPLY_ADD', haze, 0.10, 0.38))
    rough = g.math('SUBTRACT', rough, g.math('MULTIPLY', stone, 0.06))     # stones take the polish better
    rough = g.fmix(g.math('MULTIPLY', joint, 0.3), rough, 0.6)   # s3_polish: no grid in the gloss
    c_rough = g.math('MULTIPLY_ADD', haze, 0.17, 0.11)
    c_rough = g.math('SUBTRACT', c_rough, g.math('MULTIPLY', stone, 0.03))
    c_w = g.math('MULTIPLY', g.math('MULTIPLY_ADD', haze, -0.25, 0.58), g.math('MULTIPLY_ADD', joint, -0.3, 1.0))
    hgt = g.math('ADD', g.math('MULTIPLY', joint, -0.00015), g.math('MULTIPLY', sand, 0.00004))
    nrm = g.bump(hgt)
    out(g, m, color, rough, nrm, Specular_IOR_Level=0.35, Coat_Weight=c_w, Coat_Roughness=c_rough,
        Coat_IOR=1.5, Coat_Normal=g.bump(g.math('MULTIPLY', joint, -0.00015)))
    m.diffuse_color = (0.30, 0.29, 0.28, 1)


def ceiling_tiles(m):
    """600x600 smooth-faced painted stone-wool tiles (LR 0.85, e.g. Rockfon Artic), square edge.
    Photo 150430: plain fine-felt surface, no fissures. Optional painted T-grid (CEILING_PROC_GRID)."""
    g = reset(m)
    co = coords(g)
    sep = g.n("SeparateXYZ", co).outputs
    felt = g.noise(co, 900.0, 2.0, 0.6)
    drift = g.noise(co, 0.8, 2.0, 0.5)
    color = g.ramp(g.math('MULTIPLY_ADD', felt, 0.3, g.math('MULTIPLY', drift, 0.7)),
                   [(0.3, (0.815, 0.815, 0.805)), (0.7, (0.845, 0.845, 0.835))])
    rough = 0.95
    hgt = g.math('MULTIPLY', felt, 0.00012)
    if CEILING_PROC_GRID:
        def axis(v, origin):
            u = g.math('DIVIDE', g.math('SUBTRACT', v, origin), CELL)
            f = g.math('FRACT', u)
            return g.math('MULTIPLY', g.math('MINIMUM', f, g.math('SUBTRACT', 1.0, f)), CELL), g.math('FLOOR', u)
        dx, kx = axis(sep[0], GX0)
        dy, ky = axis(sep[1], GY0)
        d = g.math('MINIMUM', dx, dy)
        tbar = g.math('LESS_THAN', d, 0.012)        # 24 mm T flange
        lip = g.math('LESS_THAN', d, 0.015)
        led = g.math('MULTIPLY', g.math('COMPARE', ky, 1.0, 0.5),
                     g.math('MAXIMUM', *[g.math('COMPARE', kx, float(k), 0.5) for k in LED_CELLS]))
        color = g.mix(tbar, color, (0.86, 0.86, 0.85))
        color = g.mix(g.math('MULTIPLY', led, g.math('SUBTRACT', 1.0, tbar)), color, (0.88, 0.88, 0.88))
        rough = g.fmix(tbar, 0.95, 0.4)
        hgt = g.math('ADD', g.math('MULTIPLY', lip, 0.004), g.math('MULTIPLY', g.math('SUBTRACT', 1.0, lip), hgt))
    color = dirt(g, color, 0.2, 0.10)
    out(g, m, color, rough, g.bump(hgt))
    m.diffuse_color = (0.83, 0.83, 0.82, 1)


def vinyl_skirting(m):
    """Dark grey satin PVC/vinyl skirting (150354, 150439): not black, fine calendered texture."""
    g = reset(m)
    co = coords(g)
    fine = g.noise(co, 1500.0, 2.0, 0.5)
    mott = g.noise(co, 8.0, 2.0, 0.5)
    color = g.ramp(mott, [(0.3, (0.046, 0.046, 0.048)), (0.7, (0.054, 0.054, 0.056))])
    color = dirt(g, color, 0.05, 0.25)
    out(g, m, color, g.math('MULTIPLY_ADD', fine, 0.08, 0.40), g.bump(g.math('MULTIPLY', fine, 0.00003)),
        Specular_IOR_Level=0.5)
    m.diffuse_color = (0.05, 0.05, 0.052, 1)


def osb(m):
    """OSB/3: strands ~75-100 mm x 15-30 mm, face strands along the panel length, light resin sheen.
    Photo 150448: orange-tan, wide tone spread with dark brown bits."""
    g = reset(m)
    co = coords(g)
    ax = long_axis(m)
    warp = g.n("TexNoise", co, i={"Scale": 12.0, "Detail": 2.0}).outputs["Color"]
    cw = g.vmath('ADD', co, g.vmath('MULTIPLY', g.vmath('SUBTRACT', warp, (0.5, 0.5, 0.5)), (0.02, 0.02, 0.02)))
    color = None
    hgt = 0.0
    for k, (sc, along) in enumerate(((40.0, 0.22), (55.0, 0.25), (70.0, 0.3))):
        # strands: stretched voronoi cells, each with its own tone; rotate layers slightly via axis mix
        v = stretch(g, cw, ax, along, 1.0)
        if k == 1:
            v = g.vmath('ADD', v, (7.3, 1.1, 3.7))
        cell = g.voronoi(v, sc, 'F1')
        r = g.n("SeparateColor", cell.outputs["Color"]).outputs
        edge = g.voronoi(v, sc, 'DISTANCE_TO_EDGE').outputs["Distance"]
        tone = g.ramp(r[0], [(0.0, (0.30, 0.16, 0.055)), (0.35, (0.52, 0.30, 0.11)), (0.7, (0.66, 0.42, 0.17)),
                             (0.93, (0.72, 0.50, 0.24)), (0.97, (0.16, 0.09, 0.04))])
        if color is None:
            color = tone
        else:
            color = g.mix(g.math('GREATER_THAN', r[2], 0.45), color, tone)
        hgt = g.math('ADD', hgt, g.math('MULTIPLY', g.math('LESS_THAN', edge, 0.04), -0.0004))
    grain = g.noise(stretch(g, co, ax, 30.0, 600.0), 1.0, 3.0, 0.6)
    color = g.mix(g.math('MULTIPLY', grain, 0.25), color, (0.25, 0.13, 0.05), 'MULTIPLY')
    color = g.mix(g.math('MULTIPLY', grain, 0.2), color, (0.25, 0.13, 0.05))
    color = dirt(g, color, 0.08, 0.15)
    rough = g.math('MULTIPLY_ADD', grain, 0.15, 0.58)
    out(g, m, color, rough, g.bump(g.math('ADD', hgt, g.math('MULTIPLY', grain, 0.0002))))
    m.diffuse_color = (0.55, 0.33, 0.13, 1)


def cardboard(m):
    """Brown corrugated board: physicallybased.info Cardboard (0.351, 0.208, 0.110), faint flute ridges."""
    g = reset(m)
    co = coords(g)
    fib = g.noise(co, 300.0, 4.0, 0.6)
    blot = g.noise(co, 6.0, 3.0, 0.5)
    color = g.ramp(g.math('MULTIPLY_ADD', blot, 0.7, g.math('MULTIPLY', fib, 0.3)),
                   [(0.3, (0.31, 0.18, 0.093)), (0.7, (0.39, 0.235, 0.125))])
    flute = g.n("TexWave", co, i={"Scale": 39.8}, bands_direction='Z',
                wave_profile='SIN').outputs["Fac"]                       # wave period = 0.314/Scale m -> ~8 mm (C flute), horizontal
    color = dirt(g, color, 0.1, 0.2)
    out(g, m, color, g.math('MULTIPLY_ADD', fib, 0.1, 0.82),
        g.bump(g.math('ADD', g.math('MULTIPLY', flute, 0.00012), g.math('MULTIPLY', fib, 0.00005))))
    m.diffuse_color = (0.351, 0.208, 0.110, 1)


def paper(m):
    """Office paper: physicallybased.info Office Paper (0.794, 0.834, 0.884), fibre bump, matt."""
    g = reset(m)
    co = coords(g)
    fib = g.noise(co, 2000.0, 3.0, 0.6)
    color = g.ramp(fib, [(0.3, (0.78, 0.82, 0.87)), (0.7, (0.80, 0.84, 0.89))])
    out(g, m, color, g.math('MULTIPLY_ADD', fib, 0.1, 0.65), g.bump(g.math('MULTIPLY', fib, 0.00002)))
    m.diffuse_color = (0.794, 0.834, 0.884, 1)


def wood(m, light=(0.56, 0.33, 0.15), dark=(0.36, 0.19, 0.075), rough=0.42, coat=0.25, worn=0.0):
    """Generic plank: grain (wave rings along the longest axis), pores, optional worn/rough stain."""
    g = reset(m)
    co = coords(g)
    ax = long_axis(m)
    v = stretch(g, co, ax, 0.06, 1.0)
    rings = g.n("TexWave", v, i={"Scale": 60.0, "Distortion": 6.0, "Detail": 3.0},
                bands_direction='Y' if ax == 0 else 'X').outputs["Fac"]                 # bands across the grain
    pores = g.noise(stretch(g, co, ax, 20.0, 900.0), 1.0, 2.0, 0.5)
    blot = g.noise(co, 5.0, 3.0, 0.6)
    f = g.math('MULTIPLY_ADD', rings, 0.6, g.math('MULTIPLY', pores, 0.4))
    color = g.ramp(f, [(0.2, dark), (0.8, light)])
    if worn:
        color = g.mix(g.math('MULTIPLY', blot, worn), color, tuple(c * 0.55 for c in dark))
    color = dirt(g, color, 0.06, 0.2)
    r = g.maprange(pores, 0.3, 0.7, rough - 0.06, rough + 0.1)
    out(g, m, color, r, g.bump(g.math('ADD', g.math('MULTIPLY', rings, 0.0002), g.math('MULTIPLY', pores, 0.0001))),
        Coat_Weight=coat, Coat_Roughness=0.3)
    m.diffuse_color = (*light, 1)


def oak_threshold(m):
    wood(m)


def stained_plank(m):
    """Demo-board base (150448): dark walnut-stained rough sawn plank, worn edges."""
    wood(m, light=(0.20, 0.10, 0.05), dark=(0.085, 0.045, 0.025), rough=0.6, coat=0.0, worn=0.5)


BLIND_TRANSMIT = 0.15   # screen/dim-out fabric openness+diffuse transmittance (10-20 %)


def blind_fabric(m):
    """Lab roller blinds (Photos/3 151033): mid-light grey polyester screen fabric, ~1 mm weave.
    ~15 % of light passes: diffuse Translucent for camera/indirect rays, and shadow rays see the blind
    BLIND_TRANSMIT transparent so direct daylight reaches the lab (request from g2_light).
    Light Path is in the shader mix only, never in Base Color (bake-safe; Cycles-only effect)."""
    g = reset(m)
    co = coords(g)
    warp_ = g.n("TexWave", co, i={"Scale": 314.0}, bands_direction='X', wave_profile='SIN').outputs["Fac"]
    weft = g.n("TexWave", co, i={"Scale": 314.0}, bands_direction='Z', wave_profile='SIN').outputs["Fac"]
    weave = g.math('MULTIPLY', warp_, weft)
    color = g.ramp(g.noise(co, 3.0, 2.0, 0.5), [(0.3, (0.44, 0.445, 0.435)), (0.7, (0.47, 0.475, 0.465))])

    def shader(b):
        tr = g.n("BsdfTranslucent", color)
        surf = g.n("MixShader", BLIND_TRANSMIT, b.outputs[0], tr.outputs[0]).outputs[0]
        shadow = g.math('MULTIPLY', g.n("LightPath").outputs["Is Shadow Ray"], BLIND_TRANSMIT)
        return g.n("MixShader", shadow, surf, g.n("BsdfTransparent").outputs[0]).outputs[0]
    out(g, m, color, 0.85, g.bump(g.math('MULTIPLY', weave, 0.0002)), shader=shader)
    m.diffuse_color = (0.455, 0.46, 0.45, 1)


def ac_cassette(m):
    """Ceiling AC cassette fascia (Photos/3 151124): white ABS, satin, fine moulded texture."""
    g = reset(m)
    co = coords(g)
    fine = g.noise(co, 2500.0, 2.0, 0.5)
    color = dirt(g, (0.80, 0.80, 0.785, 1), 0.05, 0.2)
    out(g, m, color, g.math('MULTIPLY_ADD', fine, 0.08, 0.36), g.bump(g.math('MULTIPLY', fine, 0.00002)))
    m.diffuse_color = (0.80, 0.80, 0.785, 1)


# ---------- exterior (wet: 2026-10-12, light rain) ----------
# Wet rule (Lagarde, fxguide "making wet environments"; Jensen et al. EGWR99): porous albedo darkens
# (x0.5-0.7), roughness drops, a thin water layer adds a smooth specular coat; puddles go mirror-smooth.

def birch_bark(m):
    """Silver birch: chalky white (betulin) bark with dark horizontal lenticels and black fissured base."""
    g = reset(m)
    co = coords(g)
    z = g.n("SeparateXYZ", co).outputs[2]
    len_ = g.noise(g.scale_vec(co, (18.0, 18.0, 220.0)), 1.0, 2.0, 0.5)        # short in z = horizontal dashes
    lent = g.math('GREATER_THAN', len_, 0.66)
    patch = g.noise(g.scale_vec(co, (4.0, 4.0, 2.0)), 1.0, 4.0, 0.6, 0.6)
    black = g.math('GREATER_THAN', patch, 0.64)
    base = g.maprange(z, 0.2, 1.2, 1.0, 0.0)                                  # dark furrowed base of trunk
    furrow = g.noise(g.scale_vec(co, (40.0, 40.0, 4.0)), 1.0, 3.0, 0.6)
    color = g.ramp(g.noise(co, 30.0, 3.0, 0.6), [(0.3, (0.52, 0.51, 0.47)), (0.7, (0.66, 0.65, 0.61))])
    color = g.mix(g.math('MULTIPLY', lent, 0.85), color, (0.06, 0.05, 0.045))
    color = g.mix(black, color, (0.04, 0.035, 0.03))
    color = g.mix(g.math('MULTIPLY', base, g.math('GREATER_THAN', furrow, 0.42)), color, (0.05, 0.045, 0.04))
    wet = (0.80, 0.80, 0.80)
    color = g.mix(1.0, color, wet, 'MULTIPLY')
    hgt = g.math('ADD', g.math('MULTIPLY', lent, -0.0008),
                 g.math('MULTIPLY', base, g.math('MULTIPLY', furrow, 0.01)))
    out(g, m, color, 0.55, g.bump(hgt), Coat_Weight=0.2, Coat_Roughness=0.25)
    m.diffuse_color = (0.55, 0.54, 0.5, 1)


def maple_bark(m):
    """Maple/lime type grey-brown bark with shallow vertical fissures, wet."""
    g = reset(m)
    co = coords(g)
    fis = g.noise(g.scale_vec(co, (60.0, 60.0, 6.0)), 1.0, 4.0, 0.6, 0.3)
    lich = g.noise(co, 15.0, 3.0, 0.6)
    color = g.ramp(fis, [(0.35, (0.035, 0.03, 0.025)), (0.55, (0.10, 0.09, 0.075)), (0.8, (0.14, 0.13, 0.11))])
    color = g.mix(g.math('MULTIPLY', g.math('GREATER_THAN', lich, 0.68), 0.6), color, (0.16, 0.18, 0.11))  # lichen
    out(g, m, color, 0.6, g.bump(g.math('MULTIPLY', fis, 0.006)), Coat_Weight=0.2, Coat_Roughness=0.25)
    m.diffuse_color = (0.11, 0.10, 0.085, 1)


def leaves(m):
    """Autumn birch/maple leaves: yellow -> orange -> green-brown per leaf, translucent, wet sheen.
    Per-leaf variation from Object Info Random (instances) + Random Per Island (joined meshes) + world noise.
    Alpha leaf silhouette from UV (0..1 per leaf card) only if the users have a UV map."""
    g = reset(m)
    pos = g.n("NewGeometry").outputs["Position"]
    rnd = g.math('FRACT', g.math('ADD', g.n("ObjectInfo").outputs["Random"],
                                 g.n("NewGeometry").outputs["Random Per Island"]))
    big = g.noise(pos, 0.35, 2.0, 0.5)
    f = g.math('MULTIPLY_ADD', rnd, 0.55, g.math('MULTIPLY', big, 0.45))
    color = g.ramp(f, [(0.0, (0.10, 0.11, 0.025)),   # late green-brown
                       (0.18, (0.30, 0.25, 0.04)),
                       (0.40, (0.55, 0.38, 0.05)),   # birch yellow
                       (0.72, (0.60, 0.30, 0.04)),   # maple orange
                       (0.92, (0.45, 0.13, 0.03)),
                       (1.0, (0.20, 0.08, 0.03))])   # brown, dying
    uvs = all(getattr(o.data, "uv_layers", None) and len(o.data.uv_layers) for o in users_of(m)) and users_of(m)
    alpha = 1.0
    if uvs:
        uv = g.n("SeparateXYZ", g.n("TexCoord").outputs["UV"]).outputs
        u, vv = uv[0], uv[1]
        half = g.math('MULTIPLY', g.math('POWER', g.math('SINE', g.math('MULTIPLY', vv, math.pi), clamp=True), 0.75), 0.48)
        alpha = g.math('LESS_THAN', g.math('ABSOLUTE', g.math('SUBTRACT', u, 0.5)), half)
        vein = g.math('LESS_THAN', g.math('ABSOLUTE', g.math('SUBTRACT', u, 0.5)), 0.012)
        color = g.mix(g.math('MULTIPLY', vein, 0.5), color, (0.55, 0.45, 0.2))
    # translucent leaf: ~35% transmitted diffuse (Cycles only; Unity: use a two-sided foliage shader)
    trans_col = g.mix(1.0, color, (1.4, 1.2, 0.6), 'MULTIPLY')

    def shader(b):
        tr = g.n("BsdfTranslucent", trans_col)
        mx = g.n("MixShader", 0.35, b.outputs[0], tr.outputs[0])
        if alpha == 1.0:
            return mx.outputs[0]
        tp = g.n("BsdfTransparent")
        a = g.n("MixShader", alpha, tp.outputs[0], mx.outputs[0])
        return a.outputs[0]
    out(g, m, color, 0.4, shader=shader, Coat_Weight=0.25, Coat_Roughness=0.12)
    m.diffuse_color = (0.55, 0.38, 0.05, 1)


def wet_grass(m):
    """Autumn lawn, wet: physicallybased.info Grass (0.105, 0.133, 0.041) shifted to tired green/straw,
    fallen yellow leaf litter patches. Wet = darker albedo, NOT a smooth film (blades scatter the reflection)."""
    g = reset(m)
    co = coords(g)
    blades = g.noise(g.scale_vec(co, (400.0, 400.0, 40.0)), 1.0, 2.0, 0.6)
    patch = g.noise(co, 1.2, 3.0, 0.6)
    color = g.ramp(g.math('MULTIPLY_ADD', patch, 0.6, g.math('MULTIPLY', blades, 0.4)),
                   [(0.25, (0.05, 0.075, 0.02)), (0.5, (0.09, 0.12, 0.035)), (0.75, (0.16, 0.15, 0.06))])
    litter_c = g.voronoi(co, 25.0, 'F1')
    lc = g.n("SeparateColor", litter_c.outputs["Color"]).outputs
    ld = litter_c.outputs["Distance"]
    density = g.maprange(g.noise(co, 0.6, 2.0, 0.5), 0.4, 0.65, 0.05, 0.5)
    leaf = g.math('MULTIPLY', g.math('LESS_THAN', lc[0], density), g.math('LESS_THAN', ld, 0.35))
    leafcol = g.ramp(lc[1], [(0.0, (0.40, 0.25, 0.03)), (0.6, (0.55, 0.36, 0.05)), (1.0, (0.30, 0.12, 0.03))])
    color = g.mix(leaf, color, leafcol)
    color = g.mix(1.0, color, (0.75, 0.75, 0.75), 'MULTIPLY')       # wet darkening
    # lawn = millions of tilted blades, never a flat film: even wet it stays rough (R ~0.6-0.75) with a reduced
    # specular, else the flat ground mesh mirrors the sky at grazing angles (s2_atmos report: lawn read grey)
    rough = g.fmix(leaf, g.math('MULTIPLY_ADD', blades, 0.15, 0.60), 0.45)
    out(g, m, color, rough, g.bump(g.math('MULTIPLY', blades, 0.002)), Specular_IOR_Level=0.3)
    m.diffuse_color = (0.08, 0.1, 0.03, 1)


def wet_asphalt(m):
    """Aged asphalt (dry ~0.10; fresh 0.043 per physicallybased.info), wet: darker, low roughness,
    puddles in low spots (thresholded low-frequency noise) = flat, mirror-like water."""
    g = reset(m)
    co = coords(g)
    agg = g.voronoi(co, 180.0, 'F1')
    ar = g.n("SeparateColor", agg.outputs["Color"]).outputs[0]
    stone = g.math('LESS_THAN', agg.outputs["Distance"], 0.3)
    fine = g.noise(co, 600.0, 2.0, 0.6)
    patch = g.noise(co, 0.8, 3.0, 0.6)
    dry = g.ramp(g.math('MULTIPLY_ADD', patch, 0.5, g.math('MULTIPLY', ar, 0.5)),
                 [(0.2, (0.07, 0.068, 0.065)), (0.8, (0.13, 0.125, 0.12))])
    dry = g.mix(g.math('MULTIPLY', stone, g.math('GREATER_THAN', ar, 0.7)), dry, (0.2, 0.19, 0.18))
    wet = g.mix(1.0, dry, (0.55, 0.55, 0.55), 'MULTIPLY')
    low = g.noise(co, 0.35, 4.0, 0.55)
    puddle = g.maprange(low, 0.62, 0.65, 0.0, 1.0)                  # soft shoreline ~ few cm
    color = g.mix(puddle, wet, g.mix(1.0, wet, (0.8, 0.8, 0.8), 'MULTIPLY'))
    rough = g.fmix(puddle, g.math('MULTIPLY_ADD', fine, 0.15, 0.32), 0.03)
    hgt = g.math('MULTIPLY', g.math('ADD', g.math('MULTIPLY', stone, 0.0015), g.math('MULTIPLY', fine, 0.0006)),
                 g.math('SUBTRACT', 1.0, puddle))
    out(g, m, color, rough, g.bump(hgt), Coat_Weight=g.math('MULTIPLY', puddle, 0.9), Coat_Roughness=0.02)
    m.diffuse_color = (0.05, 0.05, 0.048, 1)


def facade_plaster(m, base=(0.72, 0.60, 0.36)):
    """Pale yellow lime render on the neo-classical building across (112212, 150359), damp in rain.
    Haze/desaturation in the photos is atmospheric (g2_light fog), not baked in here."""
    g = reset(m)
    co = coords(g)
    z = g.n("SeparateXYZ", co).outputs[2]
    grain = g.noise(co, 150.0, 3.0, 0.6)
    blot = g.noise(co, 0.5, 4.0, 0.6)
    lo = tuple(c * 0.9 for c in base)
    color = g.ramp(g.math('MULTIPLY_ADD', blot, 0.8, g.math('MULTIPLY', grain, 0.2)), [(0.3, lo), (0.7, base)])
    streak = g.noise(g.scale_vec(co, (25.0, 25.0, 0.6)), 1.0, 3.0, 0.6)      # vertical run-off streaks
    damp = g.math('ADD', g.maprange(z, 0.0, 1.2, 0.35, 0.0), g.math('MULTIPLY', g.math('GREATER_THAN', streak, 0.6), 0.2))
    color = g.mix(g.math('MINIMUM', damp, 0.5), color, g.mix(1.0, color, (0.6, 0.6, 0.6), 'MULTIPLY'))
    color = g.mix(1.0, color, (0.92, 0.92, 0.92), 'MULTIPLY')               # overall damp
    out(g, m, color, g.math('MULTIPLY_ADD', grain, 0.1, 0.82), g.bump(g.math('MULTIPLY', grain, 0.0008)))
    m.diffuse_color = (*base, 1)


def facade_white(m):
    facade_plaster(m, (0.74, 0.73, 0.69))


def facade_pink(m):
    """Pale pink render of the building across (150359)."""
    facade_plaster(m, (0.74, 0.62, 0.56))


def wet_roof(m):
    """Grey painted steel sheet roof (150359), wet: water film coat, slight dirt streaks."""
    g = reset(m)
    co = coords(g)
    streak = g.noise(g.scale_vec(co, (20.0, 20.0, 1.5)), 1.0, 3.0, 0.6)
    color = g.ramp(streak, [(0.3, (0.17, 0.18, 0.185)), (0.7, (0.24, 0.25, 0.255))])
    out(g, m, color, g.math('MULTIPLY_ADD', streak, 0.15, 0.3), Metallic=0.0,
        Coat_Weight=0.8, Coat_Roughness=0.05)
    m.diffuse_color = (0.21, 0.22, 0.225, 1)


# ---------- dispatch: first match wins; names are case-insensitive regexes ----------

RULES = [
    (r"^Room_Wall$|^Room2_.*(wall|plaster|pillar)", plaster_paint),
    (r"^Room_Floor$|^Room2_.*floor|^Doorend_.*floor", ceppo_floor),
    (r"^Room_Ceiling$|^Room2_.*ceil", ceiling_tiles),
    (r"^Room2_(.*_)?blind_fabric|^Room2_.*roller", blind_fabric),
    (r"^Room2_(.*(cassette|aircon|air_?con|hvac)|ac(_|$))", ac_cassette),
    (r"skirt", vinyl_skirting),
    (r"osb", osb),
    (r"cardboard(?!_?black)|carton", cardboard),
    (r"^(Doorend|Room2)_.*(paper|poster|sign|notice)", paper),
    (r"^Door_Oak$|threshold", oak_threshold),
    (r"^(Kitchen|Doorend|Room2)_.*(wood|plank|timber|base_board|baseboard)", stained_plank),
    (r"^Ext_.*birch.*(bark|trunk|branch|stem)|^Ext_.*(bark|trunk|branch|stem).*birch", birch_bark),
    (r"^Ext_.*(bark|trunk|branch|twig|stem)", maple_bark),
    (r"^Ext_.*(lea(f|ves)|foliage|canopy)", leaves),
    (r"^Ext_.*(grass|lawn|turf)", wet_grass),
    (r"^Ext_.*(asphalt|road|path|pavement|tarmac)", wet_asphalt),
    (r"^Ext_.*roof", wet_roof),
    (r"^Ext_.*(cornice|pilaster|trim|reveal_white|plaster_white)", facade_white),
    (r"^Ext_.*(pink)", facade_pink),
    (r"^Ext_.*(facade|plaster|render|building|bldg_yellow)", facade_plaster),
]


def has_image(m):
    return m.node_tree is not None and any(n.type == 'TEX_IMAGE' and not (n.image and n.image.filepath.startswith(TEX))
                                           for n in m.node_tree.nodes)   # our own maps don't count (re-runnable)


def apply():
    done, unmatched = [], []
    for m in bpy.data.materials:
        if m.users == 0 or m.library:
            continue
        for pat, fn in RULES:
            if re.search(pat, m.name, re.I):
                if has_image(m):            # printed labels/QR/posters with an image keep their own tree
                    break
                fn(m)
                done.append(m.name)
                break
        else:
            if re.match(r"(Ext|Trim|Kitchen|Doorend|Room2)_", m.name):
                unmatched.append(m.name)
    print("ARCH SHADERS", sorted(done))
    print("ARCH UNMATCHED (for hard.py or phase 2)", sorted(unmatched))


apply()
