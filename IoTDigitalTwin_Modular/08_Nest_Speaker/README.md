# 08 — Google/Nest-style smart speaker

## 1. Device and purpose

A simulated speaker with mute, active state, volume and four animated lights. Estimated nominal size: **Ø98 × 42.5 mm speaker body, plus cradle and cable**. One Unity unit is one metre; source dimensions are estimates, not manufacturer measurements. Original model render budget: 4,812 triangles, before generated controls/readouts.

## 2. Interactions and animations

Click the rim mute switch. Left-drag or scroll the fabric face for volume. A short click on the face toggles active state. The mute switch slides 3 mm. Muted lights are red; active unmuted lights animate using four colours; changing volume briefly displays a four-light level indication.

## 3. Model hierarchy and interactive parts

The generated prefab root `08_Nest_Smart_Speaker` carries `NestSpeakerDevice`. Its imported model child retains the original root `Nest_Smart_Speaker` and the hierarchy below. `Input_*` trigger boxes are added to the corresponding movable part or touch target. Displays/markers are separate generated children of the prefab root; original geometry is retained.

| Part | Parent | Type |
|---|---|---|
| `Cradle_Finger_207` | `Nest_Smart_Speaker` | MESH |
| `Cradle_Finger_270` | `Nest_Smart_Speaker` | MESH |
| `Cradle_Finger_333` | `Nest_Smart_Speaker` | MESH |
| `Cradle_Lower_Arc` | `Nest_Smart_Speaker` | MESH |
| `Cradle_Wall_Plate` | `Nest_Smart_Speaker` | MESH |
| `Fabric_Dome` | `Speaker_Body_Pivot` | MESH |
| `Microphone_Mute_Switch` | `Speaker_Body_Pivot` | MESH |
| `Nest_Smart_Speaker` | `(root)` | EMPTY |
| `Power_Cable` | `Nest_Smart_Speaker` | MESH |
| `Speaker_Body_Pivot` | `Nest_Smart_Speaker` | EMPTY |
| `Speaker_Rear_Shell` | `Speaker_Body_Pivot` | MESH |
| `Status_Light_0` | `Speaker_Body_Pivot` | MESH |
| `Status_Light_1` | `Speaker_Body_Pivot` | MESH |
| `Status_Light_2` | `Speaker_Body_Pivot` | MESH |
| `Status_Light_3` | `Speaker_Body_Pivot` | MESH |

## 4. Unity installation and prefab setup

Target Unity 2022.3 LTS or Unity 6 (6000.0), Built-in or URP. These are target versions, not versions verified in this environment. No TextMeshPro, networking or hardware is required. The optional Input System is supported when its `ENABLE_INPUT_SYSTEM` define is active; otherwise input uses Unity's legacy Input API.

1. Copy this device directory and `Shared/` into the **same parent folder beneath your Unity project's Assets/**. Keep their `.meta` files. You can omit the other eight device directories and `Demo/`.
2. Wait for import and script compilation. Save your current scene before generation: generation opens a fresh working scene.
3. Choose **Tools > IoT Digital Twin > Individual Devices > 08_Nest_Speaker**. Alternatively choose **Generate Available Prefabs** to generate all imported devices.
4. The generator saves `Prefabs/08_Nest_Smart_Speaker.prefab`, device `.mat` assets under `Materials/Generated/`, and helper meshes under `Prefabs/GeneratedMeshes/`. The shared font material is generated once in Shared.
5. Drag that prefab into your room scene. Retain root scale `(1,1,1)` for the documented metre dimensions. Position/rotate the root instead of moving mechanical child pivots.
6. Add a Camera tagged MainCamera, then choose **Tools > IoT Digital Twin > Add Mouse Input to Current Scene**. `IoTMouseInput.interactionCamera` is assigned automatically. Public methods work without that input component.

`Models/*.fbx` is the Unity import source. Editable `.blend` and alternative `.glb` exports live in `Models/Source~/` so Unity ignores them and does not require Blender or a glTF plugin. Open them directly in Blender or another model tool. Original Blender image data is packed; GLB textures are embedded. `Previews/` contains original Blender renders, not Unity screenshots.

## 5. Public C# API

Namespace: `IoTDigitalTwin`. Call methods on the configured prefab component **after Awake** (for example in Start). Use public setters to refresh visuals/events; editing raw public fields during Play Mode may not refresh all readouts.

| Method/property | Parameters and behavior |
|---|---|
| `SetVolume(float value)` | Normalized 0–1, clamped; shows volume lights for one second. |
| `SetMuted(bool value)` | Move mute switch and show red lights when muted. |
| `SetActive(bool value)` | Active lights on/off; does not erase volume or mute state. |
| `Volume / Muted / Active` | Read-only state. |

All devices inherit `SetSimulationMode(bool)`, `stateChanged` (Inspector UnityEvent), and `StateChanged` (C# event receiving IoTDevice). Simulation Mode identifies the device's local operating mode; switching it off does not create a hardware connection or stop rendering. The demo's automatic readings respect this flag. Finite float setters clamp to their documented ranges; NaN and infinity throw ArgumentOutOfRangeException.

## 6. Programmatic control

Obtain `NestSpeakerDevice` from an instantiated prefab using `GetComponent<NestSpeakerDevice>()` or assign it in the Inspector. Public methods share the same state/visual path as mouse input. Animated poses approach targets over time; target getters may differ from the currently displayed pose during motion. Use StateChanged for state notifications; it is not a network transport. Unsubscribe event handlers in OnDisable when needed.

## 7. Example C# usage

```csharp
using UnityEngine;
using IoTDigitalTwin;

public class NestSpeakerDeviceExample : MonoBehaviour
{
    [SerializeField] private NestSpeakerDevice device;

    private void Start()
    {
        device.SetActive(true);
        device.SetMuted(false);
        device.SetVolume(0.6f);
    }
}
```

Assign the generated prefab's controller to `device`. For external systems later, invoke these same setters on Unity's main thread; this pack includes no integration layer.

## 8. Inspector configuration

muteSwitch binds Microphone_Mute_Switch; lights binds Status_Light_0 through Status_Light_3. volume is normalized. muted/active are startup states; animationSpeed controls the switch easing. Keep the speaker-body pivot and cradle hierarchy unchanged.

Keep `simulationMode` enabled for local testing. Shared input colliders are triggers and require no Rigidbody. If an existing room's collider obscures a device, adjust its placement or camera raycast access. Material property blocks update the existing renderers without creating new materials each frame.

## 9. Expected Play Mode behavior and test

Click the rim mute switch. Left-drag or scroll the fabric face for volume. A short click on the face toggles active state. The mute switch slides 3 mm. Muted lights are red; active unmuted lights animate using four colours; changing volume briefly displays a four-light level indication.

For the full-library demo, generate **Prefabs and Demo**, open `Demo/Scenes/IoT_Interactive_Demo.unity`, press Play, select this device and exercise its physical controls plus matching panel sliders. Disable **Automatic readings** before setting sensor/display values manually. The panel provides **Run API / animation self-test** and prints a JSON report to Application.persistentDataPath. Complete the manual mouse checklist in `Demo/README.md`; the automated self-test does not prove mouse raycasting or visual quality.

## 10. Limitations, dependencies and validation

No audio playback, voice recognition or Google integration. Volume and status lighting are simulated.

Dependencies: this directory plus `Shared/`; optionally the blind directory for Aqara linking. `Demo/` requires all nine devices and is not needed for independent reuse. Animations are procedural C#; no Animator or AnimationClip dependency. See `Animations/README.md`.

Offline compilation passed both for the full library and for this device with only Shared. Controller state/motion calculations were tested against lightweight offline test doubles. Source models and exports were reopened/reimported in Blender. **Unity Editor import, shader compilation, prefab/scene generation and actual Play Mode have not been run here.** Check the root verification report and perform the listed Unity checks before project acceptance.
