# Lighting: window portals, ceiling LED panels, exposure baseline. Standalone, idempotent. Owner: g2_light.
# Sky world + exterior fog: render/light_world.py (s2_atmos); the portals here sample that world.
#
# Units: 1 Blender W = 683 lm (photometric convention used by the Blender glTF exporter):
#   luminance  L [cd/m2]  <->  radiance L/683 [W/(m2 sr)]  (world strength, pixel value at exposure 0)
#   flux       F [lm]     <->  light power F/683 [W]       (area light radiance = P / (pi * A), measured)
# Daylight model: 2026-10-12 15:00 EEST, Kohtla-Jarve 59.40 N 27.27 E, overcast, fog, light rain.
import math

import bpy
import mathutils

# ---------- photometry ----------
LM_PER_W = 683.0
LED_LM, LED_K = 3600.0, 4000.0   # Philips CoreLine RC132V / Sylvania START UGR19 600x600: 3600 lm, 840
LED_SIZE = 0.555             # visible diffuser inside the Trim_LED_Frames / Room2 panel alu rim
# Measured 600x600 (2x2) troffer, Day-Brite DayLED 2LTG38L840 LM-79 test 29483 (3795 lm, 4000 K):
#   I(0)=1664 cd = 0.438*F per sr (Lambertian would be F/pi = 0.318*F), I/I0 = .79/.53/.25/.15/.04 at 30/45/60/70/85 deg.
# Cycles spread is a soft-box grid: I/I0 = cos(t)*(tan(s/2)-tan(t))/tan(s/2); s=150 deg gives .73/.52/.27/.09/0, the
# measured curve to 65 deg (the cut tail is < 5 % of the flux). Total power stays normalised.
LED_SPREAD = math.radians(150)
LED_L0 = 0.438 * LED_LM / LED_SIZE ** 2          # 5120 cd/m2 nadir luminance of the visible diffuser
LED_LTAIL = 0.42             # L(t)/L0 = LTAIL + (1-LTAIL)*cos^2 t: measured avg luminance .91/.75/.51/.43 at 30/45/60/75
LED_EDGE = 0.80              # edge-lit light-guide panels: uniformity min/avg ~0.8, darker band at the rim
LED_LM_PER_M2 = LED_LM / LED_SIZE ** 2           # entrance/corridor area lights: same emitter luminance per area
ENTRANCE_SCALE = 0.70        # s2_integrate 0.35 (120945), s3_hall 0.70: the rebuilt hall (Photos/5) has fewer, smaller
                             # fittings; their warm light was missing on the ceiling (cyan bounce from the blue floor)

# ---------- exposure baseline (from the photos' EXIF: f/1.8, 1/100 s, ISO 50, Galaxy A36) ----------
EV100 = math.log2(1.8 ** 2 / 0.00998) - math.log2(50 / 100)        # 9.34
L_AVG = 12.5 * 2 ** EV100 / 100                                     # cd/m2 metered to 18 % grey (K = 12.5)
PHONE_BIAS = 1.0              # phone tone lift. s2_light re-measure with the lab lit (EV-corrected, wall/floor regions):
                              # 122209 0.0, 122216 -0.4/-0.5, 112212 -0.6, 120939 -0.8, lab 150435/150430 p50 -0.4 p85 +0.4 -> +0.3
                              # s3_comp (with Comp_PhoneLook WB/glare, AgX MHC): +0.25 -> wall boxes 112212 -0.03, 122216 0.0,
                              # 150435 +0.05, 122209 +0.27, 120945 -0.45 stop (per-view spread is lighting, not grade)
EXPOSURE = math.log2(0.18 * LM_PER_W / L_AVG) + PHONE_BIAS

# ---------- room constants (build_room.py / materials/room.py) ----------
W, D, H, T_WIN = 6.50, 2.50, 2.90, 0.10
WIN_Y0, WIN_Y1, WIN_Z0, WIN_Z1 = 0.20, 1.80, 0.85, 2.87
CELL, GX0, GY0, LED_CELLS = 0.60, 0.25, 0.35, (3, 6, 9)   # materials/room.py
LAB_Y1 = 9.00                # lab north facade, interior face (room2.py Y1)


def facade_x():
    """Outer x of the room-1 window build-out (window.py: Window_Reveal to 7.10, drip sill to 7.135); 6.6 without it."""
    xs = [W + T_WIN]
    for name in ("Window_Reveal", "Window_Sill"):
        ob = bpy.data.objects.get(name)
        if ob:
            xs += [(ob.matrix_world @ mathutils.Vector(c)).x for c in ob.bound_box]
    return max(xs)


def coll():
    c = bpy.data.collections.get("Lighting") or bpy.data.collections.new("Lighting")
    if c.name not in bpy.context.scene.collection.children:
        bpy.context.scene.collection.children.link(c)
    return c


def put(ob):
    for c in list(ob.users_collection):
        c.objects.unlink(ob)
    coll().objects.link(ob)
    return ob


def area_light(name, loc, rot, sx, sy, power, kelvin=None, portal=False):
    li = bpy.data.lights.get(name) or bpy.data.lights.new(name, 'AREA')
    li.type, li.shape = 'AREA', 'RECTANGLE'
    li.size, li.size_y, li.energy = sx, sy, power
    li.color = (1, 1, 1)
    li.use_temperature = kelvin is not None
    if kelvin:
        li.temperature = kelvin
    li.spread = LED_SPREAD if not portal else math.pi
    li.cycles.is_portal = portal
    ob = bpy.data.objects.get(name) or bpy.data.objects.new(name, li)
    ob.data = li
    ob.location, ob.rotation_euler = loc, rot
    return put(ob)


def diffuser_material(m, sampled=True):
    """Visible LED diffuser: luminance LED_L0 (4000 K, luminance-normalised blackbody) x measured view-angle falloff
    of a UGR<19 panel x faint darker rim (Generated coords: 0..1 over the object's bounds). It is what the camera and
    reflections see; the area light just above it does the diffuse lighting (see seen_emitter / led_light).
    sampled: light-sample it for glossy rays (MIS); only for objects whose diffuse visibility is off."""
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    N, L = nt.nodes.new, nt.links.new

    def op(o, a, b, c=None):
        n = N("ShaderNodeMath")
        n.operation = o
        for i, v in enumerate((a, b, c)[:3 if c is not None else 2]):
            L(v, n.inputs[i]) if isinstance(v, bpy.types.NodeSocket) else setattr(n.inputs[i], "default_value", v)
        return n.outputs[0]

    geo = N("ShaderNodeNewGeometry")
    dot = N("ShaderNodeVectorMath")
    dot.operation = 'DOT_PRODUCT'
    L(geo.outputs["Normal"], dot.inputs[0])
    L(geo.outputs["Incoming"], dot.inputs[1])
    cos2 = op('POWER', op('ABSOLUTE', dot.outputs["Value"], 0.0), 2.0)
    view = op('MULTIPLY_ADD', cos2, 1 - LED_LTAIL, LED_LTAIL)
    uv = N("ShaderNodeSeparateXYZ")
    L(N("ShaderNodeTexCoord").outputs["Generated"], uv.inputs[0])
    d = op('MINIMUM', op('MINIMUM', uv.outputs[0], op('SUBTRACT', 1.0, uv.outputs[0])),
           op('MINIMUM', uv.outputs[1], op('SUBTRACT', 1.0, uv.outputs[1])))
    rim = N("ShaderNodeMapRange")
    rim.interpolation_type = 'SMOOTHSTEP'
    L(d, rim.inputs["Value"])
    rim.inputs["From Min"].default_value, rim.inputs["From Max"].default_value = 0.03, 0.14   # ~15..80 mm in
    rim.inputs["To Min"].default_value, rim.inputs["To Max"].default_value = LED_EDGE, 1.0
    bb = N("ShaderNodeBlackbody")
    bb.inputs[0].default_value = LED_K
    gray = N("ShaderNodeRGBToBW")
    L(bb.outputs[0], gray.inputs[0])
    em = N("ShaderNodeEmission")
    L(bb.outputs[0], em.inputs["Color"])
    L(op('DIVIDE', op('MULTIPLY', op('MULTIPLY', view, rim.outputs[0]), LED_L0 / LM_PER_W), gray.outputs[0]),
      em.inputs["Strength"])
    L(em.outputs[0], N("ShaderNodeOutputMaterial").inputs["Surface"])
    m.cycles.emission_sampling = 'FRONT' if sampled else 'NONE'
    m.diffuse_color = (1, 1, 1, 1)
    return m


def seen_emitter(ob):
    """Diffuser mesh: seen by camera, glossy and transmission rays (view-dependent luminance in reflections, which the
    150 deg spread light would cut off beyond 75 deg); diffuse light comes from its area light only (no double count)."""
    ob.visible_camera = ob.visible_glossy = ob.visible_transmission = True
    ob.visible_diffuse = ob.visible_volume_scatter = ob.visible_shadow = False


def led_light(ob):
    """LED area light: diffuse/volume lighting only; camera, reflections and refractions see the diffuser mesh."""
    ob.visible_camera = ob.visible_glossy = ob.visible_transmission = False
    return ob


def make_lights():
    for name in ("Light", "Room_Window_Daylight", "Room_LED_1", "Room_LED_2", "Room_LED_3"):   # default lamp + old room.py lights
        ob = bpy.data.objects.get(name)
        if ob and ob.type == 'LIGHT':
            bpy.data.objects.remove(ob, do_unlink=True)
    yc = GY0 + 1.5 * CELL
    mat = diffuser_material(bpy.data.materials.get("Light_LED_Diffuser") or bpy.data.materials.new("Light_LED_Diffuser"))
    h = 0.278                                                # Trim_LED_Frames inner edge (trim.py i)
    for i, k in enumerate(LED_CELLS):
        xc = GX0 + (k + 0.5) * CELL
        led_light(area_light(f"Light_LED_{i + 1}", (xc, yc, H - 0.006), (0, 0, 0),   # 1 mm under the diffuser
                             LED_SIZE, LED_SIZE, LED_LM / LM_PER_W, LED_K))
        name = f"Light_LED_Diffuser_{i + 1}"
        me = bpy.data.meshes.get(name) or bpy.data.meshes.new(name)
        me.clear_geometry()
        me.from_pydata([(-h, -h, 0), (-h, h, 0), (h, h, 0), (h, -h, 0)], [], [(0, 1, 2, 3)])   # normal -Z
        me.materials.clear()
        me.materials.append(mat)
        ob = bpy.data.objects.get(name) or bpy.data.objects.new(name, me)
        ob.location = (xc, yc, H - 0.005)                    # 2 mm recessed in the 7 mm frame
        seen_emitter(put(ob))
    # Cycles light portal just outside the window wall, emitting into the room (-X)
    area_light("Light_Portal_Window", (min(facade_x() + 0.005, 7.11), (WIN_Y0 + WIN_Y1) / 2, (WIN_Z0 + WIN_Z1) / 2),
               (0, math.pi / 2, 0), WIN_Z1 - WIN_Z0, WIN_Y1 - WIN_Y0, 1.0, portal=True)


def make_lab():
    """Lab (room 2, materials/room2.py): one LED per Room2_LED_Panel_* (origin = panel centre on the ceiling),
    one portal per Room2_Window_* on the outer facade plane (E: x=6.6 facing -x, N: y=9.1 facing -y)."""
    for ob in [o for o in bpy.data.objects if o.name.startswith(("Light_LED_Lab_", "Light_Portal_Lab_"))]:
        bpy.data.objects.remove(ob, do_unlink=True)
    mat = bpy.data.materials["Light_LED_Diffuser"]   # made by make_lights
    bpy.context.view_layer.update()   # room2.py set .location in this same run: matrix_world is stale until updated
    for ob in sorted((o for o in bpy.data.objects if o.name.startswith("Room2_LED_Panel_")), key=lambda o: o.name):
        x, y, z = ob.matrix_world.translation
        led_light(area_light("Light_LED_Lab_" + ob.name[-2:], (x, y, z - 0.016), (0, 0, 0),   # under the diffuser
                             LED_SIZE, LED_SIZE, LED_LM / LM_PER_W, LED_K))
        seen_emitter(ob)                              # diffuser + alu rim
        for slot in ob.material_slots:
            if slot.material and slot.material.name in ("Room2_LED_Diffuser", "Room3_LED_Diffuser"):
                slot.material = mat
    for ob in (o for o in bpy.data.objects if o.name.startswith("Room2_Window_")):
        cs = [ob.matrix_world @ mathutils.Vector(c) for c in ob.bound_box]
        lo = [min(c[i] for c in cs) for i in range(3)]
        hi = [max(c[i] for c in cs) for i in range(3)]
        zc, sz = (WIN_Z0 + WIN_Z1) / 2, WIN_Z1 - WIN_Z0
        if hi[0] - lo[0] < hi[1] - lo[1]:             # east facade window: spans y
            area_light("Light_Portal_Lab_" + ob.name[13:], (W + T_WIN + 0.005, (lo[1] + hi[1]) / 2, zc),
                       (0, math.pi / 2, 0), sz, hi[1] - lo[1], 1.0, portal=True)
        else:                                          # north facade window: spans x, emit -y
            area_light("Light_Portal_Lab_" + ob.name[13:], ((lo[0] + hi[0]) / 2, LAB_Y1 + T_WIN + 0.005, zc),
                       (-math.pi / 2, 0, 0), hi[0] - lo[0], sz, 1.0, portal=True)


def make_entrance():
    """Entrance / corridor lights built by materials/room3_entrance.py (Room3_*, Room2_Corridor_*): same 4000 K LED
    luminance per emitter area as the panels, same distribution, lighting only (their diffuser meshes are seen)."""
    for ob in bpy.data.objects:
        if ob.type == 'LIGHT' and ob.data.type == 'AREA' and ob.name.startswith(("Room3_", "Room2_Corridor_")):
            li = ob.data
            a = li.size * (li.size_y if li.shape in ('RECTANGLE', 'ELLIPSE') else li.size)
            li.energy = LED_LM_PER_M2 * a / LM_PER_W * ENTRANCE_SCALE
            li.color, li.use_temperature, li.temperature, li.spread = (1, 1, 1), True, LED_K, LED_SPREAD
            ob.visible_camera = False                  # glossy stays: the strip diffusers are not light-sampled
            print(f"LIGHT entrance {ob.name}: {a:.3f} m2 -> {li.energy * LM_PER_W:.0f} lm")
    for name in ("Room2_LED_Diffuser", "Room3_LED_Diffuser"):   # corridor strips: part of a furniture object
        if bpy.data.materials.get(name):                         # that must stay diffuse-visible -> not sampled
            diffuser_material(bpy.data.materials[name], sampled=False)


make_lights()
make_lab()
make_entrance()
sc = bpy.context.scene
sc.view_settings.exposure = EXPOSURE
print(f"LIGHT LED {LED_LM:.0f} lm = "
      f"{LED_LM / LM_PER_W:.2f} W; EV100 {EV100:.2f}, exposure {EXPOSURE:+.2f}")
