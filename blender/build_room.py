# Rebuild the room from room_plan.py in Blender.
# Run: blender -b main.blend --python build_room.py
# Units: metres. Origin = interior bottom-left corner of the plan, x along 650, y along 250, z up.
# Plan lines are interior faces; wall thickness grows outward.
import math
import bpy

W, D, H = 6.50, 2.50, 2.90
T = 0.10                 # outer/side walls
T_TOP = 0.12             # partition to the lab (holds TV niche)
T_WIN = 0.10             # window wall

# Openings (assumed heights from photos, plan gives only widths)
DOOR_Y0, DOOR_Y1, DOOR_H = 1.15, 1.90, 2.10            # left wall: 115 / 75 / 40 / 20
PILLAR_Y = D - 0.20                                     # door frame runs on to the pillar corner
PASS_X0, PASS_X1, PASS_H = 1.00, 2.50, 2.40            # top wall: 25 pillar / 75 / 150 passage / 400
WIN_Y0, WIN_Y1, WIN_Z0, WIN_Z1 = 0.20, 1.80, 0.85, 2.87  # right wall: 20 / 160 / 70; head 2.87 (122244 frame top)
# s3_geo: niche outer edges on y=2.5 from 112212 / 122244 (x1 5.44 / 5.56, z .96..1.90), width from the 150338 ratio
NICHE_X0, NICHE_X1, NICHE_Z0, NICHE_Z1, NICHE_D = 4.07, 5.50, 0.98, 1.89, 0.06
LEAF = 0.85


# ---------- mesh helpers ----------

def box_faces(lo, hi, base=0):
    (x0, y0, z0), (x1, y1, z1) = lo, hi
    v = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
         (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    f = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    return v, [tuple(i + base for i in q) for q in f]


def boxes_mesh(boxes):
    """Disjoint closed boxes in one mesh (furniture, frames)."""
    verts, faces = [], []
    for lo, hi in boxes:
        v, f = box_faces(lo, hi, len(verts))
        verts += v
        faces += f
    return verts, faces


def solid_mesh(solids, holes=()):
    """Boolean-free union of boxes minus holes, as one manifold all-quad mesh.
    Splits space on every box coordinate and keeps only boundary faces between
    solid and empty cells, so openings get clean edge loops instead of n-gons."""
    axes = [sorted({round(b[s][a], 4) for b in (*solids, *holes) for s in (0, 1)}) for a in range(3)]

    def inside(p, b):
        return all(b[0][a] < p[a] < b[1][a] for a in range(3))

    def solid(i, j, k):
        n = (i, j, k)
        if any(n[a] < 0 or n[a] >= len(axes[a]) - 1 for a in range(3)):
            return False
        c = [(axes[a][n[a]] + axes[a][n[a] + 1]) / 2 for a in range(3)]
        return any(inside(c, b) for b in solids) and not any(inside(c, b) for b in holes)

    verts, index, faces = [], {}, []

    def vid(p):
        if p not in index:
            index[p] = len(verts)
            verts.append(p)
        return index[p]

    nx, ny, nz = (len(a) - 1 for a in axes)
    for i in range(nx):
        for j in range(ny):
            for k in range(nz):
                if not solid(i, j, k):
                    continue
                n = (i, j, k)
                for a in range(3):
                    b, c = (a + 1) % 3, (a + 2) % 3
                    for step in (1, -1):
                        m = list(n)
                        m[a] += step
                        if solid(*m):
                            continue
                        pa = axes[a][n[a] + (1 if step > 0 else 0)]
                        b0, b1 = axes[b][n[b]], axes[b][n[b] + 1]
                        c0, c1 = axes[c][n[c]], axes[c][n[c] + 1]
                        quad = [(b0, c0), (b1, c0), (b1, c1), (b0, c1)]
                        if step < 0:
                            quad.reverse()
                        pts = []
                        for qb, qc in quad:
                            p = [0, 0, 0]
                            p[a], p[b], p[c] = pa, qb, qc
                            pts.append(vid(tuple(p)))
                        faces.append(tuple(pts))
    return verts, faces


# ---------- scene helpers ----------

def material(name, rgb, rough=0.6):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.diffuse_color = (*rgb, 1)
    if m.node_tree is None:
        m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (*rgb, 1)
        bsdf.inputs["Roughness"].default_value = rough
    return m


def collection(name):
    c = bpy.data.collections.get(name)
    if c:
        for o in list(c.objects):
            bpy.data.objects.remove(o, do_unlink=True)
    else:
        c = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(c)
    return c


def add(name, mesh_data, mat, coll, loc=(0, 0, 0), rot_z=0.0):
    old = bpy.data.meshes.get(name)
    if old and old.users == 0:
        bpy.data.meshes.remove(old)
    me = bpy.data.meshes.new(name)
    verts, faces = mesh_data
    me.from_pydata(verts, [], faces)
    me.validate()
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    ob.location = loc
    ob.rotation_euler.z = rot_z
    coll.objects.link(ob)
    return ob


# ---------- build ----------

if "Cube" in bpy.data.objects:
    bpy.data.objects.remove(bpy.data.objects["Cube"], do_unlink=True)

WALL = material("Wall", (0.85, 0.85, 0.83))
FLOOR = material("Floor_Terrazzo", (0.55, 0.54, 0.52))
WHITE = material("Frame_White", (0.95, 0.95, 0.95), 0.3)
PINK = material("Door_Pink", (0.85, 0.05, 0.40), 0.4)
BLACK = material("Black", (0.03, 0.03, 0.03), 0.4)
DESK = material("Desk_White", (0.88, 0.88, 0.86), 0.4)
METAL = material("Metal", (0.6, 0.6, 0.62), 0.25)

walls = collection("Walls")
openings = collection("Openings")
furniture = collection("Furniture")

# Long walls own the corners; short walls sit between them.
add("Wall_Bottom", solid_mesh([((-T, -T, 0), (W + T_WIN, 0, H))]), WALL, walls)

add("Wall_Top", solid_mesh(
    [((-T, D, 0), (W + T_WIN, D + T_TOP, H))],
    [((PASS_X0, D, 0), (PASS_X1, D + T_TOP, PASS_H)),
     ((NICHE_X0, D, NICHE_Z0), (NICHE_X1, D + NICHE_D, NICHE_Z1))]), WALL, walls)

add("Wall_Left", solid_mesh(
    [((-T, 0, 0), (0, D, H))],
    [((-T, DOOR_Y0, 0), (0, PILLAR_Y, DOOR_H))]), WALL, walls)

add("Wall_Right", solid_mesh(
    [((W, 0, 0), (W + T_WIN, D, H))],
    [((W, WIN_Y0, WIN_Z0), (W + T_WIN, WIN_Y1, WIN_Z1))]), WALL, walls)

add("Pillar", solid_mesh([((0, PILLAR_Y, 0), (0.25, D, H))]), WALL, walls)
add("Floor", solid_mesh([((-T, -T, -0.10), (W + T_WIN, D + T_TOP, 0))]), FLOOR, walls)

# Door: pink frame from the opening to the pillar corner, post at the leaf's closing edge,
# fixed side panel filling the 40 between post and pillar (as in the photos).
f = 0.05
add("Door_Frame", solid_mesh([
    ((-T, DOOR_Y0, 0), (0, DOOR_Y0 + f, DOOR_H)),                    # hinge jamb
    ((-T, PILLAR_Y - f, 0), (0, PILLAR_Y, DOOR_H)),                  # jamb at pillar corner
    ((-T, DOOR_Y1 - f / 2, 0), (0, DOOR_Y1 + f / 2, DOOR_H)),        # post
    ((-T, DOOR_Y0, DOOR_H - f), (0, PILLAR_Y, DOOR_H)),              # head
]), PINK, openings)
add("Door_Fixed_Panel", boxes_mesh([
    ((-T / 2 - 0.02, DOOR_Y1 + f / 2, 0.01), (-T / 2 + 0.02, PILLAR_Y - f, DOOR_H - f)),
]), PINK, openings)
# Plan: leaf 85 hinged at bottom of opening, tip touching x = sqrt(85^2 - 75^2) at the opening's top.
tip_x = math.sqrt(LEAF**2 - (DOOR_Y1 - DOOR_Y0) ** 2)
add("Door_Leaf", boxes_mesh([((0, 0, 0.01), (0.04, LEAF, DOOR_H - f))]), PINK, openings,
    loc=(0, DOOR_Y0, 0), rot_z=-math.atan2(tip_x, DOOR_Y1 - DOOR_Y0))

# Window: frame set in the reveal, 3 panes wide, transom with 3 top lights.
fw, fx0, fx1 = 0.06, W + 0.02, W + 0.08
tr = 2.15                                     # transom height
m1 = WIN_Y0 + (WIN_Y1 - WIN_Y0) / 3
m2 = WIN_Y0 + 2 * (WIN_Y1 - WIN_Y0) / 3
add("Window_Frame", solid_mesh([
    ((fx0, WIN_Y0, WIN_Z0), (fx1, WIN_Y1, WIN_Z0 + fw)),              # bottom
    ((fx0, WIN_Y0, WIN_Z1 - fw), (fx1, WIN_Y1, WIN_Z1)),              # top
    ((fx0, WIN_Y0, WIN_Z0), (fx1, WIN_Y0 + fw, WIN_Z1)),              # sides
    ((fx0, WIN_Y1 - fw, WIN_Z0), (fx1, WIN_Y1, WIN_Z1)),
    ((fx0, WIN_Y0, tr), (fx1, WIN_Y1, tr + fw)),                      # transom
    ((fx0, m1 - fw / 2, WIN_Z0), (fx1, m1 + fw / 2, WIN_Z1)),         # mullions
    ((fx0, m2 - fw / 2, WIN_Z0), (fx1, m2 + fw / 2, WIN_Z1)),
]), WHITE, openings)
add("Window_Sill", boxes_mesh([((W - 0.20, WIN_Y0, WIN_Z0), (fx0, WIN_Y1, WIN_Z0 + 0.03))]), WHITE, openings)

# Kitchen sideboard on the long wall near the door end.
cx0, cx1, cd = 0.50, 2.70, 0.60
add("Cabinet", boxes_mesh([
    ((cx0 + 0.02, 0.05, 0), (cx1 - 0.02, cd - 0.03, 0.10)),           # plinth
    ((cx0, 0, 0.10), (cx1, cd, 0.87)),                                # carcass
    ((cx0 - 0.02, 0, 0.87), (cx1 + 0.02, cd + 0.02, 0.90)),           # worktop
]), BLACK, furniture)

# Desk (two 80x80 tables) in the window / partition corner.
tx0, tx1, ty0, ty1, th, lg = W - 1.60, W - 0.02, D - 0.80, D - 0.02, 0.75, 0.04
add("Desk", boxes_mesh(
    [((tx0, ty0, th - 0.03), (tx1, ty1, th))] +
    [((x, y, 0), (x + lg, y + lg, th - 0.03))
     for x in (tx0 + 0.03, tx1 - 0.03 - lg) for y in (ty0 + 0.03, ty1 - 0.03 - lg)]), DESK, furniture)


def chair(cx, cy):
    s, sh, lg = 0.44, 0.46, 0.025
    x0, y0 = cx - s / 2, cy - s / 2
    legs = [((x, y, 0), (x + lg, y + lg, sh - 0.04))
            for x in (x0 + 0.02, x0 + s - 0.02 - lg) for y in (y0 + 0.02, y0 + s - 0.02 - lg)]
    return boxes_mesh(legs + [
        ((x0, y0, sh - 0.04), (x0 + s, y0 + s, sh)),                  # seat, facing +x
        ((x0 - 0.03, y0 + 0.02, sh + 0.08), (x0, y0 + s - 0.02, sh + 0.42)),  # back
    ])


add("Chair_1", chair(tx0 - 0.25, 1.80), BLACK, furniture)
add("Chair_2", chair(tx0 - 0.25, 2.26), BLACK, furniture)

add("Monitor", boxes_mesh([
    ((W - 0.30, D - 0.70, th), (W - 0.24, D - 0.10, th + 0.38)),
]), BLACK, furniture)
add("TV", boxes_mesh([
    ((NICHE_X0 + 0.15, D + NICHE_D - 0.04, NICHE_Z0 + 0.10), (NICHE_X1 - 0.15, D + NICHE_D, NICHE_Z1 - 0.10)),
]), BLACK, furniture)
add("Radiator", boxes_mesh([((W - 0.12, 0.55, 0.12), (W - 0.03, 1.55, 0.68))]), WHITE, furniture)

# Camera from the door corner looking at the window.
cam = bpy.data.objects.get("Camera")
if cam:
    cam.location = (0.4, 0.3, 1.7)
    cam.rotation_euler = (math.radians(82), 0, math.radians(-72))
    cam.data.lens = 18

bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
print("ROOM BUILT", [o.name for c in (walls, openings, furniture) for o in c.objects])
