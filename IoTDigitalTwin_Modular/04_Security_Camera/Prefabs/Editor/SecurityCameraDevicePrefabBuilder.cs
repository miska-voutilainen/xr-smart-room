using System;using System.Collections.Generic;using System.Linq;
using UnityEngine;using UnityEngine.Rendering;using UnityEditor;
using static IoTDigitalTwin.Editor.IoTAssetGenerator;
namespace IoTDigitalTwin.Editor {
    [InitializeOnLoad] public static class SecurityCameraDevicePrefabBuilder {
        static SecurityCameraDevicePrefabBuilder(){Register(4,Build);}
        [MenuItem("Tools/IoT Digital Twin/Individual Devices/04_Security_Camera")]
        public static void Generate(){GenerateDevice(4);}
        public static IoTDevice Build(GameObject wrapper){Transform f=wrapper.transform;
var d=wrapper.AddComponent<SecurityCameraDevice>();d.head=Find(f,"Camera_Tilt_Pivot");d.status=Ind(f,"Status_LED");d.flood=Ind(f,"Floodlight_Diffuser");var light=new GameObject("Simulated_Floodlight");light.transform.SetParent(d.head,false);light.transform.position=f.TransformPoint(Photo(.024f,.012f,.127f));light.transform.rotation=f.rotation;d.flood.light=light.AddComponent<Light>();d.flood.light.type=LightType.Spot;d.flood.light.range=.8f;d.flood.light.spotAngle=65;Target(d,d.head,"Head",Photo(0,.018f,.123f),.104f,.104f);Target(d,Find(f,"Floodlight_Diffuser"),"Flood",Photo(.024f,.012f,.127f),.039f,.039f);return d;
        }
    }
}
