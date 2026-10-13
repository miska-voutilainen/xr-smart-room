using UnityEngine;
namespace IoTDigitalTwin {
    public sealed class IoTDemoController:MonoBehaviour,IPointerInputGate {
        public bool SuspendPointer{get{return smokeTest&&smokeTest.Running;}}
        public IoTDevice[] devices;public Camera viewCamera;public IoTPlayModeSmokeTest smokeTest;
        public bool automaticReadings=true,connectAqara=true,gallery;
        public int selected;public float panelWidth=310;
        Vector2 scroll,lastMouse;Vector3 focus;float zoom=1,nextReading;Quaternion viewRotation;
        static readonly string[] Names={"Zigbee dimmer","Temperature LCD","Z-Wave thermostat","Security camera","Aqara chain drive","Roller blind","Siemens BACnet","Nest speaker","DALI panel"};
        void Start(){focus=devices[0].transform.position;FocusDevice(0);lastMouse=IoTMouseInput.Position();}
        public bool PointerOverPanel(Vector2 position){return position.x<Mathf.Min(panelWidth,Screen.width*.38f);}
        public void FocusDevice(int index){selected=Mathf.Clamp(index,0,8);gallery=false;zoom=1;viewRotation=Quaternion.LookRotation(Vector3.back,Vector3.up);}
        public void ShowGallery(){gallery=true;zoom=1;viewRotation=Quaternion.LookRotation(Vector3.back,Vector3.up);}
        void Update(){
            float width=Mathf.Min(panelWidth,Screen.width*.38f);viewCamera.pixelRect=new Rect(width+8,0,Mathf.Max(32,Screen.width-width-8),Screen.height);
            var aqara=(AqaraChainController)devices[4];var blind=(RollerBlindDevice)devices[5];if(connectAqara!=(aqara.LinkedBlind!=null))aqara.ConnectBlind(connectAqara?blind:null);
            if(automaticReadings&&!smokeTest.Running&&Time.time>=nextReading){nextReading=Time.time+1;float t=22+1.5f*Mathf.Sin(Time.time*.12f);if(devices[1].simulationMode){((TemperatureLCD)devices[1]).SetTemperature(t);((TemperatureLCD)devices[1]).SetHumidity(48+9*Mathf.Sin(Time.time*.07f));}if(devices[2].simulationMode)((TemperatureController)devices[2]).SetTemperature(t+.5f);if(devices[6].simulationMode)((SiemensBACnetDevice)devices[6]).SetDisplayValue(t);}
            Vector3 wanted;float size;
            if(gallery){wanted=new Vector3(0,-.12f,.05f);size=Mathf.Max(1.15f,.93f/viewCamera.aspect);}
            else{var root=devices[selected].transform;Vector3 offset=selected==3?new Vector3(0,-.015f,.07f):selected==5?new Vector3(0,-.4f,.04f):Vector3.zero;wanted=root.TransformPoint(offset);float[] sizes={.10f,.063f,.063f,.13f,.112f,.55f,.064f,.10f,.093f};size=sizes[selected];if(selected==5)size=Mathf.Max(size,.67f/viewCamera.aspect);}
            Vector2 mouse=IoTMouseInput.Position(),delta=mouse-lastMouse;lastMouse=mouse;
            if(!PointerOverPanel(mouse)&&IoTMouseInput.OrbitHeld()){viewRotation=Quaternion.AngleAxis(delta.x*.22f,Vector3.up)*viewRotation;viewRotation=viewRotation*Quaternion.AngleAxis(-delta.y*.16f,Vector3.right);}
            focus=Vector3.Lerp(focus,wanted,1-Mathf.Exp(-Time.deltaTime*10));viewCamera.transform.rotation=Quaternion.Slerp(viewCamera.transform.rotation,viewRotation,1-Mathf.Exp(-Time.deltaTime*12));viewCamera.transform.position=focus-viewCamera.transform.forward*2;viewCamera.orthographicSize=Mathf.Lerp(viewCamera.orthographicSize,size*zoom,1-Mathf.Exp(-Time.deltaTime*12));
        }
        float Slider(string label,float value,float min,float max,System.Action<float> setter){GUILayout.Label(label+": "+value.ToString("0.##",System.Globalization.CultureInfo.InvariantCulture));float v=GUILayout.HorizontalSlider(value,min,max);if(Mathf.Abs(v-value)>.00001f)setter(v);return v;}
        bool Toggle(string label,bool value,System.Action<bool> setter){bool v=GUILayout.Toggle(value,label);if(v!=value)setter(v);return v;}
        void OnGUI(){
            float width=Mathf.Min(panelWidth,Screen.width*.38f);GUI.Box(new Rect(0,0,width,Screen.height),"");GUILayout.BeginArea(new Rect(12,12,width-24,Screen.height-24));scroll=GUILayout.BeginScrollView(scroll);
            GUILayout.Label("IoT DIGITAL TWIN",GUI.skin.box);GUILayout.Label("Local device simulation");
            for(int i=0;i<Names.Length;i++){int id=i;if(GUILayout.Button((!gallery&&selected==i?"• ":"")+(i+1)+"  "+Names[i]))FocusDevice(id);}
            if(GUILayout.Button("View all devices"))ShowGallery();GUILayout.Space(8);automaticReadings=GUILayout.Toggle(automaticReadings,"Automatic sensor readings");GUILayout.Label("Turn this off for manual sensor values.");
            GUI.enabled=!smokeTest.Running;
            if(!gallery){GUILayout.Space(6);GUILayout.Label(Names[selected],GUI.skin.box);switch(selected){
                case 0:{var d=(RotaryDimmer)devices[0];Toggle("Power",d.Power,d.SetPower);Slider("Brightness %",d.Brightness*100,0,100,v=>d.SetBrightness(v/100));GUILayout.Label("Drag the knob horizontally. Click to toggle power. Scroll to fine-adjust.");break;}
                case 1:{var d=(TemperatureLCD)devices[1];Slider("Temperature °C",d.Temperature,-10,45,d.SetTemperature);Slider("Humidity %",d.Humidity,0,100,d.SetHumidity);if(GUILayout.Button("Pairing indicator"))d.SetPairing(true);GUILayout.Label("+ / − adjust temperature. Centre button switches to humidity.");break;}
                case 2:{var d=(TemperatureController)devices[2];Toggle("Power",d.Power,d.SetPower);Slider("Measured °C",d.Temperature,-10,45,d.SetTemperature);Slider("Target °C",d.TargetTemperature,5,35,d.SetTargetTemperature);if(GUILayout.Button("Cycle mode: "+d.mode))d.SetMode((ThermostatMode)(((int)d.mode+1)%3));GUILayout.Label("All five printed touch keys respond to clicks.");break;}
                case 3:{var d=(SecurityCameraDevice)devices[3];Toggle("Power",d.Power,d.SetPower);Toggle("Floodlight",d.Floodlight,d.SetFloodlight);Slider("Tilt degrees",d.Tilt,d.tiltMin,d.tiltMax,d.SetTilt);Slider("Yaw degrees",d.Yaw,-d.yawLimit,d.yawLimit,d.SetYaw);GUILayout.Label("Drag the head to aim. Click the head for power or the round floodlight to toggle it.");break;}
                case 4:{var d=(AqaraChainController)devices[4];connectAqara=GUILayout.Toggle(connectAqara,"Connect to demo blind");Slider("Open %",d.OpenPercent,0,100,d.SetOpenPercent);GUILayout.BeginHorizontal();if(GUILayout.Button("Raise"))d.Raise();if(GUILayout.Button("Lower"))d.Lower();if(GUILayout.Button("Stop"))d.Stop();GUILayout.EndHorizontal();Toggle("Open drive cover",d.coverOpen,d.SetCoverOpen);GUILayout.Label("Hold the physical buttons to run the drive. Release to stop.");break;}
                case 5:{var d=(RollerBlindDevice)devices[5];Slider("Open %",d.TargetOpenPercent,0,100,d.SetOpenPercent);GUILayout.Label("Current: "+d.OpenPercent.ToString("0.0")+"%");GUILayout.BeginHorizontal();if(GUILayout.Button("Open"))d.Open();if(GUILayout.Button("Close"))d.Close();if(GUILayout.Button("Stop"))d.Stop();GUILayout.EndHorizontal();GUILayout.Label("Drag along the bottom rail to choose a position.");break;}
                case 6:{var d=(SiemensBACnetDevice)devices[6];Slider("Display value",d.DisplayValue,0,99,d.SetDisplayValue);Toggle("Green status indicator",d.Status,d.SetStatus);GUILayout.Label("Click/scroll the face to change its number. Click the status point to toggle it.");break;}
                case 7:{var d=(NestSpeakerDevice)devices[7];Toggle("Active",d.Active,d.SetActive);Toggle("Microphone muted",d.Muted,d.SetMuted);Slider("Volume %",d.Volume*100,0,100,v=>d.SetVolume(v/100));GUILayout.Label("Click the rim switch to mute. Drag/scroll the speaker face for volume; click its face to toggle active state.");break;}
                case 8:{var d=(DALILightingPanel)devices[8];Toggle("Power",d.Power,d.SetPower);Slider("Brightness %",d.Brightness*100,0,100,v=>d.SetBrightness(v/100));Slider("Colour temperature K",d.ColorTemperature,2000,6500,d.SetColorTemperature);GUILayout.BeginHorizontal();if(GUILayout.Button("Task"))d.SelectScene(0);if(GUILayout.Button("Presentation 1"))d.SelectScene(1);if(GUILayout.Button("Presentation 2"))d.SelectScene(2);GUILayout.EndHorizontal();if(GUILayout.Button("Red test colour"))d.SetColor(Color.red);GUILayout.Label("Click On/Off, drag either slider, select colour in the field, or choose a screen preset.");break;}
            }}
            GUILayout.Space(8);zoom=GUILayout.HorizontalSlider(zoom,.65f,2);GUILayout.Label("Zoom • Hold right mouse to inspect from another angle.");if(GUILayout.Button(smokeTest.Running?"Self-test running…":"Run API / animation self-test"))smokeTest.Begin();GUI.enabled=true;GUILayout.Label(smokeTest.Summary);GUILayout.EndScrollView();GUILayout.EndArea();
        }
    }
}
