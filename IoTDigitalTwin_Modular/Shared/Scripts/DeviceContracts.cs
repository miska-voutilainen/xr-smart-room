using UnityEngine;
namespace IoTDigitalTwin {
    public interface IBlindControl {
        float OpenPercent {get;} float TargetOpenPercent {get;}
        void SetOpenPercent(float value); void Stop();
    }
    public interface IPointerInputGate {
        bool SuspendPointer {get;}
        bool PointerOverPanel(Vector2 position);
    }
}
