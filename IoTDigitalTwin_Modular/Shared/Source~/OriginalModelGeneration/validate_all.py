import bpy,bmesh,json,math,struct,sys
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parents[1]
selected=[int(x) for x in sys.argv[sys.argv.index('--')+1:]] if '--' in sys.argv else []
reports=json.loads((P/'Reports/validation.json').read_text())['devices'] if selected and (P/'Reports/validation.json').exists() else []
def describe(objects):
 bpy.context.view_layer.update();meshes=[o for o in objects if o.type=='MESH'];pts=[o.matrix_world@Vector(c) for o in meshes for c in o.bound_box]
 return {'mesh_count':len(meshes),'bounds_min':[min(p[k] for p in pts) for k in range(3)],'bounds_max':[max(p[k] for p in pts) for k in range(3)],'names':sorted(o.name for o in meshes),'material_slots':sum(len(o.data.materials) for o in meshes),'shape_keys':{o.name:[k.name for k in o.data.shape_keys.key_blocks] for o in meshes if o.data.shape_keys},'pivots':{o.name:list(o.matrix_world.translation) for o in objects if o.type=='EMPTY' or any(t in o.name for t in ['Knob','Button','Switch'])}}
for path in sorted((P/'Blender').glob('*.blend')):
 if path.stem.startswith('00_') or (selected and int(path.stem[:2]) not in selected):continue
 bpy.ops.wm.open_mainfile(filepath=str(path));coll=next(c for c in bpy.data.collections if c.name.startswith(path.stem[:3]));src=describe(list(coll.all_objects));stats=[]
 for o in coll.all_objects:
  if o.type!='MESH':continue
  bm=bmesh.new();bm.from_mesh(o.data);deg=sum(f.calc_area()<1e-14 for f in bm.faces);bad=sum(not e.is_manifold for e in bm.edges);bm.free()
  is_decal=o.name.startswith('Decal_');assert deg==0,(path.name,o.name,deg);assert bad==0 or is_decal,(path.name,o.name,bad)
  evaluated=o.evaluated_get(bpy.context.evaluated_depsgraph_get());me=evaluated.to_mesh();me.calc_loop_triangles()
  stat={'name':o.name,'source_faces':len(o.data.polygons),'source_quads':sum(len(p.vertices)==4 for p in o.data.polygons),'render_triangles':len(me.loop_triangles),'nonmanifold_source_edges':bad,'intentional_decal_surface':is_decal,'degenerate_source_faces':deg};stats.append(stat);evaluated.to_mesh_clear()
 imports={}
 for ext,folder in [('fbx','FBX'),('glb','GLB')]:
  bpy.ops.wm.read_factory_settings(use_empty=True)
  f=P/folder/(path.stem+'.'+ext)
  if ext=='fbx':bpy.ops.import_scene.fbx(filepath=str(f))
  else:bpy.ops.import_scene.gltf(filepath=str(f))
  result=describe(list(bpy.context.scene.objects));assert result['mesh_count']==src['mesh_count'],(path.stem,ext,result['mesh_count'],src['mesh_count'])
  assert result['names']==src['names'],(path.stem,ext,'names')
  for bound in ('bounds_min','bounds_max'):
   assert all(abs(a-b)<2e-5 for a,b in zip(result[bound],src[bound])),(path.stem,ext,bound,result[bound],src[bound])
  assert result['material_slots']==src['material_slots'],(path.stem,ext,'materials')
  for name,position in src['pivots'].items():
   assert name in result['pivots'],(path.stem,ext,'missing pivot',name)
   assert all(abs(a-b)<2e-5 for a,b in zip(position,result['pivots'][name])),(path.stem,ext,'pivot shift',name)
  imports[ext]={'passed':True,'meshes':result['mesh_count'],'shape_keys':result['shape_keys'],'material_slots':result['material_slots']}
  if ext=='glb':
   b=f.read_bytes();magic,version,total=struct.unpack_from('<4sII',b);assert magic==b'glTF' and version==2 and total==len(b);l=struct.unpack_from('<I',b,12)[0];j=json.loads(b[20:20+l]);assert all('bufferView' in im for im in j.get('images',[]));imports[ext]['embedded_images']=len(j.get('images',[]));imports[ext]['morph_targets']=sum(len(p.get('targets',[])) for m in j['meshes'] for p in m['primitives'])
 reports=[r for r in reports if r['device']!=path.stem]
 reports.append({'device':path.stem,'source':src,'mesh_statistics':stats,'total_render_triangles':sum(s['render_triangles'] for s in stats),'imports':imports})
 (P/'Reports/validation.json').write_text(json.dumps({'tool':'Blender '+bpy.app.version_string,'unity_editor_tested':False,'devices':sorted(reports,key=lambda r:r['device'])},indent=2))
 print('VALIDATED',path.stem,'tris',reports[-1]['total_render_triangles'],'shape keys',imports['glb']['shape_keys'],flush=True)
print('ALL_NINE_VALIDATED',flush=True)
