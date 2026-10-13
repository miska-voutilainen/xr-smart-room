# Cameras: keeps the hero `Camera` and adds one `Cam_<photoid>` per reference photo, matched to the photo.
# Standalone + idempotent. Poses come from render/_solve_cams.py (edge-snapped lines on the shell + current furniture:
# Cabinet, Kitchen_Board, TV, Door_Leaf, window sill, trunking...; EXIF focal fixed). rms = line reprojection, 1400 px
# photo, on the picks in _solve_cams.py; "was" = the v1 pose on the same picks.
# Galaxy A36 5G main camera (EXIF, all photos): f = 4.69 mm, 25 mm equiv. (diagonal) -> 1/1.96" 4:3 sensor 6.49 x 4.87 mm.
# Each Cam_* carries custom props res_x/res_y (photo aspect, EXIF-rotated) and ev100 (EXIF exposure) for render/_compare.py.
import math

import bpy

SENSOR_W = 4.69 * math.hypot(36, 24) / 25 * 0.8      # 6.49 mm, used for the long image side (sensor_fit AUTO)
CLIP_START = 0.05

# id: (location, rotation_euler XYZ rad, lens mm, res_x, res_y)   # reprojection rms of the solve (1400 px photos)
CAMS = {
    '120939': ((1.1590, 1.2356, 1.3428), (1.51176, 0.03189, -1.37818), 4.690, 1400, 1050),  # rms 3.3 px (was 57.4)
    '112212': ((3.6569, 0.6198, 1.4422), (1.41413, -0.01999, -0.98469), 4.690, 1400, 1050),  # rms 3.1 px (v1 pose kept)
    '122209': ((0.1657, 1.8170, 1.4984), (1.50368, -0.00157, -1.66485), 4.690, 1400, 1050),  # rms 4.2 px (was 15.3)
    '122216': ((1.3762, 3.3630, 1.3844), (1.48120, -0.00118, -3.05119), 4.690, 1400, 1050),  # rms 6.5 px (s2_camfix pose kept)
    '122224': ((2.8911, 0.9860, 1.7744), (1.42161, -0.01996, 1.40787), 4.690, 1400, 1050),  # rms 1.5 px (was 110.2)
    '120945': ((3.8827, 0.4693, 1.6293), (1.45850, -0.00671, 1.29714), 4.690, 1400, 1050),  # rms 6.7 px (was 144.3)
    '122228': ((3.7459, 1.0633, 1.2015), (1.60137, -0.01966, 0.81481), 4.690, 1400, 1050),  # rms 6.7 px (was 12.9)
    '122244': ((3.6859, 1.5017, 1.4783), (1.55571, -0.00118, -1.54641), 4.690, 1400, 1050),  # rms 1.5 px (was 15.1)
    '122250': ((4.0936, 1.7203, 1.2728), (1.55138, 0.02694, 2.20705), 4.690, 1400, 1050),  # rms 5.7 px (was 178.7)
    '150319': ((1.6742, 1.6862, 1.4053), (1.54166, 0.00561, 2.21569), 4.690, 1050, 1400),  # rms 4.8 px (was 13.1)
    '150325': ((0.7514, 2.4564, 1.3331), (1.42447, 0.03142, 2.38717), 4.690, 1050, 1400),  # rms 6.3 px (was 692), on the open leaf
    '150338': ((4.8911, 1.1002, 1.5499), (1.51820, -0.00214, 0.03926), 4.690, 1400, 1050),  # rms 0.8 px, s3_geo: on the re-sized TV (x 4.247..5.297, z 1.138..1.738)
    '150354': ((5.1269, 2.1277, 1.3171), (1.43803, -0.02082, -2.97106), 4.690, 1400, 1050),  # rms 2.0 px (was 43.4)
    '150359': ((5.1253, 2.2279, 1.4095), (1.63970, 0.03443, -2.19220), 4.690, 1400, 1050),  # rms 8.0 px (was 84.6)
    '150430': ((1.0784, 2.4500, 1.5032), (2.09426, 0.07420, -1.93084), 4.690, 1050, 1400),  # rms 10.9 px, v1 kept: degenerate, see _solve_cams
    '150435': ((0.4065, 1.3120, 1.5700), (1.49877, -0.01244, -0.64879), 4.690, 1050, 1400),  # rms 0.4 px (was 29.2)
    '150439': ((1.7411, 1.8364, 1.3000), (0.82220, -0.01194, -0.85156), 4.690, 1050, 1400),  # 0.0 px (3 lines), z fixed 1.3 (was 19.5)
    '150448': ((0.2900, 1.7455, 1.3452), (1.09753, 0.21844, -2.45946), 4.690, 1400, 1050),  # rms 2.6 px (new)
    'hall_01': ((-5.0309, 2.0929, 1.3804), (1.49280, 0.00552, -1.66490), 4.690, 1400, 1050),  # s3_hall joint BA (Photos/5, 5 cams + hall layout), door-anchored
    'hall_02': ((-0.9972, 0.6002, 1.3330), (1.48655, 0.02948, 1.35844), 4.690, 1400, 1050),  # s3_hall
    'hall_03': ((1.0405, 1.2742, 1.4460), (1.43245, 0.01741, 1.36464), 4.690, 1400, 1050),  # s3_hall
    'hall_04': ((0.7381, 0.9687, 1.3571), (1.47231, -0.00155, 0.87289), 4.690, 1050, 1400),  # s3_hall
    'hall_05': ((-1.5116, 1.3104, 1.2835), (1.50538, 0.00681, 1.90022), 4.690, 1400, 1050),  # s3_hall
}

# EXIF EV100 = log2(N^2 / t) - log2(ISO / 100), per photo. Render exposure = light.py baseline + (9.34 - ev100).
EV100 = {
    '112212': 9.50, '120939': 9.35, '120945': 7.02, '122209': 9.34, '122216': 8.34, '122224': 8.02, '122228': 8.66,
    '122244': 10.32, '122250': 8.66, '150319': 8.66, '150325': 6.34, '150338': 7.66, '150354': 9.34, '150359': 9.95,
    '150430': 8.66, '150435': 8.34, '150439': 8.34, '150448': 7.02, '151011': 8.29, '151018': 8.29, '151022': 8.61,
    '151025': 8.61, '151033': 8.93, '151040': 8.29, '151124': 8.61,
    'hall_01': 7.93, 'hall_02': 6.28, 'hall_03': 7.28, 'hall_04': 6.60, 'hall_05': 6.60,
}


def cameras_coll():
    c = bpy.data.collections.get("Cameras")
    if c is None:
        c = bpy.data.collections.new("Cameras")
    if c.name not in bpy.context.scene.collection.children:
        bpy.context.scene.collection.children.link(c)
    return c


def make_cam(pid, loc, rot, lens, rx, ry):
    name = "Cam_" + pid
    cd = bpy.data.cameras.get(name) or bpy.data.cameras.new(name)
    cd.lens_unit = 'MILLIMETERS'
    cd.sensor_fit = 'AUTO'                 # sensor_width applies to the longer side, as for the phone
    cd.sensor_width = SENSOR_W
    cd.sensor_height = SENSOR_W * 0.75
    cd.lens = lens
    cd.shift_x = cd.shift_y = 0.0
    cd.clip_start = CLIP_START
    cd.clip_end = 200.0
    ob = bpy.data.objects.get(name) or bpy.data.objects.new(name, cd)
    ob.data = cd
    ob.location = loc
    ob.rotation_mode = 'XYZ'
    ob.rotation_euler = rot
    ob["res_x"], ob["res_y"] = rx, ry
    ob["ev100"] = EV100.get(pid, 9.34)
    ob["photo"] = pid
    for c in list(ob.users_collection):
        c.objects.unlink(ob)
    cameras_coll().objects.link(ob)


for pid, (loc, rot, lens, rx, ry) in CAMS.items():
    make_cam(pid, loc, rot, lens, rx, ry)

hero = bpy.data.objects.get("Camera")
if hero:
    hd = hero.data
    hd.clip_start = CLIP_START
    # Hero optics as the phone's ultra-wide would shoot it: same FOV as the build_room 18 mm / 36 mm framing
    # (pose + composition unchanged), scaled to the phone sensor so depth of field is physically right.
    # f/2.2 on a 6.5 mm sensor: hyperfocal ~1.1 m, so focused at 4 m everything past ~0.9 m is sharp; DOF is on
    # for honesty, not for a visible effect (a big-aperture blur would read as a miniature, not a phone photo).
    # build_room.py sets lens = 18 (meaning 36 mm-wide equivalent) on every rebuild without touching the sensor,
    # so read the lens as 36 mm-equivalent when it is > 8 mm (no phone lens is), else it is already converted.
    lens36 = hd.lens if hd.lens > 8.0 else hd.lens * 36.0 / hd.sensor_width
    hd.sensor_fit = 'AUTO'
    hd.sensor_width, hd.sensor_height = SENSOR_W, SENSOR_W * 0.75
    hd.lens = lens36 * SENSOR_W / 36.0
    hd.dof.use_dof = True
    hd.dof.focus_object = None
    hd.dof.focus_distance = 4.0
    hd.dof.aperture_fstop = 2.2
    hd.dof.aperture_blades = 0                 # round iris (phones have no blades)
    bpy.context.scene.camera = hero
print("CAMERAS OK", len(CAMS))
