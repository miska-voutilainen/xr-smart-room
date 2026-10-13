from pathlib import Path
import json,zipfile,hashlib
P=Path(__file__).resolve().parents[1]
for p in (P/'Blender').glob('*.blend1'):p.unlink()
j=json.loads((P/'Reports/validation.json').read_text());assert len(j['devices'])==9
manifest=[];rows=['# Mesh budget\n','Evaluated geometry, including bevels, cables and bead chains. Studio objects are excluded.\n','| Device | Mesh objects | Render triangles | Source quad faces |','|---|---:|---:|---:|']
for d in j['devices']:
 s=d['source'];manifest.append({'id':d['device'][:2],'name':d['device'][3:],'fbx':'FBX/'+d['device']+'.fbx','glb':'GLB/'+d['device']+'.glb','blender':'Blender/'+d['device']+'.blend','units':'metres','dimensions_estimated':True,'mesh_objects':s['mesh_count'],'render_triangles':d['total_render_triangles'],'pivots_exported_model_xyz':{k:[v[0],v[2],-v[1]] for k,v in s['pivots'].items()},'blend_shapes':s['shape_keys']})
 rows.append(f"| {d['device']} | {s['mesh_count']} | {d['total_render_triangles']:,} | {sum(m['source_quads'] for m in d['mesh_statistics']):,} |")
rows.append(f"\n**Total: {sum(d['total_render_triangles'] for d in j['devices']):,} render triangles.**")
(P/'Reports/Mesh_Budget.md').write_text('\n'.join(rows)+'\n')
(P/'device_manifest.json').write_text(json.dumps({'front_axis':'+Z','up_axis':'+Y','individual_export_roots_at_origin':True,'devices':manifest},indent=2))
assert len(list((P/'FBX').glob('*.fbx')))==9
assert len(list((P/'GLB').glob('*.glb')))==9
assert len(list((P/'Blender').glob('*.blend')))==10
for i in range(1,10):assert list((P/'Previews').glob(f'{i:02d}_*.png'))
files=sorted(p for p in P.rglob('*') if p.is_file() and p.name!='SHA256.json')
(P/'Reports/SHA256.json').write_text(json.dumps({str(p.relative_to(P)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files},indent=2))
archive=P.parent/'TalTech_IoT_Devices_All_9.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for p in sorted(P.rglob('*')):
  if p.is_file():z.write(p,Path(P.name)/p.relative_to(P))
with zipfile.ZipFile(archive) as z:assert z.testzip() is None;print('ARCHIVE_VALIDATED',len(z.namelist()),'files',round(archive.stat().st_size/1e6,2),'MB')
