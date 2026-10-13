using UnityEngine;
namespace IoTDigitalTwin {
    public sealed class AqaraChainController:IoTDevice {
        public Transform sprocket,cover;public BeadChainMotion chain;public MonoBehaviour linkedBlindComponent;
        public IBlindControl LinkedBlind {get{return linkedBlindComponent as IBlindControl;}}
        public PressPart raiseButton=new PressPart(),lowerButton=new PressPart();public Indicator status=new Indicator();
        public float currentOpenPercent,targetOpenPercent,percentPerSecond=25;public bool coverOpen;
        Quaternion restRotation;Vector3 axis,coverRest,coverTravel;float wheelAngle,coverShown;
        public float OpenPercent{get{return LinkedBlind!=null?LinkedBlind.OpenPercent:currentOpenPercent;}}
        void Awake(){restRotation=sprocket.localRotation;axis=LocalAxis(sprocket,transform.forward);coverRest=cover.localPosition;coverTravel=cover.parent.InverseTransformVector(transform.up*.018f);raiseButton.Capture(transform,.0004f);lowerButton.Capture(transform,.0004f);currentOpenPercent=LinkedBlind!=null?LinkedBlind.OpenPercent:currentOpenPercent;}
        public void SetOpenPercent(float value){targetOpenPercent=DeviceMath.ClampFinite(value,0,100);if(LinkedBlind!=null)LinkedBlind.SetOpenPercent(targetOpenPercent);Notify();}
        public void Raise(){raiseButton.Press();SetOpenPercent(100);}public void Lower(){lowerButton.Press();SetOpenPercent(0);}public void Stop(){if(LinkedBlind!=null)LinkedBlind.Stop();targetOpenPercent=OpenPercent;Notify();}
        public void SetCoverOpen(bool value){coverOpen=value;Notify();}
        public void ConnectBlind(IBlindControl blind){if(LinkedBlind!=null&&LinkedBlind!=blind)LinkedBlind.Stop();linkedBlindComponent=blind as MonoBehaviour;if(blind!=null){currentOpenPercent=blind.OpenPercent;targetOpenPercent=blind.TargetOpenPercent;}Notify();}
        void Update(){float before=currentOpenPercent;currentOpenPercent=LinkedBlind!=null?LinkedBlind.OpenPercent:DeviceMath.Move(currentOpenPercent,targetOpenPercent,Mathf.Max(.01f,percentPerSecond)*Time.deltaTime);float distance=(currentOpenPercent-before)*.0042525f;wheelAngle+=distance/.015f*Mathf.Rad2Deg;sprocket.localRotation=restRotation*Quaternion.AngleAxis(wheelAngle,axis);if(chain)chain.Advance(distance);raiseButton.Apply(Time.deltaTime);lowerButton.Apply(Time.deltaTime);coverShown=Ease(coverShown,coverOpen?1:0);cover.localPosition=coverRest+coverTravel*coverShown;status.Apply(Mathf.Abs(distance)>.000001f?Color.green:new Color(.04f,.08f,.04f),Mathf.Abs(distance)>.000001f?1.5f:0);}
        public override void ControlDown(string action,Vector2 uv){if(action=="Raise")Raise();else if(action=="Lower")Lower();else if(action=="Cover")SetCoverOpen(!coverOpen);}
        public override void ControlUp(string action,bool click,Vector2 uv){if(action=="Raise"||action=="Lower")Stop();}
    }
}
