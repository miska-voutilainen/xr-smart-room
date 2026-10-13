# Room shell: walls, pillar, floor, suspended ceiling, world, lights, render settings.
# Runs LAST from apply_materials.py. Standalone and idempotent.
import bpy

W, D, H = 6.50, 2.50, 2.90          # interior, from build_room.py
T, T_TOP, T_WIN = 0.10, 0.12, 0.10
CELL = 0.60                          # 600 mm ceiling grid
GX0, GY0 = 0.25, 0.35                # grid line origin: 10 full cells along x, panel row centred on y=1.25
LED_CELLS = (3, 6, 9)                # x cell index of the LED panels (centres x=2.35, 4.15, 5.95), y cell 1 (122209, 150430)
SKIRT = 0.07
LED_W = 40.0                         # W per 600x600 LED panel
WINDOW_W = 60.0                     # W, overcast daylight area light in the window opening
SKY_STRENGTH = 6.0
EXPOSURE = -1.3


# ---------- node helpers ----------

def new_mat(name):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    m.node_tree.nodes.clear()
    return m


class G:
    """Tiny node-graph builder: n('Math', operation='ADD', inputs...)."""
    def __init__(self, nt):
        self.nt, self.x = nt, 0

    def n(self, kind, *ins, **props):
        node = self.nt.nodes.new("ShaderNode" + kind)
        self.x += 1
        node.location = (self.x * 40 % 2000 - 1200, -(self.x // 50) * 300)
        for k, v in props.items():
            setattr(node, k, v)
        for i, v in enumerate(ins):
            if v is None:
                continue
            sock = node.inputs[i]
            if isinstance(v, bpy.types.NodeSocket):
                self.nt.links.new(v, sock)
            else:
                sock.default_value = v
        return node

    def link(self, a, b):
        self.nt.links.new(a, b)

    def math(self, op, a, b=0.0, c=0.0, clamp=False):
        return self.n("Math", a, b, c, operation=op, use_clamp=clamp).outputs[0]

    def fmix(self, fac, a, b):
        return self.n("Mix", fac, None, a, b, data_type='FLOAT').outputs[0]

    def bump(self, height):
        return self.n("Bump", 1.0, 1.0, 0.1, height).outputs[0]  # height in metres

    def mix(self, fac, a, b):
        m = self.n("Mix", data_type='RGBA')
        self.link_or_set(m.inputs[0], fac)
        self.link_or_set(m.inputs[6], a)
        self.link_or_set(m.inputs[7], b)
        return m.outputs[2]

    def link_or_set(self, sock, v):
        if isinstance(v, bpy.types.NodeSocket):
            self.link(v, sock)
        else:
            sock.default_value = v

    def ramp(self, fac, stops, interp='LINEAR'):
        r = self.n("ValToRGB")
        self.link_or_set(r.inputs[0], fac)
        cr = r.color_ramp
        cr.interpolation = interp
        while len(cr.elements) > 1:
            cr.elements.remove(cr.elements[-1])
        for i, (p, c) in enumerate(stops):
            e = cr.elements[0] if i == 0 else cr.elements.new(p)
            e.position = p
            e.color = (*c, 1) if len(c) == 3 else c
        return r.outputs[0]


def principled(g, color, rough, normal=None, **extra):
    b = g.n("BsdfPrincipled")
    g.link_or_set(b.inputs["Base Color"], color)
    g.link_or_set(b.inputs["Roughness"], rough)
    if normal is not None:
        g.link(normal, b.inputs["Normal"])
    for k, v in extra.items():
        g.link_or_set(b.inputs[k], v)
    out = g.n("OutputMaterial")
    g.link(b.outputs[0], out.inputs[0])
    return b


# ---------- walls: matte plaster + dark vinyl skirting ----------

def wall_material():
    m = new_mat("Room_Wall")
    g = G(m.node_tree)
    co = g.n("TexCoord").outputs["Object"]
    z = g.n("SeparateXYZ", co).outputs[2]
    skirt = g.math('LESS_THAN', z, SKIRT)
    # roller stipple + faint large-scale unevenness
    stip = g.n("TexNoise", co, None, 260.0, 4.0, 0.6).outputs[0]
    blot = g.n("TexNoise", co, None, 1.6, 3.0, 0.55).outputs[0]
    tone = g.ramp(blot, [(0.3, (0.765, 0.757, 0.728)), (0.7, (0.80, 0.792, 0.762))])
    color = g.mix(skirt, tone, (0.038, 0.038, 0.040, 1))
    rough = g.math('MULTIPLY_ADD', stip, 0.12, 0.79)
    rough = g.fmix(skirt, rough, 0.5)
    # skirting top edge step (~6 mm proud) + stipple on paint, smoother vinyl below
    hgt = g.math('ADD', g.math('MULTIPLY', skirt, 0.006),
                 g.math('MULTIPLY', stip, g.math('MULTIPLY_ADD', skirt, -0.0003, 0.0004)))
    principled(g, color, rough, g.bump(hgt))
    return m


# ---------- floor: polished grey terrazzo tiles ----------

def floor_material():
    m = new_mat("Room_Floor")
    g = G(m.node_tree)
    co = g.n("TexCoord").outputs["Object"]
    warp = g.n("TexNoise", co, None, 25.0, 2.0, 0.5).outputs["Color"]
    cw = g.n("VectorMath", co, g.n("VectorMath", warp, (0.006, 0.006, 0.006), operation='MULTIPLY').outputs[0],
             operation='ADD').outputs[0]

    def chips(scale, density, edge):
        """Per-cell chips: present where cell random > density, shape = inset of the voronoi cell."""
        f1 = g.n("TexVoronoi", cw, None, scale, feature='F1')
        de = g.n("TexVoronoi", cw, None, scale, feature='DISTANCE_TO_EDGE').outputs["Distance"]
        rgb = g.n("SeparateColor", f1.outputs["Color"]).outputs
        present = g.math('GREATER_THAN', rgb[0], density)
        shape = g.math('GREATER_THAN', de, edge)
        return g.math('MULTIPLY', present, shape), rgb[1], rgb[2]

    palette = [(0.0, (0.29, 0.285, 0.275)), (0.45, (0.37, 0.365, 0.355)), (0.70, (0.065, 0.065, 0.07)),
               (0.85, (0.25, 0.21, 0.17)), (0.93, (0.52, 0.51, 0.50))]

    # matrix: warm grey cement with sand speckle and per-tile tone shift
    sand = g.n("TexNoise", co, None, 900.0, 2.0, 0.5).outputs[0]
    cloud = g.n("TexNoise", co, None, 6.0, 4.0, 0.7).outputs[0]
    # 1200x600 tiles: per-tile tone (Color) and joint mask (Factor), sizes in metres at Scale 1
    tiles = g.n("TexBrick", co, (0.93, 0.93, 0.93, 1), (1.06, 1.05, 1.04, 1), (0.5, 0.5, 0.5, 1),
                1.0, 0.0018, 0.4, 0.0, 1.2, 0.6, offset=0.0, squash=1.0)
    matrix = g.ramp(g.math('MULTIPLY_ADD', sand, 0.4, g.math('MULTIPLY', cloud, 0.6)),
                    [(0.30, (0.245, 0.237, 0.222)), (0.70, (0.305, 0.296, 0.279))])
    mul = g.n("Mix", 1.0, data_type='RGBA', blend_type='MULTIPLY')
    g.link(matrix, mul.inputs[6])
    g.link(tiles.outputs["Color"], mul.inputs[7])
    matrix = mul.outputs[2]
    color = matrix

    # large, sparse, low-contrast "ghost" stones (5-15 cm)
    big, bg, bb = chips(7.0, 0.85, 0.15)
    bigcol = g.ramp(bg, [(0.0, (0.12, 0.12, 0.125)), (0.5, (0.30, 0.295, 0.285)), (1.0, (0.36, 0.355, 0.34))])
    color = g.mix(g.math('MULTIPLY', big, 0.6), color, bigcol)
    # medium chips 10-30 mm
    med, mg, _ = chips(25.0, 0.62, 0.20)
    color = g.mix(g.math('MULTIPLY', med, 0.9), color, g.ramp(mg, palette, 'CONSTANT'))
    # small chips 3-10 mm
    sml, sg, _ = chips(90.0, 0.45, 0.22)
    color = g.mix(g.math('MULTIPLY', sml, 0.6), color, g.ramp(sg, palette, 'CONSTANT'))
    # sand-size grit in the cement (1-3 mm), very low contrast
    grit, gg, _ = chips(350.0, 0.45, 0.15)
    color = g.mix(g.math('MULTIPLY', grit, 0.35), color, g.ramp(gg, palette, 'CONSTANT'))
    # tile joints
    joint = tiles.outputs["Factor"]
    color = g.mix(g.math('MULTIPLY', joint, 0.15), color, (0.12, 0.12, 0.12, 1))

    rn = g.n("TexNoise", co, None, 1.2, 3.0, 0.6).outputs[0]
    rough = g.math('MULTIPLY_ADD', rn, 0.14, 0.22)
    rough = g.math('ADD', rough, g.math('MULTIPLY', joint, 0.2))
    hgt = g.math('ADD', g.math('MULTIPLY', joint, -0.0005), g.math('MULTIPLY', sand, 0.00008))
    principled(g, color, rough, g.bump(hgt))
    return m


# ---------- ceiling: 600x600 mineral fibre tiles, T-grid, LED panel frames ----------

def ceiling_material():
    m = new_mat("Room_Ceiling")
    g = G(m.node_tree)
    co = g.n("TexCoord").outputs["Object"]
    sep = g.n("SeparateXYZ", co).outputs

    def axis(v, origin):
        u = g.math('DIVIDE', g.math('SUBTRACT', v, origin), CELL)
        f = g.math('FRACT', u)
        dist = g.math('MULTIPLY', g.math('MINIMUM', f, g.math('SUBTRACT', 1.0, f)), CELL)  # m to nearest line
        return dist, g.math('FLOOR', u)

    dx, kx = axis(sep[0], GX0)
    dy, ky = axis(sep[1], GY0)
    d = g.math('MINIMUM', dx, dy)
    tbar = g.math('LESS_THAN', d, 0.012)
    edge = g.math('LESS_THAN', d, 0.016)   # shadow lip where tile meets the T
    is_led = g.math('MULTIPLY', g.math('COMPARE', ky, 1.0, 0.5),
                    g.math('MAXIMUM', *[g.math('COMPARE', kx, float(k), 0.5) for k in LED_CELLS]))
    # fissured mineral fibre: fine pits + worm-like fissures
    pits = g.n("TexVoronoi", co, None, 260.0, feature='F1').outputs["Distance"]
    fis = g.n("TexNoise", co, None, 45.0, 3.0, 0.6, None, None, None, 1.5).outputs[0]
    fiss = g.math('LESS_THAN', g.math('ABSOLUTE', g.math('SUBTRACT', fis, 0.5)), 0.018)
    grain = g.n("TexNoise", co, None, 500.0, 2.0, 0.5).outputs[0]
    tile = g.ramp(g.math('SUBTRACT', grain, g.math('MULTIPLY', fiss, 0.15)),
                  [(0.2, (0.75, 0.75, 0.74)), (0.6, (0.79, 0.79, 0.78))])
    color = g.mix(tbar, tile, (0.82, 0.82, 0.81, 1))
    color = g.mix(g.math('MULTIPLY', is_led, g.math('SUBTRACT', 1.0, tbar)), color, (0.88, 0.88, 0.88, 1))
    rough = g.fmix(tbar, 0.95, 0.45)
    hgt = g.math('ADD', g.math('MULTIPLY', edge, 0.004),
                 g.math('MULTIPLY', g.math('SUBTRACT', 1.0, edge),
                        g.math('ADD', g.math('MULTIPLY', fiss, -0.0003),
                               g.math('MULTIPLY', g.math('LESS_THAN', pits, 0.12), -0.00015))))
    principled(g, color, rough, g.bump(hgt))
    return m


def set_material(ob, mat):
    ob.data.materials.clear()
    ob.data.materials.append(mat)


# ---------- objects ----------

def walls_coll():
    return bpy.data.collections.get("Walls") or bpy.context.scene.collection


def make_ceiling(mat):
    x0, x1, y0, y1, z0, z1 = -T, W + T_WIN, -T, D + T_TOP, H, H + 0.10
    v = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
         (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    f = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    ob = bpy.data.objects.get("Room_Ceiling")
    if ob is None:
        me = bpy.data.meshes.get("Room_Ceiling") or bpy.data.meshes.new("Room_Ceiling")
        ob = bpy.data.objects.new("Room_Ceiling", me)
    me = ob.data
    me.clear_geometry()
    me.from_pydata(v, [], f)
    me.validate()
    for c in list(ob.users_collection):
        c.objects.unlink(ob)
    walls_coll().objects.link(ob)
    set_material(ob, mat)


def lighting_coll():
    c = bpy.data.collections.get("Lighting")
    if c is None:
        c = bpy.data.collections.new("Lighting")
    if c.name not in bpy.context.scene.collection.children:
        bpy.context.scene.collection.children.link(c)
    return c


def area_light(name, loc, rot, size, size_y, power, color, camera_visible):
    li = bpy.data.lights.get(name) or bpy.data.lights.new(name, 'AREA')
    li.type = 'AREA'
    li.shape = 'RECTANGLE'
    li.size, li.size_y = size, size_y
    li.energy = power
    li.color = color
    ob = bpy.data.objects.get(name) or bpy.data.objects.new(name, li)
    ob.data = li
    ob.location = loc
    ob.rotation_euler = rot
    ob.visible_camera = camera_visible
    for c in list(ob.users_collection):
        c.objects.unlink(ob)
    lighting_coll().objects.link(ob)
    return ob


def make_lights():
    old = bpy.data.objects.get("Light")          # default point lamp above the ceiling
    if old and old.type == 'LIGHT':
        bpy.data.objects.remove(old, do_unlink=True)
    led = (1.0, 0.94, 0.88)                       # ~4200 K
    yc = GY0 + 1.5 * CELL
    for i, k in enumerate(LED_CELLS):
        xc = GX0 + (k + 0.5) * CELL
        area_light(f"Room_LED_{i + 1}", (xc, yc, H - 0.004), (0, 0, 0), 0.57, 0.57, LED_W, led, True)
    # overcast daylight filling the window opening (inside the reveal, so glass never blocks it)
    area_light("Room_Window_Daylight", (W - 0.01, 1.0, 1.80), (0, 1.5708, 0), 1.85, 1.55,
               WINDOW_W, (0.86, 0.92, 1.0), False)


def make_world():
    s = bpy.context.scene
    w = bpy.data.worlds.get("Room_World") or bpy.data.worlds.new("Room_World")
    s.world = w
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    g = G(nt)
    # overcast sky: bright grey horizon, slightly bluer zenith, dull ground
    z = g.n("SeparateXYZ", g.n("TexCoord").outputs["Generated"]).outputs[2]   # view dir, -1..1
    z = g.math('MULTIPLY_ADD', z, 0.5, 0.5)
    sky = g.ramp(z, [(0.0, (0.16, 0.155, 0.15)), (0.45, (0.36, 0.36, 0.35)), (0.56, (0.80, 0.83, 0.88)),
                     (1.0, (0.62, 0.68, 0.80))])
    bg = g.n("Background", sky, SKY_STRENGTH)
    out = g.n("OutputWorld")
    g.link(bg.outputs[0], out.inputs[0])


def render_settings():
    s = bpy.context.scene
    s.render.engine = 'CYCLES'
    c = s.cycles
    c.device = 'GPU'
    try:  # user prefs do not persist from -b; set them every run, fall back to CPU silently
        prefs = bpy.context.preferences.addons['cycles'].preferences
        for kind in ('OPTIX', 'CUDA'):
            prefs.compute_device_type = kind
            prefs.get_devices()
            gpus = [d for d in prefs.devices if d.type == kind]
            if gpus:
                for d in prefs.devices:
                    d.use = d.type == kind
                break
        else:
            c.device = 'CPU'
    except Exception:
        c.device = 'CPU'
    c.samples = 192
    c.use_adaptive_sampling = True
    c.adaptive_threshold = 0.01
    c.use_denoising = True
    c.denoiser = 'OPENIMAGEDENOISE'
    c.use_light_tree = True
    c.max_bounces = 10
    c.diffuse_bounces = 5
    c.glossy_bounces = 4
    c.transmission_bounces = 8
    c.transparent_max_bounces = 16
    c.caustics_reflective = False
    c.caustics_refractive = False
    c.blur_glossy = 1.0
    c.sample_clamp_direct = 0.0
    c.sample_clamp_indirect = 8.0
    s.render.resolution_x, s.render.resolution_y = 1920, 1080
    s.render.resolution_percentage = 100
    s.view_settings.view_transform = 'AgX'
    s.view_settings.look = 'None'
    s.view_settings.exposure = EXPOSURE


wall = wall_material()
for name in ("Wall_Bottom", "Wall_Top", "Wall_Left", "Wall_Right", "Pillar"):
    ob = bpy.data.objects.get(name)
    if ob:
        set_material(ob, wall)
floor = bpy.data.objects.get("Floor")
if floor:
    set_material(floor, floor_material())
make_ceiling(ceiling_material())
make_lights()
make_world()
render_settings()
print("ROOM MATERIALS OK")
