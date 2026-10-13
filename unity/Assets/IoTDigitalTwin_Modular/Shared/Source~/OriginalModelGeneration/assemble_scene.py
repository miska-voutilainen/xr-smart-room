import bpy,json
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parents[1]
bpy.ops.wm.read_factory_settings(use_empty=True);s=bpy.context.scene;s.unit_settings.system='METRIC';s.unit_settings.scale_length=1
layout={1:(-.45,0,.70),2:(-.15,0,.70),3:(.15,0,.70),4:(.45,0,.70),5:(-.45,0,.25),6:(0,0,-.15),7:(-.15,0,.25),8:(.15,0,.25),9:(.45,0,.25)}
counts={};roots=[]
for i in range(1,10):
 path=next((P/'Blender').glob(f'{i:02d}_*.blend'))
 with bpy.data.libraries.load(str(path),link=False) as (data_from,data_to):data_to.collections=[c for c in data_from.collections if c.startswith(f'{i:02d}_')]
 coll=data_to.collections[0];s.collection.children.link(coll)
 root=next(o for o in coll.objects if o.type=='EMPTY' and o.parent is None);root.location=layout[i];root['gallery_offset_only']=True;roots.append(root)
 for o in coll.objects:
  if o!=root:o.name=f'{i:02d}__'+o.name
 counts[coll.name]=len([o for o in coll.all_objects if o.type=='MESH'])
s['layout_note']='All models use real metres. Roots are translated for gallery layout only. Individual FBX/GLB files have mounting origins at zero.'
s['device_count']=9
# A renderable overview rig is kept outside all device collections.
rig=bpy.data.collections.new('Preview_Studio_NOT_FOR_EXPORT');s.collection.children.link(rig)
def link(o):
 for c in list(o.users_collection):c.objects.unlink(o)
 rig.objects.link(o)
def aim(o,target):o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.object.camera_add(location=(.8,-3.8,.7));cam=bpy.context.object;cam.name='All_Devices_Overview_Camera';link(cam);aim(cam,(0,-.03,-.10));cam.data.type='ORTHO';cam.data.ortho_scale=2.05;cam.data.clip_start=.001;s.camera=cam
for loc,power,size in [((-2,-3,3),650,3),((2,-2,1),350,2)]:
 bpy.ops.object.light_add(type='AREA',location=loc);o=bpy.context.object;link(o);o.data.energy=power;o.data.size=size;aim(o,(0,0,0))
world=bpy.data.worlds.new('Overview_World');world.use_nodes=True;world.node_tree.nodes['Background'].inputs[0].default_value=(.3,.34,.4,1);world.node_tree.nodes['Background'].inputs[1].default_value=.3;s.world=world
s.render.engine='CYCLES';s.cycles.samples=32;s.cycles.use_denoising=False;s.render.resolution_x=1200;s.render.resolution_y=1400;s.render.resolution_percentage=100;s.view_settings.view_transform='AgX'
rig.hide_viewport=True
bpy.ops.object.select_all(action='DESELECT')
for o in roots:o.select_set(True)
bpy.context.view_layer.objects.active=roots[0]
for screen in bpy.data.screens:
 for a in screen.areas:
  if a.type=='VIEW_3D':
   a.spaces.active.clip_start=.0001;a.spaces.active.region_3d.view_location=(0,0,-.1);a.spaces.active.region_3d.view_distance=2.3;a.spaces.active.region_3d.view_rotation=cam.rotation_euler.to_quaternion();a.spaces.active.shading.type='MATERIAL'
path=P/'Blender/00_All_9_Devices.blend';bpy.ops.wm.save_as_mainfile(filepath=str(path))
bpy.ops.wm.open_mainfile(filepath=str(path));actual=[c for c in bpy.data.collections if c.name[:2].isdigit()];assert len(actual)==9
assert all(sum(o.type=='MESH' for o in c.all_objects)==counts[c.name] for c in actual)
(P/'Reports/combined_scene_validation.json').write_text(json.dumps({'reopened':True,'device_collections':counts,'collection_count':9,'unit_scale_metres':bpy.context.scene.unit_settings.scale_length,'gallery_root_offsets_blender_xyz':layout},indent=2))
print('COMBINED_SCENE_VALIDATED',counts)
