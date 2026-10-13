using UnityEngine;
namespace IoTDigitalTwin {
    public sealed class DALILightingPanel:IoTDevice {
        public bool power=true,useTemperature=true;[Range(0,1)]public float brightness=.5f;
        public float colorTemperature=4500;public Color selectedColor=Color.white;public int sceneIndex;
        public LightingOutput output=new LightingOutput();public DynamicReadout percentText,kelvinText;
        public Transform brightnessThumb,tempThumb,colorMarker,sceneMarker;
        public Vector3 brightnessBottom,brightnessTop,tempWarm,tempCool,colorBottomLeft,colorTopRight;
        public Vector3[] scenePositions;float shown;
        public bool Power{get{return power;}}public float Brightness{get{return brightness;}}public float ColorTemperature{get{return colorTemperature;}}
        public Color SelectedColor{get{return useTemperature?KelvinColor(colorTemperature):selectedColor;}}
        void Awake(){shown=brightness;Refresh();}
        public void SetPower(bool value){power=value;Refresh();Notify();}
        public void SetBrightness(float value){brightness=DeviceMath.ClampFinite(value,0,1);Refresh();Notify();}
        public void SetColor(Color value){selectedColor=new Color(DeviceMath.ClampFinite(value.r,0,1),DeviceMath.ClampFinite(value.g,0,1),DeviceMath.ClampFinite(value.b,0,1),1);useTemperature=false;Refresh();Notify();}
        public void SetColorTemperature(float kelvin){colorTemperature=DeviceMath.ClampFinite(kelvin,2000,6500);useTemperature=true;Refresh();Notify();}
        public void SelectScene(int index){sceneIndex=Mathf.Clamp(index,0,2);power=true;if(sceneIndex==0){brightness=1;colorTemperature=4500;useTemperature=true;}else if(sceneIndex==1){brightness=.3f;selectedColor=new Color(1,.78f,.5f);useTemperature=false;}else{brightness=.15f;selectedColor=new Color(.25f,.45f,1);useTemperature=false;}Refresh();Notify();}
        public static Color KelvinColor(float kelvin){float t=kelvin/100;float r=t<=66?255:329.698727f*Mathf.Pow(t-60,-.13320476f);float g=t<=66?99.4708026f*Mathf.Log(t)-161.119568f:288.12217f*Mathf.Pow(t-60,-.07551485f);float b=t>=66?255:(t<=19?0:138.517731f*Mathf.Log(t-10)-305.044793f);return new Color(Mathf.Clamp01(r/255),Mathf.Clamp01(g/255),Mathf.Clamp01(b/255),1);}
        public static Color Palette(float u,float v){float x=u*685,y=(1-v)*515;float s=.9f-.65f*Mathf.Exp(-((x-220)*(x-220)+(y-280)*(y-280))/35000);return Color.HSVToRGB(.14f+.59f*u,s,.4f+.6f*v);}
        void Refresh(){
            percentText.SetText(Mathf.RoundToInt(brightness*100)+"%");kelvinText.SetText(Mathf.RoundToInt(colorTemperature)+"K");percentText.SetColor(power?new Color(.12f,.32f,.4f):new Color(.45f,.45f,.45f));
            brightnessThumb.localPosition=Vector3.Lerp(brightnessBottom,brightnessTop,brightness);tempThumb.localPosition=Vector3.Lerp(tempWarm,tempCool,(colorTemperature-2000)/4500);
            float h,s,v;Color.RGBToHSV(SelectedColor,out h,out s,out v);float u=Mathf.Clamp01((h-.14f)/.59f);float py=Mathf.Clamp01((v-.4f)/.6f);colorMarker.localPosition=new Vector3(Mathf.Lerp(colorBottomLeft.x,colorTopRight.x,u),Mathf.Lerp(colorBottomLeft.y,colorTopRight.y,py),colorBottomLeft.z);
            sceneMarker.localPosition=scenePositions[Mathf.Clamp(sceneIndex,0,2)];
        }
        void Update(){shown=Ease(shown,power?brightness:0);output.Apply(power,shown,SelectedColor);}
        public override void Control(string action,Vector2 uv){switch(action){case "On":SetPower(true);break;case "Off":SetPower(false);break;case "Brightness":SetBrightness(uv.y);break;case "Colour_Temperature":SetColorTemperature(2000+(1-uv.y)*4500);break;case "Colour_Field":SetColor(Palette(uv.x,uv.y));break;case "Scene_Task":SelectScene(0);break;case "Scene_Presentation_1":SelectScene(1);break;case "Scene_Presentation_2":SelectScene(2);break;}}
        public override void ControlDrag(string action,Vector2 uv,Vector2 pixels){if(action=="Brightness"||action=="Colour_Temperature"||action=="Colour_Field")Control(action,uv);}
    }
}
