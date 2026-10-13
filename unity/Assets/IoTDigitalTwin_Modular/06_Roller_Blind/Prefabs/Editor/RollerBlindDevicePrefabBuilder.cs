using System;using System.Collections.Generic;using System.Linq;
using UnityEngine;using UnityEngine.Rendering;using UnityEditor;
using static IoTDigitalTwin.Editor.IoTAssetGenerator;
namespace IoTDigitalTwin.Editor {
    [InitializeOnLoad] public static class RollerBlindDevicePrefabBuilder {
        static RollerBlindDevicePrefabBuilder(){Register(6,Build);}
        [MenuItem("Tools/IoT Digital Twin/Individual Devices/06_Roller_Blind")]
        public static void Generate(){GenerateDevice(6);}
        public static IoTDevice Build(GameObject wrapper){Transform f=wrapper.transform;
var d=wrapper.AddComponent<RollerBlindDevice>();d.cloth=Component<SkinnedMeshRenderer>(f,"Cloth_With_Raise_BlendShape");d.bottomRail=Find(f,"Bottom_Rail_Pivot");d.roller=Find(f,"Roller_Rotation_Pivot");d.clutch=Find(f,"Chain_Clutch_Pivot");int index=-1;for(int i=0;i<d.cloth.sharedMesh.blendShapeCount;i++)if(d.cloth.sharedMesh.GetBlendShapeName(i).EndsWith("Raise_Blind",StringComparison.Ordinal))index=i;Require(index>=0,"Raise_Blind did not import as a blend shape.");d.blendShapeIndex=index;d.fullyRaisedWeight=d.cloth.sharedMesh.GetBlendShapeFrameWeight(index,d.cloth.sharedMesh.GetBlendShapeFrameCount(index)-1);d.chain=Chain(f,"Blind_Chain_Beads",true,-.030f,-.790f,.025f,.035f,.625f);Target(d,d.bottomRail,"Position",Photo(0,-.484f,.072f),1.17f,.026f);Require(d.fullyRaisedWeight>0,"Invalid blend-shape weight range.");Require(Mathf.Abs(f.InverseTransformPoint(d.bottomRail.position).y+.484f)<.0002f,"Bottom rail pivot differs from source.");return d;
        }
    }
}
