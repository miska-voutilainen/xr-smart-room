"""Blender -> Unity 2022.3 LTS (URP 14, OpenXR, XRI 3.5) export pipeline.  Owner: g3_export.
Contract with the Unity side: unity/OrangeRoom/README.md ("Export contract") + Assets/Editor/OrangeRoomImport.cs.

Runs on a BUILT COPY of main.blend and never saves the .blend (main.blend is refused):
    W=<work dir>; cp main.blend apply_materials.py $W/; cp -r materials shaders render $W/
    tools/bl -b $W/build.blend --python build_room.py --python $W/apply_materials.py
    tools/bl --gpu -b $W/build.blend --python unity/export_unity.py -- --out $W/out/Assets --quality low
    tools/bl -b --factory-startup --python unity/_validate_fbx.py -- $W/out/Assets
--out is a Unity "Assets" folder: writes Models/{Room1,Room2,Room3,Exterior}.fbx + Models/OrangeRoom_manifest.json and
Textures/<Material>_{BaseColor,Normal,MetallicSmoothness,AO,Emission}.png. Stable names, overwritten in place
(Unity .meta GUIDs are keyed on the path).

Steps: realize instances + apply modifiers -> split glass faces (inner pane face only) -> triangulate
 -> UV0 = one Smart-UV atlas PER MATERIAL across every object using it (uniform texel density, so the per-material
    textures the Unity importer looks up by name are shared and static batching works)
 -> Cycles bake per material: BaseColor(+alpha) / Normal (tangent, OpenGL +Y) / Metallic / Roughness / AO / Emission
 -> URP packing, image-based materials under the SAME material names
 -> UV1 lightmap layer per object (Smart UV, padding sized for 40 texels/m)
 -> pivots (grabbables: centre, chairs: floor under seat, Door_Leaf: hinge) -> LOD0..2 for heavy meshes -> FBX per area.
Baking happens before any origin change: the procedural shaders read Object/Generated coordinates.
No joins: the Unity side keys behaviour on Blender object names, and static batching + the SRP Batcher merge
same-material statics at build time anyway (one atlas per material makes that possible).
"""
import json
import math
import os
import re
import sys
import time

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

# ---------------------------------------------------------------- config
QUALITY = {  # div = texture size divisor; samples for emission-type passes, normal, AO
    "low": dict(div=4, s_emit=1, s_nrm=1, s_ao=4),          # phase-1 smoke test
    "high": dict(div=1, s_emit=8, s_nrm=8, s_ao=64),
}
DENSITY = 512            # px per metre (PCVR). Quest: export with RES_MAX 1024 / halve, see report
RES_MIN, RES_MAX = 256, 2048   # OrangeRoomImport.cs caps textures at 2048
MARGIN_PX = 8            # bake dilation at full res; UV0 island gap = 2 * MARGIN_PX
AO_DISTANCE = 0.5        # m
LIGHTMAP_TPU = 40        # texels/m in OrangeRoomSceneBuilder.cs -> UV1 padding
LIGHTMAP_PAD = 4         # texels between UV1 islands
LOD_TRIS = 5000
LOD_NAMES = re.compile(r"(?i)radiator|chair|tree")
LOD_RATIOS = (0.5, 0.2)
SKIP = re.compile(r"^Ext_Rain")             # rain: Unity particle system instead
# mirrors OrangeRoomSceneBuilder.cs name rules
DOOR_LEAF = "Door_Leaf"
CHAIR_PREFIX = "Chair_"
GRAB_PARTS = ("Remote", "Cup", "Mug", "Bottle", "RobotCam")
AREAS = (("Exterior", re.compile(r"^Ext_"), "Exterior"), ("Room2", re.compile(r"^Room2_"), "Room2"),
         ("Room3", re.compile(r"^Room3_"), "Room3"))  # else Room1

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def arg(name, default):
    return ARGS[ARGS.index(name) + 1] if name in ARGS else default


# Default --out: in the team repo layout (blender/unity_export/export_unity.py) the Unity project is ../../unity;
# in the local layout (unity/export_unity.py) keep the old <blend dir>/unity_out/Assets. --out always wins.
_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO_ASSETS = os.path.join(_HERE, "..", "..", "unity", "Assets")
_DEFAULT_OUT = (_REPO_ASSETS if os.path.basename(_HERE) == "unity_export" and os.path.isdir(_REPO_ASSETS)
                else os.path.join(os.path.dirname(bpy.data.filepath), "unity_out", "Assets"))
OUT = os.path.abspath(arg("--out", _DEFAULT_OUT))
QNAME = arg("--quality", "low")
ONLY = set(arg("--areas", "").split(",")) - {""}   # e.g. --areas Room1: export a subset (trial runs)
Q = QUALITY[QNAME]
MODELS, TEXTURES = os.path.join(OUT, "Models"), os.path.join(OUT, "Textures")
scene = bpy.context.scene
vl = bpy.context.view_layer


def log(*a):
    print("[export_unity]", *a, flush=True)


if os.path.basename(bpy.data.filepath) == "main.blend":
    raise SystemExit("export_unity: refusing to run on main.blend, use a built copy")


# ---------------------------------------------------------------- helpers
def select(objs, active=None):
    if bpy.context.object and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    vl.objects.active = active or (objs[0] if objs else None)


def meshes():
    return [o for o in scene.objects if o.type == "MESH"]


def tris(o):
    return sum(len(p.vertices) - 2 for p in o.data.polygons) if o.type == "MESH" else 0


def face_area_world(o, idx=None):
    s = abs(o.matrix_world.to_3x3().determinant()) ** (1 / 3)
    return sum(p.area for p in o.data.polygons if idx is None or p.material_index in idx) * s * s


def world_bbox(objs):
    pts = [o.matrix_world @ Vector(c) for o in objs if o.type == "MESH" for c in o.bound_box]
    return (Vector([min(p[i] for p in pts) for i in range(3)]), Vector([max(p[i] for p in pts) for i in range(3)]))


def descendants(o):
    return [d for c in o.children for d in [c] + descendants(c)]


def top(o):
    while o.parent:
        o = o.parent
    return o


def area_of(o):
    t = top(o)
    for name, pat, coll in AREAS:
        if pat.search(t.name) or any(c.name == coll for c in t.users_collection):
            return name
    return "Room1"


def surface_socket(mat):
    if not mat or not mat.node_tree:
        return None
    outs = [n for n in mat.node_tree.nodes if n.type == "OUTPUT_MATERIAL" and n.target in ("ALL", "CYCLES")]
    out = next((n for n in outs if n.is_active_output), outs[0] if outs else None)
    return out.inputs["Surface"] if out else None


def all_nodes(tree, seen=None):
    seen = seen if seen is not None else set()
    for n in tree.nodes:
        yield n
        if n.type == "GROUP" and n.node_tree and n.node_tree.name not in seen:
            seen.add(n.node_tree.name)
            yield from all_nodes(n.node_tree, seen)


def is_glass(mat):
    """Transmissive glass (not alpha cut-outs: Mix(Transparent, BSDF) leaf cards are baked with alpha)."""
    if not mat or not mat.node_tree:
        return False
    if "Glass" in mat.name:              # the Unity importer keys glass on this name
        return True
    for n in all_nodes(mat.node_tree):
        if n.type in ("BSDF_GLASS", "BSDF_REFRACTION"):
            return True
        tw = n.inputs.get("Transmission Weight") if n.type == "BSDF_PRINCIPLED" else None
        if tw and not tw.is_linked and tw.default_value > 0.5:
            return True
    return False


def has_emission(mat):
    for n in all_nodes(mat.node_tree):
        if n.type == "EMISSION":
            return True
        if n.type == "BSDF_PRINCIPLED":
            s, c = n.inputs["Emission Strength"], n.inputs["Emission Color"]
            if (s.is_linked or s.default_value > 0) and (c.is_linked or max(c.default_value[:3]) > 0):
                return True
    return False


def has_alpha(mat):
    return any(n.type == "BSDF_TRANSPARENT" or n.type == "BSDF_PRINCIPLED" and (
        n.inputs["Alpha"].is_linked or n.inputs["Alpha"].default_value < 0.999) for n in all_nodes(mat.node_tree))


# ---------------------------------------------------------------- 1. prepare
def prepare():
    for o in scene.objects:
        o.hide_set(False)
        o.hide_viewport = o.hide_select = False
    # drop what Cycles would not render, SKIP and other areas; removed only after the convert below, because
    # geometry-node instancers (Ext_Leaves) read hide-render source objects (Ext_Leaf)
    drop = [o for o in scene.objects if o.hide_render or any(c.hide_render for c in o.users_collection)
            or SKIP.search(o.name) or (ONLY and area_of(o) not in ONLY)]
    if ONLY:   # a material also used outside this subset gets an own copy: its UV0 atlas / textures differ per run
        hidden = {o for o in drop if area_of(o) in ONLY}
        outside = {s.material for o in drop if o not in hidden for s in o.material_slots if s.material}
        for o in scene.objects:
            if o in drop:
                continue
            for s in o.material_slots:
                if s.material in outside:
                    name = f"{s.material.name}_{area_of(o)}"
                    s.material = bpy.data.materials.get(name) or s.material.copy()
                    s.material.name = name
    inst = [o for o in scene.objects if o not in drop and (o.instance_type != "NONE" or any(
        ps.settings.render_type in ("OBJECT", "COLLECTION") for ps in getattr(o, "particle_systems", [])))]
    if inst:
        select(inst)
        bpy.ops.object.duplicates_make_real()
        for o in inst:
            if o.particle_systems and not all(ps.settings.use_render_emitter for ps in o.particle_systems):
                bpy.data.objects.remove(o, do_unlink=True)
    geo = [o for o in scene.objects if o.type in ("MESH", "CURVE", "SURFACE", "META", "FONT") and o not in drop]
    hair = [o.name for o in scene.objects if o.type == "CURVES"]
    if hair:
        log("WARNING hair curves not exported:", hair)
    select(geo)
    bpy.ops.object.make_single_user(object=True, obdata=True, material=False)
    bpy.ops.object.convert(target="MESH")          # applies modifiers, realizes geometry-node instances
    for o in drop:
        bpy.data.objects.remove(o, do_unlink=True)
    for o in meshes():
        surf = [surface_socket(s.material) for s in o.material_slots]
        if not o.data.polygons or (surf and all(s is not None and not s.is_linked for s in surf)):
            log("skip (no faces / volume-only):", o.name)
            bpy.data.objects.remove(o, do_unlink=True)


def split_glass():
    """Glass faces -> own object '<name>_Glass' (not baked; URP transparent by material name on the Unity side).
    Texspace is frozen first so Generated coordinates of the remainder stay identical for the bake."""
    for o in meshes():
        g = [i for i, s in enumerate(o.material_slots) if is_glass(s.material)]
        if not g or len(g) == len(o.material_slots):
            continue
        me = o.data
        loc, size = tuple(me.texspace_location), tuple(me.texspace_size)
        me.use_auto_texspace = False
        me.texspace_location, me.texspace_size = loc, size
        gl = o.copy()
        gl.data = me.copy()
        gl.name = o.name + "_Glass"
        for c in o.users_collection:
            c.objects.link(gl)
        for ob, drop_glass in ((o, True), (gl, False)):
            bm = bmesh.new()
            bm.from_mesh(ob.data)
            bmesh.ops.delete(bm, geom=[f for f in bm.faces if (f.material_index in g) == drop_glass], context="FACES")
            bm.to_mesh(ob.data)
            bm.free()


def inner_glass(glass, centres):
    """Keep only the big pane faces that look into the room: one transparent layer instead of a sealed box."""
    for o in glass:
        c = centres.get(area_of(o))
        if c is None:
            continue
        bm = bmesh.new()
        bm.from_mesh(o.data)
        bm.transform(o.matrix_world)
        big = max((f.calc_area() for f in bm.faces), default=0)
        drop = [f for f in bm.faces if f.calc_area() < 0.05 * big or f.normal.dot(c - f.calc_center_median()) <= 0]
        if len(drop) < len(bm.faces):
            bmesh.ops.delete(bm, geom=drop, context="FACES")
            bm.transform(o.matrix_world.inverted())
            bm.to_mesh(o.data)
        bm.free()


def triangulate(objs):
    """Triangulate now so Unity's MikkTSpace sees the same triangles the normal maps were baked on."""
    select(objs)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.quads_convert_to_tris(quad_method="BEAUTY", ngon_method="BEAUTY")
    bpy.ops.object.mode_set(mode="OBJECT")


# ---------------------------------------------------------------- 2. UVs
def tex_res(area):
    """Full-quality texture size for a surface area at DENSITY (power of two, clamped)."""
    r = 2 ** round(math.log2(max(math.sqrt(area) * DENSITY, 1)))
    return min(max(r, RES_MIN), RES_MAX)


def ensure_uv(o, name):
    uv = o.data.uv_layers.get(name) or o.data.uv_layers.new(name=name)
    o.data.uv_layers.active = uv          # editing target; existing maps stay render-active for the bake


def unwrap(objs, face_sel, margin):
    """Smart UV on the faces face_sel(obj) of objs, packed together into 0..1 of the active UV layer."""
    scene.tool_settings.mesh_select_mode = (False, False, True)
    for o in objs:
        me, sel = o.data, face_sel(o)
        mi = np.empty(len(me.polygons), np.int32)
        me.polygons.foreach_get("material_index", mi)
        fs = np.isin(mi, list(sel)) if sel is not None else np.ones(len(mi), bool)
        me.polygons.foreach_set("select", fs)
        vs = np.zeros(len(me.vertices), bool)
        for p in np.flatnonzero(fs):
            vs[list(me.polygons[p].vertices)] = True
        me.vertices.foreach_set("select", vs)
        es = np.array([vs[e.vertices[0]] and vs[e.vertices[1]] for e in me.edges], bool)
        me.edges.foreach_set("select", es)
    select(objs)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=margin, area_weight=0.0,
                             correct_aspect=True, scale_to_bounds=False)
    bpy.ops.object.mode_set(mode="OBJECT")


def slots_of(o, mat):
    return {i for i, s in enumerate(o.material_slots) if s.material == mat}


# ---------------------------------------------------------------- 3. bake
REWIRE = {  # pass -> (inputs read, constant for shaders without one)
    "base": (("Base Color", "Color"), (0, 0, 0, 1)),
    "metal": (("Metallic",), (0, 0, 0, 1)),
    "rough": (("Roughness",), (1, 1, 1, 1)),
    "alpha": (("Alpha",), (1, 1, 1, 1)),
}
CONST_SHADERS = {"EMISSION", "BACKGROUND", "HOLDOUT", "BSDF_TRANSPARENT"}


def coated(n):
    w = n.inputs["Coat Weight"]
    return w.is_linked or w.default_value > 0


def coat_roughness(tree, n):
    """URP Lit has one specular lobe: fold the clear coat into it, r + w * (min(r, coat_r) - r)."""
    def val(sock):
        if sock.is_linked:
            return sock.links[0].from_socket
        v = tree.nodes.new("ShaderNodeValue")
        v.outputs[0].default_value = sock.default_value
        return v.outputs[0]

    def math(op, a, b):
        m = tree.nodes.new("ShaderNodeMath")
        m.operation = op
        tree.links.new(a, m.inputs[0])
        tree.links.new(b, m.inputs[1])
        return m.outputs[0]
    r = val(n.inputs["Roughness"])
    d = math("SUBTRACT", math("MINIMUM", r, val(n.inputs["Coat Roughness"])), r)
    return math("ADD", r, math("MULTIPLY", val(n.inputs["Coat Weight"]), d))


def rewire(tree, pas):
    """Replace every shader node by an Emission of the wanted input, keeping Mix/Add shader structure.
    (DIFFUSE/COLOR bakes return black for metals, hence emission.)"""
    names, const = REWIRE[pas]
    for n in list(tree.nodes):
        if n.type == "GROUP" and n.node_tree:
            n.node_tree = n.node_tree.copy()
            rewire(n.node_tree, pas)
            continue
        if n.type in ("MIX_SHADER", "ADD_SHADER") or not n.outputs or n.outputs[0].type != "SHADER":
            continue
        e = tree.nodes.new("ShaderNodeEmission")
        e.inputs["Strength"].default_value = 1.0
        src = None if n.type in CONST_SHADERS else next((n.inputs[k] for k in names if k in n.inputs), None)
        if n.type == "BSDF_TRANSPARENT" and pas == "alpha":
            e.inputs["Color"].default_value = (0, 0, 0, 1)
        elif src is None:
            e.inputs["Color"].default_value = const
        elif pas == "rough" and n.type == "BSDF_PRINCIPLED" and coated(n):
            tree.links.new(coat_roughness(tree, n), e.inputs["Color"])
        elif src.is_linked:
            tree.links.new(src.links[0].from_socket, e.inputs["Color"])
        else:
            v = src.default_value
            e.inputs["Color"].default_value = (v, v, v, 1) if isinstance(v, float) else tuple(v)
        for lk in list(n.outputs[0].links):
            tree.links.new(e.outputs[0], lk.to_socket)


def new_image(name, res, noncolor, float_buf=False):
    old = bpy.data.images.get(name)
    if old:
        bpy.data.images.remove(old)
    img = bpy.data.images.new(name, res, res, alpha=True, float_buffer=float_buf)
    img.colorspace_settings.name = "Non-Color" if noncolor else "sRGB"
    return img


_dummy = {}


def dummy_material():
    """Bake target for the other slots of an object (Cycles needs an active image in every material)."""
    if "m" not in _dummy:
        m = bpy.data.materials.new("_bake_dummy")
        m.use_nodes = True
        t = m.node_tree.nodes.new("ShaderNodeTexImage")
        t.image = new_image("_bake_dummy", 8, True)
        m.node_tree.nodes.active = t
        _dummy["m"] = m
    return _dummy["m"]


def bake_pass(objs, mat, pas, img, samples):
    c = mat.copy()
    if pas in REWIRE:
        rewire(c.node_tree, pas)
    t = c.node_tree.nodes.new("ShaderNodeTexImage")
    t.image = img
    c.node_tree.nodes.active = t
    saved = [(s, s.material) for o in objs for s in o.material_slots]
    for s, m in saved:
        s.material = c if m == mat else dummy_material()
    scene.cycles.samples = samples
    select(objs)
    t0 = time.time()
    bpy.ops.object.bake(type={"normal": "NORMAL", "ao": "AO"}.get(pas, "EMIT"),
                        margin=max(2, MARGIN_PX // Q["div"]), margin_type="ADJACENT_FACES", use_clear=True,
                        uv_layer="UV0", target="IMAGE_TEXTURES",
                        normal_space="TANGENT", normal_r="POS_X", normal_g="POS_Y", normal_b="POS_Z")
    log(f"    {pas:6s} {img.size[0]}px {time.time() - t0:.1f}s")
    for s, m in saved:
        s.material = m
    bpy.data.materials.remove(c)


def px(img):
    a = np.empty(img.size[0] * img.size[1] * 4, np.float32)
    img.pixels.foreach_get(a)
    return a.reshape(-1, 4)


def save(img, arr, path):
    img.pixels.foreach_set(np.ascontiguousarray(arr, np.float32).ravel())
    img.filepath_raw = path
    img.file_format = "PNG"
    img.save()
    bpy.data.images.remove(img)


def lin2srgb(x):
    x = np.clip(x, 0, 1)
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * np.power(x, 1 / 2.4) - 0.055)


def bake_material(mat, objs, res):
    """Bakes all maps of one material over all objects using it. Returns manifest info."""
    stem = os.path.join(TEXTURES, mat.name)
    ones = np.ones(res * res, np.float32)

    def gray(pas, samples):
        im = new_image("_tmp_" + pas, res, True)
        bake_pass(objs, mat, pas, im, samples)
        a = px(im)[:, 0].copy()
        bpy.data.images.remove(im)
        return a

    base = new_image(mat.name + "_BaseColor", res, False)
    bake_pass(objs, mat, "base", base, Q["s_emit"])
    rgba = px(base)
    alpha = has_alpha(mat)
    rgba[:, 3] = gray("alpha", Q["s_emit"]) if alpha else 1.0
    save(base, rgba, stem + "_BaseColor.png")

    nrm = new_image(mat.name + "_Normal", res, True)
    bake_pass(objs, mat, "normal", nrm, Q["s_nrm"])
    a = px(nrm)
    a[:, 3] = 1.0
    save(nrm, a, stem + "_Normal.png")

    metal, rough, ao = gray("metal", Q["s_emit"]), gray("rough", Q["s_emit"]), gray("ao", Q["s_ao"])
    save(new_image(mat.name + "_MetallicSmoothness", res, True), np.stack([metal, ao, 0 * ones, 1 - rough], 1),
         stem + "_MetallicSmoothness.png")                       # URP: R metallic, A smoothness (G = AO, unused)
    save(new_image(mat.name + "_AO", res, True), np.stack([ao, ao, ao, ones], 1), stem + "_AO.png")  # URP reads G

    info = {"resolution": res, "alpha": alpha, "emission_intensity": 0.0,
            "maps": ["BaseColor", "Normal", "MetallicSmoothness", "AO"]}
    if has_emission(mat):
        em = new_image("_tmp_emit", res, True, float_buf=True)
        bake_pass(objs, mat, "emit", em, Q["s_emit"])
        a = px(em)
        bpy.data.images.remove(em)
        peak = float(a[:, :3].max())
        if peak > 1e-4:
            k = max(peak, 1.0)       # LDR map normalized to 1, HDR multiplier goes to the manifest
            save(new_image(mat.name + "_Emission", res, True),
                 np.concatenate([lin2srgb(a[:, :3] / k), ones[:, None]], 1), stem + "_Emission.png")
            info["emission_intensity"] = round(k, 4)
            info["maps"].append("Emission")
    return info


def image_material(mat, info):
    """Rebuild mat (same name: the Unity importer finds textures by material name) on the baked maps."""
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    p = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(p.outputs[0], out.inputs["Surface"])

    def img(m, noncolor):
        t = nt.nodes.new("ShaderNodeTexImage")
        t.image = bpy.data.images.load(os.path.join(TEXTURES, f"{mat.name}_{m}.png"), check_existing=True)
        t.image.colorspace_settings.name = "Non-Color" if noncolor else "sRGB"
        return t

    t = img("BaseColor", False)
    nt.links.new(t.outputs["Color"], p.inputs["Base Color"])
    if info["alpha"]:
        nt.links.new(t.outputs["Alpha"], p.inputs["Alpha"])
    nm = nt.nodes.new("ShaderNodeNormalMap")
    nt.links.new(img("Normal", True).outputs["Color"], nm.inputs["Color"])
    nt.links.new(nm.outputs["Normal"], p.inputs["Normal"])
    t = img("MetallicSmoothness", True)
    sep = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(t.outputs["Color"], sep.inputs[0])
    nt.links.new(sep.outputs["Red"], p.inputs["Metallic"])
    inv = nt.nodes.new("ShaderNodeMath")
    inv.operation = "SUBTRACT"
    inv.inputs[0].default_value = 1.0
    nt.links.new(t.outputs["Alpha"], inv.inputs[1])
    nt.links.new(inv.outputs[0], p.inputs["Roughness"])
    if "Emission" in info["maps"]:
        nt.links.new(img("Emission", False).outputs["Color"], p.inputs["Emission Color"])
        p.inputs["Emission Strength"].default_value = info["emission_intensity"]


# ---------------------------------------------------------------- 4. assemble
def set_origin(o, world_pt):
    kids = [(c, c.matrix_world.copy()) for c in o.children]
    local = o.matrix_world.inverted() @ world_pt
    o.data.transform(Matrix.Translation(-local))
    o.matrix_world = o.matrix_world @ Matrix.Translation(local)
    for c, mw in kids:
        c.matrix_world = mw


def pivot(o):
    """Contract pivots. Returns the rule applied."""
    if o.name == DOOR_LEAF:
        return "hinge (authored origin)"
    lo, hi = world_bbox([o])
    c = (lo + hi) / 2
    if o.name.startswith(CHAIR_PREFIX):
        set_origin(o, Vector((c.x, c.y, lo.z)))
        return "floor under seat"
    if any(g in o.name for g in GRAB_PARTS):
        set_origin(o, c)
        return "centre"
    return None


def make_lods(o):
    """o -> Empty 'name' with name_LOD0..2 children (Unity builds the LODGroup from the suffixes)."""
    name, mw, parent = o.name, o.matrix_world.copy(), o.parent
    kids = list(o.children)
    o.name = o.data.name = name + "_LOD0"
    root = bpy.data.objects.new(name, None)
    for c in o.users_collection:
        c.objects.link(root)
    root.parent = parent
    root.matrix_world = mw
    lods = [o]
    for i, r in enumerate(LOD_RATIOS, 1):
        c = o.copy()
        c.data = o.data.copy()
        c.name = c.data.name = f"{name}_LOD{i}"
        for coll in o.users_collection:
            coll.objects.link(c)
        c.modifiers.new("lod", "DECIMATE").ratio = r
        select([c])
        bpy.ops.object.modifier_apply(modifier="lod")
        lods.append(c)
    for c in lods + kids:
        w = c.matrix_world.copy()
        c.parent = root
        c.matrix_world = w
    return root, lods


def setup_gpu():
    scene.render.engine = "CYCLES"
    prefs = bpy.context.preferences.addons["cycles"].preferences
    for dev in ("OPTIX", "CUDA"):
        try:
            prefs.compute_device_type = dev
        except TypeError:
            continue
        prefs.get_devices()
        if any(d.type == dev for d in prefs.devices):
            for d in prefs.devices:
                d.use = d.type == dev
            scene.cycles.device = "GPU"
            log("bake device", dev)
            return
    scene.cycles.device = "CPU"
    log("bake device CPU")


def r4(v):
    return [round(x, 4) for x in v]


def export_fbx(objs, path):
    select(objs)
    bpy.ops.export_scene.fbx(
        filepath=path, use_selection=True, object_types={"MESH", "EMPTY"},   # empties = LOD group parents only
        global_scale=1.0, apply_unit_scale=True, apply_scale_options="FBX_SCALE_UNITS",
        axis_forward="-Z", axis_up="Y", bake_space_transform=False,           # Unity: bakeAxisConversion = true
        use_mesh_modifiers=False, mesh_smooth_type="OFF", use_tspace=False,    # Unity recomputes MikkTSpace
        use_custom_props=False, add_leaf_bones=False, bake_anim=False,
        path_mode="RELATIVE", embed_textures=False, colors_type="NONE")


# ---------------------------------------------------------------- main
def main():
    t0 = time.time()
    os.makedirs(MODELS, exist_ok=True)
    os.makedirs(TEXTURES, exist_ok=True)
    setup_gpu()
    scene.render.bake.use_selected_to_active = False
    if scene.world:
        scene.world.light_settings.distance = AO_DISTANCE
    prepare()
    split_glass()
    glass = [o for o in meshes() if o.material_slots and all(is_glass(s.material) for s in o.material_slots)]
    for o in glass:
        for s in o.material_slots:
            if "Glass" not in s.material.name:
                log(f"WARNING glass material '{s.material.name}' lacks 'Glass' in its name: Unity makes it opaque")
    opaque = [o for o in meshes() if o not in glass]
    centres = {}
    for o in opaque:
        centres.setdefault(area_of(o), []).append(o)
    centres = {a: sum(world_bbox(objs), Vector()) / 2 for a, objs in centres.items()}
    inner_glass(glass, centres)
    triangulate(meshes())

    # UV0: one atlas per material
    mats = sorted({s.material for o in opaque for s in o.material_slots if s.material}, key=lambda m: m.name)
    users = {m: [o for o in opaque if slots_of(o, m)] for m in mats}
    for o in opaque:
        ensure_uv(o, "UV0")
    plan = {}
    for m in mats:
        area = sum(face_area_world(o, slots_of(o, m)) for o in users[m])
        full = tex_res(area)
        plan[m] = (full, max(64, full // Q["div"]), area)
        unwrap(users[m], lambda o, m=m: slots_of(o, m), 2 * MARGIN_PX / full)
    for o in glass:
        ensure_uv(o, "UV0")
        unwrap([o], lambda o: None, 0.02)
    log(f"UV0 done {time.time() - t0:.0f}s")

    # bake
    manifest = {"version": 2, "generated": time.strftime("%Y-%m-%dT%H:%M:%S"), "blender": bpy.app.version_string,
                "quality": QNAME, "units": "metre", "contract": "unity/OrangeRoom/README.md",
                "fbx": {"axis_forward": "-Z", "axis_up": "Y", "apply_transform": False,
                        "apply_scalings": "FBX_SCALE_UNITS", "uv0": "per-material atlas", "uv1": "lightmap, per object"},
                "materials": {}, "objects": [], "files": []}
    for m in mats:
        full, res, area = plan[m]
        log(f"bake {m.name}: {len(users[m])} obj, {area:.2f} m2, {res}px (full {full})")
        info = bake_material(m, users[m], res)
        info.update(area_m2=round(area, 3), resolution_full=full, objects=[o.name for o in users[m]])
        manifest["materials"][m.name] = info
    for m in mats:
        image_material(m, manifest["materials"][m.name])
    for o in glass:
        for s in o.material_slots:
            manifest["materials"].setdefault(s.material.name, {"glass": True})
    log(f"bake done {time.time() - t0:.0f}s")

    # UV1 lightmap per object, then drop source UV maps so UV0/UV1 are channels 0/1
    for o in meshes():
        if o in opaque:
            ensure_uv(o, "UV1")
            side = math.sqrt(max(face_area_world(o), 1e-6)) * LIGHTMAP_TPU
            unwrap([o], lambda o: None, min(max(LIGHTMAP_PAD / side, 0.005), 0.1))
        for uv in [u for u in o.data.uv_layers if u.name not in ("UV0", "UV1")]:
            o.data.uv_layers.remove(uv)
        o.data.uv_layers["UV0"].active_render = True
        o.data.uv_layers.active = o.data.uv_layers["UV0"]
    log(f"UV1 done {time.time() - t0:.0f}s")

    # pivots, LODs, manifest entries
    for o in sorted(meshes(), key=lambda o: o.name):
        src_bbox = [r4(v) for v in world_bbox([o])]
        rule = pivot(o)
        entry = {"name": o.name, "area": area_of(o), "parent": o.parent.name if o.parent else None,
                 "materials": [s.material.name for s in o.material_slots if s.material], "tris": tris(o),
                 "glass": o in glass, "bbox_blender": src_bbox}
        if rule:
            entry["pivot"] = rule
        if o.name == DOOR_LEAF:
            entry["hinge"] = {"origin_blender": r4(o.matrix_world.translation),
                              "authored_angle_deg": round(math.degrees(o.matrix_world.to_euler().z), 2)}
        if o not in glass and o.name != DOOR_LEAF and (tris(o) > LOD_TRIS or LOD_NAMES.search(o.name)):
            _, lods = make_lods(o)
            entry["lods"] = [{"name": x.name, "tris": tris(x)} for x in lods]
        manifest["objects"].append(entry)

    for area in sorted({e["area"] for e in manifest["objects"]}):
        roots = [o for o in scene.objects if o.parent is None and o.type in ("MESH", "EMPTY")
                 and (o.type == "MESH" or o.children) and area_of(o) == area]
        path = os.path.join(MODELS, area + ".fbx")
        export_fbx([x for r in roots for x in [r] + descendants(r)], path)
        manifest["files"].append(os.path.relpath(path, OUT))
    objs = manifest["objects"]
    manifest["stats"] = {
        "objects": len(objs), "tris_lod0": sum(e["tris"] for e in objs),
        "tris_by_area": {a: sum(e["tris"] for e in objs if e["area"] == a) for a in {e["area"] for e in objs}},
        "draw_calls_lod0_before_batching": sum(len(e["materials"]) for e in objs),
        "materials": len(manifest["materials"]),
        "texture_mb_uncompressed": round(sum(len(i.get("maps", [])) * i.get("resolution", 0) ** 2 * 4
                                             for i in manifest["materials"].values()) / 2 ** 20, 1),
        "seconds": round(time.time() - t0, 1)}
    with open(os.path.join(MODELS, "OrangeRoom_manifest.json"), "w") as f:
        json.dump(manifest, f, indent=1)
    log("DONE", json.dumps(manifest["stats"]), "->", OUT)
    if "--debug-blend" in ARGS:
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(os.path.dirname(OUT), "export_debug.blend"), copy=True)


main()
