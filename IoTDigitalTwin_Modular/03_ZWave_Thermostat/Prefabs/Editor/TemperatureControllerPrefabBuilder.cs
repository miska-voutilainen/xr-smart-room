using System;using System.Collections.Generic;using System.Linq;
using UnityEngine;using UnityEngine.Rendering;using UnityEditor;
using static IoTDigitalTwin.Editor.IoTAssetGenerator;
namespace IoTDigitalTwin.Editor {
    [InitializeOnLoad] public static class TemperatureControllerPrefabBuilder {
        static TemperatureControllerPrefabBuilder(){Register(3,Build);}
        [MenuItem("Tools/IoT Digital Twin/Individual Devices/03_ZWave_Thermostat")]
        public static void Generate(){GenerateDevice(3);}
        public static IoTDevice Build(GameObject wrapper){Transform f=wrapper.transform;
var d=wrapper.AddComponent<TemperatureController>();ReplaceScreen(f,"Temperature_Display","Runtime_Thermostat_Background.png");Color blue=new Color(.16f,.43f,.9f);d.measuredText=Text(f,"Live_Measured","22.6°C",Photo(0,.008f,.0146f),.015f,blue);d.targetText=Text(f,"Live_Target","SET 22.0",Photo(-.020f,-.014f,.0146f),.0028f,blue);d.stateText=Text(f,"Power_State","ON",Photo(.029f,-.014f,.0146f),.0028f,blue);d.modeText=Text(f,"Control_Mode","AUTO",Photo(0,.025f,.0146f),.0025f,blue);
                foreach(string action in new[]{"Schedule","Mode","Down","Up","Power"}){Transform target=Find(f,"Touch_"+action);Vector3 p=f.InverseTransformPoint(target.position);p.z=.015f;Target(d,target,action,p,.014f,.017f);}return d;
        }
    }
}
