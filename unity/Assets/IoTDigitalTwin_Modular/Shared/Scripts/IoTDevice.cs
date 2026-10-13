using System;
using UnityEngine;
using UnityEngine.Events;
namespace IoTDigitalTwin {
    public abstract class IoTDevice : MonoBehaviour {
        public bool simulationMode=true;
        public float animationSpeed=10f;
        public UnityEvent stateChanged=new UnityEvent();
        public event Action<IoTDevice> StateChanged;
        protected void Notify(){stateChanged.Invoke();if(StateChanged!=null)StateChanged(this);}
        public void SetSimulationMode(bool enabled){simulationMode=enabled;Notify();}
        public virtual void ControlDown(string action,Vector2 uv){Control(action,uv);}
        public virtual void ControlDrag(string action,Vector2 uv,Vector2 pixels){}
        public virtual void ControlUp(string action,bool click,Vector2 uv){}
        public virtual void ControlScroll(string action,float amount){}
        public virtual void Control(string action,Vector2 uv){}
        protected float Ease(float current,float target){return Mathf.Lerp(current,target,1-Mathf.Exp(-Mathf.Max(.01f,animationSpeed)*Time.deltaTime));}
        public static Vector3 InwardLocal(Transform part,Transform frame,float metres){return part.parent.InverseTransformVector(-frame.forward*metres);}
        public static Vector3 LocalAxis(Transform part,Vector3 worldAxis){return part.InverseTransformDirection(worldAxis).normalized;}
    }
    [Serializable] public class PressPart {
        public Transform part; public Vector3 rest,offset; public float amount;
        public void Capture(Transform frame,float travel){rest=part.localPosition;offset=IoTDevice.InwardLocal(part,frame,travel);}
        public void Apply(float dt){amount=Mathf.MoveTowards(amount,0,dt*5);if(part)part.localPosition=rest+offset*amount;}
        public void Press(){amount=1;}
    }
    [Serializable] public class Indicator {
        public Renderer renderer; public Light light;
        [NonSerialized] MaterialPropertyBlock block;
        public void Apply(Color color,float intensity){
            if(renderer){if(block==null)block=new MaterialPropertyBlock();block.SetColor("_Color",color);block.SetColor("_BaseColor",color);block.SetColor("_EmissionColor",color*intensity);renderer.SetPropertyBlock(block);}
            if(light){light.color=color;light.intensity=intensity;light.enabled=intensity>.001f;}
        }
    }
    [Serializable] public class LightingOutput {
        public Light light; public Renderer lamp;
        [NonSerialized] MaterialPropertyBlock block;
        public void Apply(bool powered,float brightness,Color color){
            float value=powered?Mathf.Clamp01(brightness):0;
            if(light){light.color=color;light.intensity=value*2;light.enabled=value>.001f;}
            if(lamp){if(block==null)block=new MaterialPropertyBlock();Color c=Color.Lerp(new Color(.06f,.07f,.08f),color,value);block.SetColor("_Color",c);block.SetColor("_BaseColor",c);block.SetColor("_EmissionColor",color*value*2);lamp.SetPropertyBlock(block);}
        }
    }
}
