using System;using System.Collections.Generic;using System.Linq;
using UnityEngine;using UnityEngine.Rendering;using UnityEditor;
using static IoTDigitalTwin.Editor.IoTAssetGenerator;
namespace IoTDigitalTwin.Editor {
    [InitializeOnLoad] public static class AqaraChainControllerPrefabBuilder {
        static AqaraChainControllerPrefabBuilder(){Register(5,Build);}
        [MenuItem("Tools/IoT Digital Twin/Individual Devices/05_Aqara_Controller")]
        public static void Generate(){GenerateDevice(5);}
        public static IoTDevice Build(GameObject wrapper){Transform f=wrapper.transform;
var d=wrapper.AddComponent<AqaraChainController>();d.sprocket=Find(f,"Drive_Sprocket_Pivot");d.cover=Find(f,"Sliding_Drive_Cover");d.raiseButton=Press(f,"Button_Raise");d.lowerButton=Press(f,"Button_Lower");d.status=Ind(f,"Status_LED");d.chain=Chain(f,"BeadChain_Beads",false,.257f,.071f,.016f,.013f,0);Target(d,d.raiseButton.part,"Raise",Photo(0,-.039f,.034f),.012f,.012f);Target(d,d.lowerButton.part,"Lower",Photo(0,-.062f,.034f),.012f,.012f);Target(d,d.cover,"Cover",Photo(0,.044f,.038f),.038f,.067f);return d;
        }
    }
}
