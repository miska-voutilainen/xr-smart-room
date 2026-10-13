using System;using System.Collections.Generic;using System.Linq;
using UnityEngine;using UnityEngine.Rendering;using UnityEditor;
using static IoTDigitalTwin.Editor.IoTAssetGenerator;
namespace IoTDigitalTwin.Editor {
    [InitializeOnLoad] public static class TemperatureLCDPrefabBuilder {
        static TemperatureLCDPrefabBuilder(){Register(2,Build);}
        [MenuItem("Tools/IoT Digital Twin/Individual Devices/02_Zigbee_Temperature_Sensor")]
        public static void Generate(){GenerateDevice(2);}
        public static IoTDevice Build(GameObject wrapper){Transform f=wrapper.transform;
var d=wrapper.AddComponent<TemperatureLCD>();ReplaceScreen(f,"LCD_Display","Runtime_LCD_Background.png");Color green=new Color(.06f,.1f,.05f);d.temperatureText=Text(f,"Live_Temperature","21.7°C",Photo(-.0095f,.011f,.02225f),.013f,green);d.humidityText=Text(f,"Live_Humidity","48%",Photo(-.0095f,-.021f,.02225f),.009f,green);d.pairingText=Text(f,"Pairing","",Photo(-.0095f,.026f,.02225f),.002f,green);d.buttons=new[]{Press(f,"Button_1_Plus"),Press(f,"Button_2_Mode"),Press(f,"Button_3_Minus")};
                string[] actions={"Plus","Mode","Minus"};float[] ys={.025f,0,-.025f};for(int i=0;i<3;i++)Target(d,d.buttons[i].part,actions[i],Photo(.0317f,ys[i],.024f),.018f,.022f);Target(d,Find(f,"Top_Pairing_Button"),"Pair",Photo(0,.043f,.011f),.013f,.006f);return d;
        }
    }
}
