# 02 — Zigbee temperature and humidity LCD sensor

## 1. Device and purpose

A room sensor with a live temperature and relative-humidity display and editable simulated readings. Estimated nominal size: **86 × 86 × 23 mm**. One Unity unit is one metre; source dimensions are estimates, not manufacturer measurements. Original model render budget: 2,348 triangles, before generated controls/readouts.

## 2. Interactions and animations

Click Plus/Minus for ±0.5 °C. Click Mode to switch those buttons to ±1% humidity. Side buttons depress by 0.4 mm and return. Click the small top pairing control for a five-second PAIR indicator. The static sample numbers are replaced with live mesh text.

## 3. Model hierarchy and interactive parts

The generated prefab root `02_Zigbee_Temperature_LCD` carries `TemperatureLCD`. Its imported model child retains the original root `Zigbee_Temperature_LCD` and the hierarchy below. `Input_*` trigger boxes are added to the corresponding movable part or touch target. Displays/markers are separate generated children of the prefab root; original geometry is retained.

| Part | Parent | Type |
|---|---|---|
| `Bezel_Seam_Trim` | `Zigbee_Temperature_LCD` | MESH |
| `Button_1_Plus` | `Zigbee_Temperature_LCD` | MESH |
| `Button_2_Mode` | `Zigbee_Temperature_LCD` | MESH |
| `Button_3_Minus` | `Zigbee_Temperature_LCD` | MESH |
| `Decal_02_Minus` | `Button_3_Minus` | MESH |
| `Decal_02_Plus` | `Button_1_Plus` | MESH |
| `Front_Rounded_Bezel` | `Zigbee_Temperature_LCD` | MESH |
| `LCD_Display` | `Zigbee_Temperature_LCD` | MESH |
| `Rear_Cover` | `Zigbee_Temperature_LCD` | MESH |
| `Top_Pairing_Button` | `Zigbee_Temperature_LCD` | MESH |
| `Zigbee_Temperature_LCD` | `(root)` | EMPTY |

Generated display/feedback children: `Live_Temperature`, `Live_Humidity`, `Pairing`. Their meshes/materials are generated and saved with the owning device.

## 4. Unity installation and prefab setup

Target Unity 2022.3 LTS or Unity 6 (6000.0), Built-in or URP. These are target versions, not versions verified in this environment. No TextMeshPro, networking or hardware is required. The optional Input System is supported when its `ENABLE_INPUT_SYSTEM` define is active; otherwise input uses Unity's legacy Input API.

1. Copy this device directory and `Shared/` into the **same parent folder beneath your Unity project's Assets/**. Keep their `.meta` files. You can omit the other eight device directories and `Demo/`.
2. Wait for import and script compilation. Save your current scene before generation: generation opens a fresh working scene.
3. Choose **Tools > IoT Digital Twin > Individual Devices > 02_Zigbee_Temperature_Sensor**. Alternatively choose **Generate Available Prefabs** to generate all imported devices.
4. The generator saves `Prefabs/02_Zigbee_Temperature_LCD.prefab`, device `.mat` assets under `Materials/Generated/`, and helper meshes under `Prefabs/GeneratedMeshes/`. The shared font material is generated once in Shared.
5. Drag that prefab into your room scene. Retain root scale `(1,1,1)` for the documented metre dimensions. Position/rotate the root instead of moving mechanical child pivots.
6. Add a Camera tagged MainCamera, then choose **Tools > IoT Digital Twin > Add Mouse Input to Current Scene**. `IoTMouseInput.interactionCamera` is assigned automatically. Public methods work without that input component.

`Models/*.fbx` is the Unity import source. Editable `.blend` and alternative `.glb` exports live in `Models/Source~/` so Unity ignores them and does not require Blender or a glTF plugin. Open them directly in Blender or another model tool. Original Blender image data is packed; GLB textures are embedded. `Previews/` contains original Blender renders, not Unity screenshots.

## 5. Public C# API

Namespace: `IoTDigitalTwin`. Call methods on the configured prefab component **after Awake** (for example in Start). Use public setters to refresh visuals/events; editing raw public fields during Play Mode may not refresh all readouts.

| Method/property | Parameters and behavior |
|---|---|
| `SetTemperature(float value)` | Measured/simulated °C, clamped −40 to 80. Updates one decimal place. |
| `SetHumidity(float value)` | Relative humidity %, clamped 0–100. Display rounds to integer. |
| `SetPairing(bool enabled)` | True displays PAIR for five seconds; false clears it. |
| `Temperature / Humidity` | Read-only current readings. |

All devices inherit `SetSimulationMode(bool)`, `stateChanged` (Inspector UnityEvent), and `StateChanged` (C# event receiving IoTDevice). Simulation Mode identifies the device's local operating mode; switching it off does not create a hardware connection or stop rendering. The demo's automatic readings respect this flag. Finite float setters clamp to their documented ranges; NaN and infinity throw ArgumentOutOfRangeException.

## 6. Programmatic control

Obtain `TemperatureLCD` from an instantiated prefab using `GetComponent<TemperatureLCD>()` or assign it in the Inspector. Public methods share the same state/visual path as mouse input. Animated poses approach targets over time; target getters may differ from the currently displayed pose during motion. Use StateChanged for state notifications; it is not a network transport. Unsubscribe event handlers in OnDisable when needed.

## 7. Example C# usage

```csharp
using UnityEngine;
using IoTDigitalTwin;

public class TemperatureLCDExample : MonoBehaviour
{
    [SerializeField] private TemperatureLCD device;

    private void Start()
    {
        device.SetTemperature(23.5f);
        device.SetHumidity(56f);
        device.SetPairing(true);
    }
}
```

Assign the generated prefab's controller to `device`. For external systems later, invoke these same setters on Unity's main thread; this pack includes no integration layer.

## 8. Inspector configuration

temperature/humidity are initial values; editHumidity is the button edit mode. temperatureText, humidityText and pairingText bind generated DynamicReadout components. buttons has three PressPart entries in Plus/Mode/Minus order. Their rest positions are captured at Awake.

Keep `simulationMode` enabled for local testing. Shared input colliders are triggers and require no Rigidbody. If an existing room's collider obscures a device, adjust its placement or camera raycast access. Material property blocks update the existing renderers without creating new materials each frame.

## 9. Expected Play Mode behavior and test

Click Plus/Minus for ±0.5 °C. Click Mode to switch those buttons to ±1% humidity. Side buttons depress by 0.4 mm and return. Click the small top pairing control for a five-second PAIR indicator. The static sample numbers are replaced with live mesh text.

For the full-library demo, generate **Prefabs and Demo**, open `Demo/Scenes/IoT_Interactive_Demo.unity`, press Play, select this device and exercise its physical controls plus matching panel sliders. Disable **Automatic readings** before setting sensor/display values manually. The panel provides **Run API / animation self-test** and prints a JSON report to Application.persistentDataPath. Complete the manual mouse checklist in `Demo/README.md`; the automated self-test does not prove mouse raycasting or visual quality.

## 10. Limitations, dependencies and validation

Pairing is a timed visual indicator. No sensor acquisition. Extremely long formatted values may extend past the LCD layout; nominal room values fit.

Dependencies: this directory plus `Shared/`; optionally the blind directory for Aqara linking. `Demo/` requires all nine devices and is not needed for independent reuse. Animations are procedural C#; no Animator or AnimationClip dependency. See `Animations/README.md`.

Offline compilation passed both for the full library and for this device with only Shared. Controller state/motion calculations were tested against lightweight offline test doubles. Source models and exports were reopened/reimported in Blender. **Unity Editor import, shader compilation, prefab/scene generation and actual Play Mode have not been run here.** Check the root verification report and perform the listed Unity checks before project acceptance.
