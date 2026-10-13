from pathlib import Path
import subprocess,json
root=Path(__file__).resolve().parents[1];check=root/'Verification~/Offline';logs=root/'Verification~/Logs';logs.mkdir(exist_ok=True)
stub=check/'UnityApiStubs.cs';runtime=list(root.glob('Shared/Scripts/*.cs'));editor=list(root.glob('Shared/Editor/*.cs'))
results=[]
def run(name,cmd):
 p=subprocess.run([str(c) for c in cmd],capture_output=True,text=True);out=p.stdout+p.stderr;(logs/(name+'.txt')).write_text(out or 'PASS: compilation succeeded without diagnostics.\n');results.append({'check':name,'passed':p.returncode==0,'output':out.strip()});print(name,p.returncode,out.strip()[:150]);return p.returncode==0
run('FullLibrary_CSharp_Compilation',['mcs','-target:library','-r:System.Numerics','-out:/tmp/iot_full.dll',*[p for p in root.glob('**/*.cs') if p.name not in ('ControllerLogicTests.cs','PureLogicTests.cs')]]) # remove duplicate stub below
for folder in sorted(root.glob('[0-9][0-9]_*')):
 run(folder.name+'_Independent_Compilation',['mcs','-target:library','-r:System.Numerics','-out:/tmp/iot_single.dll',stub,*runtime,*editor,*folder.rglob('*.cs')])
run('InputSystem_Branch_Compilation',['mcs','-define:ENABLE_INPUT_SYSTEM','-target:library','-r:System.Numerics','-out:/tmp/iot_input.dll',*[p for p in root.glob('**/*.cs') if p.name not in ('ControllerLogicTests.cs','PureLogicTests.cs')]])
run('Pure_Logic_Compilation',['mcs','-out:/tmp/iot_pure.exe',root/'Shared/Scripts/DeviceMath.cs',check/'PureLogicTests.cs'])
run('Pure_Logic_Execution',['mono','/tmp/iot_pure.exe'])
controllers=[p for d in root.glob('[0-9][0-9]_*') for p in d.glob('Scripts/*.cs')]
if run('Controller_Logic_Compilation',['mcs','-r:System.Numerics','-out:/tmp/iot_controller.exe',stub,*runtime,*controllers,check/'ControllerLogicTests.cs']):run('Controller_Logic_Execution',['mono','/tmp/iot_controller.exe'])
(logs/'Offline_Results.json').write_text(json.dumps({'actualUnityEditorRun':False,'tests':results},indent=2));assert all(r['passed'] for r in results),'See logs for failed tests'
