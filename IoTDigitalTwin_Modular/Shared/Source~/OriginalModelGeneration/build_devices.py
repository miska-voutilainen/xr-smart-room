import bpy,bmesh,math,json,sys
from pathlib import Path
from mathutils import Vector,Matrix
P=Path(__file__).resolve().parents[1]
SCENE=bpy.context.scene
META=[];COL=None;ROOT=None

def material(name,color,rough=.36,metal=0,emission=0):
 m=bpy.data.materials.get(name)
 if m:return m
 m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.use_nodes=True
 bs=m.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(*color,1);bs.inputs['Roughness'].default_value=rough;bs.inputs['Metallic'].default_value=metal
 if emission:bs.inputs['Emission Color'].default_value=(*color,1);bs.inputs['Emission Strength'].default_value=emission
 return m

def textured(name,file,rough=.35,emission=0,alpha=False,normal=None):
 m=material(name,(1,1,1),rough);ns=m.node_tree.nodes;lk=m.node_tree.links;bs=ns.get('Principled BSDF')
 im=bpy.data.images.load(str(P/'Textures'/file),check_existing=True);im.pack();n=ns.new('ShaderNodeTexImage');n.image=im;lk.new(n.outputs['Color'],bs.inputs['Base Color'])
 if emission:lk.new(n.outputs['Color'],bs.inputs['Emission Color']);bs.inputs['Emission Strength'].default_value=emission
 if alpha:m.blend_method='CLIP';m.alpha_threshold=.35;lk.new(n.outputs['Alpha'],bs.inputs['Alpha'])
 if normal:
  im=bpy.data.images.load(str(P/'Textures'/normal),check_existing=True);im.colorspace_settings.name='Non-Color';im.pack();n=ns.new('ShaderNodeTexImage');n.image=im;nm=ns.new('ShaderNodeNormalMap');nm.inputs['Strength'].default_value=.65;lk.new(n.outputs['Color'],nm.inputs['Color']);lk.new(nm.outputs['Normal'],bs.inputs['Normal'])
 return m

def new_device(num,name,dims,note):
 global COL,ROOT
 bpy.ops.wm.read_factory_settings(use_empty=True);s=bpy.context.scene;s.unit_settings.system='METRIC';s.unit_settings.scale_length=1
 COL=bpy.data.collections.new(f'{num:02d}_{name}');s.collection.children.link(COL);ROOT=empty(name,(0,0,0),parent=False)
 ROOT['scale']='metres; back mounting plane at origin; -Y facing in Blender, +Z facing in Unity/glTF'
 ROOT['reference_dimensions']=dims;ROOT['reference_limits']=note
 ROOT['device_index']=num
 return ROOT

def empty(name,loc=(0,0,0),parent=None):
 o=bpy.data.objects.new(name,None);COL.objects.link(o);o.empty_display_type='PLAIN_AXES';o.empty_display_size=.012;o.location=loc
 if parent is not False:o.parent=parent or ROOT
 return o

def pivot(o,loc):
 p=Vector(loc)
 if o.type=='MESH':
  for v in o.data.vertices:v.co-=p
 o.location=p
 return o

def setparent(o,p):
 # Geometry and positions are authored in root coordinates.
 bpy.context.view_layer.update();mw=o.matrix_world.copy();o.parent=p;o.matrix_world=mw;bpy.context.view_layer.update()
 return o

def mesh(name,verts,faces,mat,smooth=True,parent=None):
 me=bpy.data.meshes.new(name+'_Mesh');me.from_pydata(verts,[],faces);me.update();bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bm.to_mesh(me);bm.free()
 o=bpy.data.objects.new(name,me);COL.objects.link(o);o.parent=ROOT
 if mat:me.materials.append(mat)
 for f in me.polygons:f.use_smooth=smooth and len(f.vertices)<=4
 me.use_auto_smooth=True
 if smooth:
  mod=o.modifiers.new('Weighted_Surface_Normals','WEIGHTED_NORMAL');mod.keep_sharp=True
 # A default planar UV map; detailed fabric/display mappings are set separately.
 uv=me.uv_layers.new(name='UVMap')
 xs=[v.co.x for v in me.vertices];zs=[v.co.z for v in me.vertices];dx=max(max(xs)-min(xs),1e-5);dz=max(max(zs)-min(zs),1e-5)
 for f in me.polygons:
  for i in f.loop_indices:
   v=me.vertices[me.loops[i].vertex_index].co;uv.data[i].uv=((v.x-min(xs))/dx,(v.z-min(zs))/dz)
 if parent:setparent(o,parent)
 return o

def rr(w,h,r,d,x=0,z=0,n=8):
 r=min(r,w/2-.000001,h/2-.000001);r=max(r,.000001);pts=[]
 for cx,cz,start in [(w/2-r,h/2-r,0),(-w/2+r,h/2-r,90),(-w/2+r,-h/2+r,180),(w/2-r,-h/2+r,270)]:
  for i in range(n):
   a=math.radians(start+90*i/(n-1));pts.append((x+cx+r*math.cos(a),-d,z+cz+r*math.sin(a)))
 return pts

def loops(name,arr,mat,closed=False,caps=True,parent=None):
 n=len(arr[0]);v=[p for ring in arr for p in ring];f=[]
 for j in range(len(arr) if closed else len(arr)-1):
  k=(j+1)%len(arr)
  for i in range(n):f.append((j*n+i,j*n+(i+1)%n,k*n+(i+1)%n,k*n+i))
 if caps and not closed:f.extend([tuple(range(n-1,-1,-1)),tuple((len(arr)-1)*n+i for i in range(n))])
 return mesh(name,v,f,mat,parent=parent)

def rbox(name,w,h,d0,d1,r,mat,x=0,z=0,b=.0006,parent=None):
 b=min(b,(d1-d0)*.3,r*.6,w*.1,h*.1)
 return loops(name,[rr(w-2*b,h-2*b,r-b,d0,x,z),rr(w,h,r,d0+b,x,z),rr(w,h,r,d1-b,x,z),rr(w-2*b,h-2*b,r-b,d1,x,z)],mat,parent=parent)

def asym_rbox(name,w,h,d0,d1,rt,rb,mat,b=.001):
 def contour(w,h,rt,rb,d):
  pts=[]
  for sx,sz,start,r in [(1,1,0,rt),(-1,1,90,rt),(-1,-1,180,rb),(1,-1,270,rb)]:
   cx=sx*(w/2-r);cz=sz*(h/2-r)
   for i in range(8):
    a=math.radians(start+90*i/7);pts.append((cx+r*math.cos(a),-d,cz+r*math.sin(a)))
  return pts
 return loops(name,[contour(w-2*b,h-2*b,rt-b,rb-b,d0),contour(w,h,rt,rb,d0+b),contour(w,h,rt,rb,d1-b),contour(w-2*b,h-2*b,rt-b,rb-b,d1)],mat)

def frame(name,w,h,iw,ih,d0,d1,r,ir,mat,ix=0,iz=0,b=.0005):
 return loops(name,[rr(w-2*b,h-2*b,r-b,d0),rr(w,h,r,d0+b),rr(w,h,r,d1-b),rr(w-2*b,h-2*b,r-b,d1),rr(iw+2*b,ih+2*b,ir+b,d1,ix,iz),rr(iw,ih,ir,d1-b,ix,iz),rr(iw,ih,ir,d0,ix,iz)],mat,True,False)

def disk(name,r,d0,d1,mat,x=0,z=0,bevel=.0004,n=48,parent=None):
 b=min(bevel,(d1-d0)/3,r/3)
 def ring(rad,dep):return [(x+rad*math.cos(i*2*math.pi/n),-dep,z+rad*math.sin(i*2*math.pi/n)) for i in range(n)]
 return loops(name,[ring(r-b,d0),ring(r,d0+b),ring(r,d1-b),ring(r-b,d1)],mat,parent=parent)

def ring(name,ro,ri,d0,d1,mat,x=0,z=0,n=48,parent=None):
 def c(r,d):return [(x+r*math.cos(2*math.pi*i/n),-d,z+r*math.sin(2*math.pi*i/n)) for i in range(n)]
 return loops(name,[c(ro,d0),c(ro,d1),c(ri,d1),c(ri,d0)],mat,True,False,parent)

def block(name,loc,dim,mat,b=.0005,parent=None):
 bpy.ops.mesh.primitive_cube_add(size=1,location=loc);o=bpy.context.object;o.name=name
 for c in list(o.users_collection):c.objects.unlink(o)
 COL.objects.link(o);o.dimensions=dim;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);o.data.materials.append(mat);o.parent=ROOT
 if b:
  mo=o.modifiers.new('Editable_Edge_Bevel','BEVEL');mo.width=min(b,min(dim)/3);mo.segments=3
  no=o.modifiers.new('Weighted_Surface_Normals','WEIGHTED_NORMAL');no.keep_sharp=True
 o.data.use_auto_smooth=True
 if parent:setparent(o,parent)
 return o

def cylinder_between(name,a,b,r,mat,n=32,parent=None):
 a,b=Vector(a),Vector(b);axis=(b-a).normalized();u=axis.cross(Vector((0,0,1)))
 if u.length<.01:u=axis.cross(Vector((0,1,0)))
 u.normalize();v=axis.cross(u).normalized();rs=[]
 for p,rad in [(a,r*.96),(a+axis*min(r*.1,(b-a).length*.2),r),(b-axis*min(r*.1,(b-a).length*.2),r),(b,r*.96)]:rs.append([tuple(p+rad*(math.cos(i*2*math.pi/n)*u+math.sin(i*2*math.pi/n)*v)) for i in range(n)])
 o=loops(name,rs,mat,parent=parent);return o

def tube(name,points,r,mat,sides=10,parent=None,closed=False):
 pts=[Vector(p) for p in points];rs=[]
 for i,p in enumerate(pts):
  tangent=(pts[(i+1)%len(pts)]-pts[i-1 if i else (-1 if closed else 0)]).normalized() if i<len(pts)-1 or closed else (pts[-1]-pts[-2]).normalized()
  u=tangent.cross(Vector((0,1,0)))
  if u.length<.01:u=tangent.cross(Vector((0,0,1)))
  u.normalize();v=tangent.cross(u).normalized();rs.append([tuple(p+r*(math.cos(k*2*math.pi/sides)*u+math.sin(k*2*math.pi/sides)*v)) for k in range(sides)])
 return loops(name,rs,mat,closed,not closed,parent)

def bezier_points(a,b,c,d,n=24):
 return [tuple((1-t)**3*Vector(a)+3*(1-t)**2*t*Vector(b)+3*(1-t)*t*t*Vector(c)+t**3*Vector(d)) for t in [i/(n-1) for i in range(n)]]

def decal(name,w,h,d,x,z,texture,parent=None):
 ma=textured(name+'_Material',texture,.6,alpha=True)
 o=mesh('Decal_'+name,[(x-w/2,-d,z-h/2),(x+w/2,-d,z-h/2),(x+w/2,-d,z+h/2),(x-w/2,-d,z+h/2)],[(0,1,2,3)],ma,False)
 o['surface_type']='intentional open printed decal; alpha cutout; not collision geometry'
 if parent:setparent(o,parent)
 return o

def display(name,w,h,d0,d1,r,texture,x=0,z=0,emit=0):
 ma=textured(name+'_Material',texture,.25,emit);return rbox(name,w,h,d0,d1,r,ma,x,z,b=.00015)

def bead_mesh(name,positions,r,mat,parent=None,seg=8,rings=6):
 # Batched disconnected closed beads, with shared object/material to limit draw calls.
 verts=[];faces=[]
 for cx,cy,cz in positions:
  base=len(verts)
  # nonzero small pole rings avoid degenerate quads; planar polygon caps close each bead.
  for j in range(rings):
   a=math.pi*(.07+.86*j/(rings-1));rad=r*math.sin(a)
   for k in range(seg):
    b=2*math.pi*k/seg;verts.append((cx+rad*math.cos(b),cy+rad*math.sin(b),cz+r*math.cos(a)))
  for j in range(rings-1):
   for k in range(seg):faces.append((base+j*seg+k,base+j*seg+(k+1)%seg,base+(j+1)*seg+(k+1)%seg,base+(j+1)*seg+k))
  faces.extend([tuple(base+k for k in range(seg-1,-1,-1)),tuple(base+(rings-1)*seg+k for k in range(seg))])
 ob=mesh(name,verts,faces,mat,parent=parent)
 ob.data.auto_smooth_angle=math.pi
 for mod in list(ob.modifiers):ob.modifiers.remove(mod)
 return ob

def chain_loop(name,top,bottom,rad,depth,mat,parent=None,axis='XZ',xoffset=0,pitch=.006):
 # Capsule path sampled by arc length. Real beads are separate islands in one named mesh.
 points=[];straight=top-bottom;length=2*straight+2*math.pi*rad;count=max(20,round(length/pitch))
 for i in range(count):
  s=length*i/count
  if s<straight:q=rad;z=top-s
  elif s<straight+math.pi*rad:
   a=(s-straight)/rad;q=rad*math.cos(a);z=bottom-rad*math.sin(a)
  elif s<2*straight+math.pi*rad:q=-rad;z=bottom+(s-straight-math.pi*rad)
  else:
   a=(s-2*straight-math.pi*rad)/rad;q=-rad*math.cos(a);z=top+rad*math.sin(a)
  points.append((q+xoffset,-depth,z) if axis=='XZ' else (xoffset,-depth+q,z))
 o=bead_mesh(name+'_Beads',points,.0022,mat,parent,8,6);tube(name+'_Cord',points,.00065,mat,6,parent,True);o['bead_pitch_m']=pitch
 return o

def join_matching(prefixes,name):
 objects=[o for o in COL.objects if o.type=='MESH' and o.name.startswith(tuple(prefixes))]
 if len(objects)<2:return
 bpy.ops.object.select_all(action='DESELECT')
 for o in objects:o.select_set(True)
 bpy.context.view_layer.objects.active=objects[0];bpy.ops.object.join();objects[0].name=name

def finish(num,name):
 s=bpy.context.scene
 for prefixes,newname in [(['Connector_Rib_'],'Connector_Grip_Ribs'),(['Cover_Grip_Rib_'],'Cover_Grip_Ribs'),(['Clutch_Tooth_'],'Clutch_Teeth'),(['Display_','Level_'],'LED_Dot_Display')]:join_matching(prefixes,newname)
 bpy.context.view_layer.update();obs=list(COL.objects)
 for o in obs:
  if o.type=='MESH' and o.parent==ROOT and o.location.length==0:
   # Centre small independent parts; articulated groups are already given explicit pivots.
   if not o.name.startswith(('Cloth','Roller')):
    centre=sum((v.co for v in o.data.vertices),Vector())/len(o.data.vertices);pivot(o,centre)
 bpy.context.view_layer.update();bpy.ops.object.select_all(action='DESELECT')
 for o in obs:o.select_set(True)
 bpy.context.view_layer.objects.active=ROOT
 stem=f'{num:02d}_{name}'
 bpy.ops.export_scene.fbx(filepath=str(P/'FBX'/(stem+'.fbx')),use_selection=True,object_types={'MESH','EMPTY'},apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',axis_forward='-Z',axis_up='Y',use_mesh_modifiers=True,mesh_smooth_type='FACE',use_triangles=False,bake_anim=False,path_mode='COPY',embed_textures=True,use_custom_props=True)
 bpy.ops.export_scene.gltf(filepath=str(P/'GLB'/(stem+'.glb')),export_format='GLB',use_selection=True,export_apply=True,export_yup=True,export_extras=True)
 s['project']='TalTech smart-room digital twin';s['reference_dimensions_are_estimates']=True
 for screen in bpy.data.screens:
  for area in screen.areas:
   if area.type=='VIEW_3D':
    area.spaces.active.clip_start=.0001;area.spaces.active.region_3d.view_distance=.3;area.spaces.active.shading.type='MATERIAL'
 bpy.ops.wm.save_as_mainfile(filepath=str(P/'Blender'/(stem+'.blend')))
 print('DEVICE_SAVED',stem,flush=True)


def device02():
 new_device(2,'Zigbee_Temperature_LCD','86 x 86 x 23 mm','Dimensions estimated; LCD sample is 21.7 C / 48%.')
 white=material('02_Warm_ABS',(.8,.81,.755),.32);edge=material('02_Pearl_Rim',(.66,.7,.66),.24);shadow=material('02_Seams',(.08,.1,.08),.6)
 rbox('Rear_Cover',.084,.084,0,.016,.012,white,b=.002)
 frame('Front_Rounded_Bezel',.085,.083,.054,.065,.0162,.022,.011,.0045,white,ix=-.0095,b=.0008)
 # Silver-grey narrow surround is visible at the cover split.
 frame('Bezel_Seam_Trim',.0856,.0836,.083,.081,.0156,.0161,.0115,.010,edge,b=.0001)
 display('LCD_Display',.0536,.0646,.018,.02185,.0043,'02_LCD_BaseColor.png',x=-.0095)
 for i,(z,icon) in enumerate([(.025,'Plus'),(0,None),(-.025,'Minus')]):
  b=rbox(f'Button_{i+1}_{icon or "Mode"}',.0167,.0215,.02205,.023,.002,white,x=.0317,z=z,b=.00035);pivot(b,(.0317,-.02205,z));b['interaction']='Press along local +Y (Unity -Z), 0.4 mm'
  if icon:decal('02_'+icon,.004,.004,.02304,.0317,z,'Icon_'+icon+'.png',b)
 block('Top_Pairing_Button',(0,-.010,.0422),(.010,.004,.0009),white,.0003)
 finish(2,'Zigbee_Temperature_LCD')

def device03():
 new_device(3,'ZWave_Temperature_Controller','86 x 86 x 15 mm','Nice-style controller; screen graphics recreated from photograph, not live data.')
 white=material('03_Pearl_Plastic',(.75,.79,.745),.25);rear=material('03_Rear_ABS',(.68,.7,.65),.4)
 rbox('Rear_Mounting_Case',.083,.083,0,.010,.0018,rear,b=.0008)
 frame('Gloss_Front_Frame',.086,.086,.073,.051,.0102,.0143,.0025,.0007,white,iz=.005,b=.00065)
 display('Temperature_Display',.0726,.0506,.011,.01415,.0005,'03_Thermostat_Display.png',z=.005,emit=.12)
 # Five independent capacitive touch targets, printed legends held on a separate surface.
 for i,x in enumerate([-.033,-.017,0,.017,.033]):
  o=empty(['Touch_Schedule','Touch_Mode','Touch_Down','Touch_Up','Touch_Power'][i],(x,-.01435,-.031));o['interaction']='Capacitive touch target; add a BoxCollider in Unity'
 decal('03_Touch_Keys',.079,.011,.01436,0,-.034,'03_Touch_Key_Legends.png')
 finish(3,'ZWave_Temperature_Controller')

def device04():
 new_device(4,'Security_Camera','110 x 110 x 72 mm head; approximately 130 mm wall projection','Mount and cable rear routing estimated from a single photograph.')
 white=material('04_Camera_White',(.79,.8,.765),.31);black=material('04_Gloss_Black',(.007,.01,.014),.13);rubber=material('04_Rubber',(.018,.021,.024),.55);metal=material('04_Metal',(.28,.30,.31),.27,.7);glass=material('04_Lens_Glass',(.002,.008,.012),.09,.12)
 rbox('Wall_Base',.042,.060,0,.008,.008,white,z=-.020,b=.0012)
 for z in (-.041,.001):disk('Mount_Screw_'+str(z),.003,.008,.009,metal,z=z,n=24)
 cylinder_between('Mount_Arm',(0,-.008,-.018),(0,-.044,.002),.008,white)
 ball=disk('Tilt_Joint',.014,.038,.051,white,z=.01);pivot(ball,(0,-.044,.01))
 head=empty('Camera_Tilt_Pivot',(0,-.050,.015));head['interaction']='Rotate about local X for tilt; local Z for yaw in Blender (Unity X / Y).'
 def H(o):bpy.context.view_layer.update();return setparent(o,head)
 H(rbox('Camera_Housing',.110,.110,.050,.120,.025,white,z=.018,b=.004))
 H(rbox('Black_Front_Fascia',.102,.102,.1201,.1214,.022,black,z=.018,b=.0005))
 H(ring('Lens_Barrel_Rim',.0192,.0159,.1215,.1254,rubber,x=-.024,z=.042))
 H(ring('Lens_Metal_Retainer',.016,.0148,.125,.1258,metal,x=-.024,z=.042))
 H(disk('Optical_Lens',.01465,.1248,.1257,glass,x=-.024,z=.042,bevel=.0002))
 H(disk('Lens_Inner_Aperture',.0055,.12572,.12576,material('04_Lens_Coating',(.001,.002,.002),.16),x=-.024,z=.042,bevel=.000005,n=32))
 H(ring('Floodlight_Rim',.021,.0189,.1215,.1243,rubber,x=.024,z=.012))
 H(disk('Floodlight_Diffuser',.0188,.123,.1244,textured('04_Faceted_Diffuser','04_Diffuser_BaseColor.png',.32),x=.024,z=.012,bevel=.0002))
 H(disk('PIR_Sensor_Window',.019,.1215,.1242,rubber,x=-.024,z=-.006,bevel=.0008))
 H(disk('Status_LED',.0011,.1215,.122,material('04_LED_Red',(.7,.002,.009),.3,emission=2),x=-.001,z=.014,n=20,bevel=.0001))
 H(disk('Microphone_Port',.0008,.12145,.12165,rubber,x=.033,z=.048,n=16,bevel=.00002))
 pts=bezier_points((.032,-.055,-.026),(.075,-.058,-.14),(-.023,-.055,-.13),(-.010,-.05,-.082),36)
 tube('Weatherproof_Power_Cable',pts,.003,white,10)
 cylinder_between('Weatherproof_Connector',(-.020,-.05,-.090),(.020,-.05,-.090),.0085,white)
 for i in range(7):cylinder_between('Connector_Rib_'+str(i),(-.015+i*.004,-.05,-.090),(-.014+i*.004,-.05,-.090),.0091,white,n=24)
 finish(4,'Security_Camera')

def device05():
 new_device(5,'Aqara_Bead_Chain_Controller','43 x 165 x 38 mm body; short 220 mm demonstration chain loop','Bead chain length is an editable representative segment; rear drive internals simplified.')
 white=material('05_Ivory_ABS',(.78,.785,.70),.36);grey=material('05_Chain_Polymer',(.38,.40,.37),.38);seam=material('05_Seam',(.15,.16,.14),.62)
 rbox('Wall_Mount_Plate',.038,.160,0,.004,.011,white,b=.001)
 asym_rbox('Motor_Housing',.043,.165,.0043,.031,.020,.003,white,b=.001)
 # Sliding upper cover, with a rounded top and ribbed grip.
 cover=rbox('Sliding_Drive_Cover',.041,.076,.0312,.037,.019,white,z=.044,b=.001)
 pivot(cover,(0,-.0312,.044));cover['interaction']='Slide upwards along local Z (Unity +Y) to expose drive.'
 for i in range(7):rbox('Cover_Grip_Rib_'+str(i),.030-i*.0017,.00065,.03705,.03755,.0002,white,z=.020-i*.0017,b=.00015,parent=cover)
 decal('05_OPEN',.014,.0035,.03761,0,.016,'05_Open_Legend.png',cover)
 decal('05_Aqara',.020,.0046,.0311,0,-.015,'05_Aqara_Logo.png')
 rbox('Button_Recess',.014,.041,.0311,.0313,.006,seam,z=-.051,b=.00004)
 rbox('Button_Fascia',.0134,.040,.03135,.032,.006,white,z=-.051,b=.0002)
 for name,z,icon in [('Raise',-.039,'Up'),('Lower',-.062,'Down')]:
  b=disk('Button_'+name,.0045,.0321,.0332,white,z=z,n=32);pivot(b,(0,-.0321,z));b['interaction']='Press inward 0.4 mm along local +Y / Unity -Z'
  decal('05_'+name,.004,.004,.03325,0,z,'Icon_'+icon+'.png',b)
 disk('Status_LED',.0005,.0321,.0324,material('05_LED',(.06,.08,.06),.4),z=-.051,n=16,bevel=.00005)
 drive=empty('Drive_Sprocket_Pivot',(0,-.013,.071));drive['interaction']='Rotate local Y / Unity Z; chain is a separate visual assembly.'
 wheel=disk('Chain_Drive_Wheel',.015,.008,.018,white,z=.071,n=48);bpy.context.view_layer.update();setparent(wheel,drive)
 chain=empty('Chain_Assembly',(0,0,0));chain_loop('BeadChain',.257,.071,.016,.013,grey,chain,pitch=.006)
 finish(5,'Aqara_Bead_Chain_Controller')

def device06():
 new_device(6,'Roller_Blind_Mechanism','1.20 m roller width; 0.45 m visible cloth drop; 0.80 m chain','Window and wall excluded; hidden clutch detail simplified. Cloth has Raise_Blind blend shape.')
 white=material('06_Casing_White',(.75,.76,.7),.4);metal=material('06_Roller_Aluminium',(.55,.57,.58),.32,.75);clothmat=material('06_Blind_Fabric',(.43,.42,.37),.9);chainmat=material('06_Chain',(.57,.57,.53),.4)
 # Root is top centre of mounting plane; roller's shaft is at depth 35 mm, z=-30 mm.
 for x,label in [(-.603,'Left'),(.603,'Right')]:
  block('Wall_Bracket_'+label,(x,-.012,-.030),(.015,.024,.070),white,.002)
  cylinder_between('Axle_'+label,(x-.01,-.035,-.03),(x+.01,-.035,-.03),.009,metal)
 roller=empty('Roller_Rotation_Pivot',(0,-.035,-.030));roller['interaction']='Rotate local X; rod and rolled cloth follow this pivot.'
 o=cylinder_between('Roller_Tube',(-.589,-.035,-.03),(.589,-.035,-.03),.023,metal,64);bpy.context.view_layer.update();setparent(o,roller)
 o=cylinder_between('Rolled_Fabric',(-.581,-.035,-.03),(.581,-.035,-.03),.0255,clothmat,64);bpy.context.view_layer.update();setparent(o,roller)
 for x,label in [(-.593,'Left'),(.593,'Right')]:cylinder_between('Roll_Endcap_'+label,(x-.004,-.035,-.030),(x+.004,-.035,-.030),.027,white,48)
 # Front half-round fascia casing, open underneath; annular arc with quad strips.
 verts=[];faces=[];steps=32
 for x in (-.598,.598):
  for rad in (.036,.034):
   for i in range(steps):
    a=math.radians(-8+196*i/(steps-1));verts.append((x,-.035-rad*math.cos(a),-.030+rad*math.sin(a)))
 for side in range(2):
  b=side*steps*2
  for i in range(steps-1):faces.append((b+i,b+i+1,b+steps+i+1,b+steps+i))
 for ringidx in range(2):
  b=ringidx*steps
  for i in range(steps-1):faces.append((b+i,b+i+1,b+2*steps+i+1,b+2*steps+i))
 for i in (0,steps-1):faces.append((i,steps+i,3*steps+i,2*steps+i))
 mesh('Half_Round_Head_Cassette',verts,faces,white)
 # Closed thin cloth prism with a regular editable quad grid; shape key raises it.
 nx,nz=16,20;verts=[];faces=[]
 for side in range(2):
  for j in range(nz+1):
   t=j/nz
   for i in range(nx+1):
    x=-.580+1.16*i/nx;y=-.061-side*.0007-.0012*math.sin(i/nx*math.pi)*math.sin(t*math.pi);verts.append((x,y,-.034-.45*t))
 count=(nx+1)*(nz+1)
 for side in range(2):
  off=side*count
  for j in range(nz):
   for i in range(nx):
    a=off+j*(nx+1)+i;faces.append((a,a+1,a+nx+2,a+nx+1))
 for j in range(nz):
  for i in (0,nx):a=j*(nx+1)+i;faces.append((a,a+nx+1,a+nx+1+count,a+count))
 for i in range(nx):
  for j in (0,nz):a=j*(nx+1)+i;faces.append((a,a+1,a+1+count,a+count))
 cloth=mesh('Cloth_With_Raise_BlendShape',verts,faces,clothmat,False);cloth.shape_key_add(name='Basis');key=cloth.shape_key_add(name='Raise_Blind')
 for v in key.data:v.co.z=-.034+(v.co.z+.034)*.055
 cloth['interaction']='Blend shape Raise_Blind 0..1; move Bottom_Rail_Pivot from z=-0.484 to -0.05875 in Blender.'
 rail=empty('Bottom_Rail_Pivot',(0,-.061,-.484));rail['interaction']='Translate local Z; Unity Y. Raised centre is -0.05875 m.'
 bar=block('Bottom_Rail',(0,-.061,-.484),(1.168,.013,.013),metal,.0018);bpy.context.view_layer.update();setparent(bar,rail)
 for x in (-.584,.584):o=block('Bottom_Endplug_'+str(x),(x,-.061,-.484),(.005,.014,.014),white,.001);bpy.context.view_layer.update();setparent(o,rail)
 clutch=empty('Chain_Clutch_Pivot',(.620,-.035,-.030));clutch['interaction']='Rotate local X with the roller.'
 o=cylinder_between('Chain_Sprocket',(.612,-.035,-.030),(.625,-.035,-.030),.025,white,48);bpy.context.view_layer.update();setparent(o,clutch)
 for k in range(16):
  a=k*2*math.pi/16;y=-.035+.025*math.cos(a);z=-.030+.025*math.sin(a);o=block('Clutch_Tooth_'+str(k),(.621,y,z),(.009,.004,.004),white,.0005);bpy.context.view_layer.update();setparent(o,clutch)
 c=empty('Chain_Loop_Assembly');chain_loop('Blind_Chain',-.030,-.790,.025,.035,chainmat,c,axis='YZ',xoffset=.625,pitch=.007)
 finish(6,'Roller_Blind_Mechanism')

def device07():
 new_device(7,'Siemens_BACnet_Device','88 x 88 x 25 mm','Front face, logo and dotted 93 indicator reproduced; hidden electronics omitted.')
 white=material('07_White_ABS',(.78,.79,.72),.34);face=material('07_Satin_Grey',(.19,.20,.17),.44);dark=material('07_Seam',(.06,.07,.06),.6);led=material('07_Display_Dots',(.70,.66,1),.4,emission=1.4)
 rbox('Rear_Wall_Plate',.088,.088,0,.007,.008,white,b=.002)
 frame('White_Rounded_Frame',.083,.083,.076,.076,.0072,.024,.011,.009,white,b=.0008)
 rbox('Front_Shadow_Gasket',.076,.076,.017,.0229,.009,dark,b=.0004)
 panel=rbox('Grey_Front_Panel',.0746,.0746,.023,.0248,.0085,face,b=.0007)
 decal('07_SIEMENS',.027,.0055,.02485,-.016,.030,'07_Siemens_Logo.png')
 disk('Ambient_Sensor',.00065,.02481,.02496,dark,x=.022,z=.027,n=16,bevel=.00003)
 disk('Status_LED_Green',.00065,.02481,.025,material('07_LED_Green',(.01,.8,.06),.4,emission=1.3),x=.028,z=.027,n=16,bevel=.00003)
 group=empty('Dot_Display_Assembly')
 patterns={'9':['111','101','111','001','001'],'3':['111','001','111','001','111']}
 for index,digit in enumerate('93'):
  for row,line in enumerate(patterns[digit]):
   for col,v in enumerate(line):
    if v=='1':
     o=disk(f'Display_{index}_Dot_{row}_{col}',.00047,.02482,.02494,led,x=.010+index*.012+col*.003,z=-.012-row*.003,n=12,bevel=.00002);bpy.context.view_layer.update();setparent(o,group)
 for i in range(5):disk('Level_Dot_'+str(i),.00047,.02482,.02494,led,x=-.027+i*.006,z=-.024,n=12,bevel=.00002)
 disk('Level_Cursor',.00047,.02482,.02494,led,x=-.015,z=-.021,n=12,bevel=.00002)
 finish(7,'Siemens_BACnet_Device')

def device08():
 new_device(8,'Nest_Smart_Speaker','98 mm speaker diameter, 42 mm body depth; removable wall cradle','Nest/Home Mini family appearance from photo; small status lights are separate and initially dark.')
 white=material('08_Chalk_Plastic',(.7,.72,.68),.4);black=material('08_Cradle_Black',(.013,.016,.017),.52);fabric=textured('08_Woven_Fabric','08_Fabric_BaseColor.png',.92,normal='08_Fabric_Normal.png')
 rbox('Cradle_Wall_Plate',.055,.050,0,.005,.008,black,z=-.014,b=.001)
 body=empty('Speaker_Body_Pivot',(0,-.025,0))
 rear=disk('Speaker_Rear_Shell',.0478,.0053,.015,white,n=64,bevel=.001);bpy.context.view_layer.update();setparent(rear,body)
 profile=[(.047,.0153),(.0484,.017),(.049,.020),(.0489,.023),(.0478,.027),(.0458,.031),(.0426,.035),(.038,.038),(.032,.040),(.024,.0415),(.014,.0422),(.003,.0425)]
 rs=[[(r*math.cos(i*2*math.pi/64),-d,r*math.sin(i*2*math.pi/64)) for i in range(64)] for r,d in profile];shell=loops('Fabric_Dome',rs,fabric)
 # Planar front-projected UV maintains a regular weave across the visible dome.
 bpy.context.view_layer.update();setparent(shell,body)
 # Three support fingers and lower cradle arc are actual geometry.
 verts=[];faces=[];n=40
 for r,d in [(.051,.018),(.051,.031),(.0488,.031),(.0488,.018)]:
  for i in range(n):
   a=math.radians(190+160*i/(n-1));verts.append((r*math.cos(a),-d,r*math.sin(a)))
 for j in range(4):
  for i in range(n-1):faces.append((j*n+i,j*n+i+1,((j+1)%4)*n+i+1,((j+1)%4)*n+i))
 faces.extend([(0,n,2*n,3*n),(n-1,2*n-1,3*n-1,4*n-1)]);mesh('Cradle_Lower_Arc',verts,faces,black)
 for angle in (207,270,333):
  a=math.radians(angle);x=.047*math.cos(a);z=.047*math.sin(a)
  rbox('Cradle_Finger_'+str(angle),.011,.018,.019,.036,.004,black,x=x,z=z,b=.001)
 # A small mute slider along the rim.
 mute=block('Microphone_Mute_Switch',(.045,-.014,-.008),(.003,.006,.010),white,.001);bpy.context.view_layer.update();setparent(mute,body)
 for i in range(4):o=disk('Status_Light_'+str(i),.0012,.0424,.04255,material('08_LED_Diffuser',(.58,.60,.57),.7),x=(i-1.5)*.007,n=20,bevel=.00003);bpy.context.view_layer.update();setparent(o,body)
 pts=bezier_points((-.029,-.012,-.035),(-.055,-.016,-.073),(-.10,-.013,-.050),(-.108,-.005,-.048),32);tube('Power_Cable',pts,.0016,white,10)
 finish(8,'Nest_Smart_Speaker')

def device09():
 new_device(9,'DALI_Touchscreen_Panel','180 x 120 x 22 mm; 156 x 88 mm active screen','Screen reconstructed from photo; graphical controls are textures with named touch targets.')
 white=material('09_Pearl_Bezel',(.69,.72,.69),.28);dark=material('09_Dark_Rear',(.04,.038,.032),.46);gasket=material('09_Screen_Gasket',(.07,.09,.09),.5)
 rbox('Wall_Mount',.105,.070,0,.005,.004,dark,b=.001)
 rbox('Rear_Housing',.176,.116,.0052,.018,.004,dark,b=.001)
 frame('Front_White_Bezel',.180,.120,.157,.089,.0182,.022,.005,.001,white,b=.0007)
 rbox('Screen_Gasket',.1569,.0889,.019,.02155,.001,gasket,b=.0001)
 display('Touchscreen_Display',.156,.088,.0216,.0219,.0006,'09_DALI_Touchscreen_BaseColor.png',emit=.38)
 for name,x,z,w,h in [('On',-.059,.017,.023,.024),('Off',-.059,-.006,.023,.024),('Brightness',-.036,0,.015,.054),('Colour_Temperature',-.014,0,.021,.050),('Colour_Field',.033,0,.067,.050),('Scene_Task',-.052,-.034,.038,.014),('Scene_Presentation_1',0,-.034,.038,.014),('Scene_Presentation_2',.052,-.034,.038,.014)]:
  o=empty('Touch_'+name,(x,-.02195,z));o['interaction']='Touch target; attach a Unity BoxCollider or map screen UV coordinates.';o['target_size_m']=[w,.001,h]
 finish(9,'DALI_Touchscreen_Panel')

FUNCS={2:device02,3:device03,4:device04,5:device05,6:device06,7:device07,8:device08,9:device09}
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
for index in ([int(x) for x in args] if args else range(2,10)):FUNCS[index]()
print('ALL_DEVICE_BUILDS_FINISHED',flush=True)
