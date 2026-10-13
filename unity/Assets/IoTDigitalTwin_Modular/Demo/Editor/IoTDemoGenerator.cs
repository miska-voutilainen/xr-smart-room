using UnityEngine;using UnityEngine.Rendering;using UnityEditor;
using static IoTDigitalTwin.Editor.IoTAssetGenerator;
namespace IoTDigitalTwin.Editor {
    [InitializeOnLoad] public static class IoTDemoGenerator {
        static IoTDemoGenerator(){DemoBuilder=ConfigureDemo;}
        static LightingOutput DemoLamp(Transform frame,string name,Vector3 position){
            var bulb=GameObject.CreatePrimitive(PrimitiveType.Sphere);bulb.name=name;UnityEngine.Object.DestroyImmediate(bulb.GetComponent<Collider>());bulb.transform.SetParent(frame,false);bulb.transform.localPosition=position;bulb.transform.localScale=Vector3.one*.014f;var material=new Material(lit);material.EnableKeyword("_EMISSION");bulb.GetComponent<Renderer>().sharedMaterial=StoreMaterial(material,name);var light=bulb.AddComponent<Light>();light.type=LightType.Point;light.range=.25f;light.intensity=1;return new LightingOutput{lamp=bulb.GetComponent<Renderer>(),light=light};
        }
        static void ConfigureDemo(IoTDevice[] devices){
            Vector3[] positions={new Vector3(-.60f,.72f,0),new Vector3(-.20f,.72f,0),new Vector3(.20f,.72f,0),new Vector3(.60f,.72f,0),new Vector3(-.60f,.24f,0),new Vector3(0,-.22f,0),new Vector3(-.20f,.24f,0),new Vector3(.20f,.24f,0),new Vector3(.60f,.24f,0)};
            for(int i=0;i<devices.Length;i++)devices[i].transform.position=positions[i];
            ((RotaryDimmer)devices[0]).output=DemoLamp(devices[0].transform,"Dimmer_Lamp",Photo(.065f,.020f,.025f));((DALILightingPanel)devices[8]).output=DemoLamp(devices[8].transform,"DALI_Lamp",Photo(.112f,0,.025f));((AqaraChainController)devices[4]).ConnectBlind((RollerBlindDevice)devices[5]);
            var wall=GameObject.CreatePrimitive(PrimitiveType.Cube);wall.name="Demo_Backboard";wall.transform.position=new Vector3(0,-.03f,-.011f);wall.transform.localScale=new Vector3(1.75f,2.12f,.02f);UnityEngine.Object.DestroyImmediate(wall.GetComponent<Collider>());var wallMat=new Material(lit);wallMat.color=new Color(.18f,.23f,.27f);wall.GetComponent<Renderer>().sharedMaterial=StoreMaterial(wallMat,"Demo_Backboard");
            var camera=new GameObject("Demo_Camera").AddComponent<Camera>();camera.tag="MainCamera";camera.orthographic=true;camera.orthographicSize=.10f;camera.nearClipPlane=.005f;camera.farClipPlane=10;camera.clearFlags=CameraClearFlags.SolidColor;camera.backgroundColor=new Color(.075f,.1f,.12f);camera.transform.position=new Vector3(-.60f,.72f,2);camera.transform.rotation=Quaternion.LookRotation(Vector3.back,Vector3.up);
            var light=new GameObject("Demo_KeyLight").AddComponent<Light>();light.type=LightType.Directional;light.intensity=1;light.transform.rotation=Quaternion.Euler(45,170,0);RenderSettings.ambientMode=AmbientMode.Flat;RenderSettings.ambientLight=new Color(.55f,.57f,.6f);
            var gui=new GameObject("Simulation_Demo").AddComponent<IoTDemoController>();gui.devices=devices;gui.viewCamera=camera;var input=camera.gameObject.AddComponent<IoTMouseInput>();input.interactionCamera=camera;input.inputGate=gui;var smoke=gui.gameObject.AddComponent<IoTPlayModeSmokeTest>();smoke.devices=devices;gui.smokeTest=smoke;
            results.Add("PASS standalone simulation wiring; Aqara linked to blind in demo only");
        }
    }
}
