# 01 — Zigbee rotary dimmer

## 1. Device and purpose

Wall-mounted rotary light control. Brightness and power are local simulation states. Estimated nominal size: **86 × 86 × 25.9 mm**. One Unity unit is one metre; source dimensions are estimates, not manufacturer measurements. Original model render budget: 5,764 triangles, before generated controls/readouts.

## 2. Interactions and animations

Left-drag the knob horizontally to adjust brightness. Scroll for fine adjustment. A short click toggles power and pushes the knob inward by 0.7 mm. Rotation spans −135° to +135° around the existing shaft pivot. The optional linked lamp fades with brightness.

## 3. Model hierarchy and interactive parts

The generated prefab root `01_Zigbee_Rotary_Dimmer` carries `RotaryDimmer`. Its imported model child retains the original root `Zigbee_Rotary_Dimmer` and the hierarchy below. `Input_*` trigger boxes are added to the corresponding movable part or touch target. Displays/markers are separate generated children of the prefab root; original geometry is retained.

| Part | Parent | Type |
|---|---|---|
| `01_Rear_Mounting_Cover` | `Zigbee_Rotary_Dimmer` | MESH |
| `02_Beveled_Outer_Frame` | `Zigbee_Rotary_Dimmer` | MESH |
| `03_Inset_Square_Plate` | `Zigbee_Rotary_Dimmer` | MESH |
| `04_Recessed_Knob_Collar` | `Zigbee_Rotary_Dimmer` | MESH |
| `05_Rotary_Knob` | `Zigbee_Rotary_Dimmer` | MESH |
| `06_Removable_Installation_Label` | `Zigbee_Rotary_Dimmer` | MESH |
| `Zigbee_Rotary_Dimmer` | `(root)` | EMPTY |

## 4. Unity installation and prefab setup

Target Unity 2022.3 LTS or Unity 6 (6000.0), Built-in or URP. These are target versions, not versions verified in this environment. No TextMeshPro, networking or hardware is required. The optional Input System is supported when its `ENABLE_INPUT_SYSTEM` define is active; otherwise input uses Unity's legacy Input API.

1. Copy this device directory and `Shared/` into the **same parent folder beneath your Unity project's Assets/**. Keep their `.meta` files. You can omit the other eight device directories and `Demo/`.
2. Wait for import and script compilation. Save your current scene before generation: generation opens a fresh working scene.
3. Choose **Tools > IoT Digital Twin > Individual Devices > 01_Zigbee_Dimmer**. Alternatively choose **Generate Available Prefabs** to generate all imported devices.
4. The generator saves `Prefabs/01_Zigbee_Rotary_Dimmer.prefab`, device `.mat` assets under `Materials/Generated/`, and helper meshes under `Prefabs/GeneratedMeshes/`. The shared font material is generated once in Shared.
5. Drag that prefab into your room scene. Retain root scale `(1,1,1)` for the documented metre dimensions. Position/rotate the root instead of moving mechanical child pivots.
6. Add a Camera tagged MainCamera, then choose **Tools > IoT Digital Twin > Add Mouse Input to Current Scene**. `IoTMouseInput.interactionCamera` is assigned automatically. Public methods work without that input component.

`Models/*.fbx` is the Unity import source. Editable `.blend` and alternative `.glb` exports live in `Models/Source~/` so Unity ignores them and does not require Blender or a glTF plugin. Open them directly in Blender or another model tool. Original Blender image data is packed; GLB textures are embedded. `Previews/` contains original Blender renders, not Unity screenshots.

## 5. Public C# API

Namespace: `IoTDigitalTwin`. Call methods on the configured prefab component **after Awake** (for example in Start). Use public setters to refresh visuals/events; editing raw public fields during Play Mode may not refresh all readouts.

| Method/property | Parameters and behavior |
|---|---|
| `SetBrightness(float value)` | Normalized 0–1; finite values clamp to the range. Changes knob target and optional lamp. |
| `SetPower(bool on)` | Enable/disable optional lamp output; preserves brightness. |
| `Brightness / Power` | Read-only properties of current commanded state. |

All devices inherit `SetSimulationMode(bool)`, `stateChanged` (Inspector UnityEvent), and `StateChanged` (C# event receiving IoTDevice). Simulation Mode identifies the device's local operating mode; switching it off does not create a hardware connection or stop rendering. The demo's automatic readings respect this flag. Finite float setters clamp to their documented ranges; NaN and infinity throw ArgumentOutOfRangeException.

## 6. Programmatic control

Obtain `RotaryDimmer` from an instantiated prefab using `GetComponent<RotaryDimmer>()` or assign it in the Inspector. Public methods share the same state/visual path as mouse input. Animated poses approach targets over time; target getters may differ from the currently displayed pose during motion. Use StateChanged for state notifications; it is not a network transport. Unsubscribe event handlers in OnDisable when needed.

## 7. Example C# usage

```csharp
using UnityEngine;
using IoTDigitalTwin;

public class RotaryDimmerExample : MonoBehaviour
{
    [SerializeField] private RotaryDimmer device;

    private void Start()
    {
        device.SetPower(true);
        device.SetBrightness(0.75f); // 75%, not 75
    }
}
```

Assign the generated prefab's controller to `device`. For external systems later, invoke these same setters on Unity's main thread; this pack includes no integration layer.

## 8. Inspector configuration

knob binds 05_Rotary_Knob; press is captured at Awake. minimumAngle/maximumAngle are degrees; dragSensitivity is normalized brightness per horizontal pixel. output.light and output.lamp are optional scene references; the demo binds a test lamp. animationSpeed controls exponential smoothing.

Keep `simulationMode` enabled for local testing. Shared input colliders are triggers and require no Rigidbody. If an existing room's collider obscures a device, adjust its placement or camera raycast access. Material property blocks update the existing renderers without creating new materials each frame.

## 9. Expected Play Mode behavior and test

Left-drag the knob horizontally to adjust brightness. Scroll for fine adjustment. A short click toggles power and pushes the knob inward by 0.7 mm. Rotation spans −135° to +135° around the existing shaft pivot. The optional linked lamp fades with brightness.

For the full-library demo, generate **Prefabs and Demo**, open `Demo/Scenes/IoT_Interactive_Demo.unity`, press Play, select this device and exercise its physical controls plus matching panel sliders. Disable **Automatic readings** before setting sensor/display values manually. The panel provides **Run API / animation self-test** and prints a JSON report to Application.persistentDataPath. Complete the manual mouse checklist in `Demo/README.md`; the automated self-test does not prove mouse raycasting or visual quality.

## 10. Limitations, dependencies and validation

Knob drag is a horizontal gesture rather than a polar-angle gesture. No electrical load or Zigbee protocol simulation.

Dependencies: this directory plus `Shared/`; optionally the blind directory for Aqara linking. `Demo/` requires all nine devices and is not needed for independent reuse. Animations are procedural C#; no Animator or AnimationClip dependency. See `Animations/README.md`.

Offline compilation passed both for the full library and for this device with only Shared. Controller state/motion calculations were tested against lightweight offline test doubles. Source models and exports were reopened/reimported in Blender. **Unity Editor import, shader compilation, prefab/scene generation and actual Play Mode have not been run here.** Check the root verification report and perform the listed Unity checks before project acceptance.
