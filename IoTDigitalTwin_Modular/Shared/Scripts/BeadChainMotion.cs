using System;
using UnityEngine;
namespace IoTDigitalTwin {
    [Serializable] public class ChainIsland {public int[] indices;public Vector3 centre;public double arcDistance;}
    public sealed class BeadChainMotion:MonoBehaviour {
        public Transform frame; public MeshFilter filter; public ChainIsland[] islands;
        public float top,bottom,radius,depth,xOffset; public bool sidePlane;
        Mesh owned;Vector3[] original,buffer;double phase;
        void Awake(){owned=Instantiate(filter.sharedMesh);owned.name=filter.sharedMesh.name+"_AnimatedInstance";owned.MarkDynamic();filter.sharedMesh=owned;Bounds bounds=owned.bounds;bounds.Expand(.01f);owned.bounds=bounds;original=owned.vertices;buffer=(Vector3[])original.Clone();}
        public void Advance(float metres){
            if(Mathf.Abs(metres)<.0000001f||owned==null)return;
            phase=DeviceMath.Wrap(phase+metres,DeviceMath.CapsuleLength(top,bottom,radius));
            foreach(var bead in islands){
                double horizontal,vertical;DeviceMath.CapsulePoint(bead.arcDistance+phase,top,bottom,radius,out horizontal,out vertical);
                // Canonical Unity X is minus photographic/Blender X.
                Vector3 point=sidePlane?new Vector3(-xOffset,(float)vertical,depth-(float)horizontal):new Vector3(-(float)horizontal,(float)vertical,depth);
                Vector3 centre=filter.transform.InverseTransformPoint(frame.TransformPoint(point));Vector3 delta=centre-bead.centre;
                foreach(int i in bead.indices)buffer[i]=original[i]+delta;
            }
            owned.vertices=buffer; // Translation preserves each bead's authored vertex normals.
        }
        void OnDestroy(){if(owned)Destroy(owned);}
    }
}
