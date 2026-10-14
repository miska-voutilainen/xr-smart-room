// XR select on an IoT device -> the same ControlDown/Drag/Up calls IoTMouseInput makes with the mouse (README Next Step 4).
// Sits next to the XRSimpleInteractable that OrangeRoomDevicePlacer adds; the hit zone nearest the ray picks the action.
// The rig's ray casters must hit trigger colliders (the hit zones are triggers): OrangeRoomSceneBuilder sets that.
using IoTDigitalTwin;
using UnityEngine;
using UnityEngine.XR.Interaction.Toolkit;
using UnityEngine.XR.Interaction.Toolkit.Interactables;
using UnityEngine.XR.Interaction.Toolkit.Interactors;

[RequireComponent(typeof(XRSimpleInteractable))]
public sealed class XRDeviceInput : MonoBehaviour
{
    XRSimpleInteractable interactable;
    RoomBridge bridge;
    DevicePointerTarget[] targets;
    Transform origin, frame;
    DevicePointerTarget target;
    Plane plane;
    Vector2 uv, lastScreen;
    Vector3 startForward;
    float turned;
    const float PixelsPerMetre = 4000f;   // ray end-point motion -> the library's mouse-pixel drag units
    // ponytail: tuning knob. Click = the ray turned less than this between press and release (Grip squeeze jolts it)
    const float ClickDegrees = 1.5f;

    Ray Aim => new Ray(origin.position, origin.forward);

    void Awake()
    {
        interactable = GetComponent<XRSimpleInteractable>();
        bridge = FindObjectOfType<RoomBridge>();
        targets = GetComponentsInChildren<DevicePointerTarget>(true);
        interactable.selectEntered.AddListener(OnSelect);
        interactable.selectExited.AddListener(OnRelease);
    }

    // XRI selected this device with a cone cast, so the exact ray can pass a few cm beside a 2-3 cm hit zone:
    // take this device's zone nearest the ray instead of a fresh physics hit.
    DevicePointerTarget Nearest(Ray ray, out Vector3 point)
    {
        DevicePointerTarget best = null;
        float bestAngle = float.MaxValue;
        point = default;
        foreach (var t in targets)
        {
            var col = t.GetComponent<Collider>();
            if (!col || !col.enabled || !t.gameObject.activeInHierarchy) continue;
            var p = col.ClosestPoint(ray.GetPoint(Vector3.Dot(col.bounds.center - ray.origin, ray.direction)));
            float a = Vector3.Angle(ray.direction, p - ray.origin);
            if (a < bestAngle) { bestAngle = a; best = t; point = p; }
        }
        return best;
    }

    // drag deltas in the device root's frame (it never moves), not the zone's: the knob, camera head and blind rail
    // zones ride on the part they move
    Vector2 Screen(Vector3 p) => (Vector2)frame.InverseTransformPoint(p) * PixelsPerMetre * new Vector2(-1, 1);

    void OnSelect(SelectEnterEventArgs args)
    {
        var i = args.interactorObject;
        origin = i is NearFarInteractor nf && nf.farInteractionCaster != null ? nf.farInteractionCaster.effectiveCastOrigin   // the origin XRI casts from
               : i is IXRRayProvider ray ? ray.GetOrCreateRayOrigin() : i.transform;
        target = Nearest(Aim, out var point);
        if (!target) return;
        if (bridge && bridge.Mirrored(target.device)) { target = null; return; }   // read-only while the real device drives it
        frame = target.device.transform;
        plane = new Plane(frame.forward, point);
        uv = target.Coordinates(Aim);
        lastScreen = Screen(point);
        startForward = origin.forward;
        turned = 0;
        target.device.ControlDown(target.action, uv);
        if (bridge) bridge.UserControl(target.device, target.action, true);
    }

    void Update()
    {
        if (!target) return;
        turned = Mathf.Max(turned, Vector3.Angle(startForward, origin.forward));
        if (!plane.Raycast(Aim, out var d)) return;
        var p = Screen(Aim.GetPoint(d));
        uv = target.Coordinates(Aim);
        target.device.ControlDrag(target.action, uv, p - lastScreen);
        lastScreen = p;
    }

    void OnRelease(SelectExitEventArgs args)
    {
        if (!target) return;
        bool click = Mathf.Max(turned, Vector3.Angle(startForward, origin.forward)) < ClickDegrees;
        target.device.ControlUp(target.action, click, uv);
        if (bridge) bridge.UserControl(target.device, target.action, false, click);
        target = null;
    }
}
