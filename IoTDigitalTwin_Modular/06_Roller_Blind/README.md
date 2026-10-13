# 06 — Roller blind mechanism

## 1. Device and purpose

A blind assembly with synchronized cloth morph, bottom rail, roller, clutch and chain movement. Estimated nominal size: **1.20 m roller; 1.16 m cloth width; 0.45 m deployed cloth; approximately 0.80 m chain drop**. One Unity unit is one metre; source dimensions are estimates, not manufacturer measurements. Original model render budget: 33,244 triangles, before generated controls/readouts.

## 2. Interactions and animations

Drag horizontally along the bottom rail to choose a 0–100% target, or call Open/Close/Stop. At 100%, cloth Raise_Blind reaches its imported maximum frame weight and the rail moves from Y=−0.484 m to −0.05875 m. Roller and clutch rotate together about their existing pivots; chain beads circulate inside one mesh. The rail and cloth share the same 0.42525 m travel.

## 3. Model hierarchy and interactive parts

The generated prefab root `06_Roller_Blind_Mechanism` carries `RollerBlindDevice`. Its imported model child retains the original root `Roller_Blind_Mechanism` and the hierarchy below. `Input_*` trigger boxes are added to the corresponding movable part or touch target. Displays/markers are separate generated children of the prefab root; original geometry is retained.

| Part | Parent | Type |
|---|---|---|
| `Axle_Left` | `Roller_Blind_Mechanism` | MESH |
| `Axle_Right` | `Roller_Blind_Mechanism` | MESH |
| `Blind_Chain_Beads` | `Chain_Loop_Assembly` | MESH |
| `Blind_Chain_Cord` | `Chain_Loop_Assembly` | MESH |
| `Bottom_Endplug_-0.584` | `Bottom_Rail_Pivot` | MESH |
| `Bottom_Endplug_0.584` | `Bottom_Rail_Pivot` | MESH |
| `Bottom_Rail` | `Bottom_Rail_Pivot` | MESH |
| `Bottom_Rail_Pivot` | `Roller_Blind_Mechanism` | EMPTY |
| `Chain_Clutch_Pivot` | `Roller_Blind_Mechanism` | EMPTY |
| `Chain_Loop_Assembly` | `Roller_Blind_Mechanism` | EMPTY |
| `Chain_Sprocket` | `Chain_Clutch_Pivot` | MESH |
| `Cloth_With_Raise_BlendShape` | `Roller_Blind_Mechanism` | MESH |
| `Clutch_Teeth` | `Chain_Clutch_Pivot` | MESH |
| `Half_Round_Head_Cassette` | `Roller_Blind_Mechanism` | MESH |
| `Roll_Endcap_Left` | `Roller_Blind_Mechanism` | MESH |
| `Roll_Endcap_Right` | `Roller_Blind_Mechanism` | MESH |
| `Rolled_Fabric` | `Roller_Rotation_Pivot` | MESH |
| `Roller_Blind_Mechanism` | `(root)` | EMPTY |
| `Roller_Rotation_Pivot` | `Roller_Blind_Mechanism` | EMPTY |
| `Roller_Tube` | `Roller_Rotation_Pivot` | MESH |
| `Wall_Bracket_Left` | `Roller_Blind_Mechanism` | MESH |
| `Wall_Bracket_Right` | `Roller_Blind_Mechanism` | MESH |

## 4. Unity installation and prefab setup

Target Unity 2022.3 LTS or Unity 6 (6000.0), Built-in or URP. These are target versions, not versions verified in this environment. No TextMeshPro, networking or hardware is required. The optional Input System is supported when its `ENABLE_INPUT_SYSTEM` define is active; otherwise input uses Unity's legacy Input API.

1. Copy this device directory and `Shared/` into the **same parent folder beneath your Unity project's Assets/**. Keep their `.meta` files. You can omit the other eight device directories and `Demo/`.
2. Wait for import and script compilation. Save your current scene before generation: generation opens a fresh working scene.
3. Choose **Tools > IoT Digital Twin > Individual Devices > 06_Roller_Blind**. Alternatively choose **Generate Available Prefabs** to generate all imported devices.
4. The generator saves `Prefabs/06_Roller_Blind_Mechanism.prefab`, device `.mat` assets under `Materials/Generated/`, and helper meshes under `Prefabs/GeneratedMeshes/`. The shared font material is generated once in Shared.
5. Drag that prefab into your room scene. Retain root scale `(1,1,1)` for the documented metre dimensions. Position/rotate the root instead of moving mechanical child pivots.
6. Add a Camera tagged MainCamera, then choose **Tools > IoT Digital Twin > Add Mouse Input to Current Scene**. `IoTMouseInput.interactionCamera` is assigned automatically. Public methods work without that input component.

`Models/*.fbx` is the Unity import source. Editable `.blend` and alternative `.glb` exports live in `Models/Source~/` so Unity ignores them and does not require Blender or a glTF plugin. Open them directly in Blender or another model tool. Original Blender image data is packed; GLB textures are embedded. `Previews/` contains original Blender renders, not Unity screenshots.

## 5. Public C# API

Namespace: `IoTDigitalTwin`. Call methods on the configured prefab component **after Awake** (for example in Start). Use public setters to refresh visuals/events; editing raw public fields during Play Mode may not refresh all readouts.

| Method/property | Parameters and behavior |
|---|---|
| `SetOpenPercent(float value)` | Target 0–100%; finite values clamp. 0 is closed, 100 is open. |
| `Open() / Close() / Stop()` | Run to endpoint or freeze target at current position. |
| `OpenPercent / TargetOpenPercent` | Read-only animated current position and commanded target. |

All devices inherit `SetSimulationMode(bool)`, `stateChanged` (Inspector UnityEvent), and `StateChanged` (C# event receiving IoTDevice). Simulation Mode identifies the device's local operating mode; switching it off does not create a hardware connection or stop rendering. The demo's automatic readings respect this flag. Finite float setters clamp to their documented ranges; NaN and infinity throw ArgumentOutOfRangeException.

## 6. Programmatic control

Obtain `RollerBlindDevice` from an instantiated prefab using `GetComponent<RollerBlindDevice>()` or assign it in the Inspector. Public methods share the same state/visual path as mouse input. Animated poses approach targets over time; target getters may differ from the currently displayed pose during motion. Use StateChanged for state notifications; it is not a network transport. Unsubscribe event handlers in OnDisable when needed.

## 7. Example C# usage

```csharp
using UnityEngine;
using IoTDigitalTwin;

public class RollerBlindDeviceExample : MonoBehaviour
{
    [SerializeField] private RollerBlindDevice device;

    private void Start()
    {
        device.SetOpenPercent(40f);
        // Later: device.Open(); device.Close(); or device.Stop();
    }
}
```

Assign the generated prefab's controller to `device`. For external systems later, invoke these same setters on Unity's main thread; this pack includes no integration layer.

## 8. Inspector configuration

cloth, bottomRail, roller, clutch and chain are generator-bound. blendShapeIndex and fullyRaisedWeight are read from the imported Raise_Blind channel. percentPerSecond is percentage points/second. rollerRadius defaults to 0.0255 m. Keep currentOpenPercent and targetOpenPercent in 0–100 and avoid zero rollerRadius. Move/rotate the complete prefab root to place it; keep root scale (1,1,1).

Keep `simulationMode` enabled for local testing. Shared input colliders are triggers and require no Rigidbody. If an existing room's collider obscures a device, adjust its placement or camera raycast access. Material property blocks update the existing renderers without creating new materials each frame.

## 9. Expected Play Mode behavior and test

Drag horizontally along the bottom rail to choose a 0–100% target, or call Open/Close/Stop. At 100%, cloth Raise_Blind reaches its imported maximum frame weight and the rail moves from Y=−0.484 m to −0.05875 m. Roller and clutch rotate together about their existing pivots; chain beads circulate inside one mesh. The rail and cloth share the same 0.42525 m travel.

For the full-library demo, generate **Prefabs and Demo**, open `Demo/Scenes/IoT_Interactive_Demo.unity`, press Play, select this device and exercise its physical controls plus matching panel sliders. Disable **Automatic readings** before setting sensor/display values manually. The panel provides **Run API / animation self-test** and prints a JSON report to Application.persistentDataPath. Complete the manual mouse checklist in `Demo/README.md`; the automated self-test does not prove mouse raycasting or visual quality.

## 10. Limitations, dependencies and validation

Uses the existing Raise_Blind compression morph as a visual approximation; fabric is not physically rolled or simulated. Roller radius is an approximation, so physical chain gearing is not calibrated. Read/Write is enabled for the animated FBX. No cloth physics.

Dependencies: this directory plus `Shared/`; optionally the blind directory for Aqara linking. `Demo/` requires all nine devices and is not needed for independent reuse. Animations are procedural C#; no Animator or AnimationClip dependency. See `Animations/README.md`.

Offline compilation passed both for the full library and for this device with only Shared. Controller state/motion calculations were tested against lightweight offline test doubles. Source models and exports were reopened/reimported in Blender. **Unity Editor import, shader compilation, prefab/scene generation and actual Play Mode have not been run here.** Check the root verification report and perform the listed Unity checks before project acceptance.
