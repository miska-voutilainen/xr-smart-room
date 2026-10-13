import bpy
for kind, coll in (("MAT", bpy.data.materials), ("IMG", bpy.data.images), ("NG", bpy.data.node_groups)):
    for d in coll:
        if d.users == 0 or (d.users == 1 and d.use_fake_user):
            print("ORPHAN", kind, d.name)
# materials on objects that never render
used = {}
for ob in bpy.data.objects:
    if ob.type == "MESH":
        for m in ob.data.materials:
            if m: used.setdefault(m.name, []).append((ob.name, ob.hide_render, ob.name in bpy.context.scene.objects))
for m, obs in used.items():
    if all(h or not insc for _, h, insc in obs):
        print("HIDDENONLY MAT", m, obs)
# material slots never referenced by any face
for ob in bpy.context.scene.objects:
    if ob.type == "MESH" and not ob.hide_render:
        idx = {p.material_index for p in ob.data.polygons}
        for i, m in enumerate(ob.data.materials):
            if i not in idx and m:
                print("UNUSEDSLOT", ob.name, i, m.name)
