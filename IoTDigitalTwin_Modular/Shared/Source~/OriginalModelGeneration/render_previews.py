import bpy,sys,math,json
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parents[1]
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
draft='draft' in args
indices=[int(x) for x in args if x.isdigit()] or list(range(2,10))
for idx in indices:
 path=next((P/'Blender').glob(f'{idx:02d}_*.blend'));bpy.ops.wm.open_mainfile(filepath=str(path));s=bpy.context.scene
 device=bpy.data.collections.get(path.stem)
 if not device:device=next(c for c in bpy.data.collections if c.name.startswith(f'{idx:02d}_'))
 obs=[o for o in device.all_objects if o.type=='MESH'];bpy.context.view_layer.update()
 pts=[o.matrix_world@Vector(c) for o in obs for c in o.bound_box]
 lo=Vector([min(p[k] for p in pts) for k in range(3)]);hi=Vector([max(p[k] for p in pts) for k in range(3)]);centre=(lo+hi)/2;size=max(hi.x-lo.x,hi.z-lo.z,(hi.y-lo.y)*1.35)
 for c in list(bpy.data.collections):
  if 'Studio' in c.name:
   for o in list(c.objects):bpy.data.objects.remove(o,do_unlink=True)
   bpy.data.collections.remove(c)
 studio=bpy.data.collections.new('Preview_Studio_NOT_FOR_EXPORT');s.collection.children.link(studio)
 def link(o):
  for c in list(o.users_collection):c.objects.unlink(o)
  studio.objects.link(o)
 def aim(o,target):o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()
 bpy.ops.object.camera_add(location=centre+Vector((size*1.15,-size*2.8,size*.75)));cam=bpy.context.object;cam.name='Preview_Camera';link(cam);aim(cam,centre);cam.data.type='ORTHO';cam.data.ortho_scale=size*1.24;cam.data.clip_start=.0001;s.camera=cam
 if idx==6:cam.location=centre+Vector((size*.35,-size*3,size*.40));aim(cam,centre);cam.data.ortho_scale=size*1.16
 for name,offset,power,area in [('Key',(-1.3,-2.0,2.2),300,1.9),('Fill',(1.7,-1.4,.6),105,1.5),('Rim',(.3,.7,1.8),240,1.1)]:
  bpy.ops.object.light_add(type='AREA',location=centre+Vector(offset)*size);o=bpy.context.object;o.name=name;link(o);o.data.energy=power*size*size;o.data.shape='DISK';o.data.size=area*size;aim(o,centre)
 bpy.ops.mesh.primitive_plane_add(size=size*200,location=(0,.0004,centre.z),rotation=(math.pi/2,0,0));o=bpy.context.object;o.name='Studio_Wall';link(o)
 ma=bpy.data.materials.new('Studio_Background');ma.use_nodes=True;bs=ma.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(.12,.16,.18,1);bs.inputs['Roughness'].default_value=.88;o.data.materials.append(ma)
 world=bpy.data.worlds.new('Studio_World');world.use_nodes=True;world.node_tree.nodes['Background'].inputs[0].default_value=(.3,.34,.4,1);world.node_tree.nodes['Background'].inputs[1].default_value=.30;s.world=world
 s.render.engine='CYCLES';s.cycles.samples=8 if draft else 48;s.cycles.use_denoising=False;s.cycles.max_bounces=6
 s.render.resolution_x=s.render.resolution_y=420 if draft else 1000;s.render.resolution_percentage=100;s.view_settings.view_transform='AgX';s.render.image_settings.file_format='PNG'
 if not draft:
  studio.hide_viewport=True;bpy.ops.wm.save_as_mainfile(filepath=str(path))
 out=(P.parent/'draft_previews') if draft else P/'Previews';out.mkdir(exist_ok=True)
 s.render.filepath=str(out/(path.stem+'.png'));bpy.ops.render.render(write_still=True)
 print('PREVIEW_COMPLETE',idx,flush=True)
