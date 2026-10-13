import bpy, bmesh, math, json, os
from pathlib import Path
from mathutils import Vector
OUT=Path(__file__).resolve().parents[1]
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
for c in list(bpy.data.collections):
 if c.name!='Collection': bpy.data.collections.remove(c)
scene=bpy.context.scene
scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1.0
coll=bpy.data.collections.get('Collection');coll.name='01_Zigbee_Rotary_Dimmer'
root=bpy.data.objects.new('Zigbee_Rotary_Dimmer',None);coll.objects.link(root)
root['estimated_dimensions_m']='0.086 x 0.086 x 0.026'
root['source']='TalTech reference image(20261013-084139).png'
root['mounting_origin']='Centre of back mounting plane; Blender -Y front, Z up; exported +Z front, +Y up.'

def mat(name,col,rough=.33):
 m=bpy.data.materials.new(name);m.diffuse_color=(*col,1);m.use_nodes=True
 bs=m.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(*col,1);bs.inputs['Roughness'].default_value=rough
 return m
cream=mat('ABS_Warm_White',(0.78,.785,.728),.31)
rear=mat('ABS_Rear_Cover',(.56,.575,.54),.46)
dark=mat('Collar_Charcoal',(.062,.071,.067),.48)
labelmat=mat('Installation_Label',(.8,.8,.74),.62)
tex=bpy.data.images.load(str(OUT/'Textures/Dimmer_InstallationLabel_BaseColor.png'));tex.pack()
node=labelmat.node_tree.nodes.new('ShaderNodeTexImage');node.image=tex
labelmat.node_tree.links.new(node.outputs['Color'],labelmat.node_tree.nodes.get('Principled BSDF').inputs['Base Color'])
# Shared radial samples keep square-to-circle bands non-overlapping.
ANGLES=sorted(set([round(2*math.pi*i/64,10) for i in range(64)]+[round(math.radians(45+90*k+off),10) for k in range(4) for off in (-2,-1,1,2)]))
N=len(ANGLES)
def square(size,r,d):
 h=size/2;pts=[]
 for a in ANGLES:
  ux,uz=math.cos(a),math.sin(a);t=h/max(abs(ux),abs(uz))
  if min(abs(t*ux),abs(t*uz))>h-r:
   cx=math.copysign(h-r,ux);cz=math.copysign(h-r,uz)
   dot=ux*cx+uz*cz;t=dot+math.sqrt(max(0,dot*dot-cx*cx-cz*cz+r*r))
  pts.append((t*ux,-d,t*uz))
 return pts

def circle(r,d):
 return [(r*math.cos(a),-d,r*math.sin(a)) for a in ANGLES]

def meshloops(name,loops,material,closed=False,caps=True):
 verts=[v for ring in loops for v in ring];faces=[]
 count=len(loops)
 for j in range(count if closed else count-1):
  j2=(j+1)%count
  for i in range(N):faces.append((j*N+i,j*N+(i+1)%N,j2*N+(i+1)%N,j2*N+i))
 if not closed and caps:
  faces.extend([tuple(range(N-1,-1,-1)),tuple((count-1)*N+i for i in range(N))])
 mesh=bpy.data.meshes.new(name+'_Mesh');mesh.from_pydata(verts,[],faces);mesh.update()
 bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bm.to_mesh(mesh);bm.free()
 ob=bpy.data.objects.new(name,mesh);coll.objects.link(ob);ob.parent=root;mesh.materials.append(material)
 for p in mesh.polygons:p.use_smooth=(len(p.vertices)==4)
 # Area-weighted normals protect broad planar surfaces while preserving curved bevels.
 mod=ob.modifiers.new('Surface_Normals','WEIGHTED_NORMAL');mod.keep_sharp=True;mod.weight=40
 mesh.use_auto_smooth=True
 bpy.context.view_layer.objects.active=ob;ob.select_set(True)
 bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=1.15,island_margin=.02);bpy.ops.object.mode_set(mode='OBJECT');ob.select_set(False)
 return ob

base=meshloops('01_Rear_Mounting_Cover',[
 square(.083,.0014,0),square(.084,.0018,.00045),square(.084,.0018,.0026),square(.0834,.0015,.003)],rear)
frame=meshloops('02_Beveled_Outer_Frame',[
 square(.0848,.00135,.0032),square(.0857,.0017,.00365),square(.086,.00185,.0042),
 square(.086,.00185,.0084),square(.0858,.00175,.009),square(.0853,.00155,.0095),square(.0846,.0013,.0098),
 square(.0558,.00085,.0098),square(.0553,.00065,.00965),square(.055,.0005,.00935),square(.055,.0005,.0032)],cream,closed=True,caps=False)
plate=meshloops('03_Inset_Square_Plate',[
 square(.0542,.00055,.0035),square(.0542,.00055,.0094),square(.054,.00055,.00985),square(.0535,.0005,.01015),
 circle(.0181,.01015),circle(.0179,.0099),circle(.0179,.0035)],cream,closed=True,caps=False)
collar=meshloops('04_Recessed_Knob_Collar',[
 circle(.0178,.007),circle(.0178,.0102),circle(.01765,.0106),circle(.01695,.0106),circle(.01695,.007)],dark,closed=True,caps=False)
knob=meshloops('05_Rotary_Knob',[
 circle(.01615,.0088),circle(.01665,.0093),circle(.01675,.010),circle(.01675,.0241),
 circle(.01669,.02462),circle(.01645,.02514),circle(.01605,.02553),circle(.01555,.0258),circle(.01495,.0259)],cream)
# Put geometry around a shaft-axis pivot; location is distinct from mesh coordinates.
pivot=Vector((0,-.010,0))
for v in knob.data.vertices:v.co-=pivot
knob.location=pivot
knob['interaction']='Rotate around local Y axis; press inward along local +Y. Exported shaft axis is Z.'
knob['suggested_press_travel_m']=.0007
knob['estimated_knob_diameter_m']=.0335
# Thin, removable warning strip across the lower frame; a closed six-quad solid.
x0,x1=-.0345,.0345;z0,z1=-.0419,-.0355;d0,d1=.00986,.00998
verts=[(x,-d,z) for d in (d0,d1) for x,z in [(x0,z0),(x1,z0),(x1,z1),(x0,z1)]]
faces=[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]
me=bpy.data.meshes.new('WarningStrip_Mesh');me.from_pydata(verts,[],faces);me.update()
ob=bpy.data.objects.new('06_Removable_Installation_Label',me);coll.objects.link(ob);ob.parent=root;me.materials.append(labelmat)
uv=me.uv_layers.new(name='UVMap')
for p in me.polygons:
 for li in p.loop_indices:
  v=me.vertices[me.loops[li].vertex_index].co
  uv.data[li].uv=((v.x-x0)/(x1-x0),(v.z-z0)/(z1-z0))
ob['note']='Cosmetic reconstruction: first line is partly obscured in photograph. Not installation guidance.'

# Export device alone; source meshes retain quad bands and planar n-gon caps.
bpy.ops.object.select_all(action='DESELECT')
for o in coll.objects:o.select_set(True)
bpy.context.view_layer.objects.active=root
bpy.ops.export_scene.fbx(filepath=str(OUT/'FBX/01_Zigbee_Rotary_Dimmer.fbx'),use_selection=True,object_types={'EMPTY','MESH'},apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',axis_forward='-Z',axis_up='Y',use_mesh_modifiers=True,mesh_smooth_type='FACE',use_triangles=False,bake_anim=False,path_mode='COPY',embed_textures=True)
bpy.ops.export_scene.gltf(filepath=str(OUT/'GLB/01_Zigbee_Rotary_Dimmer.glb'),export_format='GLB',use_selection=True,export_apply=True,export_yup=True)

stats={};total=0
for o in coll.objects:
 if o.type!='MESH':continue
 me=o.data;me.calc_loop_triangles();bm=bmesh.new();bm.from_mesh(me)
 stats[o.name]={'vertices':len(me.vertices),'faces':len(me.polygons),'quads':sum(len(p.vertices)==4 for p in me.polygons),'triangles_after_tessellation':len(me.loop_triangles),'nonmanifold_edges':sum(not e.is_manifold for e in bm.edges),'degenerate_faces':sum(f.calc_area()<1e-14 for f in bm.faces)};bm.free();total+=len(me.loop_triangles)
(OUT/'Reports/01_mesh_statistics.json').write_text(json.dumps({'objects':stats,'total_render_triangles':total},indent=2))

# A separate studio collection is excluded from exports.
studio=bpy.data.collections.new('Preview_Studio_NOT_FOR_EXPORT');scene.collection.children.link(studio)
def studio_link(o):
 for c in list(o.users_collection):c.objects.unlink(o)
 studio.objects.link(o)
def aim(o,target):o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.object.camera_add(location=(.127,-.245,.115));cam=bpy.context.object;cam.name='Preview_Camera';studio_link(cam);aim(cam,(0,-.005,0));cam.data.type='ORTHO';cam.data.ortho_scale=.15;cam.data.lens=60;cam.data.clip_start=.001;scene.camera=cam
for name,loc,power,size in [('Key',(-.13,-.20,.22),2.4,.16),('Fill',(.16,-.14,.04),.8,.13),('Edge',(.01,.06,.17),2.0,.10)]:
 bpy.ops.object.light_add(type='AREA',location=loc);light=bpy.context.object;light.name=name;studio_link(light);light.data.energy=power;light.data.shape='DISK';light.data.size=size;aim(light,(0,0,0))
# Wall is slightly behind mounting plane.
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,.0002,0),rotation=(math.pi/2,0,0));wall=bpy.context.object;wall.name='Studio_Wall';studio_link(wall);wall.data.materials.append(mat('Studio_Background',(.11,.145,.17),.9))
scene.render.engine='CYCLES';scene.cycles.samples=48;scene.cycles.use_denoising=False
scene.world.color=(.22,.22,.22);scene.render.resolution_x=1100;scene.render.resolution_y=1100;scene.render.resolution_percentage=100
scene.view_settings.view_transform='AgX';scene.render.image_settings.file_format='PNG';scene.render.film_transparent=False
# Native file opens with the device selected in material preview.
bpy.ops.object.select_all(action='DESELECT');knob.select_set(True);bpy.context.view_layer.objects.active=knob
for screen in bpy.data.screens:
 for area in screen.areas:
  if area.type=='VIEW_3D':
   area.spaces.active.region_3d.view_distance=.20;area.spaces.active.region_3d.view_location=(0,0,0);area.spaces.active.clip_start=.001
   area.spaces.active.shading.type='MATERIAL'
scene['delivery_stage']='Device 01 of 09: rotary dimmer review checkpoint'
scene['dimension_caveat']='Estimated from one photograph; hidden rear cover is simplified, no certified electrical internals.'
studio.hide_viewport=True
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Blender/01_Zigbee_Rotary_Dimmer.blend'))
scene.render.filepath=str(OUT/'Previews/01_Zigbee_Rotary_Dimmer.png');bpy.ops.render.render(write_still=True)
cam.location=(0,-.25,0);aim(cam,(0,0,0));cam.data.ortho_scale=.113
scene.render.filepath=str(OUT/'Previews/01_Zigbee_Rotary_Dimmer_Front.png');bpy.ops.render.render(write_still=True)
print('DIMMER_BUILD_COMPLETE',total)
