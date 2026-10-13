import sys

# Blender must have its bundled NumPy and import addons available.
import bpy,bmesh,json,struct
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parents[1]
rows=[]
for folder in sorted(P.glob('[0-9][0-9]_*')):
 definition=json.loads((folder/'Materials/DeviceDefinition.json').read_text());stem=definition['stem'];source=folder/'Models/Source~'/f'{stem}.blend';bpy.ops.wm.open_mainfile(filepath=str(source));coll=next(c for c in bpy.data.collections if c.name.startswith(folder.name[:3]));objects=list(coll.all_objects);meshes=[o for o in objects if o.type=='MESH'];names=sorted(o.name for o in meshes)
 hierarchy=[{'name':o.name,'parent':o.parent.name if o.parent else None,'type':o.type,'source_position':list(o.matrix_world.translation),'unity_position':[-o.matrix_world.translation.x,o.matrix_world.translation.z,-o.matrix_world.translation.y]} for o in sorted(objects,key=lambda o:o.name)]
 (folder/'Models/Source~/Hierarchy.json').write_text(json.dumps(hierarchy,indent=2))
 for o in meshes:
  bm=bmesh.new();bm.from_mesh(o.data);assert all(f.calc_area()>1e-14 for f in bm.faces),o.name;assert o.name.startswith('Decal_') or all(e.is_manifold for e in bm.edges),o.name;bm.free()
 reference={o.name:list(o.matrix_world.translation) for o in objects if o.type=='EMPTY'};importRows={}
 if definition['id']==6:
  cloth=bpy.data.objects['Cloth_With_Raise_BlendShape'];assert 'Raise_Blind' in cloth.data.shape_keys.key_blocks
  bottom0=min((cloth.matrix_world@v.co).z for v in cloth.data.shape_keys.key_blocks['Basis'].data);bottom1=min((cloth.matrix_world@v.co).z for v in cloth.data.shape_keys.key_blocks['Raise_Blind'].data);assert abs(bottom0+.484)<1e-6 and abs(bottom1+.05875)<1e-6
 for ext,sub in [('fbx','Models'),('glb','Models/Source~')]:
  bpy.ops.wm.read_factory_settings(use_empty=True);f=folder/sub/(stem+'.'+ext)
  if ext=='fbx':bpy.ops.import_scene.fbx(filepath=str(f))
  else:bpy.ops.import_scene.gltf(filepath=str(f))
  imported=list(bpy.context.scene.objects);assert sorted(o.name for o in imported if o.type=='MESH')==names
  for name,position in reference.items():
   obj=bpy.data.objects[name];assert max(abs(a-b) for a,b in zip(position,obj.matrix_world.translation))<2e-5,(name,ext)
  if definition['id']==6:assert 'Raise_Blind' in bpy.data.objects['Cloth_With_Raise_BlendShape'].data.shape_keys.key_blocks
  importRows[ext]={'passed':True,'meshes':len(names),'pivots_preserved':True,'method':'Blender reimport, not Unity'}
 rows.append({'device':folder.name,'blender_opened':True,'clean_topology_checked':True,'imports':importRows});print('PASS',folder.name,flush=True)
(P/'Verification~/Logs/Modular_Model_Validation.json').write_text(json.dumps({'unityEditorTested':False,'blenderVersion':bpy.app.version_string,'devices':rows},indent=2))
