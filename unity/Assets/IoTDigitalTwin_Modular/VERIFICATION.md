# Verification and remaining acceptance work

## Completed here

| Check | Result | Method |
|---|---|---|
| Existing work recovery | PASS | All previously generated project files and the original 3D archive were present; resumed existing work |
| Original models preserved | PASS | SHA-256 equality for all nine Blender, FBX and GLB files, plus combined Blender project |
| Blender source reopen | PASS, all nine | Blender 4.0.2 loads the reorganized per-device files |
| FBX and GLB reimport | PASS, 18 imports | Blender import; same mesh names/counts and mechanical pivot positions within 0.02 mm |
| Editable topology | PASS | No zero-area source faces; closed source meshes except intentional planar decals; original detailed statistics retained |
| Blind geometry/morph | PASS | Existing Raise_Blind retained through both export imports; source cloth endpoints agree with rail Y=−0.484/−0.05875 m |
| Full C# library | PASS | Mono C# compilation against offline Unity API doubles |
| Nine independent device imports | PASS, all nine | Each device's controller/builder compiled with only Shared and test doubles; no other device or Demo dependency |
| Input System branch | PASS | Conditional C# compilation with ENABLE_INPUT_SYSTEM and compile-only API doubles |
| Pure logic | PASS, 8,329 assertions | Real DeviceMath: finite clamps, no overshoot, blind rail/cloth equation, capsule inversion/wrapping/joins, digits and island connectivity |
| Controller logic | PASS, 59 assertions | Real controller methods against lightweight doubles: state/events, button feedback, readout updates, tilt/yaw limits, pivot preservation, endpoints/Stop, optional Aqara link, LEDs, DALI dispatch/markers and bead geometry |
| Folder/material/reference audit | PASS | Nine directory structures, ten documentation sections each, texture mappings, original source hashes, shared dependencies and no old hard-coded Unity paths |
| Source GUIDs | PASS | Unique deterministic source .meta GUIDs supplied; original archive had no Unity .meta files to retain |

Details are in Verification~/Logs/. Original model reports remain in Verification~/OriginalModelReports/. The Blender log may contain host socket warnings unrelated to model import; every device's import check completed successfully.

## Not performed here — Unity Editor unavailable

Offline doubles implement only the signatures and limited behavior needed for testing. They are **not Unity Engine**, do not validate Unity serialization, rendering, shader compilation, actual FBX importer behavior, physics raycasts or coroutine timing, and are isolated in a Unity-ignored Verification~/ directory. Successful offline compilation is not a claim of successful Unity import or Play Mode.

The delivered pack contains real Unity Editor scripts that generate the actual prefabs, materials and fully wired demo scene. No fabricated .prefab or .unity files are included. Source .meta files carry stable GUIDs and basic importer metadata; Unity fills/version-migrates actual importer settings, and the generator applies the required FBX/texture settings.

Complete these checks in the project used by TalTech:

1. Import into a clean Unity 2022.3 LTS or Unity 6 (6000.0) Built-in or URP project. Confirm actual script/shader import and no Console errors. Verify the chosen pipeline's materials and normal maps.
2. Generate Prefabs and Demo. Review Shared/Generator_Verification.txt. Verify nine prefabs, their materials/meshes/references, calibration and real Demo/Scenes/IoT_Interactive_Demo.unity output. Reopen the saved scene and inspect serialization.
3. Run the demo's API / animation self-test in Play Mode. Review the actual IoT_PlayMode_Verification.json path logged in Console. None was generated in this environment.
4. Complete Demo/README.md's manual mouse checklist for all nine devices, checking occlusion, click/drag/scroll capture, return animations, screen legibility, no duplicate digits, LED emission and lighting output.
5. Inspect blind cloth/rail contact at 0/25/50/75/100%, including side views; observe chain beads, roller/clutch and correct pivot movement.
6. In another clean Unity project import only Shared plus one device. Generate its prefab, add camera/input and run it. Repeat for any device intended for separate distribution. Offline standalone compilation passed; actual single-device Unity importing still needs this check.
7. Move/rename the common parent inside Unity (preserving .meta), regenerate and reopen. Verify source/generated GUID references. Avoid duplicate copies of Shared.
8. Make a development player build for the target platform and check input, custom shader inclusion, material output and performance on the intended hardware. HDRP, touch, XR and gamepads require additional adapters/conversion.

## Reproducing offline checks

Install Mono mcs/mono and Python 3, then run `python Verification~/run_offline_validation.py` from any working directory. It compiles the full library, each standalone device, the optional input branch and executes the pure/controller tests. Outputs are written to Verification~/Logs; temporary binaries are in /tmp. This test setup deliberately excludes all test doubles from active Unity folders.

With Blender 4.0.2 and its NumPy/import addons available, run `blender -b -t 2 --python Verification~/validate_modular_models.py`. The script discovers this package relative to itself. It reopens sources/reimports both formats and refreshes hierarchy metadata and validation logs. Blender is not required to use the Unity asset pack.

## Practical limitations

Dimensions are estimates from photographs. The blind uses the original compression morph rather than physical cloth rolling. Beads move within grouped meshes, while continuous chain cord remains fixed. Device behaviors are local simulation; schedule is a state indicator, audio/video/protocols are not implemented. DALI Kelvin/RGB conversion is a visual approximation. The default independent dimmer/DALI prefabs have optional output light references; the demo supplies the test lamps. See each device README for details.

Official API references used during implementation: [ModelImporter](https://docs.unity3d.com/2022.3/Documentation/ScriptReference/ModelImporter.html), [useFileScale](https://docs.unity3d.com/2022.3/Documentation/ScriptReference/ModelImporter-useFileScale.html), [AssetDatabase.FindAssets](https://docs.unity3d.com/2022.3/Documentation/ScriptReference/AssetDatabase.FindAssets.html), and [PrefabUtility.SaveAsPrefabAsset](https://docs.unity3d.com/2022.3/Documentation/ScriptReference/PrefabUtility.SaveAsPrefabAsset.html). These documentation checks do not replace running the Editor.
