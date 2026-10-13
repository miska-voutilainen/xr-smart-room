# OrangeRoom (Unity 2022.3 LTS, URP, OpenXR, XR Interaction Toolkit)

Unity side of the Blender office/lab model. Blender export: `blender/unity_export/export_unity.py` (g3_export) writes
`Assets/Models/*.fbx` and `Assets/Textures/*.png`. Two editor scripts do the rest:

- `Assets/Editor/OrangeRoomImport.cs`: import rules (scale, axes, URP/Lit materials from texture names, glass, lightmap-UV fallback).
- `Assets/Editor/OrangeRoomSceneBuilder.cs`: menu **OrangeRoom > Build Scene** (static flags, colliders, lights,
  probes, lightmap settings, post volume, XR rig, teleport floor, grabbables, hinged door).

## Versions (checked 2026-10-12)

| What | Version | Why |
|---|---|---|
| Editor | **2022.3.76f1** (changeset d938583f0741, released 2026-05-06, latest 2022.3; 77f1 does not exist) | Pinned in `ProjectSettings/ProjectVersion.txt`. It is a "3-year LTS" patch (Unity Enterprise/Industry tier). If your licence can't install it, any 2022.3.x >= 2022.3.50 works: Hub offers to open the project with it. |
| URP | 14.0.11 | Core package, locked to the editor. Unity rewrites the pin to the editor's bundled 14.0.x on open, that's expected. |
| OpenXR Plugin | 1.17.1 | Newest release that still declares `unity: 2022.3` (1.19 needs Unity 6). |
| XR Plugin Management | 4.6.1 | Registry `latest` tag. |
| XR Interaction Toolkit | **3.5.0** | Newest XRI for 2022.3 (3.6 needs Unity 6). Needs Input System >= 1.8.1, XR Core Utils >= 2.4.0 (pulled in automatically). |
| Input System | 1.19.0 | Newest for 2022.3. |

No scoped registry is needed: everything comes from the Unity registry.

### Why XRI and not VRTK v4 / Tilia

VRTK v4 is the Tilia package family on OpenUPM (scoped registry `https://package.openupm.com`, scopes `io.extendreality`).
Checked 2026-10-12: `tilia.camerarigs.xrpluginframework.unity` 2.1.14, `tilia.interactions.interactables.unity` 2.18.1,
`tilia.locomotors.teleporter.unity` 2.2.4, `zinnia.unity` 2.16.2, all last published 2024-09-28 (one snapzone release 2025-03).
VRTK repo last push 2024-04, Zinnia 2025-01. Package metadata still declares Unity 2018.3/2019.3 and XR Management 4.0.1;
no statement about 2022.3, URP or OpenXR anywhere, and the teleporter/pointer visuals come from
`tilia.utilities.shaders` (Built-in RP shaders: pink under URP until rewritten). It would work with effort, but nobody
maintains it. XRI is first party, released for 2022.3 this year, and its Starter Assets give a tested rig with teleport,
snap turn, grab and UI interaction. Hence XRI. The brief asked for "XRI 2.x"; 2.6.5 is the 2021.3-era maintenance line,
3.5.0 is the current line for this editor, so 3.5.0 it is. The C# uses the 3.x namespaces
(`...Interactables.XRGrabInteractable`, `...Locomotion.Teleportation.TeleportationArea`); on 2.6 those two `using` lines change.

If you still want Tilia: add to `manifest.json`
```json
"scopedRegistries": [{ "name": "OpenUPM", "url": "https://package.openupm.com", "scopes": ["io.extendreality"] }]
```
plus `io.extendreality.tilia.camerarigs.xrpluginframework.unity: 2.1.14`, `...interactions.interactables.unity: 2.18.1`,
`...locomotors.teleporter.unity: 2.2.4`, `...indicators.objectpointers.unity: 2.2.16`, `...input.unityinputsystem: 2.4.11`,
and rewrite `OrangeRoomSceneBuilder.MakeGrab/MakeDoor/MakeTeleportFloor/XRRig` against Tilia prefabs.

## Export contract (what the scripts expect from g3_export)

- FBX, Blender `apply_scale_options='FBX_SCALE_UNITS'`, default axes (Unity side bakes axis conversion). 1 unit = 1 m.
- One FBX per area: `Room1.fbx`, `Room2.fbx`, `Room3.fbx` (hall beyond the pink door), `Exterior.fbx` (the name must contain `Exterior`). Each file root
  gets its own light-probe grid and box-projected reflection probe; Exterior gets neither and no colliders.
- Object names kept from Blender: `Floor` / `*_Floor` (teleport), `Door_Leaf` (origin on the hinge axis, children ride along),
  `Chair_*`, grabbables containing `Remote`, `Cup`, `Mug`, `Bottle`, `RobotCam` (origin at the object's centre),
  window glass named `*Window*Glass*`, ceiling LED panels named `*LED*Panel*`. Phase 2 pins these to the real names.
- UV0 for textures, UV1 (2nd UV layer) non-overlapping for lightmaps. Missing UV1 gets unwrapped on import with a warning.
- Textures `Assets/Textures/<MaterialName>_<Map>.png`, Map in `BaseColor` (sRGB), `Normal` (OpenGL +Y, as Blender bakes),
  `MetallicSmoothness` (linear, R = metallic, A = 1 - roughness), `AO` (linear, G read), `Emission` (sRGB).
  Material names must match the Blender material names (`Room_Wall`, `Door_Paint_Leaf`, ...). Glass: any material with `Glass` in its name.

## Steps

1. Unity Hub > Add > Add project from disk > `unity`. Open with 2022.3.76f1 (or see above).
   Packages resolve from `Packages/manifest.json`. When the Input System asks to enable the new backend: **Yes** (restart).
2. Project Settings > Player > Other Settings: Color Space **Linear** (the menu command also sets it),
   Active Input Handling **Input System Package (New)** or **Both**.
3. Create the URP asset: Project window > `Assets/Settings` > Create > Rendering > **URP Asset (with Universal Renderer)**.
   On it: HDR on, MSAA 4x, Render Scale 1, Main Light: Disabled is fine (all lighting is baked), Mixed Lighting on,
   Additional Lights: Per Pixel. Quest standalone: HDR off, MSAA 4x, Depth/Opaque texture off.
4. Project Settings > XR Plug-in Management: install, tick **OpenXR** for PC (and Android if Quest).
   OpenXR > Interaction Profiles: add Oculus Touch / Meta Quest Touch Pro, Valve Index, HTC Vive as needed.
   Render Mode: Single Pass Instanced. Fix everything Project Validation lists.
5. Package Manager > XR Interaction Toolkit > Samples > import **Starter Assets** (it also defines the `Teleport` interaction layer).
   Accept the Preset Manager prompt.
6. Copy the export into `Assets/Models` and `Assets/Textures` (textures first, or just reimport the models afterwards).
7. Menu **OrangeRoom > Build Scene**. Read the Console: it reports missing URP asset, Starter Assets, lights or UV2.
   It writes `Assets/Scenes/OrangeRoom.unity`, `Assets/Settings/OrangeRoom.lighting`, `OrangeRoom_Post.asset`, `OrangeRoom_Sky.mat`
   and puts the scene in Build Settings. Re-running rebuilds all of it from scratch.
8. Window > Rendering > Lighting > **Generate Lighting** (Progressive GPU; with a 4 GB GPU Unity may fall back to CPU, that's fine).
   Then Window > Rendering > Occlusion Culling > Bake.
9. Play with a headset (or the XR Device Simulator from the XRI samples).

## What the builder sets up

- **Static**: everything that isn't an interactable: Contribute GI, Occluder/Occludee, Batching, Reflection Probe static.
  Glass is not an occluder and casts no shadows. Meshes under 25 cm get light probes instead of lightmap space.
  Exterior: batching/occludee only, lit by ambient + fog.
- **Colliders**: non-convex MeshCollider on all static meshes except `Door_*` (frame would fight the leaf).
- **Lights**: one baked rectangle light per `*LED*Panel*` (facing down) and per `*Window*Glass*` (facing into the room).
  Area lights are baked only in URP; dynamic objects get them through light probes. Overcast procedural sky (no sun) as ambient,
  exponential-squared fog for the rainy exterior.
- **Lightmapping**: Progressive GPU, 40 texels/m, 2048 max, padding 4, directional, shadowmask, AO 0.5 m, 32/512/256 samples, 3 bounces.
- **Probes**: light-probe grid every 0.6 m at 0.3/1.1/1.8/2.5 m per room; one baked box-projected reflection probe per room.
- **Post**: global Volume, XR profile of `blender/unity_export/POSTFX.md` (fitted to the Blender AgX grade): Tonemapping **ACES**,
  Color Adjustments post-exposure -0.6 EV + contrast -12, White Balance -34 / -13, Bloom threshold 0 / intensity 0.03 /
  scatter 0.8. No vignette/grain/CA (bad in VR). Calibrate `PostExposure` as POSTFX.md "Exposure" describes.
- **XR**: Starter Assets `XR Interaction Setup` prefab on the room-1 floor, post-processing enabled on its camera, near clip 5 cm.
  `TeleportationArea` on the floors (interaction layer `Teleport`).
  Grabbables and chairs: Rigidbody + convex colliders + `XRGrabInteractable` (velocity tracking, dynamic attach).
  Door: Rigidbody + `HingeJoint` (axis up, anchor at the leaf origin, limits -110..0 deg) + `XRGrabInteractable` without rotation tracking.

## Calibrate after the first bake

Knobs are constants at the top of `OrangeRoomSceneBuilder.cs`:
`LedIntensity`, `WindowIntensity` (Blender watts don't convert; match the Cycles render side by side),
`PostExposure`, `DoorMinAngle/DoorMaxAngle` (door opens outward into the corridor: flip the sign if it swings into the room),
`TexelsPerUnit`, `ProbeSpacing`, `FogDensity`. Probes that land inside the cabinet or walls can be deleted by hand.
