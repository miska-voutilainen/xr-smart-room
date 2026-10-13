using UnityEngine;
#if ENABLE_INPUT_SYSTEM
using UnityEngine.InputSystem;
#endif
namespace IoTDigitalTwin {
    public sealed class IoTMouseInput:MonoBehaviour {
        public Camera interactionCamera;public MonoBehaviour inputGate;
        IPointerInputGate Gate {get{return inputGate as IPointerInputGate;}}
        DevicePointerTarget captured;Vector2 start,last;Vector2 finalUv;float moved;
        public static Vector2 Position(){
#if ENABLE_INPUT_SYSTEM
            return Mouse.current==null?Vector2.zero:Mouse.current.position.ReadValue();
#else
            return Input.mousePosition;
#endif
        }
        public static bool Down(){
#if ENABLE_INPUT_SYSTEM
            return Mouse.current!=null&&Mouse.current.leftButton.wasPressedThisFrame;
#else
            return Input.GetMouseButtonDown(0);
#endif
        }
        public static bool Held(){
#if ENABLE_INPUT_SYSTEM
            return Mouse.current!=null&&Mouse.current.leftButton.isPressed;
#else
            return Input.GetMouseButton(0);
#endif
        }
        public static bool Up(){
#if ENABLE_INPUT_SYSTEM
            return Mouse.current!=null&&Mouse.current.leftButton.wasReleasedThisFrame;
#else
            return Input.GetMouseButtonUp(0);
#endif
        }
        public static float Wheel(){
#if ENABLE_INPUT_SYSTEM
            return Mouse.current==null?0:Mouse.current.scroll.ReadValue().y/120f;
#else
            return Input.mouseScrollDelta.y;
#endif
        }
        public static bool OrbitHeld(){
#if ENABLE_INPUT_SYSTEM
            return Mouse.current!=null&&Mouse.current.rightButton.isPressed;
#else
            return Input.GetMouseButton(1);
#endif
        }
        void Update(){
            if(!interactionCamera || (Gate!=null&&Gate.SuspendPointer))return;Vector2 p=Position();Ray ray=interactionCamera.ScreenPointToRay(p);RaycastHit hit;
            bool blocked=Gate!=null&&Gate.PointerOverPanel(p);
            if(Down()&&!blocked&&Physics.Raycast(ray,out hit,10f,~0,QueryTriggerInteraction.Collide)){
                captured=hit.collider.GetComponent<DevicePointerTarget>();if(captured){start=last=p;moved=0;finalUv=captured.Coordinates(ray);captured.device.ControlDown(captured.action,finalUv);}
            }
            if(captured&&Held()){
                Vector2 delta=p-last;last=p;moved=Mathf.Max(moved,(p-start).magnitude);finalUv=captured.Coordinates(ray);captured.device.ControlDrag(captured.action,finalUv,delta);
            }
            if(captured&&Up()){captured.device.ControlUp(captured.action,moved<4f,finalUv);captured=null;}
            float wheel=Wheel();if(!blocked&&wheel!=0&&Physics.Raycast(ray,out hit,10f,~0,QueryTriggerInteraction.Collide)){
                var t=hit.collider.GetComponent<DevicePointerTarget>();if(t)t.device.ControlScroll(t.action,wheel);
            }
        }
        void OnDisable(){if(captured){captured.device.ControlUp(captured.action,false,finalUv);captured=null;}}
    }
}
