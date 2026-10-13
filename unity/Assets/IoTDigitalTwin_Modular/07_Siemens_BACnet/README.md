# 07 — Siemens BACnet device

## 1. Device and purpose

A room automation faceplate with a changing two-digit LED-dot display and green status indicator. Estimated nominal size: **88 × 88 × 25 mm**. One Unity unit is one metre; source dimensions are estimates, not manufacturer measurements. Original model render budget: 3,938 triangles, before generated controls/readouts.

## 2. Interactions and animations

Click the grey display face to increment the number; scroll to adjust it. Click the green status point to toggle it. The original static LED_Dot_Display renderer is retained but disabled. A generated 36-dot mesh displays two 3×5 digits, five level dots and one cursor; per-vertex colours change at runtime.

## 3. Model hierarchy and interactive parts

The generated prefab root `07_Siemens_BACnet_Device` carries `SiemensBACnetDevice`. Its imported model child retains the original root `Siemens_BACnet_Device` and the hierarchy below. `Input_*` trigger boxes are added to the corresponding movable part or touch target. Displays/markers are separate generated children of the prefab root; original geometry is retained.

| Part | Parent | Type |
|---|---|---|
| `Ambient_Sensor` | `Siemens_BACnet_Device` | MESH |
| `Decal_07_SIEMENS` | `Siemens_BACnet_Device` | MESH |
| `Dot_Display_Assembly` | `Siemens_BACnet_Device` | EMPTY |
| `Front_Shadow_Gasket` | `Siemens_BACnet_Device` | MESH |
| `Grey_Front_Panel` | `Siemens_BACnet_Device` | MESH |
| `LED_Dot_Display` | `Dot_Display_Assembly` | MESH |
| `Rear_Wall_Plate` | `Siemens_BACnet_Device` | MESH |
| `Siemens_BACnet_Device` | `(root)` | EMPTY |
| `Status_LED_Green` | `Siemens_BACnet_Device` | MESH |
| `White_Rounded_Frame` | `Siemens_BACnet_Device` | MESH |

Generated display/feedback children: `Live_Dot_Display`. Their meshes/materials are generated and saved with the owning device.

## 4. Unity installation and prefab setup

Target Unity 2022.3 LTS or Unity 6 (6000.0), Built-in or URP. These are target versions, not versions verified in this environment. No TextMeshPro, networking or hardware is required. The optional Input System is supported when its `ENABLE_INPUT_SYSTEM` define is active; otherwise input uses Unity's legacy Input API.

1. Copy this device directory and `Shared/` into the **same parent folder beneath your Unity project's Assets/**. Keep their `.meta` files. You can omit the other eight device directories and `Demo/`.
2. Wait for import and script compilation. Save your current scene before generation: generation opens a fresh working scene.
3. Choose **Tools > IoT Digital Twin > Individual Devices > 07_Siemens_BACnet**. Alternatively choose **Generate Available Prefabs** to generate all imported devices.
4. The generator saves `Prefabs/07_Siemens_BACnet_Device.prefab`, device `.mat` assets under `Materials/Generated/`, and helper meshes under `Prefabs/GeneratedMeshes/`. The shared font material is generated once in Shared.
5. Drag that prefab into your room scene. Retain root scale `(1,1,1)` for the documented metre dimensions. Position/rotate the root instead of moving mechanical child pivots.
6. Add a Camera tagged MainCamera, then choose **Tools > IoT Digital Twin > Add Mouse Input to Current Scene**. `IoTMouseInput.interactionCamera` is assigned automatically. Public methods work without that input component.

`Models/*.fbx` is the Unity import source. Editable `.blend` and alternative `.glb` exports live in `Models/Source~/` so Unity ignores them and does not require Blender or a glTF plugin. Open them directly in Blender or another model tool. Original Blender image data is packed; GLB textures are embedded. `Previews/` contains original Blender renders, not Unity screenshots.

## 5. Public C# API

Namespace: `IoTDigitalTwin`. Call methods on the configured prefab component **after Awake** (for example in Start). Use public setters to refresh visuals/events; editing raw public fields during Play Mode may not refresh all readouts.

| Method/property | Parameters and behavior |
|---|---|
| `SetDisplayValue(float value)` | 0–99, clamped; display rounds to a whole number with leading zero. |
| `SetStatus(bool value)` | Control green status emission. |
| `DisplayValue / Status` | Read-only stored value (float) and status. |

All devices inherit `SetSimulationMode(bool)`, `stateChanged` (Inspector UnityEvent), and `StateChanged` (C# event receiving IoTDevice). Simulation Mode identifies the device's local operating mode; switching it off does not create a hardware connection or stop rendering. The demo's automatic readings respect this flag. Finite float setters clamp to their documented ranges; NaN and infinity throw ArgumentOutOfRangeException.

## 6. Programmatic control

Obtain `SiemensBACnetDevice` from an instantiated prefab using `GetComponent<SiemensBACnetDevice>()` or assign it in the Inspector. Public methods share the same state/visual path as mouse input. Animated poses approach targets over time; target getters may differ from the currently displayed pose during motion. Use StateChanged for state notifications; it is not a network transport. Unsubscribe event handlers in OnDisable when needed.

## 7. Example C# usage

```csharp
using UnityEngine;
using IoTDigitalTwin;

public class SiemensBACnetDeviceExample : MonoBehaviour
{
    [SerializeField] private SiemensBACnetDevice device;

    private void Start()
    {
        device.SetDisplayValue(42f);
        device.SetStatus(true);
    }
}
```

Assign the generated prefab's controller to `device`. For external systems later, invoke these same setters on Unity's main thread; this pack includes no integration layer.

## 8. Inspector configuration

displayValue and status define initial state. display binds Live_Dot_Display and its owned runtime mesh. statusIndicator.renderer binds Status_LED_Green. The disabled original LED renderer is preserved for editing/reference; do not re-enable it with the runtime display.

Keep `simulationMode` enabled for local testing. Shared input colliders are triggers and require no Rigidbody. If an existing room's collider obscures a device, adjust its placement or camera raycast access. Material property blocks update the existing renderers without creating new materials each frame.

## 9. Expected Play Mode behavior and test

Click the grey display face to increment the number; scroll to adjust it. Click the green status point to toggle it. The original static LED_Dot_Display renderer is retained but disabled. A generated 36-dot mesh displays two 3×5 digits, five level dots and one cursor; per-vertex colours change at runtime.

For the full-library demo, generate **Prefabs and Demo**, open `Demo/Scenes/IoT_Interactive_Demo.unity`, press Play, select this device and exercise its physical controls plus matching panel sliders. Disable **Automatic readings** before setting sensor/display values manually. The panel provides **Run API / animation self-test** and prints a JSON report to Application.persistentDataPath. Complete the manual mouse checklist in `Demo/README.md`; the automated self-test does not prove mouse raycasting or visual quality.

## 10. Limitations, dependencies and validation

Two digits only, unsigned integers for display; floats round visually. The five level dots are a simulated value indicator. No BACnet protocol.

Dependencies: this directory plus `Shared/`; optionally the blind directory for Aqara linking. `Demo/` requires all nine devices and is not needed for independent reuse. Animations are procedural C#; no Animator or AnimationClip dependency. See `Animations/README.md`.

Offline compilation passed both for the full library and for this device with only Shared. Controller state/motion calculations were tested against lightweight offline test doubles. Source models and exports were reopened/reimported in Blender. **Unity Editor import, shader compilation, prefab/scene generation and actual Play Mode have not been run here.** Check the root verification report and perform the listed Unity checks before project acceptance.
