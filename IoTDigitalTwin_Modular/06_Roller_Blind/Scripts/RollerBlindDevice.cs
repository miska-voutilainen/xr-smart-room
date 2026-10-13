using UnityEngine;
namespace IoTDigitalTwin {
    public sealed class RollerBlindDevice:IoTDevice,IBlindControl {
        public SkinnedMeshRenderer cloth;public int blendShapeIndex;public float fullyRaisedWeight=100;
        public Transform bottomRail,roller,clutch;public BeadChainMotion chain;
        [Range(0,100)]public float currentOpenPercent,targetOpenPercent;
        public float percentPerSecond=25,rollerRadius=.0255f;
        Quaternion rollerRest,clutchRest;Vector3 railRest,rollerAxis,clutchAxis,railTravel;
        public float OpenPercent{get{return currentOpenPercent;}}public float TargetOpenPercent{get{return targetOpenPercent;}}
        void Awake(){railRest=bottomRail.localPosition;rollerRest=roller.localRotation;clutchRest=clutch.localRotation;rollerAxis=LocalAxis(roller,transform.right);clutchAxis=LocalAxis(clutch,transform.right);railTravel=bottomRail.parent.InverseTransformVector(transform.up*.42525f);ApplyPose();}
        public void SetOpenPercent(float value){targetOpenPercent=DeviceMath.ClampFinite(value,0,100);Notify();}
        public void Open(){SetOpenPercent(100);}public void Close(){SetOpenPercent(0);}public void Stop(){targetOpenPercent=currentOpenPercent;Notify();}
        void Update(){float before=currentOpenPercent;currentOpenPercent=DeviceMath.Move(currentOpenPercent,targetOpenPercent,Mathf.Max(.01f,percentPerSecond)*Time.deltaTime);if(currentOpenPercent!=before){ApplyPose();if(chain)chain.Advance((currentOpenPercent-before)*.0042525f);if(currentOpenPercent==targetOpenPercent)Notify();}}
        void ApplyPose(){float t=currentOpenPercent/100;cloth.SetBlendShapeWeight(blendShapeIndex,fullyRaisedWeight*t);bottomRail.localPosition=railRest+railTravel*t;float angle=-.42525f*t/rollerRadius*Mathf.Rad2Deg;roller.localRotation=rollerRest*Quaternion.AngleAxis(angle,rollerAxis);clutch.localRotation=clutchRest*Quaternion.AngleAxis(angle,clutchAxis);}
        public override void ControlDrag(string action,Vector2 uv,Vector2 pixels){if(action=="Position")Control(action,uv);}
        public override void Control(string action,Vector2 uv){if(action=="Open")Open();else if(action=="Close")Close();else if(action=="Stop")Stop();else SetOpenPercent(uv.x*100);}
    }
}
