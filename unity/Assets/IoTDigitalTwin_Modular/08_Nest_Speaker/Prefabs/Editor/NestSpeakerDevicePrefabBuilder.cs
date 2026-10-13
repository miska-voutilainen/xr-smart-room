using System;using System.Collections.Generic;using System.Linq;
using UnityEngine;using UnityEngine.Rendering;using UnityEditor;
using static IoTDigitalTwin.Editor.IoTAssetGenerator;
namespace IoTDigitalTwin.Editor {
    [InitializeOnLoad] public static class NestSpeakerDevicePrefabBuilder {
        static NestSpeakerDevicePrefabBuilder(){Register(8,Build);}
        [MenuItem("Tools/IoT Digital Twin/Individual Devices/08_Nest_Speaker")]
        public static void Generate(){GenerateDevice(8);}
        public static IoTDevice Build(GameObject wrapper){Transform f=wrapper.transform;
var d=wrapper.AddComponent<NestSpeakerDevice>();d.muteSwitch=Find(f,"Microphone_Mute_Switch");d.lights=Enumerable.Range(0,4).Select(i=>Ind(f,"Status_Light_"+i)).ToArray();Target(d,d.muteSwitch,"Mute",Photo(.047f,-.008f,.020f),.010f,.016f);Target(d,Find(f,"Fabric_Dome"),"Volume",Photo(0,0,.044f),.082f,.082f);return d;
        }
    }
}
