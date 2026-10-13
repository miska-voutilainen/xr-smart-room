# TalTech — Interactive IoT Device Library

Nine preserved 3D devices with local simulation controllers, mouse input, dynamic displays, procedural motion and Unity Editor setup tools. No Home Assistant integration, hardware connection, voice services or backend is included.

**Unity Editor was unavailable during delivery.** This package supplies real Editor generators rather than pre-generated or invented Unity prefab/scene YAML. Prefabs, materials and the configured demonstration scene are created inside your Unity project. Offline checks do not substitute for Unity import and Play Mode validation.

## Contents and modular layout

| Directory | Controller | Device |
|---|---|---|
| 01_Zigbee_Dimmer | RotaryDimmer | Rotary light dimmer |
| 02_Zigbee_Temperature_Sensor | TemperatureLCD | Temperature/humidity sensor |
| 03_ZWave_Thermostat | TemperatureController | Thermostat |
| 04_Security_Camera | SecurityCameraDevice | Articulated camera |
| 05_Aqara_Controller | AqaraChainController | Bead-chain actuator |
| 06_Roller_Blind | RollerBlindDevice | Animated roller blind |
| 07_Siemens_BACnet | SiemensBACnetDevice | LED-dot room device |
| 08_Nest_Speaker | NestSpeakerDevice | Speaker simulation |
| 09_DALI_Touchscreen | DALILightingPanel | Lighting touchscreen |
| Shared | Common runtime, Editor helpers, shader and font atlas | Import once |
| Demo | Demo scripts, scene generator, gallery sources/previews | Requires all nine |
| Verification~ | Reports, test sources and logs | Ignored by Unity |

Each device has Models/, Materials/, Textures/, Scripts/, Prefabs/, Animations/, Previews/ and a detailed README.md. FBX files are directly under Models/. Editable Blender projects and GLB alternatives are inside Models/Source~/, a Unity-ignored directory. The combined editable Blender project with all nine original named collections is under Demo/Models/Source~/. Source assets are unchanged; runtime display overlays do not modify original meshes or textures.

## Unity version and dependencies

Target versions: **Unity 2022.3 LTS or Unity 6 (6000.0)**. These are implementation targets, not tested Editor versions. Built-in Standard and URP/Lit material generation are supported. HDRP material conversion is not implemented. URP is only required if your project uses URP. The display shader has an unlit SRPDefaultUnlit pass and is included locally.

No external runtime packages, TextMeshPro, Blender installation or glTF importer are required for normal FBX-based setup. Legacy Input is supported. If the Unity Input System is installed and enabled (`ENABLE_INPUT_SYSTEM`), the input script uses its Mouse API. This implementation targets mouse/desktop testing; touch, XR and gamepad adapters are not supplied. Your existing project must have Unity's built-in physics and IMGUI facilities enabled.

## Import the full library and generate the demo

1. Unzip the archive. Copy the complete `IoTDigitalTwin_Modular/` directory into your project's `Assets/` folder. It is an asset library, not a full Unity project; create or use an existing project in Unity Hub.
2. Preserve `.meta` files. Wait for import and C# compilation, then check Console for errors. Do not place a second copy of the scripts elsewhere in Assets.
3. Save your current work. Choose **Tools > IoT Digital Twin > Generate Prefabs and Demo**. The generator asks Unity to save modified scenes and opens a new scene. It discovers the library root and imported DeviceDefinition.json files automatically; the outer directory can be renamed or moved within Assets.
4. The generator sets FBX units, axis conversion, normals, hierarchy and morph import; calibrates roots/pivots from source landmarks; assigns materials and textures; creates all interaction components and invisible trigger colliders; builds each independent prefab; and creates the demo with camera, lighting, input, panel and test tools.
5. Open `Demo/Scenes/IoT_Interactive_Demo.unity` (it is also opened after generation), press Play, and select a device on the left panel. All nine scene instances are configured. Aqara is connected to the blind only in the demo; its independent prefab has no link.
6. Use **Gallery** to view all devices, the zoom slider to inspect, and hold right mouse to orbit. Operate physical buttons/knobs or the matching panel. Read `Demo/README.md` for all controls and the acceptance checklist.
7. Generated material and mesh assets live beside their owning device. The font material is in Shared; demo-only lamp/backboard materials are in Demo. `Shared/Generator_Verification.txt` records actual generation checks once run.

Batch-mode generation, after importing into a licensed Unity project:

```bash
Unity -batchmode -projectPath /absolute/path/to/project -executeMethod IoTDigitalTwin.Editor.IoTAssetGenerator.GenerateBatch -quit -logFile /absolute/path/to/generation.log
```

## Import and use one device independently

Copy **Shared/** and the desired **one device folder** beneath the same parent in Assets. Omit Demo and the other eight devices. Use that device's Individual Devices menu, or **Generate Available Prefabs**. The shared generator compiles without referencing any concrete device or the demo; each device builder registers its own implementation. Aqara's optional blind uses an interface so its standalone import does not require RollerBlindDevice.

Drag the generated prefab into your room. Add/tag MainCamera and use **Add Mouse Input to Current Scene** for mouse operation. Public APIs work without mouse input. The dimmer and DALI prefab controllers expose optional LightingOutput fields; bind a scene Light/Renderer to visualize output on your room's lighting. Only the demo binds test lamps automatically. Keep one copy of Shared when adding more devices. Exporting a generated prefab for another Unity project requires its FBX, scripts, generated meshes/materials, device textures, Shared shader and shared glyph material/texture; use Unity's Export Package with dependencies.

## Metres, orientation, topology and pivots

Root scale is (1,1,1); one Unity unit equals one metre. Dimensions are photographic estimates documented per device and in Verification~/Original_Device_Specifications.md. Blender retains its original X/Z/−Y basis. The generated interaction frame uses Y up, Z toward the front, and X opposite photographic horizontal so text/control positions agree when viewed from the front in Unity's left-handed coordinates. Imported model conversion is corrected from landmarks; move and rotate the prefab root without editing mechanical child origins. The generator validates landmark positions within 0.2 mm and preserves named pivots.

Original source geometry is retained, including the blind Raise_Blind morph. Runtime chains use one cloned mesh per chain with grouped, welded bead islands; no per-bead GameObjects are created. Read/Write is enabled for the two chain-bearing imports. Indicators use material property blocks. Live text uses a shared bitmap atlas and rebuilds meshes when strings change. Animations are procedural; no Animator controller is needed. Original geometry totals 71,644 render triangles, plus generated readouts and helper controls.

## Test all nine devices

Run **API / animation self-test** in the demo panel. It checks setters, dynamic readings, camera lamp, Aqara standalone bead movement, blind endpoint/morph/rail synchronization and Stop, LED display, speaker, DALI presets and collider references. It prints a real Play Mode report to `Application.persistentDataPath/IoT_PlayMode_Verification.json`. This file is created only by running the test in Unity; none is supplied as if already run.

Then complete the nine-device manual mouse checklist in Demo/README.md. Verify visuals from several angles and inspect the blind at 0%, 25%, 50%, 75% and 100%. Disable Automatic readings before manually controlling temperature/humidity/BACnet values; otherwise the demo deliberately updates them once per second. Review `VERIFICATION.md` for checks already performed and the Unity checks still required. Re-import one device plus Shared in a separate empty Unity project to complete the standalone-import acceptance test.

## Public APIs and future external state integration

Each device README contains exact method signatures, units, ranges, Inspector fields and runnable example snippets. Brightness and speaker volume use 0–1, blind opening uses 0–100%, temperatures use °C or Kelvin as documented, and camera angles use degrees. Use setters after Awake; direct edits to raw state fields may bypass display refresh/events.

Controllers expose a `StateChanged` C# event and an Inspector `stateChanged` UnityEvent. Future adapters should translate external values into these setters on Unity's main thread, subscribe to state events for outbound commands, and avoid echo loops by tracking update origin or suppressing adapter-side retransmission. Disable demo Automatic readings for external control. Simulation Mode is a local state flag used by demo-generated readings; it does not connect to hardware when disabled. Transport, authentication, device identifiers, reconnect handling and persistence belong to a future integration layer and are not implemented here.

## Source files, previews and licenses

Previews are original Blender renders, not screenshots of tested Unity behavior. Per-device Blender files include packed textures; GLB includes embedded images. Shared/Source~/OriginalModelGeneration contains historical original scripts; they retain their original flat-package layout assumptions and are not Unity setup tools. Source metadata and original reports are kept in Verification~ for traceability. The bitmap font atlas derives from DejaVu Sans; its license is included in Shared/Textures. Brand names and printed labels identify the referenced devices; this library is not endorsed by those manufacturers.

Stable source .meta GUIDs are supplied. No existing Unity .meta files were present in the source archive; none were discarded. Preserve these files and any newly generated Unity .meta files when moving assets. Re-running the generator updates existing materials/meshes in place and saves prefabs at stable paths. Back up customized generated prefabs before regeneration, which intentionally replaces generated configuration. The generated demo scene is recreated and custom scene edits can be overwritten.
