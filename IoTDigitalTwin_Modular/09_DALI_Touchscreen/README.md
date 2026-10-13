# 09 — DALI touchscreen lighting panel

## 1. Device and purpose

A touchscreen lighting controller with power, brightness, Kelvin control, colour selection and presets. Estimated nominal size: **180 × 120 × 22 mm housing; 156 × 88 mm active screen**. One Unity unit is one metre; source dimensions are estimates, not manufacturer measurements. Original model render budget: 1,456 triangles, before generated controls/readouts.

## 2. Interactions and animations

Click On/Off, drag Brightness vertically, drag Colour Temperature vertically, click/drag the Colour Field, and click any of the three scenes. Runtime numeric readouts and four visual markers overlay a cleaned version of the original UI, without duplicate static sample readings. Task uses 100%/4500 K; Presentation 1 uses 30% warm RGB; Presentation 2 uses 15% blue RGB.

## 3. Model hierarchy and interactive parts

The generated prefab root `09_DALI_Touchscreen_Panel` carries `DALILightingPanel`. Its imported model child retains the original root `DALI_Touchscreen_Panel` and the hierarchy below. `Input_*` trigger boxes are added to the corresponding movable part or touch target. Displays/markers are separate generated children of the prefab root; original geometry is retained.

| Part | Parent | Type |
|---|---|---|
| `DALI_Touchscreen_Panel` | `(root)` | EMPTY |
| `Front_White_Bezel` | `DALI_Touchscreen_Panel` | MESH |
| `Rear_Housing` | `DALI_Touchscreen_Panel` | MESH |
| `Screen_Gasket` | `DALI_Touchscreen_Panel` | MESH |
| `Touch_Brightness` | `DALI_Touchscreen_Panel` | EMPTY |
| `Touch_Colour_Field` | `DALI_Touchscreen_Panel` | EMPTY |
| `Touch_Colour_Temperature` | `DALI_Touchscreen_Panel` | EMPTY |
| `Touch_Off` | `DALI_Touchscreen_Panel` | EMPTY |
| `Touch_On` | `DALI_Touchscreen_Panel` | EMPTY |
| `Touch_Scene_Presentation_1` | `DALI_Touchscreen_Panel` | EMPTY |
| `Touch_Scene_Presentation_2` | `DALI_Touchscreen_Panel` | EMPTY |
| `Touch_Scene_Task` | `DALI_Touchscreen_Panel` | EMPTY |
| `Touchscreen_Display` | `DALI_Touchscreen_Panel` | MESH |
| `Wall_Mount` | `DALI_Touchscreen_Panel` | MESH |

Generated display/feedback children: `Live_Brightness`, `Live_Kelvin`, `Brightness_Thumb`, `Temperature_Handle`, `Colour_Marker`, `Scene_Selection`. Their meshes/materials are generated and saved with the owning device.

## 4. Unity installation and prefab setup

Target Unity 2022.3 LTS or Unity 6 (6000.0), Built-in or URP. These are target versions, not versions verified in this environment. No TextMeshPro, networking or hardware is required. The optional Input System is supported when its `ENABLE_INPUT_SYSTEM` define is active; otherwise input uses Unity's legacy Input API.

1. Copy this device directory and `Shared/` into the **same parent folder beneath your Unity project's Assets/**. Keep their `.meta` files. You can omit the other eight device directories and `Demo/`.
2. Wait for import and script compilation. Save your current scene before generation: generation opens a fresh working scene.
3. Choose **Tools > IoT Digital Twin > Individual Devices > 09_DALI_Touchscreen**. Alternatively choose **Generate Available Prefabs** to generate all imported devices.
4. The generator saves `Prefabs/09_DALI_Touchscreen_Panel.prefab`, device `.mat` assets under `Materials/Generated/`, and helper meshes under `Prefabs/GeneratedMeshes/`. The shared font material is generated once in Shared.
5. Drag that prefab into your room scene. Retain root scale `(1,1,1)` for the documented metre dimensions. Position/rotate the root instead of moving mechanical child pivots.
6. Add a Camera tagged MainCamera, then choose **Tools > IoT Digital Twin > Add Mouse Input to Current Scene**. `IoTMouseInput.interactionCamera` is assigned automatically. Public methods work without that input component.

`Models/*.fbx` is the Unity import source. Editable `.blend` and alternative `.glb` exports live in `Models/Source~/` so Unity ignores them and does not require Blender or a glTF plugin. Open them directly in Blender or another model tool. Original Blender image data is packed; GLB textures are embedded. `Previews/` contains original Blender renders, not Unity screenshots.

## 5. Public C# API

Namespace: `IoTDigitalTwin`. Call methods on the configured prefab component **after Awake** (for example in Start). Use public setters to refresh visuals/events; editing raw public fields during Play Mode may not refresh all readouts.

| Method/property | Parameters and behavior |
|---|---|
| `SetPower(bool value)` | Set lighting output power; brightness is retained. |
| `SetBrightness(float value)` | Normalized 0–1, clamped; refresh percentage and marker. |
| `SetColor(Color value)` | RGB components clamped 0–1; alpha is fixed at 1. Switches from Kelvin to RGB output. |
| `SetColorTemperature(float kelvin)` | 2000–6500 K, clamped; switches to approximate Kelvin-derived RGB output. |
| `SelectScene(int index)` | Clamped 0–2: Task, Presentation 1, Presentation 2. Applies preset and powers on. |
| `Power / Brightness / ColorTemperature / SelectedColor` | Read-only values; SelectedColor resolves Kelvin or RGB mode. |

All devices inherit `SetSimulationMode(bool)`, `stateChanged` (Inspector UnityEvent), and `StateChanged` (C# event receiving IoTDevice). Simulation Mode identifies the device's local operating mode; switching it off does not create a hardware connection or stop rendering. The demo's automatic readings respect this flag. Finite float setters clamp to their documented ranges; NaN and infinity throw ArgumentOutOfRangeException.

## 6. Programmatic control

Obtain `DALILightingPanel` from an instantiated prefab using `GetComponent<DALILightingPanel>()` or assign it in the Inspector. Public methods share the same state/visual path as mouse input. Animated poses approach targets over time; target getters may differ from the currently displayed pose during motion. Use StateChanged for state notifications; it is not a network transport. Unsubscribe event handlers in OnDisable when needed.

## 7. Example C# usage

```csharp
using UnityEngine;
using IoTDigitalTwin;

public class DALILightingPanelExample : MonoBehaviour
{
    [SerializeField] private DALILightingPanel device;

    private void Start()
    {
        device.SetPower(true);
        device.SetBrightness(0.65f);
        device.SetColorTemperature(4500f);
        // Alternative RGB mode: device.SetColor(Color.red);
        // Or apply a complete preset: device.SelectScene(2);
    }
}
```

Assign the generated prefab's controller to `device`. For external systems later, invoke these same setters on Unity's main thread; this pack includes no integration layer.

## 8. Inspector configuration

power, brightness, useTemperature, colorTemperature, selectedColor and sceneIndex define initial state. Generator assigns all readouts, markers and their calibration vectors. output.light/output.lamp are optional scene references. The demo binds a test lamp. animationSpeed controls output fading; marker changes are immediate.

Keep `simulationMode` enabled for local testing. Shared input colliders are triggers and require no Rigidbody. If an existing room's collider obscures a device, adjust its placement or camera raycast access. Material property blocks update the existing renderers without creating new materials each frame.

## 9. Expected Play Mode behavior and test

Click On/Off, drag Brightness vertically, drag Colour Temperature vertically, click/drag the Colour Field, and click any of the three scenes. Runtime numeric readouts and four visual markers overlay a cleaned version of the original UI, without duplicate static sample readings. Task uses 100%/4500 K; Presentation 1 uses 30% warm RGB; Presentation 2 uses 15% blue RGB.

For the full-library demo, generate **Prefabs and Demo**, open `Demo/Scenes/IoT_Interactive_Demo.unity`, press Play, select this device and exercise its physical controls plus matching panel sliders. Disable **Automatic readings** before setting sensor/display values manually. The panel provides **Run API / animation self-test** and prints a JSON report to Application.persistentDataPath. Complete the manual mouse checklist in `Demo/README.md`; the automated self-test does not prove mouse raycasting or visual quality.

## 10. Limitations, dependencies and validation

Kelvin conversion and palette are visual approximations. The colour-field marker clamps arbitrary external RGB colours to the available palette area, so red can be output even though the field cannot show a matching red coordinate. Kelvin text retains its last setting in RGB mode. No DALI bus protocol.

Dependencies: this directory plus `Shared/`; optionally the blind directory for Aqara linking. `Demo/` requires all nine devices and is not needed for independent reuse. Animations are procedural C#; no Animator or AnimationClip dependency. See `Animations/README.md`.

Offline compilation passed both for the full library and for this device with only Shared. Controller state/motion calculations were tested against lightweight offline test doubles. Source models and exports were reopened/reimported in Blender. **Unity Editor import, shader compilation, prefab/scene generation and actual Play Mode have not been run here.** Check the root verification report and perform the listed Unity checks before project acceptance.
