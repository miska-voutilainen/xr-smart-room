# XR-readiness audit of the Blender project (g3_unity)

Scope: `build_room.py`, `apply_materials.py`, `materials/*.py`, `tools/`, measured on a full build of a copy
(`scratchpad/w2_g3_unity/audit.blend`, Blender 5.2.0 LTS, built 2026-10-12 ~15:50 from the wave-1 scripts:
cabinet, chair, desk, door, monitor, radiator, room, tv, window). Wave-2 scripts that appeared since
(exterior, kitchen, trim, shaders/arch, render/light) are reviewed from source only (section 6); phase 2 re-measures everything.
Measurement scripts: `scratchpad/w2_g3_unity/audit_scene.py`, `audit2.py` (evaluated meshes, modifiers applied).

## 1. Summary

| | Now | Target | Verdict |
|---|---|---|---|
| Total triangles (evaluated) | **65,124** in 25 meshes | < 300k room total | OK, but 58% of it is the radiator |
| Worst prop | Radiator + Radiator_Pipes **38,144** | hero prop <= ~5k | 7.6x over |
| Topology | all quads except Desk (80 tris, caps); 0 n-gons; 0 non-manifold edges; 0 loose verts | | good |
| Normals | outward on all 25 meshes (signed volume > 0 for every closed mesh) | | good |
| Degenerate (zero-area) faces | Door_Leaf 56, Window_Frame 46, TV 8 | 0 | fix (breaks lightmap UV packing, FBX warnings) |
| UVs | none, except Monitor (`UVMap`) | UV0 + UV1 everywhere | g3_export's job, see 4 |
| Materials | 33, all procedural node trees (up to 59 nodes), 0 image textures | baked PBR sets | g3_export bake list, see 4 |
| Scene units | metric, scale 1.0, metres | | good |
| Clip | camera 0.1 / 100 m, viewport 0.01 / 1000 m | | ok; exterior reaches x = 124 m, raise camera clip_end to 200 m for Blender renders of it |
| Orphan data | 0 meshes / materials / node groups / images | | good (scripts purge properly) |
| Instancing | Chair_1 / Chair_2 share one mesh (users = 2) | | good, keep; Unity gets one mesh asset |

## 2. Per-object table (evaluated, i.e. what FBX export with "Apply Modifiers" produces)

| Object | Coll. | Base tris | Eval tris | Modifiers | Materials | Origin | Notes |
|---|---|---:|---:|---|---|---|---|
| Radiator | Furniture | 27,648 | 27,648 | (subsurf applied in script, lvl 1) | Radiator_Paint | world 0 | 5.5x budget |
| Radiator_Pipes | Furniture | 10,496 | 10,496 | (subsurf applied, lvl 2) | Radiator_PipePaint | world 0 | 2x budget alone |
| Window_Frame | Openings | 1,288 | 6,104 | Bevel 2 seg | Window_PVC, Window_Gasket | world 0 | 46 degenerate faces |
| Desk | Furniture | 1,080 | 5,912 | Bevel 3 seg | Desk_Laminate, Desk_PowderCoat, Desk_Glide | world 0 | 5.5x from bevel |
| Cabinet | Furniture | 404 | 3,124 | Bevel 2 seg | 5 materials | world 0 | 7.7x from bevel |
| Door_Hardware | Openings | 2,736 | 2,736 | - | Door_Steel | parent Door_Leaf | fine |
| Chair_1 / Chair_2 | Furniture | 2,532 | 2,532 each | - | Chrome, Fabric, Shell | seat (4.65, y, 0) | shared mesh, good pivot |
| Door_Leaf | Openings | 416 | 1,632 | Bevel 2 seg | Door_Paint_Leaf | hinge (0, 1.15, 0), rot z -28 deg | 56 degenerate faces; pivot right for HingeJoint |
| Window_Sill | Openings | 36 | 644 | Bevel **4** seg | Window_SillBoard | world 0 | 18x from bevel |
| TV | Furniture | 52 | 436 | Bevel 2 seg | 4 materials | world 0 | 8 degenerate faces |
| Door_Frame | Openings | 68 | 404 | Bevel 2 seg | Door_Paint | world 0 | |
| Wall_Top | Walls | 172 | 172 | - | Room_Wall | world 0 | |
| Window_Glass | Openings | 144 | 144 | - | Window_Glass | world 0 | |
| Monitor | Furniture | 20 | 116 | Bevel 2 seg | 4 materials | world 0 | only object with UVs |
| Door_Fixed_Panel, Door_Threshold, Monitor_Stand | | 12 | 108 | Bevel 2 seg | | world 0 | |
| Wall_Bottom/Left/Right, Pillar, Floor, Room_Ceiling, Door_Glass | | 12-64 | 12-64 | - | | world 0 | |

Lights: Room_LED_1/2 (area 0.57 m, 40 W, 2.896 m high), Room_Window_Daylight (area 1.85 x 1.55 m, 60 W). Not exported
(Unity rebuilds them as baked rectangle lights from the LED panel / window glass meshes).

## 3. Findings and actions per owner

### g1_radiator (`materials/radiator.py`)
- 38k tris for radiator + pipes. `subdivided_mesh(..., levels=2)` for pipes and level 1 on a dense cage for the body.
  Action: radiator body cage at subdiv level 0 with a 1-segment bevel (MS-140 sections are boxy; 12 sections x ~300 tris = ~4k),
  pipes 8-sided at level 0 (~1k). Keep the current mesh as the high-poly for a normal-map bake if g3_export wants it.
  Budget: radiator 4k + pipes 1.5k.

### g1_window (`materials/window.py`)
- Window_Frame 1,288 -> 6,104 tris, 46 zero-area faces after `Window_Bevel` (2 segments). Window_Sill uses 4 segments: 36 -> 644.
  Action: bevel `segments = 1`, `limit_method = 'ANGLE'`, `harden_normals = True` (+ mesh auto-smooth by angle) gives the same
  highlight at a third of the cost; set `clamp_overlap = True` and remove the coplanar cuts that produce zero-area faces.
  Budget: frame + sashes + handles <= 8k.

### g1_desk (`materials/desk.py`, tv.py, monitor.py)
- Desk 1,080 -> 5,912 (Bevel 3 segments, width 2 mm). A 2 mm bevel is invisible beyond ~1 m in VR; use 1 segment + harden normals: ~2.5k.
- TV: 8 degenerate faces after bevel. Same fix as above.
- Monitor is the only object with UVs (`UVMap`): keep the name `UVMap` so g3_export can reuse it as UV0.
- Desk has 80 triangles (cylinder caps of the legs/glides): fine.

### g1_kitchen (`materials/cabinet.py`)
- Cabinet 404 -> 3,124 (Bevel 2 segments on everything). Same 1-segment recommendation.
- Cabinet (0/1562), TV (0/218) and Monitor_Stand (0/54) are flat-shaded although they carry a bevel: the bevel then shows as
  facets and every vertex is split in Unity. Shade smooth + `harden_normals` on the bevel (or smooth by angle 30 deg).

### g1_doorend (`materials/door.py`)
- Door_Leaf: 56 zero-area faces after `Door_Bevel`. The superellipsoid handle helpers are fine (all quads).
- Pivot on the hinge (0, 1.15, 0) and Door_Glass / Door_Hardware parented to Door_Leaf: exactly what Unity's HingeJoint needs. Keep it
  when the leaf is turned to open outward. Please model the leaf CLOSED (rotation 0 in the frame) and drive the photo pose
  with the object rotation only; then Unity's hinge limits are simply 0..-110 deg (or 0..110).
- Door_Frame / Door_Fixed_Panel / Door_Threshold are separate objects with the same `Door_Bevel`; fine.

### g1_chair (`materials/chair.py`)
- 2.5k tris per chair, shared mesh, origin on the floor under the seat: ideal (grab + Rigidbody pivot). Keep the mesh sharing
  (`Chair_2` linked to `Chair_1`'s data) when rebuilding.

### g1_trim, g1_room2, g1_exterior, g1_kitchen, g1_desk (new objects)
- Naming the Unity scripts rely on (please use): LED panels contain `LED` and `Panel` (e.g. `Trim_LED_Panel_1`);
  window glass contains `Window` and `Glass` (e.g. `Room2_Window_Glass_1`); floors are `Floor` / `Room2_Floor`;
  grabbables contain `Remote`, `Cup`, `Mug`, `Bottle` or `RobotCam`; each grabbable is ONE object (or a parent with children)
  with its origin at its centre of mass.
- Don't name decorative LED strips `*LED*Panel*` (they'd get a ceiling light).
- Keep big flat surfaces (walls, floor, ceiling tiles) as few large quads; the ceiling T-grid as one joined mesh per room.
- Skirting / trunking: no bevel modifier beyond 1 segment; they are long and linear, every segment multiplies along the whole room.

### g2 (shaders, light, render)
- Every material is procedural (Noise/Voronoi/ColorRamp/Bump trees, up to 59 nodes in Room_Floor, 52 in Monitor_Bezel,
  49 in Room_Ceiling). None of it survives FBX. Keep each final material ending in ONE Principled BSDF (no Mix Shader at the top,
  no Shader-to-RGB, no light-path tricks) so g3_export can bake BaseColor / Roughness / Metallic / Normal / Emission cleanly.
- Keep material NAMES stable (Unity maps textures by `<material>_BaseColor.png` etc.).
- World is a procedural gradient (strength 6) + window area light. For Unity, please render (once) a 2:1 equirect HDR of the
  sky + exterior from the room-1 window position (Cycles, no interior): it becomes the Unity skybox and the source of
  ambient light, and is far cheaper than real-time trees in VR.
- AgX view transform with exposure -1.3: Unity URP 14 has only Neutral/ACES; Neutral is used. If a closer match is
  needed, export a 32^3 LUT of "AgX base" from Blender's OCIO config and Unity applies it as Color Lookup.

### g3_export (`unity/export_unity.py`)
- UV0 + UV1 for every mesh (only Monitor has UVs). UV1: Smart UV Project / Lightmap Pack, non-overlapping, ~4 px padding
  at 40 texels/m. If UV1 is missing the Unity importer unwraps on import (warning in the Console) but quality is lower.
- Texel density: don't unique-bake large tiling surfaces. Walls, floor terrazzo, ceiling tiles, laminate, cabinet fronts,
  chair fabric: bake one tileable 1 m (ceiling: 0.6 m tile) square at 1024-2048 px and give UV0 world-metre box mapping;
  the lightmap carries the unique shading. Unique bakes only for hero props (TV, monitor, door leaf, radiator, demo board):
  ~1024 px per prop, ~512 px/m. Small hardware (hinges, handles, glides, sockets): one shared atlas.
- Apply bevel modifiers on export but drop them to 1 segment (or bake the bevel highlight into the normal map) and
  remove the zero-area faces (`bmesh.ops.dissolve_degenerate`, dist 1e-6) before UV packing.
- Export one FBX per area (`Room1`, `Room2`, `Exterior`), `apply_scale_options='FBX_SCALE_UNITS'`, mesh-only
  (no lights/cameras), keep object names and parenting (Door_Leaf children).
- Exterior: realise the GN leaf instances (`Ext_LeafScatter`) and reduce to alpha-cutout leaf-card clusters, or drop the exterior
  meshes in favour of the equirect skybox above. Don't export `Ext_Rain` (2,500 streak cards, transparent overdraw in VR);
  Unity gets a particle system instead. Hide-render helpers (`Ext_Leaf` source) must not be exported.
- Interactable pivots: origin at the centre for grabbables, hinge for Door_Leaf, floor under seat for chairs.
- Normals: export with custom split normals so harden-normals bevels survive; Unity imports them (`importNormals = Import`).

### tools/
- `tools/bl` slot lock works; nothing to change. `tools/ortho.py` is check-sheet only and not part of the build.

## 4. Proposed triangle budget for the final scene (Unity)

| Area / owner | Budget |
|---|---:|
| Room 1 shell + trim + ceiling grid (room, g1_trim) | 15k |
| Window + reveal (g1_window) | 8k |
| Door end: door, frame, electrical boxes (g1_doorend) | 10k |
| Radiator + pipes (g1_radiator) | 5.5k |
| Desk, TV, monitor, desk props (g1_desk) | 15k |
| Cabinet + demo board + kitchen props (g1_kitchen) | 25k |
| Chairs (2 x 2.5k, shared) | 5k |
| Room 2 lab (g1_room2) | 80k |
| Exterior (g1_exterior), or 0 with an equirect skybox | 100k |
| Headroom | 36k |
| **Total** | **< 300k** |

### room / build_room.py (FROZEN, for the record)
- Floor and Room_Ceiling are 0.1 m slabs running under/over the walls (-0.1..6.6 x -0.1..2.72): the hidden faces under the walls
  still get lightmap texels and the wall bottoms are coplanar with the floor top (hidden, so no visible z-fight).
  g3_export: delete faces fully covered by walls (or just accept ~3% lightmap waste).
- Window_Glass is 12 closed thin boxes (2 glass surfaces per pane in the view): fine for Cycles; in Unity that is double transparent
  overdraw on the biggest surface in view. g3_export: export only the inner face of each pane (or a single quad per pane).

## 5. Things that are already right

- Boolean-free, all-quad, manifold generators (`solid_mesh`) in build_room.py and door.py: clean for lightmap UVs and colliders.
- Idempotent scripts with stable names and no orphan data.
- Metric units, scale 1.0, z-up; FBX + Unity axis baking gives correct transforms without -90 deg roots.
- Pivots of chairs and door already where physics needs them.

## 6. Not measured yet (phase 2)

Wave-2 objects (Exterior, Room2, Trim, Kitchen, Deskprops, Doorend) and the final shader/light setup. Phase 2 reruns
`audit_scene.py` on the integrated main.blend copy and on the exported FBX, and pins the Unity scripts to the exported names.
