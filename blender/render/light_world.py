# Outside atmosphere: overcast sky world (measured misty-overcast HDRI, photometrically scaled) and the exterior fog volume.
# Standalone, idempotent. Owner: s2_atmos. Split out of render/light.py (which keeps lights, portals, exposure;
# the Cycles window portals there sample this world at render time, so run order does not matter).
#
# Units: 1 Blender W = 683 lm: luminance L [cd/m2] <-> radiance L/683 (world strength, pixel value at exposure 0).
# Daylight model: 2026-10-12 15:00 EEST, Kohtla-Jarve 59.40 N 27.27 E, overcast, fog, light rain.
import datetime
import math
import os

import bpy
import mathutils

# ---------- site / time ----------
LAT, LON = 59.40, 27.27
UTC = datetime.datetime(2026, 10, 12, 12, 0, tzinfo=datetime.timezone.utc)   # 15:00 EEST
WINDOW_AZIMUTH_DEG = 180.0   # ASSUMPTION: compass bearing the window wall (+X, outward normal) faces. Unknown; south.

# ---------- photometry ----------
LM_PER_W = 683.0
E_H = 6000.0                 # lx, horizontal diffuse illuminance: Krochmann overcast 300+21000*sin(h) ~7 klx, -15% rain/fog
GROUND_RHO = 0.12            # wet asphalt / grass albedo for the world below the horizon
SKY_K = 6800.0               # overcast daylight CCT (tints the analytic ground only; the sky colour is the HDRI's)
HDRI = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "textures", "s2_atmos",
                    "kloofendal_misty_morning_puresky_2k.hdr")   # Poly Haven CC0, misty overcast (textures/s2_atmos/SOURCES.txt)
FOG_SIGMA = 0.004            # 1/m extinction = mist, visibility 3.912/sigma ~ 1 km. From 150359: the block ~130 m away
                             # keeps readable windows (T=0.59) and the TV mast ~900 m is a faint ghost (T=0.03); near
                             # trees 2-10 m stay crisp (T>=0.96). (v1 had 0.015 = 260 m fog: washed the near trees.)
FOG_R, FOG_TOP = 1500.0, 40.0   # fog slab outside the facades: horizontal reach / top (m). Top above the tree crowns,
                             # so rays above ~2 deg mostly see the HDRI sky (already a misty sky: no double haze)
FOG_G = 0.6                  # forward scattering of fog droplets

# ---------- room constants (build_room.py / materials/room.py, room2.py) ----------
W, T_WIN = 6.50, 0.10
LAB_Y1 = 9.00                # lab north facade, interior face (room2.py Y1)
HALL_YSF = -5.36             # hall south facade, outer face (room3_entrance.py YSF - TS; its windows look south)


def sun_position(lat, lon, utc):
    """NOAA solar position (gml.noaa.gov/grad/solcalc/calcdetails.html): azimuth (deg from N, clockwise), elevation."""
    r = math.radians
    T = (utc.timestamp() / 86400 + 2440587.5 - 2451545) / 36525
    L0 = (280.46646 + T * (36000.76983 + T * 0.0003032)) % 360
    M = 357.52911 + T * (35999.05029 - 0.0001537 * T)
    e = 0.016708634 - T * (0.000042037 + 0.0000001267 * T)
    C = (math.sin(r(M)) * (1.914602 - T * (0.004817 + 0.000014 * T)) + math.sin(r(2 * M)) * (0.019993 - 0.000101 * T)
         + math.sin(r(3 * M)) * 0.000289)
    lam = L0 + C - 0.00569 - 0.00478 * math.sin(r(125.04 - 1934.136 * T))
    eps = 23 + (26 + (21.448 - T * (46.815 + T * (0.00059 - T * 0.001813))) / 60) / 60 \
        + 0.00256 * math.cos(r(125.04 - 1934.136 * T))
    dec = math.asin(math.sin(r(eps)) * math.sin(r(lam)))
    y = math.tan(r(eps / 2)) ** 2
    eqt = 4 * math.degrees(y * math.sin(2 * r(L0)) - 2 * e * math.sin(r(M)) + 4 * e * y * math.sin(r(M)) * math.cos(2 * r(L0))
                           - 0.5 * y * y * math.sin(4 * r(L0)) - 1.25 * e * e * math.sin(2 * r(M)))
    ha = r(((utc.hour * 60 + utc.minute + utc.second / 60 + eqt + 4 * lon) % 1440) / 4 - 180)
    elev = math.asin(math.sin(r(lat)) * math.sin(dec) + math.cos(r(lat)) * math.cos(dec) * math.cos(ha))
    az = math.atan2(math.sin(ha), math.cos(ha) * math.sin(r(lat)) - math.tan(dec) * math.cos(r(lat)))
    return (math.degrees(az) + 180) % 360, math.degrees(elev)


def compass_to_blender(az_deg, elev_deg):
    """Unit vector: window normal (+X) has bearing WINDOW_AZIMUTH_DEG, bearings turn clockwise seen from above."""
    d, h = math.radians(az_deg - WINDOW_AZIMUTH_DEG), math.radians(elev_deg)
    return (math.cos(h) * math.cos(d), -math.cos(h) * math.sin(d), math.sin(h))


def facade_x():
    """Outer x of the room-1 window build-out (window.py: Window_Reveal to 7.10, drip sill to 7.135); 6.6 without it."""
    xs = [W + T_WIN]
    for name in ("Window_Reveal", "Window_Sill"):
        ob = bpy.data.objects.get(name)
        if ob:
            xs += [(ob.matrix_world @ mathutils.Vector(c)).x for c in ob.bound_box]
    return max(xs)


def put(ob):
    c = bpy.data.collections.get("Lighting") or bpy.data.collections.new("Lighting")
    if c.name not in bpy.context.scene.collection.children:
        bpy.context.scene.collection.children.link(c)
    for u in list(ob.users_collection):
        u.objects.unlink(ob)
    c.objects.link(ob)
    return ob


def hdri_stats(im):
    """Horizontal illuminance of the upper hemisphere (image radiance units) and the azimuth u of its brightest
    sky column (the hidden sun's glow). Equirect row j: zenith angle th = pi*(j+0.5)/h."""
    import numpy as np
    w, h = im.size
    px = np.empty(w * h * 4, dtype=np.float32)
    im.pixels.foreach_get(px)
    y = (px.reshape(h, w, 4)[::-1, :, :3] @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32))
    th = math.pi * (np.arange(h // 2) + 0.5) / h
    e = float((y[:h // 2] * (np.cos(th) * np.sin(th))[:, None]).sum() * (math.pi / h) * (2 * math.pi / w))
    return e, (int(y[:h // 2 - h // 20].mean(0).argmax()) + 0.5) / w


def make_world(sun_dir):
    """Sky above the horizon = real misty-overcast HDRI, scaled so its horizontal illuminance is E_H and rotated so
    its cloud-deck glow sits at the sun azimuth. Below the horizon: Lambertian wet ground under that sky."""
    im = bpy.data.images.get(os.path.basename(HDRI)) or bpy.data.images.load(HDRI, check_existing=True)
    e_img, u_glow = hdri_stats(im)
    gain = E_H / LM_PER_W / e_img
    # rotate the lookup so the glow column faces the sun azimuth (sign/offset verified by a 4-azimuth Cycles probe:
    # brightest view toward the sun, darkest away)
    rz = math.atan2(sun_dir[1], -sun_dir[0]) - (u_glow - 0.5) * 2 * math.pi + math.pi
    w = bpy.data.worlds.get("Light_World") or bpy.data.worlds.new("Light_World")
    bpy.context.scene.world = w
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    N, L = nt.nodes.new, nt.links.new
    d = N("ShaderNodeTexCoord").outputs["Generated"]   # world: view direction
    mp = N("ShaderNodeMapping")
    mp.inputs["Rotation"].default_value = (0, 0, rz)
    L(d, mp.inputs["Vector"])
    env = N("ShaderNodeTexEnvironment")
    env.image = im
    L(mp.outputs[0], env.inputs["Vector"])
    sky = N("ShaderNodeVectorMath")
    sky.operation = 'SCALE'
    L(env.outputs["Color"], sky.inputs[0])
    sky.inputs["Scale"].default_value = gain
    bb = N("ShaderNodeBlackbody")
    bb.inputs[0].default_value = SKY_K
    ground = N("ShaderNodeVectorMath")
    ground.operation = 'SCALE'
    L(bb.outputs[0], ground.inputs[0])
    ground.inputs["Scale"].default_value = GROUND_RHO * E_H / math.pi / LM_PER_W
    z = N("ShaderNodeSeparateXYZ")
    L(d, z.inputs[0])
    above = N("ShaderNodeMath")
    above.operation = 'GREATER_THAN'
    L(z.outputs[2], above.inputs[0])
    above.inputs[1].default_value = 0.0
    mix = N("ShaderNodeMix")
    mix.data_type = 'RGBA'
    L(above.outputs[0], mix.inputs["Factor"])
    L(ground.outputs[0], mix.inputs["A"])
    L(sky.outputs[0], mix.inputs["B"])
    bg = N("ShaderNodeBackground")
    L(mix.outputs["Result"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = 1.0
    L(bg.outputs[0], N("ShaderNodeOutputWorld").inputs[0])
    return e_img, gain, rz


def make_fog():
    """Homogeneous fog box outside the facade. Camera/glossy/transmission rays see it; it is hidden from
    shadow and diffuse rays, so interior daylight keeps the full sky (high-albedo fog conserves diffuse light)."""
    e, n = facade_x() + 0.01, LAB_Y1 + T_WIN + 0.01   # outside the window build-out / lab north facade
    s = HALL_YSF - 0.01                               # outside the hall's south facade (room3_entrance.py, s3_hall)
    v, f = [], []
    for x0, x1, y0, y1 in ((e, e + FOG_R, -FOG_R, FOG_R), (e - FOG_R, e, n, FOG_R), (e - FOG_R, e, -FOG_R, s)):
        b = len(v)
        v += [(x0, y0, -30), (x1, y0, -30), (x1, y1, -30), (x0, y1, -30),
              (x0, y0, FOG_TOP), (x1, y0, FOG_TOP), (x1, y1, FOG_TOP), (x0, y1, FOG_TOP)]
        f += [tuple(b + i for i in q) for q in ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7))]
    me = bpy.data.meshes.get("Light_Fog") or bpy.data.meshes.new("Light_Fog")
    me.clear_geometry()
    me.from_pydata(v, [], f)
    me.validate()
    ob = bpy.data.objects.get("Light_Fog") or bpy.data.objects.new("Light_Fog", me)
    put(ob)
    mat = bpy.data.materials.get("Light_Fog") or bpy.data.materials.new("Light_Fog")
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    vol = nt.nodes.new("ShaderNodeVolumePrincipled")
    vol.inputs["Color"].default_value = (0.92, 0.95, 1.0, 1)
    vol.inputs["Density"].default_value = FOG_SIGMA
    vol.inputs["Anisotropy"].default_value = FOG_G
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(vol.outputs[0], out.inputs["Volume"])
    me.materials.clear()
    me.materials.append(mat)
    ob.visible_shadow = False
    ob.visible_diffuse = False
    ob.display_type = 'BOUNDS'


az, el = sun_position(LAT, LON, UTC)
sun_dir = compass_to_blender(az, el)
e_img, gain, rz = make_world(sun_dir)
make_fog()
print(f"LIGHT_WORLD sun az {az:.1f} el {el:.1f} (window faces {WINDOW_AZIMUTH_DEG:.0f} deg, ASSUMED) -> dir {sun_dir}; "
      f"HDRI E_up {e_img:.3f} x gain {gain:.3f} = E_h {E_H:.0f} lx, rot z {math.degrees(rz):.1f} deg")
