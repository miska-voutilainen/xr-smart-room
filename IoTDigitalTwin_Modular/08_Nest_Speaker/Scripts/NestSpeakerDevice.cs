using UnityEngine;
namespace IoTDigitalTwin {
    public sealed class NestSpeakerDevice:IoTDevice {
        public Transform muteSwitch;public Indicator[] lights;
        public bool muted,active=true;[Range(0,1)]public float volume=.5f;
        Vector3 rest,travel;float shown,volumeUntil;
        static readonly Color[] GoogleColors={new Color(.18f,.42f,1),new Color(1,.14f,.07f),new Color(1,.66f,.04f),new Color(.05f,.68f,.18f)};
        public float Volume{get{return volume;}}public bool Muted{get{return muted;}}public bool Active{get{return active;}}
        void Awake(){rest=muteSwitch.localPosition;travel=muteSwitch.parent.InverseTransformVector(transform.up*.003f);}
        public void SetVolume(float value){volume=DeviceMath.ClampFinite(value,0,1);volumeUntil=Time.time+1;Notify();}
        public void SetMuted(bool value){muted=value;Notify();}
        public void SetActive(bool value){active=value;Notify();}
        void Update(){shown=Ease(shown,muted?1:0);muteSwitch.localPosition=rest+travel*shown;for(int i=0;i<lights.Length;i++){
            Color color=muted?new Color(1,.1f,.03f):GoogleColors[i%4];float amount=active?(muted?1:(Time.time<volumeUntil?(i<Mathf.CeilToInt(volume*4)?1:0):.25f+.75f*(.5f+.5f*Mathf.Sin(Time.time*2.8f-i*.8f)))):0;
            lights[i].Apply(amount>.01f?color:new Color(.2f,.21f,.2f),amount*1.5f);
        }}
        public override void ControlDown(string action,Vector2 uv){if(action=="Mute")SetMuted(!muted);}
        public override void ControlDrag(string action,Vector2 uv,Vector2 pixels){if(action=="Volume")SetVolume(volume+pixels.x*.003f);}
        public override void ControlUp(string action,bool click,Vector2 uv){if(action=="Volume"&&click)SetActive(!active);}
        public override void ControlScroll(string action,float amount){SetVolume(volume+amount*.05f);}
    }
}
