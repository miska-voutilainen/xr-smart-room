using UnityEngine;
namespace IoTDigitalTwin {
    public sealed class RotaryDimmer:IoTDevice {
        [Range(0,1)]public float brightness=.5f;public bool power=true;
        public Transform knob;public PressPart press=new PressPart();public LightingOutput output=new LightingOutput();
        public float minimumAngle=-135,maximumAngle=135,dragSensitivity=.004f;
        Quaternion restRotation;Vector3 axis;float shown;
        public float Brightness {get{return brightness;}}public bool Power {get{return power;}}
        void Awake(){restRotation=knob.localRotation;axis=LocalAxis(knob,transform.forward);press.part=knob;press.Capture(transform,.0007f);shown=brightness;Refresh();}
        public void SetBrightness(float value){value=DeviceMath.ClampFinite(value,0,1);if(value==brightness)return;brightness=value;Notify();}
        public void SetPower(bool on){if(power==on)return;power=on;Notify();}
        void Update(){shown=Ease(shown,brightness);press.Apply(Time.deltaTime);Refresh();}
        void Refresh(){knob.localRotation=restRotation*Quaternion.AngleAxis(Mathf.Lerp(minimumAngle,maximumAngle,shown),axis);output.Apply(power,shown,Color.white);}
        public override void ControlDown(string action,Vector2 uv){press.Press();}
        public override void ControlDrag(string action,Vector2 uv,Vector2 pixels){SetBrightness(brightness+pixels.x*dragSensitivity);}
        public override void ControlUp(string action,bool click,Vector2 uv){if(click)SetPower(!power);}
        public override void ControlScroll(string action,float amount){SetBrightness(brightness+amount*.04f);}
    }
}
