# 03 — Z-Wave temperature controller

## 1. Device and purpose

A room thermostat with a measured temperature, target setpoint, power state and selectable mode. Estimated nominal size: **86 × 86 × 15 mm**. One Unity unit is one metre; source dimensions are estimates, not manufacturer measurements. Original model render budget: 954 triangles, before generated controls/readouts.

## 2. Interactions and animations

Click all five existing touch regions: Schedule toggles a simulated schedule indicator; Mode cycles Auto → Heat → Cool; Down/Up change target by 0.5 °C; Power toggles the display state. OFF hides the measured reading. Schedule is an indicator, not a time-based schedule engine.

## 3. Model hierarchy and interactive parts

The generated prefab root `03_ZWave_Temperature_Controller` carries `TemperatureController`. Its imported model child retains the original root `ZWave_Temperature_Controller` and the hierarchy below. `Input_*` trigger boxes are added to the corresponding movable part or touch target. Displays/markers are separate generated children of the prefab root; original geometry is retained.

| Part | Parent | Type |
|---|---|---|
| `Decal_03_Touch_Keys` | `ZWave_Temperature_Controller` | MESH |
| `Gloss_Front_Frame` | `ZWave_Temperature_Controller` | MESH |
| `Rear_Mounting_Case` | `ZWave_Temperature_Controller` | MESH |
| `Temperature_Display` | `ZWave_Temperature_Controller` | MESH |
| `Touch_Down` | `ZWave_Temperature_Controller` | EMPTY |
| `Touch_Mode` | `ZWave_Temperature_Controller` | EMPTY |
| `Touch_Power` | `ZWave_Temperature_Controller` | EMPTY |
| `Touch_Schedule` | `ZWave_Temperature_Controller` | EMPTY |
| `Touch_Up` | `ZWave_Temperature_Controller` | EMPTY |
| `ZWave_Temperature_Controller` | `(root)` | EMPTY |

Generated display/feedback children: `Live_Measured`, `Live_Target`, `Power_State`, `Control_Mode`. Their meshes/materials are generated and saved with the owning device.

## 4. Unity installation and prefab setup

Target Unity 2022.3 LTS or Unity 6 (6000.0), Built-in or URP. These are target versions, not versions verified in this environment. No TextMeshPro, networking or hardware is required. The optional Input System is supported when its `ENABLE_INPUT_SYSTEM` define is active; otherwise input uses Unity's legacy Input API.

1. Copy this device directory and `Shared/` into the **same parent folder beneath your Unity project's Assets/**. Keep their `.meta` files. You can omit the other eight device directories and `Demo/`.
2. Wait for import and script compilation. Save your current scene before generation: generation opens a fresh working scene.
3. Choose **Tools > IoT Digital Twin > Individual Devices > 03_ZWave_Thermostat**. Alternatively choose **Generate Available Prefabs** to generate all imported devices.
4. The generator saves `Prefabs/03_ZWave_Temperature_Controller.prefab`, device `.mat` assets under `Materials/Generated/`, and helper meshes under `Prefabs/GeneratedMeshes/`. The shared font material is generated once in Shared.
5. Drag that prefab into your room scene. Retain root scale `(1,1,1)` for the documented metre dimensions. Position/rotate the root instead of moving mechanical child pivots.
6. Add a Camera tagged MainCamera, then choose **Tools > IoT Digital Twin > Add Mouse Input to Current Scene**. `IoTMouseInput.interactionCamera` is assigned automatically. Public methods work without that input component.

`Models/*.fbx` is the Unity import source. Editable `.blend` and alternative `.glb` exports live in `Models/Source~/` so Unity ignores them and does not require Blender or a glTF plugin. Open them directly in Blender or another model tool. Original Blender image data is packed; GLB textures are embedded. `Previews/` contains original Blender renders, not Unity screenshots.

## 5. Public C# API

Namespace: `IoTDigitalTwin`. Call methods on the configured prefab component **after Awake** (for example in Start). Use public setters to refresh visuals/events; editing raw public fields during Play Mode may not refresh all readouts.

| Method/property | Parameters and behavior |
|---|---|
| `SetTemperature(float value)` | Measured °C, clamped −40 to 80. |
| `SetTargetTemperature(float value)` | Setpoint °C, clamped 5–35. |
| `SetPower(bool value)` | Toggle power and refresh display. |
| `SetMode(ThermostatMode value)` | Use Auto, Heat or Cool. |
| `Control("Schedule", Vector2.zero)` | Toggle simulated schedule indicator. |
| `Temperature / TargetTemperature / Power` | Read-only current state. |

All devices inherit `SetSimulationMode(bool)`, `stateChanged` (Inspector UnityEvent), and `StateChanged` (C# event receiving IoTDevice). Simulation Mode identifies the device's local operating mode; switching it off does not create a hardware connection or stop rendering. The demo's automatic readings respect this flag. Finite float setters clamp to their documented ranges; NaN and infinity throw ArgumentOutOfRangeException.

## 6. Programmatic control

Obtain `TemperatureController` from an instantiated prefab using `GetComponent<TemperatureController>()` or assign it in the Inspector. Public methods share the same state/visual path as mouse input. Animated poses approach targets over time; target getters may differ from the currently displayed pose during motion. Use StateChanged for state notifications; it is not a network transport. Unsubscribe event handlers in OnDisable when needed.

## 7. Example C# usage

```csharp
using UnityEngine;
using IoTDigitalTwin;

public class TemperatureControllerExample : MonoBehaviour
{
    [SerializeField] private TemperatureController device;

    private void Start()
    {
        device.SetTemperature(21.8f);
        device.SetTargetTemperature(24f);
        device.SetMode(ThermostatMode.Heat);
        device.SetPower(true);
    }
}
```

Assign the generated prefab's controller to `device`. For external systems later, invoke these same setters on Unity's main thread; this pack includes no integration layer.

## 8. Inspector configuration

temperature, targetTemperature, power, schedule and mode define startup state. Four generated readouts bind measuredText, targetText, stateText and modeText. Keep each Touch_* child and Input_* collider intact.

Keep `simulationMode` enabled for local testing. Shared input colliders are triggers and require no Rigidbody. If an existing room's collider obscures a device, adjust its placement or camera raycast access. Material property blocks update the existing renderers without creating new materials each frame.

## 9. Expected Play Mode behavior and test

Click all five existing touch regions: Schedule toggles a simulated schedule indicator; Mode cycles Auto → Heat → Cool; Down/Up change target by 0.5 °C; Power toggles the display state. OFF hides the measured reading. Schedule is an indicator, not a time-based schedule engine.

For the full-library demo, generate **Prefabs and Demo**, open `Demo/Scenes/IoT_Interactive_Demo.unity`, press Play, select this device and exercise its physical controls plus matching panel sliders. Disable **Automatic readings** before setting sensor/display values manually. The panel provides **Run API / animation self-test** and prints a JSON report to Application.persistentDataPath. Complete the manual mouse checklist in `Demo/README.md`; the automated self-test does not prove mouse raycasting or visual quality.

## 10. Limitations, dependencies and validation

No thermal dynamics or scheduled heating timetable. Modes and schedule are local state only.

Dependencies: this directory plus `Shared/`; optionally the blind directory for Aqara linking. `Demo/` requires all nine devices and is not needed for independent reuse. Animations are procedural C#; no Animator or AnimationClip dependency. See `Animations/README.md`.

Offline compilation passed both for the full library and for this device with only Shared. Controller state/motion calculations were tested against lightweight offline test doubles. Source models and exports were reopened/reimported in Blender. **Unity Editor import, shader compilation, prefab/scene generation and actual Play Mode have not been run here.** Check the root verification report and perform the listed Unity checks before project acceptance.
