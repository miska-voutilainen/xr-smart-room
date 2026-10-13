using System;using System.Collections.Generic;using System.Linq;
using UnityEngine;using UnityEngine.Rendering;using UnityEditor;
using static IoTDigitalTwin.Editor.IoTAssetGenerator;
namespace IoTDigitalTwin.Editor {
    [InitializeOnLoad] public static class SiemensBACnetDevicePrefabBuilder {
        static SiemensBACnetDevicePrefabBuilder(){Register(7,Build);}
        [MenuItem("Tools/IoT Digital Twin/Individual Devices/07_Siemens_BACnet")]
        public static void Generate(){GenerateDevice(7);}
        public static IoTDevice Build(GameObject wrapper){Transform f=wrapper.transform;
var d=wrapper.AddComponent<SiemensBACnetDevice>();d.statusIndicator=Ind(f,"Status_LED_Green");Component<Renderer>(f,"LED_Dot_Display").enabled=false;d.display=DotGrid(f);Target(d,Find(f,"Grey_Front_Panel"),"Display",Photo(0,0,.0265f),.075f,.075f);Target(d,Find(f,"Status_LED_Green"),"Status",Photo(.028f,.027f,.027f),.008f,.008f);return d;
        }
        static DynamicDotDisplay DotGrid(Transform frame){
            var go=new GameObject("Live_Dot_Display");go.transform.SetParent(frame,false);var vertices=new List<Vector3>();var triangles=new List<int>();var colors=new List<Color>();
            var positions=new List<Vector3>();for(int digit=0;digit<2;digit++)for(int row=0;row<5;row++)for(int col=0;col<3;col++)positions.Add(Photo(.010f+digit*.012f+col*.003f,-.012f-row*.003f,.02505f));for(int i=0;i<5;i++)positions.Add(Photo(-.027f+i*.006f,-.024f,.02505f));positions.Add(Photo(-.015f,-.021f,.02505f));
            foreach(var p in positions){int start=vertices.Count;for(int i=0;i<8;i++){float angle=i*Mathf.PI/4;vertices.Add(p+new Vector3(Mathf.Cos(angle)*.00047f,Mathf.Sin(angle)*.00047f,0));colors.Add(Color.white);}for(int i=1;i<7;i++){triangles.Add(start);triangles.Add(start+i);triangles.Add(start+i+1);}}
            var mesh=new Mesh();mesh.name="Live_Dot_Grid";mesh.SetVertices(vertices);mesh.SetTriangles(triangles,0);mesh.SetColors(colors);mesh.RecalculateNormals();mesh.RecalculateBounds();var filter=go.AddComponent<MeshFilter>();filter.sharedMesh=StoreMesh(mesh,"Live_Dot_Grid");var renderer=go.AddComponent<MeshRenderer>();var material=new Material(displayShader);material.mainTexture=Texture2D.whiteTexture;renderer.sharedMaterial=StoreMaterial(material,"Live_Dot_Display");renderer.shadowCastingMode=ShadowCastingMode.Off;var display=go.AddComponent<DynamicDotDisplay>();display.filter=filter;return display;
        }
    }
}
