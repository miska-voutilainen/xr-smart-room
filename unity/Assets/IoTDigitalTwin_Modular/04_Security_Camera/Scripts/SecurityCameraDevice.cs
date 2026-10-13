using UnityEngine;
namespace IoTDigitalTwin {
    public sealed class SecurityCameraDevice:IoTDevice {
        public Transform head;public Indicator status=new Indicator(),flood=new Indicator();
        public bool power=true,floodlight;public float tilt,yaw;public float tiltMin=-30,tiltMax=35,yawLimit=30;
        Quaternion rest;Vector3 tiltAxis,yawAxis;float shownTilt,shownYaw;
        public float Tilt{get{return tilt;}}public float Yaw{get{return yaw;}}public bool Power{get{return power;}}public bool Floodlight{get{return floodlight;}}
        void Awake(){rest=head.localRotation;tiltAxis=LocalAxis(head,transform.right);yawAxis=LocalAxis(head,transform.up);}
        public void SetTilt(float value){tilt=DeviceMath.ClampFinite(value,tiltMin,tiltMax);Notify();}
        public void SetYaw(float value){yaw=DeviceMath.ClampFinite(value,-yawLimit,yawLimit);Notify();}
        public void SetPower(bool value){power=value;Notify();}
        public void SetFloodlight(bool value){floodlight=value;Notify();}
        void Update(){shownTilt=Ease(shownTilt,tilt);shownYaw=Ease(shownYaw,yaw);head.localRotation=rest*Quaternion.AngleAxis(shownYaw,yawAxis)*Quaternion.AngleAxis(shownTilt,tiltAxis);status.Apply(power?Color.red:new Color(.08f,.01f,.01f),power?1.7f:0);flood.Apply(power&&floodlight?Color.white:new Color(.5f,.5f,.5f),power&&floodlight?2:0);}
        public override void ControlDown(string action,Vector2 uv){if(action=="Flood")SetFloodlight(!floodlight);}
        public override void ControlDrag(string action,Vector2 uv,Vector2 pixels){if(action=="Head"){SetTilt(tilt-pixels.y*.2f);SetYaw(yaw+pixels.x*.2f);}}
        public override void ControlUp(string action,bool click,Vector2 uv){if(action=="Head"&&click)SetPower(!power);}
    }
}
