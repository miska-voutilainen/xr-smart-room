# 05 — Aqara bead-chain controller

## 1. Device and purpose

A motorized bead-chain actuator with independent simulated position and optional linked blind. Estimated nominal size: **43 × 165 × 38 mm body, with chain extending above it**. One Unity unit is one metre; source dimensions are estimates, not manufacturer measurements. Original model render budget: 12,256 triangles, before generated controls/readouts.

## 2. Interactions and animations

Hold the physical Raise/Lower buttons to drive; release to Stop. Demo-panel Raise/Lower commands continue to their endpoints until Stop. Click the sliding drive cover to move it 18 mm upwards. Buttons depress 0.4 mm. The sprocket rotates and bead islands travel around a closed capsule loop inside one mesh. Standalone operation is the prefab default.

## 3. Model hierarchy and interactive parts

The generated prefab root `05_Aqara_Bead_Chain_Controller` carries `AqaraChainController`. Its imported model child retains the original root `Aqara_Bead_Chain_Controller` and the hierarchy below. `Input_*` trigger boxes are added to the corresponding movable part or touch target. Displays/markers are separate generated children of the prefab root; original geometry is retained.

| Part | Parent | Type |
|---|---|---|
| `Aqara_Bead_Chain_Controller` | `(root)` | EMPTY |
| `BeadChain_Beads` | `Chain_Assembly` | MESH |
| `BeadChain_Cord` | `Chain_Assembly` | MESH |
| `Button_Fascia` | `Aqara_Bead_Chain_Controller` | MESH |
| `Button_Lower` | `Aqara_Bead_Chain_Controller` | MESH |
| `Button_Raise` | `Aqara_Bead_Chain_Controller` | MESH |
| `Button_Recess` | `Aqara_Bead_Chain_Controller` | MESH |
| `Chain_Assembly` | `Aqara_Bead_Chain_Controller` | EMPTY |
| `Chain_Drive_Wheel` | `Drive_Sprocket_Pivot` | MESH |
| `Cover_Grip_Ribs` | `Sliding_Drive_Cover` | MESH |
| `Decal_05_Aqara` | `Aqara_Bead_Chain_Controller` | MESH |
| `Decal_05_Lower` | `Button_Lower` | MESH |
| `Decal_05_OPEN` | `Sliding_Drive_Cover` | MESH |
| `Decal_05_Raise` | `Button_Raise` | MESH |
| `Drive_Sprocket_Pivot` | `Aqara_Bead_Chain_Controller` | EMPTY |
| `Motor_Housing` | `Aqara_Bead_Chain_Controller` | MESH |
| `Sliding_Drive_Cover` | `Aqara_Bead_Chain_Controller` | MESH |
| `Status_LED` | `Aqara_Bead_Chain_Controller` | MESH |
| `Wall_Mount_Plate` | `Aqara_Bead_Chain_Controller` | MESH |

## 4. Unity installation and prefab setup

Target Unity 2022.3 LTS or Unity 6 (6000.0), Built-in or URP. These are target versions, not versions verified in this environment. No TextMeshPro, networking or hardware is required. The optional Input System is supported when its `ENABLE_INPUT_SYSTEM` define is active; otherwise input uses Unity's legacy Input API.

1. Copy this device directory and `Shared/` into the **same parent folder beneath your Unity project's Assets/**. Keep their `.meta` files. You can omit the other eight device directories and `Demo/`.
2. Wait for import and script compilation. Save your current scene before generation: generation opens a fresh working scene.
3. Choose **Tools > IoT Digital Twin > Individual Devices > 05_Aqara_Controller**. Alternatively choose **Generate Available Prefabs** to generate all imported devices.
4. The generator saves `Prefabs/05_Aqara_Bead_Chain_Controller.prefab`, device `.mat` assets under `Materials/Generated/`, and helper meshes under `Prefabs/GeneratedMeshes/`. The shared font material is generated once in Shared.
5. Drag that prefab into your room scene. Retain root scale `(1,1,1)` for the documented metre dimensions. Position/rotate the root instead of moving mechanical child pivots.
6. Add a Camera tagged MainCamera, then choose **Tools > IoT Digital Twin > Add Mouse Input to Current Scene**. `IoTMouseInput.interactionCamera` is assigned automatically. Public methods work without that input component.

`Models/*.fbx` is the Unity import source. Editable `.blend` and alternative `.glb` exports live in `Models/Source~/` so Unity ignores them and does not require Blender or a glTF plugin. Open them directly in Blender or another model tool. Original Blender image data is packed; GLB textures are embedded. `Previews/` contains original Blender renders, not Unity screenshots.

## 5. Public C# API

Namespace: `IoTDigitalTwin`. Call methods on the configured prefab component **after Awake** (for example in Start). Use public setters to refresh visuals/events; editing raw public fields during Play Mode may not refresh all readouts.

| Method/property | Parameters and behavior |
|---|---|
| `SetOpenPercent(float value)` | Target position 0–100%; 100 is raised/open. Optional link receives the same target. |
| `Raise() / Lower() / Stop()` | Run to 100%, run to 0%, or hold current position. |
| `SetCoverOpen(bool value)` | Slide cover to open/closed visual pose. |
| `ConnectBlind(IBlindControl blind)` | Optional MonoBehaviour implementing Shared IBlindControl; null disconnects. RollerBlindDevice implements it. |
| `OpenPercent / LinkedBlind` | Current position and optional link. Standalone current and target fields are also inspectable. |

All devices inherit `SetSimulationMode(bool)`, `stateChanged` (Inspector UnityEvent), and `StateChanged` (C# event receiving IoTDevice). Simulation Mode identifies the device's local operating mode; switching it off does not create a hardware connection or stop rendering. The demo's automatic readings respect this flag. Finite float setters clamp to their documented ranges; NaN and infinity throw ArgumentOutOfRangeException.

## 6. Programmatic control

Obtain `AqaraChainController` from an instantiated prefab using `GetComponent<AqaraChainController>()` or assign it in the Inspector. Public methods share the same state/visual path as mouse input. Animated poses approach targets over time; target getters may differ from the currently displayed pose during motion. Use StateChanged for state notifications; it is not a network transport. Unsubscribe event handlers in OnDisable when needed.

## 7. Example C# usage

```csharp
using UnityEngine;
using IoTDigitalTwin;

public class AqaraChainControllerExample : MonoBehaviour
{
    [SerializeField] private AqaraChainController device;

    private void Start()
    {
        device.ConnectBlind(null); // standalone
        device.SetOpenPercent(65f);
        device.SetCoverOpen(true);
        // Later: device.Stop();
    }
}
```

Assign the generated prefab's controller to `device`. For external systems later, invoke these same setters on Unity's main thread; this pack includes no integration layer.

## 8. Inspector configuration

sprocket, cover, chain, raiseButton, lowerButton and status are generator-bound. percentPerSecond is position percentage points/second (25 means approximately 4 seconds end-to-end). linkedBlindComponent optionally accepts a MonoBehaviour implementing IBlindControl. Leave it empty for standalone use. coverOpen defines initial cover state.

Keep `simulationMode` enabled for local testing. Shared input colliders are triggers and require no Rigidbody. If an existing room's collider obscures a device, adjust its placement or camera raycast access. Material property blocks update the existing renderers without creating new materials each frame.

## 9. Expected Play Mode behavior and test

Hold the physical Raise/Lower buttons to drive; release to Stop. Demo-panel Raise/Lower commands continue to their endpoints until Stop. Click the sliding drive cover to move it 18 mm upwards. Buttons depress 0.4 mm. The sprocket rotates and bead islands travel around a closed capsule loop inside one mesh. Standalone operation is the prefab default.

For the full-library demo, generate **Prefabs and Demo**, open `Demo/Scenes/IoT_Interactive_Demo.unity`, press Play, select this device and exercise its physical controls plus matching panel sliders. Disable **Automatic readings** before setting sensor/display values manually. The panel provides **Run API / animation self-test** and prints a JSON report to Application.persistentDataPath. Complete the manual mouse checklist in `Demo/README.md`; the automated self-test does not prove mouse raycasting or visual quality.

## 10. Limitations, dependencies and validation

No torque, chain tension, slip or mechanical feedback. Beads translate along the supplied loop; cord stays geometrically fixed. A link must be a Unity MonoBehaviour, not a plain C# object.

Dependencies: this directory plus `Shared/`; optionally the blind directory for Aqara linking. `Demo/` requires all nine devices and is not needed for independent reuse. Animations are procedural C#; no Animator or AnimationClip dependency. See `Animations/README.md`.

Offline compilation passed both for the full library and for this device with only Shared. Controller state/motion calculations were tested against lightweight offline test doubles. Source models and exports were reopened/reimported in Blender. **Unity Editor import, shader compilation, prefab/scene generation and actual Play Mode have not been run here.** Check the root verification report and perform the listed Unity checks before project acceptance.
