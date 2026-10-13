import bpy, sys
dg = bpy.context.evaluated_depsgraph_get()
rows = {}
for inst in dg.object_instances:
    ob = inst.object
    if ob.type != 'MESH': continue
    src = inst.parent.original.name if inst.is_instance and inst.parent else ob.original.name
    if not ob.original.visible_get() and not inst.is_instance: pass
    if ob.original.hide_render and not inst.is_instance: continue
    me = ob.data
    me.calc_loop_triangles()
    rows[src] = rows.get(src, 0) + len(me.loop_triangles)
tot = sum(rows.values()); ext = sum(v for k, v in rows.items() if k.startswith("Ext_"))
for k, v in sorted(rows.items(), key=lambda kv: -kv[1]):
    print(f"TRI {v:8d} {k}")
print("TOTAL", tot, "EXT", ext)
