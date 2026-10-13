using System;using System.Collections.Generic;using System.Linq;
using UnityEngine;using UnityEngine.Rendering;using UnityEditor;
using static IoTDigitalTwin.Editor.IoTAssetGenerator;
namespace IoTDigitalTwin.Editor {
    [InitializeOnLoad] public static class DALILightingPanelPrefabBuilder {
        static DALILightingPanelPrefabBuilder(){Register(9,Build);}
        [MenuItem("Tools/IoT Digital Twin/Individual Devices/09_DALI_Touchscreen")]
        public static void Generate(){GenerateDevice(9);}
        public static IoTDevice Build(GameObject wrapper){Transform f=wrapper.transform;
            var panel=wrapper.AddComponent<DALILightingPanel>();ReplaceScreen(f,"Touchscreen_Display","Runtime_DALI_Background.png");panel.percentText=Text(f,"Live_Brightness","50%",DaliPixel(420,186),.0029f,new Color(.12f,.32f,.4f));panel.kelvinText=Text(f,"Live_Kelvin","4500K",DaliPixel(646,704),.0024f,new Color(.12f,.32f,.4f));panel.brightnessBottom=DaliPixel(420,642);panel.brightnessTop=DaliPixel(420,217);panel.tempWarm=DaliPixel(644,167);panel.tempCool=DaliPixel(644,646);panel.colorBottomLeft=DaliPixel(793,665);panel.colorTopRight=DaliPixel(1478,149);panel.scenePositions=new[]{DaliPixel(250,854),DaliPixel(800,854),DaliPixel(1325,854)};
            panel.brightnessThumb=Sprite(f,"Brightness_Thumb",panel.brightnessBottom,.015f,.0038f,"UI_Thumb.png");panel.tempThumb=Sprite(f,"Temperature_Handle",panel.tempWarm,.017f,.0035f,"UI_Temp_Handle.png");panel.colorMarker=Sprite(f,"Colour_Marker",DaliPixel(937,553),.010f,.005f,"UI_Color_Marker.png");panel.sceneMarker=Sprite(f,"Scene_Selection",panel.scenePositions[0],.028f,.0018f,"UI_Scene_Marker.png");
            string[] names={"On","Off","Brightness","Colour_Temperature","Colour_Field","Scene_Task","Scene_Presentation_1","Scene_Presentation_2"};float[,] sizes={{.023f,.024f},{.023f,.024f},{.015f,.054f},{.021f,.050f},{.067f,.050f},{.038f,.014f},{.038f,.014f},{.038f,.014f}};
            for(int i=0;i<names.Length;i++){var t=Find(f,"Touch_"+names[i]);var p=f.InverseTransformPoint(t.position);p.z=.0233f;Target(panel,t,names[i],p,sizes[i,0],sizes[i,1]);}return panel;

        }
    }
}
