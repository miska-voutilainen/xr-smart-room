# Offline camera solver for the reference photos (points + lines). NOT run by apply_materials ("_" prefix).
#   python3 render/_solve_cams.py [photo_id ...] [--eval]     (system python3: numpy, scipy, PIL)
# Picks are pixels in the EXIF-rotated photo scaled to 1400 px long side; 3D references are the CURRENT scene
# (room shell from build_room.py + Cabinet / Desk / Window_Frame / Door_Frame / niche / Kitchen_Board / Room2, world bboxes).
# Prints rms of the current CAMS pose ("before"), solves from it, prints rms after + the CAMS line for render/cameras.py,
# and writes OUT/<id>_fit.jpg (picks cyan, model refs re-projected: red = before, green = after).
# Phone height bounded to 0.7-1.8 m, position only bounded to the building (no binding caps).
import glob, math, os, re, sys
import numpy as np
from PIL import Image, ImageDraw, ImageOps
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.environ.get('SOLVE_OUT', '/tmp/solve_cams')
LENS = 4.69
SENSOR_W = 4.69 * math.hypot(36, 24) / 25 * 0.8
LONG = 1400.0
W, D, H = 6.50, 2.50, 2.90           # room 1 interior; partition y 2.50..2.62 (passage x 1.0..2.5, h 2.4)
DP = 2.62                            # partition back face (lab side)
X = lambda *p: np.array(p, float)

# Reference lines/points (world, m). Names used in the picks below.
R = dict(
    # shell
    c00=(X(0, 0, 0), X(0, 0, H)), cW0=(X(W, 0, 0), X(W, 0, H)), cWD=(X(W, D, 0), X(W, D, H)),
    c0D=(X(0, D, 0), X(0, D, H)),
    fy0=(X(0, 0, 0), X(W, 0, 0)), fyD=(X(0, D, 0), X(W, D, 0)), fx0=(X(0, 0, 0), X(0, D, 0)), fxW=(X(W, 0, 0), X(W, D, 0)),
    hy0=(X(0, 0, H), X(W, 0, H)), hyD=(X(0, D, H), X(W, D, H)), hx0=(X(0, 0, H), X(0, D, H)), hxW=(X(W, 0, H), X(W, D, H)),
    # skirting top (z .07) on the four walls: the white wall / dark skirting edge is the strongest floor-line edge
    sy0=(X(0, 0, .07), X(W, 0, .07)), syD=(X(0, D, .07), X(W, D, .07)), sx0=(X(0, 0, .07), X(0, D, .07)),
    sxW=(X(W, 0, .07), X(W, D, .07)),
    c00d=(X(0, .04, 0), X(0, .04, H)),                 # door-end corner behind the corner duct (duct face y .04)
    # cable trunking on the y=0 wall (Legrand 50x130: z .98..1.11, face y .05)
    trb=(X(0, .05, .98), X(W, .05, .98)), trt=(X(0, .05, 1.11), X(W, .05, 1.11)),
    # Doorend_Board_1/2 (electrical cabinets on the door wall, front x .103, y .068-.373 / .443-.748, z 1.07-1.71);
    # seen from +y the right outline is the back edge (x 0)
    eb1l=(X(.103, .068, 0), X(.103, .068, H)), eb1r=(X(0, .373, 0), X(0, .373, H)),
    eb2l=(X(.103, .443, 0), X(.103, .443, H)), eb2r=(X(0, .748, 0), X(0, .748, H)),
    ebt=(X(.103, 0, 1.71), X(.103, D, 1.71)), ebb=(X(.103, 0, 1.07), X(.103, D, 1.07)),
    # window wall x=W: pilaster face x 6.37 for y<0.2; reveal edges y=.2/1.8 (z .85..2.75 opening, reveal .7..2.9 deep)
    pil=(X(6.37, 0, 0), X(6.37, 0, H)), pilE=(X(6.37, .2, 0), X(6.37, .2, H)),
    wy02=(X(W, .2, 0), X(W, .2, H)), wy18=(X(W, 1.8, 0), X(W, 1.8, H)),
    sill=(X(6.46, .2, .87), X(6.46, 1.8, .87)),       # sill board front top edge
    wf18=(X(6.76, 1.8, 0), X(6.76, 1.8, H)), wf02=(X(6.76, .2, 0), X(6.76, .2, H)),   # frame outer edges (room face)
    wft=(X(6.76, 0, 2.75), X(6.76, D, 2.75)), whd=(X(W, 0, 2.75), X(W, D, 2.75)),     # frame top / reveal head
    # Desk top (z .75): near edge x 5.28, side y 1.277
    # partition y=D: passage jambs x 1.0 / 2.5 (front y=D, back y=DP), head z 2.4; niche x 4.3..5.9 z 1.1..2.0
    p10=(X(1.0, D, 0), X(1.0, D, H)), p25=(X(2.5, D, 0), X(2.5, D, H)),
    p10b=(X(1.0, DP, 0), X(1.0, DP, H)), p25b=(X(2.5, DP, 0), X(2.5, DP, H)),
    phd=(X(0, D, 2.4), X(W, D, 2.4)), phdb=(X(0, DP, 2.4), X(W, DP, 2.4)),
    n43=(X(4.3, D, 0), X(4.3, D, H)), n59=(X(5.9, D, 0), X(5.9, D, H)),
    nlo=(X(0, D, 1.1), X(W, D, 1.1)), nhi=(X(0, D, 2.0), X(W, D, 2.0)),
    # door wall x=0: opening y 1.15..1.9 (frame to 2.3) h 2.1; pillar x 0..0.25 at y 2.3
    d115=(X(0, 1.15, 0), X(0, 1.15, H)), d19=(X(0, 1.9, 0), X(0, 1.9, H)), d23=(X(0, 2.3, 0), X(0, 2.3, H)),
    dhd=(X(0, 0, 2.1), X(0, D, 2.1)), pilr=(X(.25, 2.3, 0), X(.25, 2.3, H)),
    # Cabinet (worktop x .60..3.08, front y .62, top z .90)
    cwf=(X(0, .62, .90), X(W, .62, .90)), cwfb=(X(0, .62, .86), X(W, .62, .86)),
    cwb=(X(0, 0, .90), X(W, 0, .90)),                  # worktop / wall junction
    cwe=(X(3.08, 0, .90), X(3.08, D, .90)), cwe0=(X(.60, 0, .90), X(.60, D, .90)),
    cev=(X(3.08, .62, 0), X(3.08, .62, H)), cev0=(X(.60, .62, 0), X(.60, .62, H)),
    # Kitchen_Board (x .615..1.27, front y .29?, z .9..1.66)
    kbt=(X(0, .29, 1.66), X(W, .29, 1.66)),
    dkf=(X(5.28, 0, .75), X(5.28, D, .75)), dky=(X(0, 1.277, .75), X(W, 1.277, .75)),
)
P = dict(   # points
    cab_fr=X(3.08, .62, .90), cab_fl=X(.60, .62, .90), desk_c=X(5.28, 1.277, .75),
)


def ref(n):
    return R[n]


# picks: id -> dict(L=[(refname, [(u,v),...]), ...], P=[(pointname or xyz, (u,v)), ...])
PICKS = {
    '120939': dict(L=[('cWD', [(655.2, 250), (656.1, 415), (657.1, 580)]), ('wy18', [(788.7, 250), (786.9, 405), (785.2, 560)]),
                      ('syD', [(354.3, 1024.5), (470.5, 905.6), (586.8, 786.6)]), ('cev', [(1257.1, 740), (1256.3, 1040)]),
                      ('sy0', [(1218, 762), (1248, 796)])]),
        # left out: window-wall skirting (steps at x 1117 / 1172 px: real wall below the window is not one plane at x=6.5)
    '120945': dict(L=[('d115', [(592.7, 320), (589.2, 540), (585.6, 760)]), ('d23', [(872.9, 320), (872.1, 540), (871.2, 760)]),
                      ('dhd', [(620, 282.8), (740, 289.8), (860, 296.8)]), ('sx0', [(510, 806.5), (580, 803.2)]),
                      ('cwf', [(461.2, 658.3), (508, 822.8), (554.7, 987.3)]), ('c00d', [(285.8, 60), (286.2, 330)]),
                      ('cwb', [(265.6, 662), (150.2, 829.2), (34.8, 996.4)])]),
    '122209': dict(L=[('cWD', [(489.4, 250), (490.4, 470), (491.4, 690)]), ('wy18', [(601.8, 250), (604.6, 405), (607.5, 560)]),
                      ('pilE', [(873.2, 240), (871.9, 400), (870.5, 560)]),
                      ('cev', [(999, 660), (998.5, 880)]), ('cwf', [(1007.7, 654.7), (1197.3, 750.4), (1387, 846.1)]),
                      ('trt', [(935.7, 527.1), (1162.9, 583.2), (1390.2, 639.3)]),
                      ('syD', [(331.2, 1030.6), (402.8, 886.4), (474.4, 742.1)])]),
    '122216': dict(L=[('cwf', [(209.9, 604.3), (644.9, 611), (1079.9, 617.6)]), ('cev', [(201.5, 620.1), (216, 880)]),
                      ('cev0', [(1078.6, 630), (1072.1, 880)]), ('sy0', [(10.1, 793.7), (190, 800)]),
                      ('trt', [(10.1, 498.8), (415.1, 503.2), (820.1, 507.6)])]),
        # left out: trunking bottom (photo band 499..557 px = ~0.18 m, model 0.13 m: real bottom ~.93), Kitchen_Board sides (photo 175 px
        # wide vs model 0.655 m -> ~0.6 m), door-end corner (duct edge, weak)
    '122224': dict(L=[('d115', [(590.4, 300), (589.7, 590), (589.1, 880)]), ('dhd', [(600, 252.1), (780, 259), (960, 266)]),
                      ('sx0', [(385, 948.2), (482.5, 940.4), (579.9, 932.7)]), ('cev0', [(372.6, 740), (374, 1000)]),
                      ('cwf', [(376.6, 747), (321.4, 874.9), (266.1, 1002.7)])]),
        # left out: wall right of the door (white face 940..1150 px, then the jamb at ~1150 px: the real pillar
        # does not match the model's 0.25 m pillar at the door frame)
    '122250': dict(L=[('c00d', [(945.5, 100), (944.7, 330), (943.8, 560)]), ('d115', [(1255.1, 250), (1254.9, 525), (1254.7, 800)]),
                      ('sx0', [(1065.3, 791.3), (1146.8, 810.4), (1228.3, 829.6)]), ('cwb', [(344.6, 700.7), (522.2, 672.4), (699.9, 644.1)]),
                      ('cwf', [(523.9, 760.6), (767.5, 684.4), (1011.1, 608.3)]), 
                      ('cev', [(519.1, 790), (518.6, 915), (518.1, 1040)]),
                      ('trt', [(0, 642), (180, 621), (360, 600)])]),
        # worktop end edge (334,706)-(517,762) left out: ~19 px off with everything else fitted (cabinet end x?)
        # trunking bottom left out: it sits ~2.5 cm above the worktop in this photo (real trunking ~0.18 m tall, z ~.93..1.11)
    '150319': dict(L=[('eb1l', [(365.9, 560), (365.5, 800)]),
                      ('dhd', [(879.2, 236.2), (961.4, 217.3), (1043.6, 198.4)]), ('d115', [(877, 300), (872, 1300)]),
                      ('ebt', [(370, 531.3), (490, 528.9)]), (((.103, .748, 0), (.103, .748, 2)), [(641.8, 520), (636, 830.1)])]),
    '150325': dict(L=[  # the open leaf (Door_Leaf at 90 deg: room face y 1.257, x -0.11..-0.855, z .015..2.047; glass sight
                        # x -.241..-.721, z .249..1.923), from materials/door.py
                      (((-.855, 1.257, 0), (-.855, 1.257, 2)), [(706.8, 200), (707.1, 680), (707.5, 1160)]),
                      (((0, 1.257, 2.047), (-1, 1.257, 2.047)), [(345.6, 18.3), (523.1, 82.3), (700.6, 146.4)]),
                      (((0, 1.257, .015), (-1, 1.257, .015)), [(424.6, 1396), (566.8, 1286.7), (709.1, 1177.3)]),
                      (((-.721, 1.26, 0), (-.721, 1.26, 2)), [(660.8, 230), (663.2, 645), (665.5, 1060)]),
                      (((-.241, 1.26, 0), (-.241, 1.26, 2)), [(444.6, 149.9), (465.9, 659.9), (487.3, 1169.9)]),
                      (((0, 1.26, 1.923), (-1, 1.26, 1.923)), [(446, 129.4), (548.9, 167.6), (651.7, 205.8)]),
                      (((0, 1.26, .249), (-1, 1.26, .249)), [(494.6, 1198.8), (580.6, 1138.8), (666.6, 1078.8)]),
                      ]),
        # left out: the side panel / post edge at x 1000 px: with the leaf fitted, the model post (y 1.95) lands at
        # ~770 px. Leaf + post together are inconsistent (rms 26): real leaf opens past 90 deg or the opening is wider.
    '150338': dict(L=[  # TV front (bbox x 4.247..5.297, z 1.138..1.738, face y 2.475); the niche itself is mis-sized in
                        # the model (photo niche outer edges 141..1184 x 210..890 px = ~1.65 x 1.05 m vs model 1.6 x 0.9)
                      (((4.247, 2.475, 0), (4.247, 2.475, 2)), [(271.1, 360), (275.3, 550), (279.5, 740)]),
                      (((5.297, 2.475, 0), (5.297, 2.475, 2)), [(1044.7, 360), (1040.6, 550), (1036.5, 740)]),
                      (((0, 2.475, 1.738), (6, 2.475, 1.738)), [(300, 332.1), (660, 331.3), (1020, 330.6)]),
                      (((0, 2.475, 1.138), (6, 2.475, 1.138)), [(300, 766.5), (660, 771.1), (1020, 775.6)])]),
    '150354': dict(L=[('trt', [(319.8, 475.5), (854.8, 495.6), (1389.8, 515.8)]), ('sy0', [(359.8, 904.7), (874.8, 962.7), (1389.7, 1020.8)]),
                      ('pil', [(328.4, 560), (329.4, 720), (330.3, 880)]),
                      (((6.37, .05, 0), (6.37, .05, 2)), [(306.2, 470), (308.4, 520)]),          # trunking end at the pilaster
                      ]),
        # sockets (460,490) / (1040,520) px left out: they pull the fit ~15 px (socket x positions?)
        # trunking bottom left out (real trunking ~0.18 m tall)
    '150359': dict(L=[('wy18', [(357.2, 100), (362.8, 450), (368.4, 800)]), ('pilE', [(1102, 100), (1112.8, 399.9), (1123.5, 699.8)]),
                      ('sill', [(1139.7, 839), (769.4, 930.1), (399, 1021.1)]),
                      ('trt', [(1262, 713), (1330, 722), (1400, 731.7)])]),
        # left out: trunking end at 1261 px (model x 6.37 would sit ~150 px left: real pilaster deeper than 0.13 m)
        # left out: radiator feed pipe (1010,961)-(1189,914) px, conflicts with the sill slope by ~17 px
        # left out: Monitor top/side ((20,959)-(341,895), (348,900)-(372,1039) px): ~20 px off the sill fit, prop moved?
        # left out: frame/sash edges and head (photo window ~0.1 m taller than the model), pilaster/wall corner
        # (1159..1178 px: real pilaster wider than the model's 0.13 x 0.2 m, as in 122209)
    '150430': dict(L=[('wy18', [(246.2, 1039.9), (240.4, 1209.9), (234.7, 1379.8)]), ('wf02', [(540.6, 1040), (543.5, 1210), (546.3, 1380)]),
                      ('hxW', [(130, 999.9), (365, 993.6), (600, 987.3)]), ('cWD', [(96.9, 1010), (91.9, 1194.9), (87, 1379.9)])]),
        # NOT re-solved (v1 pose kept, rms 10.9 on these picks): with only window-wall features the solve is
        # degenerate (runs into the 1.8 m height bound, also at 2.1 m) and the corner pick disagrees by ~13 px either way;
        # adding the near LED panel (in the model's vent cell) lands at (1.14, 2.36, 1.64), next to the v1 pose
        # ceiling fixtures left out: the photo row reads LED, vent, LED, LED from the door end, the model vent, LED, -, LED
        # (vent and LED swapped); the T-grid lines do not match either
    '150435': dict(L=[('p10', [(334.4, 300), (334.9, 800), (335.5, 1300)]), ('p25', [(977, 250), (957.5, 700), (938, 1150)]),
                      ('syD', [(930, 1290), (990, 1250), (1045, 1210)])]),
        # passage jamb back edge (873,150)-(838,1240) px left out: real jamb ~0.2 m deep (model 0.12)
    '150439': dict(L=[('p25', [(523.3, 50), (519.7, 435), (516.2, 820)]), ('syD', [(530.3, 825.4), (755.9, 627.6), (981.4, 429.7)]),
                      ], zfix=1.3),
        # height is not observable from one corner + skirting (the solve slides along the view ray): fixed at 1.3 m
        # (standing, phone tilted ~45 deg down). The skirting bottom edge (527,881)-(1037,436) px would pull it to
        # <0.7 m with the model's 7 cm skirting, left out. Lab chairs in view were moved, not usable.
        # jamb back edge (356,100)-(353,780) px left out: real jamb ~0.2 m deep (model 0.12)
    '150448': dict(init=((1.6, 2.2, 1.4), (1.05, 0, 3.14)),   # (loc, blender euler) start: looking -y, down
                   L=[('cwf', [(999.8, 343.3), (1094.8, 348.7), (1189.9, 354.1)]), ('cwfb', [(999.9, 372.3), (1189.9, 383.3)]),
                      (((.58, 0, .90), (.58, 1, .90)), [(1323.3, 228.8), (1263.5, 301.3)]),       # worktop door end
                      (((.62, .60, 0), (.62, .60, 2)), [(1196.3, 400), (1193.7, 650), (1191.2, 900)]),  # end panel front
                      (((.62, 0, 0), (.62, 0, 2)), [(1315, 260.5), (1305, 450.5), (1295, 640.5)]),      # end panel / wall
                      ('sy0', [(129.8, 433.8), (229.6, 447.3), (329.3, 460.7)])]),
        # trunking top (560,148)-(880,134) px left out: same pose with or without it, but +-15 px off (real trunking
        # sits differently from the model's z 0.98..1.11)
    '122228': dict(L=[('p10', [(411, 250), (407.8, 575), (404.6, 900)]), ('p25', [(811.6, 150), (802, 595), (792.5, 1040)]),
                      ('pilr', [(266.4, 200.2), (256.6, 540.1), (246.8, 880)]), ('syD', [(333.4, 909), (391.2, 930.8), (449, 952.6)])]),
        # left out: passage jamb back edge (461 px, real jamb deeper than 0.12 m) and door frame edge at 187 px
        # (real wall between door and pillar differs, see 122224)
    '122244': dict(L=[('cWD', [(368.6, 100), (369.6, 370), (370.5, 640)]), ('wy18', [(615.5, 100), (615.3, 400), (615.2, 700)]),
                      ('pilE', [(1226.4, 100), (1222.7, 400), (1218.9, 700)]),
                      ('sill', [(620, 732.7), (890, 732.1), (1160, 731.6)]), ('dkf', [(200, 961.5), (530, 966.5), (860, 971.4)]),
                      ('dky', [(807.5, 782.4), (835.5, 870.6), (863.5, 958.8)])]),
        # left out: frame outer edges (photo frame 656..1131 px sits ~30 px wider than the model's frame at x 6.76) and
        # frame top (photo window is taller: head ~0.1 m above the model's 2.75 relative to the sill, also in 120939)
    '112212': dict(L=[('cWD', [(707.6, 30), (704.6, 245), (701.5, 460)]), ('wy18', [(917.3, 30.1), (905.1, 285), (892.8, 539.8)]),
                      ('syD', [(189.6, 1034.1), (309, 973), (428.4, 911.8)]), ('sill', [(879.1, 567.5), (1134.2, 596.8), (1389.3, 626.1)])]),
        # TV / niche left out: TV top (59,176)-(395,222), bottom (60,526)-(395,492), right (397,230)-(402,480) px do not
        # fit together with the shell (rms 18): the model TV + niche sit ~0.2-0.3 m too close to the window corner
        # (same offset in 122244). Desk / chairs were moved between photos.
}


def cams_table():
    src = open(os.path.join(ROOT, 'render', 'cameras.py')).read()
    out = {}
    for m in re.finditer(r"'(\d{6})': \(\(([^)]*)\), \(([^)]*)\), ([\d.]+), (\d+), (\d+)\)", src):
        out[m.group(1)] = ([float(v) for v in m.group(2).split(',')], [float(v) for v in m.group(3).split(',')],
                           float(m.group(4)), int(m.group(5)), int(m.group(6)))
    return out


def from_blender(loc, eul):
    Rbl = Rotation.from_euler('xyz', eul).as_matrix()
    Rcv = np.diag([1, -1, -1]) @ Rbl.T
    return np.concatenate([Rotation.from_matrix(Rcv).as_rotvec(), loc])


def to_blender(p):
    Rcv = Rotation.from_rotvec(p[:3]).as_matrix()
    return p[3:6], Rotation.from_matrix(Rcv.T @ np.diag([1, -1, -1])).as_euler('xyz')


def project(p, pts, size, f):
    Rm = Rotation.from_rotvec(p[:3]).as_matrix()
    pc = (np.atleast_2d(pts) - p[3:6]) @ Rm.T
    return np.stack([f * pc[:, 0] / pc[:, 2] + size[0] / 2, f * pc[:, 1] / pc[:, 2] + size[1] / 2], 1), pc[:, 2]


def residuals(p, pk, size, f):
    r = []
    for name, px in pk.get('P', []):
        uv, z = project(p, P[name] if isinstance(name, str) else X(*name), size, f)
        r += list(uv[0] - px) if z[0] > 0 else [1e3, 1e3]
    for name, pxs in pk.get('L', []):
        a, b = ref(name) if isinstance(name, str) else (X(*name[0]), X(*name[1]))
        Rm = Rotation.from_rotvec(p[:3]).as_matrix()
        za, zb = (Rm @ (a - p[3:6]))[2], (Rm @ (b - p[3:6]))[2]
        if min(za, zb) < .05:                             # clip to the front of the camera
            if max(za, zb) < .05:
                r += [1e3] * len(pxs); continue
            t = (.05 - za) / (zb - za)
            a, b = (a + (b - a) * t, b) if za < .05 else (a, a + (b - a) * t)
        uv, _ = project(p, np.array([a, b]), size, f)
        d = uv[1] - uv[0]
        n = np.array([-d[1], d[0]]) / (np.linalg.norm(d) + 1e-9)
        r += [float(np.dot(np.array(q) - uv[0], n)) for q in pxs]
    return np.array(r)


def rms(p, pk, size, f):
    return math.sqrt(np.mean(residuals(p, pk, size, f) ** 2))


def draw(d, p, pk, size, f, col):
    for name, pxs in pk.get('L', []):
        a, b = ref(name) if isinstance(name, str) else (X(*name[0]), X(*name[1]))
        pts = np.array([a + (b - a) * t for t in np.linspace(0, 1, 200)])
        uv, z = project(p, pts, size, f)
        uv = [tuple(q) for q, zz in zip(uv, z) if zz > .05 and -2000 < q[0] < 4000 and -2000 < q[1] < 4000]
        if len(uv) > 1:
            d.line(uv, fill=col, width=2)
    for name, _ in pk.get('P', []):
        uv, z = project(p, P[name] if isinstance(name, str) else X(*name), size, f)
        if z[0] > 0:
            d.ellipse([uv[0][0] - 6, uv[0][1] - 6, uv[0][0] + 6, uv[0][1] + 6], outline=col, width=2)


def solve(pid):
    pk = PICKS[pid]
    src = glob.glob(os.path.join(ROOT, 'Photos', '*', '*%s.jpg' % pid))[0]
    im = ImageOps.exif_transpose(Image.open(src)).convert('RGB')
    k = LONG / max(im.size)
    im = im.resize((round(im.size[0] * k), round(im.size[1] * k)), Image.LANCZOS)
    size = im.size
    f = LENS / SENSOR_W * LONG
    cams = cams_table()
    p0 = from_blender(*cams[pid][:2]) if pid in cams else from_blender(pk['init'][0], pk['init'][1])
    before = rms(p0, pk, size, f) if pid in cams else float('nan')
    lo = [-np.inf] * 3 + [-0.9, 0.02, 0.7]
    hi = [np.inf] * 3 + [6.48, 8.9, 1.8]
    if 'zfix' in pk:                                     # height not observable from the picks: fixed, see the note
        lo[5], hi[5] = pk['zfix'] - 1e-3, pk['zfix'] + 1e-3
    best = None
    rng = np.random.default_rng(1)
    for i in range(30):
        x0 = p0 + (np.concatenate([rng.normal(0, .08, 3), rng.normal(0, .25, 3)]) if i else 0)
        x0 = np.clip(x0, np.array(lo) + 1e-3, np.array(hi) - 1e-3)
        res = least_squares(residuals, x0, args=(pk, size, f), loss='soft_l1', f_scale=4.0, bounds=(lo, hi))
        if best is None or res.cost < best.cost:
            best = res
    p = best.x
    after = rms(p, pk, size, f)
    loc, eul = to_blender(p)
    bound = [n for n, v, l_, h_ in zip('xyz', p[3:], lo[3:], hi[3:]) if min(v - l_, h_ - v) < 1e-3 and h_ - l_ > .01]
    d = ImageDraw.Draw(im)
    if pid in cams:
        draw(d, p0, pk, size, f, (255, 40, 40))
    draw(d, p, pk, size, f, (40, 255, 40))
    for _, pxs in pk.get('L', []):
        for q in pxs:
            d.rectangle([q[0] - 4, q[1] - 4, q[0] + 4, q[1] + 4], outline=(0, 220, 255), width=2)
    for _, q in pk.get('P', []):
        d.rectangle([q[0] - 4, q[1] - 4, q[0] + 4, q[1] + 4], outline=(0, 220, 255), width=2)
    os.makedirs(OUT, exist_ok=True)
    im.save(os.path.join(OUT, '%s_fit.jpg' % pid), quality=88)
    res_after = residuals(p, pk, size, f)
    line = ("    '%s': ((%.4f, %.4f, %.4f), (%.5f, %.5f, %.5f), %.3f, %d, %d),  # rms %.1f px (was %.1f)%s"
            % (pid, *loc, *eul, LENS, size[0], size[1], after, before, ' BOUND ' + ''.join(bound) if bound else ''))
    print(line)
    if '--write' in sys.argv:                            # replace / add this camera's line in render/cameras.py
        fn = os.path.join(ROOT, 'render', 'cameras.py')
        src = open(fn).read()
        m = re.search(r"\n    '%s': \(\(.*" % pid, src)
        src = src.replace(m.group(0), '\n' + line) if m else src.replace('\n}\n', '\n' + line + '\n}\n', 1)
        open(fn, 'w').write(src)
    print('      residuals', np.round(res_after, 1).tolist())
    return before, after


if __name__ == '__main__':
    ids = [a for a in sys.argv[1:] if not a.startswith('-')] or list(PICKS)
    for pid in ids:
        solve(pid)
