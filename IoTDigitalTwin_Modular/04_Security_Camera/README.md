# 04 — Security camera

## 1. Device and purpose

A camera with an articulated head, indicator and simulated floodlight. Estimated nominal size: **110 × 110 × 72 mm head; approximately 130 mm wall projection**. One Unity unit is one metre; source dimensions are estimates, not manufacturer measurements. Original model render budget: 6,872 triangles, before generated controls/readouts.

## 2. Interactions and animations

Left-drag the head for tilt and yaw. A short head click toggles power. Click the round floodlight surface to toggle it. The head smoothly rotates about Camera_Tilt_Pivot; the wall mount and cable remain fixed. A powered camera shows a red status light; floodlight emission and its spot light require both power and floodlight enabled.

## 3. Model hierarchy and interactive parts

The generated prefab root `04_Security_Camera` carries `SecurityCameraDevice`. Its imported model child retains the original root `Security_Camera` and the hierarchy below. `Input_*` trigger boxes are added to the corresponding movable part or touch target. Displays/markers are separate generated children of the prefab root; original geometry is retained.

| Part | Parent | Type |
|---|---|---|
| `Black_Front_Fascia` | `Camera_Tilt_Pivot` | MESH |
| `Camera_Housing` | `Camera_Tilt_Pivot` | MESH |
| `Camera_Tilt_Pivot` | `Security_Camera` | EMPTY |
| `Connector_Grip_Ribs` | `Security_Camera` | MESH |
| `Floodlight_Diffuser` | `Camera_Tilt_Pivot` | MESH |
| `Floodlight_Rim` | `Camera_Tilt_Pivot` | MESH |
| `Lens_Barrel_Rim` | `Camera_Tilt_Pivot` | MESH |
| `Lens_Inner_Aperture` | `Camera_Tilt_Pivot` | MESH |
| `Lens_Metal_Retainer` | `Camera_Tilt_Pivot` | MESH |
| `Microphone_Port` | `Camera_Tilt_Pivot` | MESH |
| `Mount_Arm` | `Security_Camera` | MESH |
| `Mount_Screw_-0.041` | `Security_Camera` | MESH |
| `Mount_Screw_0.001` | `Security_Camera` | MESH |
| `Optical_Lens` | `Camera_Tilt_Pivot` | MESH |
| `PIR_Sensor_Window` | `Camera_Tilt_Pivot` | MESH |
| `Security_Camera` | `(root)` | EMPTY |
| `Status_LED` | `Camera_Tilt_Pivot` | MESH |
| `Tilt_Joint` | `Security_Camera` | MESH |
| `Wall_Base` | `Security_Camera` | MESH |
| `Weatherproof_Connector` | `Security_Camera` | MESH |
| `Weatherproof_Power_Cable` | `Security_Camera` | MESH |

Generated display/feedback children: `Simulated_Floodlight`. Their meshes/materials are generated and saved with the owning device.

## 4. Unity installation and prefab setup

Target Unity 2022.3 LTS or Unity 6 (6000.0), Built-in or URP. These are target versions, not versions verified in this environment. No TextMeshPro, networking or hardware is required. The optional Input System is supported when its `ENABLE_INPUT_SYSTEM` define is active; otherwise input uses Unity's legacy Input API.

1. Copy this device directory and `Shared/` into the **same parent folder beneath your Unity project's Assets/**. Keep their `.meta` files. You can omit the other eight device directories and `Demo/`.
2. Wait for import and script compilation. Save your current scene before generation: generation opens a fresh working scene.
3. Choose **Tools > IoT Digital Twin > Individual Devices > 04_Security_Camera**. Alternatively choose **Generate Available Prefabs** to generate all imported devices.
4. The generator saves `Prefabs/04_Security_Camera.prefab`, device `.mat` assets under `Materials/Generated/`, and helper meshes under `Prefabs/GeneratedMeshes/`. The shared font material is generated once in Shared.
5. Drag that prefab into your room scene. Retain root scale `(1,1,1)` for the documented metre dimensions. Position/rotate the root instead of moving mechanical child pivots.
6. Add a Camera tagged MainCamera, then choose **Tools > IoT Digital Twin > Add Mouse Input to Current Scene**. `IoTMouseInput.interactionCamera` is assigned automatically. Public methods work without that input component.

`Models/*.fbx` is the Unity import source. Editable `.blend` and alternative `.glb` exports live in `Models/Source~/` so Unity ignores them and does not require Blender or a glTF plugin. Open them directly in Blender or another model tool. Original Blender image data is packed; GLB textures are embedded. `Previews/` contains original Blender renders, not Unity screenshots.

## 5. Public C# API

Namespace: `IoTDigitalTwin`. Call methods on the configured prefab component **after Awake** (for example in Start). Use public setters to refresh visuals/events; editing raw public fields during Play Mode may not refresh all readouts.

| Method/property | Parameters and behavior |
|---|---|
| `SetTilt(float value)` | Degrees; clamped to tiltMin/tiltMax (default −30/+35). |
| `SetYaw(float value)` | Degrees; clamped to ±yawLimit (default 30). |
| `SetPower(bool value)` | Toggle camera indicator and allow floodlight output. |
| `SetFloodlight(bool value)` | Set desired floodlight state; output also requires power. |
| `Tilt / Yaw / Power / Floodlight` | Read-only commanded state; displayed pose eases towards it. |

All devices inherit `SetSimulationMode(bool)`, `stateChanged` (Inspector UnityEvent), and `StateChanged` (C# event receiving IoTDevice). Simulation Mode identifies the device's local operating mode; switching it off does not create a hardware connection or stop rendering. The demo's automatic readings respect this flag. Finite float setters clamp to their documented ranges; NaN and infinity throw ArgumentOutOfRangeException.

## 6. Programmatic control

Obtain `SecurityCameraDevice` from an instantiated prefab using `GetComponent<SecurityCameraDevice>()` or assign it in the Inspector. Public methods share the same state/visual path as mouse input. Animated poses approach targets over time; target getters may differ from the currently displayed pose during motion. Use StateChanged for state notifications; it is not a network transport. Unsubscribe event handlers in OnDisable when needed.

## 7. Example C# usage

```csharp
using UnityEngine;
using IoTDigitalTwin;

public class SecurityCameraDeviceExample : MonoBehaviour
{
    [SerializeField] private SecurityCameraDevice device;

    private void Start()
    {
        device.SetTilt(20f);
        device.SetYaw(-10f);
        device.SetPower(true);
        device.SetFloodlight(true);
    }
}
```

Assign the generated prefab's controller to `device`. For external systems later, invoke these same setters on Unity's main thread; this pack includes no integration layer.

## 8. Inspector configuration

head binds Camera_Tilt_Pivot. tiltMin, tiltMax and yawLimit are degrees. status.renderer binds Status_LED; flood.renderer binds Floodlight_Diffuser; flood.light is the generated spot light. animationSpeed adjusts angular easing.

Keep `simulationMode` enabled for local testing. Shared input colliders are triggers and require no Rigidbody. If an existing room's collider obscures a device, adjust its placement or camera raycast access. Material property blocks update the existing renderers without creating new materials each frame.

## 9. Expected Play Mode behavior and test

Left-drag the head for tilt and yaw. A short head click toggles power. Click the round floodlight surface to toggle it. The head smoothly rotates about Camera_Tilt_Pivot; the wall mount and cable remain fixed. A powered camera shows a red status light; floodlight emission and its spot light require both power and floodlight enabled.

For the full-library demo, generate **Prefabs and Demo**, open `Demo/Scenes/IoT_Interactive_Demo.unity`, press Play, select this device and exercise its physical controls plus matching panel sliders. Disable **Automatic readings** before setting sensor/display values manually. The panel provides **Run API / animation self-test** and prints a JSON report to Application.persistentDataPath. Complete the manual mouse checklist in `Demo/README.md`; the automated self-test does not prove mouse raycasting or visual quality.

## 10. Limitations, dependencies and validation

No video stream, recording, movement detection or security backend. Yaw is a limited visual articulation.

Dependencies: this directory plus `Shared/`; optionally the blind directory for Aqara linking. `Demo/` requires all nine devices and is not needed for independent reuse. Animations are procedural C#; no Animator or AnimationClip dependency. See `Animations/README.md`.

Offline compilation passed both for the full library and for this device with only Shared. Controller state/motion calculations were tested against lightweight offline test doubles. Source models and exports were reopened/reimported in Blender. **Unity Editor import, shader compilation, prefab/scene generation and actual Play Mode have not been run here.** Check the root verification report and perform the listed Unity checks before project acceptance.
