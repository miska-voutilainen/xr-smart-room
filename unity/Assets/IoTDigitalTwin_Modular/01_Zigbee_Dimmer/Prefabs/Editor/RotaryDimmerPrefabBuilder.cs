using System;using System.Collections.Generic;using System.Linq;
using UnityEngine;using UnityEngine.Rendering;using UnityEditor;
using static IoTDigitalTwin.Editor.IoTAssetGenerator;
namespace IoTDigitalTwin.Editor {
    [InitializeOnLoad] public static class RotaryDimmerPrefabBuilder {
        static RotaryDimmerPrefabBuilder(){Register(1,Build);}
        [MenuItem("Tools/IoT Digital Twin/Individual Devices/01_Zigbee_Dimmer")]
        public static void Generate(){GenerateDevice(1);}
        public static IoTDevice Build(GameObject wrapper){Transform f=wrapper.transform;
var d=wrapper.AddComponent<RotaryDimmer>();d.knob=Find(f,"05_Rotary_Knob");Target(d,d.knob,"Knob",Photo(0,0,.027f),.034f,.034f);return d;
        }
    }
}
