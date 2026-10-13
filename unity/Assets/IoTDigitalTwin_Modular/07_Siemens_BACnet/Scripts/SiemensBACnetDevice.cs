using UnityEngine;
namespace IoTDigitalTwin {
    public sealed class SiemensBACnetDevice:IoTDevice {
        public float displayValue=93;public bool status=true;public DynamicDotDisplay display;public Indicator statusIndicator=new Indicator();
        public float DisplayValue{get{return displayValue;}}public bool Status{get{return status;}}
        void Start(){Refresh();}
        public void SetDisplayValue(float value){displayValue=DeviceMath.ClampFinite(value,0,99);Refresh();Notify();}
        public void SetStatus(bool value){status=value;Refresh();Notify();}
        public override void Control(string action,Vector2 uv){if(action=="Status")SetStatus(!status);else SetDisplayValue((displayValue+1)%100);}
        public override void ControlScroll(string action,float amount){SetDisplayValue(displayValue+amount);}
        void Refresh(){display.SetValue(Mathf.RoundToInt(displayValue));statusIndicator.Apply(status?Color.green:new Color(.02f,.06f,.02f),status?1.3f:0);}
    }
}
