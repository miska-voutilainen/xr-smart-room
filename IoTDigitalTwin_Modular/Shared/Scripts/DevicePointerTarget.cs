using UnityEngine;
namespace IoTDigitalTwin {
    public sealed class DevicePointerTarget:MonoBehaviour {
        public IoTDevice device;
        public string action;
        public float width=.02f,height=.02f;
        public Vector2 Coordinates(Ray ray){
            Plane plane=new Plane(transform.forward,transform.position);float distance;
            if(!plane.Raycast(ray,out distance))return new Vector2(.5f,.5f);
            Vector3 p=transform.InverseTransformPoint(ray.GetPoint(distance));
            return new Vector2(Mathf.Clamp01(.5f-p.x/width),Mathf.Clamp01(.5f+p.y/height));
        }
    }
}
