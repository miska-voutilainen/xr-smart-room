import bpy,sys
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parents[1]
settings=[(5,'05_Controller_Detail',(0,-.022,.002),(.10,-.35,.075),.205),(6,'06_Clutch_Detail',(.606,-.035,-.05),(.90,-.38,.13),.20),(8,'08_Fabric_Detail',(0,-.032,.006),(.03,-.19,.060),.072),(4,'04_Mount_Detail',(0,-.040,-.01),(.18,.17,.07),.22)]
selected=[int(x) for x in sys.argv[sys.argv.index('--')+1:]] if '--' in sys.argv else []
for idx,name,target,loc,scale in settings:
 if selected and idx not in selected:continue
 path=next((P/'Blender').glob(f'{idx:02d}_*.blend'));bpy.ops.wm.open_mainfile(filepath=str(path));s=bpy.context.scene;cam=s.camera;cam.location=loc;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=scale
 if idx==4:
  bpy.data.objects['Studio_Wall'].hide_render=True;k=bpy.data.objects['Key'];k.location=(.02,.18,.18);k.rotation_euler=(Vector(target)-k.location).to_track_quat('-Z','Y').to_euler()
 s.render.resolution_x=s.render.resolution_y=900;s.cycles.samples=48;s.render.filepath=str(P/'Previews'/(name+'.png'));bpy.ops.render.render(write_still=True);print('DETAIL_COMPLETE',name,flush=True)
