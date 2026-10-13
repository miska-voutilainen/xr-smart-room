# Device dimensions and interactions

All values are in metres unless shown as millimetres. Estimates follow the supplied photographs. The table gives nominal bodies, not the complete bounding box including cables and chains; measured full bounds are recorded in `Reports/validation.json`.

| ID | Device | Nominal size / estimate | Separate parts and interaction |
|---|---|---|---|
| 01 | Zigbee rotary dimmer | 86 × 86 × 25.9 mm | Fixed frame and inset; `05_Rotary_Knob` pivots on its shaft, 10 mm forward of the back plane. Rotate about model Z in Unity. Optional 0.7 mm inward press. Removable installation sticker. |
| 02 | Zigbee LCD temperature sensor | 86 × 86 × 23 mm | LCD, three right-side buttons, top pairing button. Buttons have centred pivots and can press 0.4 mm along Unity −Z. Display sample: 21.7 °C and 48%. |
| 03 | Z-Wave temperature controller | 86 × 86 × 15 mm | Screen and five `Touch_…` target empties for schedule, mode, down, up and power. Printed Nice-style legends. Sample temperature: 22.6 °C. |
| 04 | Security camera | Head 110 × 110 × 72 mm; wall projection about 130 mm | `Camera_Tilt_Pivot` at Unity (0, 0.015, 0.050), X tilt / Y yaw. Separate lens, aperture, floodlight, sensor window and red status LED. Mount and weatherproof cable connector included. |
| 05 | Aqara bead-chain controller | Body 43 × 165 × 38 mm | Sliding drive cover, two buttons, status light, drive-wheel pivot and chain assembly. `Drive_Sprocket_Pivot` at Unity (0, 0.071, 0.013); rotate about Z. Cover slides upwards along Unity Y. Chain loop rises to about 273 mm above the body-centre origin. |
| 06 | Roller blind mechanism | Roller 1.20 m wide; cloth 1.16 m wide and 0.45 m deployed; chain drop about 0.80 m | Separate head casing, brackets, roller, clutch, cloth, rail and bead-chain loop. Detailed instructions below. |
| 07 | Siemens BACnet device | Back plate 88 × 88 mm; depth 25 mm | Rounded front frame, grey face, printed logo, sensor dot, green status LED, separately addressable LED display material. Recreated dot display: 93. |
| 08 | Google/Nest-style smart speaker | Speaker Ø98 × 42.5 mm, excluding cradle/cable | Fabric dome, rear shell, mute slider, four status-light surfaces, separate black wall cradle and cable. `Speaker_Body_Pivot` lies at body centre, Unity (0, 0, 0.025). Status lights are initially unlit. |
| 09 | DALI touchscreen panel | 180 × 120 × 22 mm; active screen 156 × 88 mm | Housing, bezel, screen, and named touch targets for On/Off, brightness, colour temperature, colour field and three scenes. Sample interface follows the “MEETING ROOM” reference. |

## Coordinate and pivot conventions

Blender uses X right, Z up and −Y forward. Geometry and transforms are exported to Y up and +Z forward. Blender (x, y, z) maps to exported model coordinates (x, z, −y). Inward button movement is therefore Blender +Y / Unity −Z. Check local axes after any additional importer axis-conversion setting before connecting animation code.

Each device has one named root empty. The individual projects and exports place this root at (0, 0, 0). Small assembly parts have centred origins where useful. Named mechanical pivots take precedence over a part's geometric centre. The combined project translates roots for viewing only; it does not rescale them. Object names inside the combined scene are prefixed with the device number to prevent collisions.

## Raising the blind

- `Roller_Rotation_Pivot`: Unity (0, −0.030, 0.035). Rotate around X.
- `Chain_Clutch_Pivot`: Unity (0.620, −0.030, 0.035). Rotate around X.
- `Cloth_With_Raise_BlendShape`: `Raise_Blind` at 0 is deployed; at 1 it is nearly rolled up. Unity's blend-shape weight range is 0–100.
- `Bottom_Rail_Pivot`: move Unity Y from −0.484 to −0.05875 as the cloth is raised. X stays 0 and Z stays 0.061. Keep both actions synchronised in your controller.
- The shape key is a visual approximation, not a cloth simulation. Roller rotation, clutch motion and chain motion are not linked automatically. Chain beads are real mesh geometry grouped into assemblies; no per-bead rig is supplied.

## Materials, topology and scope

Source meshes use quad strips, rounded profiles and planar n-gon caps. Cloth uses a regular quad grid; cables use quad tubes. Beads are closed mesh islands combined into shared objects. Small fixed details are merged where practical to reduce renderer count. FBX preserves editable polygon topology where supported; GLB is triangulated for rendering. Bevel/weighted-normal modifiers remain editable on appropriate source parts.

All meshes have UV maps. Screens and decals have dedicated planar UVs. Other UVs are sufficient for supplied materials; they are not a hand-authored lightmap atlas. Generate lightmap UVs in Unity if required. Screen textures are static example values; real sensor data must be connected by your application's code, replacement textures, text meshes or UI.

The photos do not establish exact model variants or hidden internals. The classroom display board, external labels, wall, window and adjacent devices are excluded. The dimmer sticker's partly hidden first line is reconstructed cosmetic text, not verified installation guidance. The Aqara and blind chain lengths are representative and should be adapted to the room layout.
