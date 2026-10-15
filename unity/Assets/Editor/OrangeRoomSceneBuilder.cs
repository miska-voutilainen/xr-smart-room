// Menu "OrangeRoom/Build Scene": builds Assets/Scenes/OrangeRoom.unity from every model in Assets/Models.
// Re-run any time (it recreates the scene and its settings assets). Then Window > Rendering > Lighting > Generate Lighting.
// Unity 2022.3.76f1, URP 14, XR Interaction Toolkit 3.5.0 (namespaces below are the 3.x ones).
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;
using UnityEngine.XR.Interaction.Toolkit;
using UnityEngine.XR.Interaction.Toolkit.Interactables;
using UnityEngine.XR.Interaction.Toolkit.Locomotion.Teleportation;

public static class OrangeRoomSceneBuilder
{
    // ---------- export contract: object names from the Blender scene (phase 2: match unity/export_unity.py) ----------
    const string DoorLeaf = "Door_Leaf";                                  // pivot on the hinge axis
    static readonly string[] ChairPrefixes = { "Chair_" };
    static readonly string[] GrabParts = { "Remote", "Cup", "Mug", "Bottle", "RobotCam" };   // substring match
    static readonly string[] NoColliderPrefixes = { "Door_" };            // frame/threshold would fight the hinged leaf
    const string ExteriorTag = "Exterior";                                // model file / root name containing this

    // ---------- calibration knobs (Blender watts do not convert; tune against the Cycles render) ----------
    const float LedIntensity = 8f, WindowIntensity = 4f;              // Quest build: matched to renders/v2 mean brightness (was 3 / 2)
    const float LabLedBaked = 0.7f;                                       // lab (Room2) LEDs: share baked; CeilingLights adds the rest at runtime
    const float LabRealtime = 8f;                                         // CeilingLights.intensity (spots); was 3 on the old point lights
    const float LabWindow = 0.6f;                                         // lab windows: blinds mostly down in the reference, daylight only fills in
    const float HallLedBoost = 1.5f;                                      // hall (Room3) read darker than the rooms
    // Room1 vs renders/v2/best/02_Cam_122209 (Ref_02 snapshot): the vertical Lambertian window rect lit the ceiling as much
    // as the walls (Blender: ceiling ~0.55 x wall, overcast sky comes in from above) and the floor least (Blender: most).
    const float WindowTilt = 45f;                                         // Room1 window light aims down; 45 = CIE overcast shape (direct-light model)
    const float Room1Window = 1.3f;                                       // the tilted rect loses ~25 % to the sill/reveal: same floor light as before
    const float Room1Led = 1.3f;                                          // Blender panels (150 deg spread) put more on the floor than a Lambertian rect
    static readonly Color LedColor = new Color(1f, 0.94f, 0.88f);         // = Room_LED_* in Blender
    static readonly Color WindowColor = new Color(0.93f, 0.95f, 0.97f);   // was (0.86, 0.92, 1): Room1 ceiling read blue (B/Y 1.08 vs Blender 0.85)
    const float DoorMinAngle = -110f, DoorMaxAngle = 0f;                  // relative to the pose in the FBX; sign depends on hinge side
    const float TexelsPerUnit = 30f;                                      // lightmap density; hero props get x2 via scaleInLightmap
    const float SmallObject = 0.25f;                                      // static meshes smaller than this use probes, not lightmaps
    const float ProbeSpacing = 0.6f;
    static readonly float[] ProbeHeights = { 0.3f, 1.1f, 1.8f, 2.5f };
    const float FogDensity = 0.015f;                                      // <1% at 6 m, ~12% at 24 m (hall haze at 0.025); still heavy on the trees

    const string Scenes = "Assets/Scenes", Settings = "Assets/Settings";
    const string ScenePath = Scenes + "/OrangeRoom.unity";

    const StaticEditorFlags StaticAll = StaticEditorFlags.ContributeGI | StaticEditorFlags.OccluderStatic |
        StaticEditorFlags.OccludeeStatic | StaticEditorFlags.BatchingStatic | StaticEditorFlags.ReflectionProbeStatic;

    [MenuItem("OrangeRoom/Build Scene")]
    static void Build()
    {
        var rp = AssetDatabase.FindAssets("t:UniversalRenderPipelineAsset")
            .Select(g => AssetDatabase.LoadAssetAtPath<UniversalRenderPipelineAsset>(AssetDatabase.GUIDToAssetPath(g)))
            .FirstOrDefault();
        if (rp == null)
        {
            Debug.LogError("[OrangeRoom] No URP asset. Assets > Create > Rendering > URP Asset (with Universal Renderer), then re-run.");
            return;
        }
        GraphicsSettings.defaultRenderPipeline = rp;
        var rpo = new SerializedObject(rp);   // Light Layers (no setter): keeps the lab ceiling lights out of Room1/hall
        rpo.FindProperty("m_SupportsLightLayers").boolValue = true;
        rpo.ApplyModifiedProperties();
        AssetDatabase.SaveAssets();   // SaveScene does not write the URP asset; the APK reads it from disk
        PlayerSettings.colorSpace = ColorSpace.Linear;
        Folder(Scenes);
        Folder(Settings);

        var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
        var roots = AssetDatabase.FindAssets("t:Model", new[] { "Assets/Models" })
            .Select(g => (GameObject)PrefabUtility.InstantiatePrefab(
                AssetDatabase.LoadAssetAtPath<GameObject>(AssetDatabase.GUIDToAssetPath(g))))
            .ToList();
        if (roots.Count == 0) { Debug.LogError("[OrangeRoom] No models in Assets/Models."); return; }

        Transform floor = null;
        foreach (var root in roots)
        {
            bool exterior = root.name.Contains(ExteriorTag);
            var dynamic = new HashSet<Transform>();
            foreach (var t in root.GetComponentsInChildren<Transform>(true))   // parents before children
            {
                if (UnderAny(t, dynamic)) continue;                                // one Rigidbody per prop
                if (t.name == DoorLeaf) { MakeDoor(t.gameObject); dynamic.Add(t); }
                else if (ChairPrefixes.Any(p => t.name.StartsWith(p))) { MakeGrab(t.gameObject, 5f); dynamic.Add(t); }
                else if (GrabParts.Any(p => t.name.Contains(p))) { MakeGrab(t.gameObject, 0.3f); dynamic.Add(t); }
            }
            foreach (var t in root.GetComponentsInChildren<Transform>(true))
            {
                if (UnderAny(t, dynamic)) continue;
                var r = t.GetComponent<MeshRenderer>();
                bool glass = r && r.sharedMaterials.Any(m => m && m.name.Contains("Glass"));
                var flags = exterior ? StaticEditorFlags.BatchingStatic | StaticEditorFlags.OccludeeStatic
                          : glass ? StaticAll & ~StaticEditorFlags.OccluderStatic : StaticAll;
                GameObjectUtility.SetStaticEditorFlags(t.gameObject, flags);
                if (!r || exterior) continue;

                if (glass) r.shadowCastingMode = ShadowCastingMode.Off;   // let window light into the bake
                bool small = r.bounds.size.x < SmallObject && r.bounds.size.y < SmallObject && r.bounds.size.z < SmallObject;
                bool decal = t.name.Contains("Poster");   // Room3_Posters lightmap baked ~20 % black texels
                r.receiveGI = small || decal ? ReceiveGI.LightProbes : ReceiveGI.Lightmaps;
                if (Ext(r)) r.scaleInLightmap = 0.1f;   // 42 m backdrop/lawn/treeline took half of the atlas
                if (!NoColliderPrefixes.Any(p => t.name.StartsWith(p)))
                    t.gameObject.AddComponent<MeshCollider>().sharedMesh = t.GetComponent<MeshFilter>().sharedMesh;
                if (t.name == "Floor" || t.name.EndsWith("_Floor"))
                {
                    MakeTeleportFloor(t.gameObject);
                    if (floor == null || t.name == "Floor") floor = t;   // spawn in room 1
                }
            }
            if (!exterior) RoomProbes(root, dynamic);
            if (root.name.StartsWith("Room2"))   // lab: also receives the realtime ceiling lights (rendering layer 2)
                foreach (var r in root.GetComponentsInChildren<Renderer>(true)) r.renderingLayerMask |= 2;
        }

        AddLights(roots);
        Environment();
        Lighting();
        XRRig(floor);

        EditorSceneManager.SaveScene(scene, ScenePath);
        EditorBuildSettings.scenes = new[] { new EditorBuildSettingsScene(ScenePath, true) };
        Debug.Log($"[OrangeRoom] Scene built: {ScenePath} from {roots.Count} model(s). Next: Lighting > Generate Lighting.");
    }

    // ---------- interactables ----------

    static void MakeGrab(GameObject go, float mass)
    {
        foreach (var mf in go.GetComponentsInChildren<MeshFilter>(true))
        {
            var mc = mf.gameObject.AddComponent<MeshCollider>();
            mc.sharedMesh = mf.sharedMesh;
            mc.convex = true;   // Rigidbody needs convex
        }
        var rb = go.AddComponent<Rigidbody>();
        rb.mass = mass;
        rb.interpolation = RigidbodyInterpolation.Interpolate;
        rb.collisionDetectionMode = CollisionDetectionMode.ContinuousDynamic;
        var g = go.AddComponent<XRGrabInteractable>();
        g.movementType = XRBaseInteractable.MovementType.VelocityTracking;   // respects walls/desk
        g.useDynamicAttach = true;                                          // hold it where you grabbed it
        g.interactionLayers = InteractionLayerMask.GetMask("Default");      // not grabbable by the teleport ray
    }

    static void MakeDoor(GameObject leaf)
    {
        var box = leaf.AddComponent<BoxCollider>();   // glass/hardware children ride along
        var mb = leaf.GetComponent<MeshFilter>().sharedMesh.bounds;
        box.center = mb.center;
        box.size = mb.size;
        var rb = leaf.AddComponent<Rigidbody>();
        rb.mass = 25f;
        rb.angularDrag = 4f;
        rb.useGravity = false;
        var hinge = leaf.AddComponent<HingeJoint>();
        hinge.anchor = Vector3.zero;        // Blender origin sits on the hinge axis
        hinge.axis = Vector3.up;
        hinge.useLimits = true;
        hinge.limits = new JointLimits { min = DoorMinAngle, max = DoorMaxAngle };
        var g = leaf.AddComponent<XRGrabInteractable>();
        g.movementType = XRBaseInteractable.MovementType.VelocityTracking;
        g.trackRotation = false;            // hand position drives the swing, the joint does the rest
        g.throwOnDetach = false;
        g.useDynamicAttach = true;
        g.interactionLayers = InteractionLayerMask.GetMask("Default");
    }

    static void MakeTeleportFloor(GameObject go)
    {
        var area = go.AddComponent<TeleportationArea>();
        int tp = InteractionLayerMask.GetMask("Teleport");   // layer used by the Starter Assets teleport interactor
        if (tp != 0) area.interactionLayers = tp;
        else Debug.LogWarning("[OrangeRoom] Interaction layer 'Teleport' missing; import XRI Starter Assets and re-run.");
    }

    // ---------- lighting ----------

    static void RoomProbes(GameObject root, HashSet<Transform> dynamic)
    {
        var b = WorldBounds(root, r => !UnderAny(r.transform, dynamic) && !Ext(r));   // Room3: 30k probes over the backdrop otherwise
        if (b.size == Vector3.zero) return;
        var pos = new List<Vector3>();
        float x0 = b.min.x + 0.25f, x1 = b.max.x - 0.25f, z0 = b.min.z + 0.25f, z1 = b.max.z - 0.25f;
        for (float x = x0; x <= x1 + 1e-3f; x += ProbeSpacing)
            for (float z = z0; z <= z1 + 1e-3f; z += ProbeSpacing)
                foreach (var h in ProbeHeights)
                    if (b.min.y + h < b.max.y - 0.15f) pos.Add(new Vector3(x, b.min.y + h, z));
        // ponytail: plain box grid over the room bounds; hand-delete probes inside walls/cabinet if they leak

        var go = new GameObject(root.name + "_LightProbes");
        go.AddComponent<LightProbeGroup>().probePositions = pos.ToArray();

        var rp = new GameObject(root.name + "_ReflectionProbe").AddComponent<ReflectionProbe>();
        rp.transform.position = b.center;
        rp.mode = ReflectionProbeMode.Baked;
        rp.size = b.size;
        rp.boxProjection = true;
        rp.resolution = 256;
        rp.hdr = true;
        rp.blendDistance = 0.5f;
    }

    static void AddLights(List<GameObject> roots)
    {
        var placed = new List<Vector3>();
        var labPanels = new List<Renderer>();
        var parent = new GameObject("Lights").transform;
        foreach (var root in roots)
        {
            if (root.name.Contains(ExteriorTag)) continue;
            var center = WorldBounds(root, r => !Ext(r)).center;   // the backdrop pulled it outside: hall window light faced out
            foreach (var r in root.GetComponentsInChildren<MeshRenderer>(true))
            {
                string n = r.name.ToLowerInvariant();
                var b = r.bounds;
                if (n.Contains("led") && (n.Contains("panel") || n.Contains("diffuser") || n.StartsWith("room3_led_")))   // Room3_LED_NN = hall, Light_LED_Diffuser_N = Room1
                {
                    bool lab = n.StartsWith("room2_");
                    if (lab)
                    {
                        labPanels.Add(r);   // tinted at runtime via MaterialPropertyBlock: keep it out of static batches
                        GameObjectUtility.SetStaticEditorFlags(r.gameObject, GameObjectUtility.GetStaticEditorFlags(r.gameObject) & ~StaticEditorFlags.BatchingStatic);
                    }
                    AreaLight(parent, placed, r.name, b.center + Vector3.down * 0.02f, Vector3.down,
                         new Vector2(Mathf.Max(b.size.x, 0.3f), Mathf.Max(b.size.z, 0.3f)), LedColor,
                         LedIntensity * (lab ? LabLedBaked : n.StartsWith("room3_") ? HallLedBoost : Room1Led));
                }
                else if ((n.Contains("window") || n.Contains("winglass")) && n.Contains("glass"))   // Room2_WinGlass_*
                {
                    var d = center - b.center;   // windows are axis aligned: snap to the dominant horizontal axis
                    var dir = Mathf.Abs(d.x) > Mathf.Abs(d.z) ? new Vector3(Mathf.Sign(d.x), 0, 0) : new Vector3(0, 0, Mathf.Sign(d.z));
                    float w = dir.x != 0 ? b.size.z : b.size.x;
                    bool room1 = !n.StartsWith("room2_") && !n.StartsWith("room3_");   // Window_Glass
                    var aim = room1 ? Vector3.Slerp(dir, Vector3.down, WindowTilt / 90f) : dir;
                    // tilting leans the top edge into the room: slide out so it stays at the glass (no hot spot on the ceiling)
                    var pos = b.center + dir * 0.05f - (room1 ? dir * (b.size.y * 0.5f * Mathf.Sin(WindowTilt * Mathf.Deg2Rad)) : Vector3.zero);
                    AreaLight(parent, placed, r.name, pos, aim, new Vector2(w, b.size.y), WindowColor,
                        WindowIntensity * (n.StartsWith("room2_") ? LabWindow : room1 ? Room1Window : 1f));
                }
            }
        }
        if (placed.Count == 0) Debug.LogWarning("[OrangeRoom] No '*LED*Panel*' or '*Window*Glass*' meshes found: no lights placed.");
        if (labPanels.Count > 0) LabCeiling(parent, labPanels);
    }

    // Runtime part of the lab ceiling lights (dimmer brightness, DALI colour): two shadowless realtime spot lights over
    // the two halves of the LED panel area. Two, not one per panel: the Quest URP asset allows 4 lights per object.
    // Spots aimed down, not points: a point 0.3 m under the ceiling blows out a disc on it (~I/0.09).
    static void LabCeiling(Transform parent, List<Renderer> panels)
    {
        var b = panels[0].bounds;
        foreach (var p in panels) b.Encapsulate(p.bounds);
        var along = b.size.x > b.size.z ? new Vector3(b.extents.x * 0.5f, 0, 0) : new Vector3(0, 0, b.extents.z * 0.5f);
        var go = new GameObject("Lab_CeilingLights");
        go.transform.SetParent(parent);
        var lights = new List<Light>();
        foreach (var offset in new[] { -along, along })
        {
            var l = new GameObject("Lab_Ceiling_Realtime").AddComponent<Light>();
            l.transform.SetParent(go.transform);
            l.transform.SetPositionAndRotation(new Vector3(b.center.x, b.min.y - 0.3f, b.center.z) + offset, Quaternion.Euler(90f, 0f, 0f));   // +Z down
            l.type = LightType.Spot;
            l.spotAngle = 150f;
            l.innerSpotAngle = 90f;
            l.lightmapBakeType = LightmapBakeType.Realtime;
            l.shadows = LightShadows.None;
            l.range = Mathf.Max(b.size.x, b.size.z) * 0.9f + 2f;
            l.GetUniversalAdditionalLightData().renderingLayers = 2;   // lab renderers only (no shadows: would light Room1/hall through the walls)
            l.color = LedColor;
            lights.Add(l);
        }
        var c = go.AddComponent<CeilingLights>();
        c.lights = lights.ToArray();
        c.panels = panels.ToArray();
        c.intensity = LabRealtime;
        foreach (var l in lights) l.intensity = c.intensity;   // edit-mode look (snapshots) = full brightness
        Debug.Log($"[OrangeRoom] Lab ceiling: {panels.Count} LED panels, realtime lights at {lights[0].transform.position} / {lights[1].transform.position}");
    }

    static void AreaLight(Transform parent, List<Vector3> placed, string src, Vector3 pos, Vector3 dir, Vector2 size, Color c, float intensity)
    {
        if (placed.Any(p => (p - pos).sqrMagnitude < 0.04f)) return;   // one light per panel even if it is split in parts
        placed.Add(pos);
        var go = new GameObject("Light_" + src);
        go.transform.SetParent(parent);
        go.transform.SetPositionAndRotation(pos, Quaternion.LookRotation(dir, Mathf.Abs(dir.y) > 0.9f ? Vector3.forward : Vector3.up));
        var l = go.AddComponent<Light>();
        l.type = LightType.Rectangle;            // area light: baked only, emits along +Z
        l.lightmapBakeType = LightmapBakeType.Baked;
        l.areaSize = size;
        l.color = c;
        l.intensity = intensity;
        l.shadows = LightShadows.Soft;
    }

    static void Environment()
    {
        var sky = new Material(Shader.Find("Skybox/Procedural")) { name = "OrangeRoom_Sky" };
        sky.SetFloat("_SunDisk", 0f);                       // overcast: no sun disc (KeywordEnum: float + keyword)
        sky.EnableKeyword("_SUNDISK_NONE");
        sky.DisableKeyword("_SUNDISK_HIGH_QUALITY");
        sky.SetFloat("_AtmosphereThickness", 1f);           // 1.6 read as a sunset band through the windows
        sky.SetColor("_SkyTint", new Color(0.5f, 0.5f, 0.5f));          // neutral: the cool tint made the Quest build blue
        sky.SetColor("_GroundColor", new Color(0.30f, 0.30f, 0.28f));
        sky.SetFloat("_Exposure", 0.8f);
        Save(sky, Settings + "/OrangeRoom_Sky.mat");
        RenderSettings.skybox = sky;
        var sun = new GameObject("Sun").AddComponent<Light>();          // daylight through the windows; null sun = orange horizon
        sun.type = LightType.Directional;
        sun.transform.rotation = Quaternion.Euler(40f, 200f, 0f);
        sun.intensity = 1.2f;
        sun.color = new Color(1f, 0.97f, 0.92f);
        sun.lightmapBakeType = LightmapBakeType.Baked;
        sun.shadows = LightShadows.Soft;
        RenderSettings.sun = sun;
        RenderSettings.ambientMode = AmbientMode.Skybox;
        RenderSettings.fog = true;
        RenderSettings.fogMode = FogMode.ExponentialSquared;
        RenderSettings.fogDensity = FogDensity;
        RenderSettings.fogColor = new Color(0.62f, 0.64f, 0.66f);
    }

    static void Lighting()
    {
        var s = new LightingSettings
        {
            name = "OrangeRoom_Lighting",
            bakedGI = true,
            realtimeGI = false,
            lightmapper = LightingSettings.Lightmapper.ProgressiveCPU,   // the 4 GB RTX 3050 is below the GPU lightmapper minimum
            denoiserTypeDirect = LightingSettings.DenoiserType.OpenImage,
            denoiserTypeIndirect = LightingSettings.DenoiserType.OpenImage,
            denoiserTypeAO = LightingSettings.DenoiserType.OpenImage,
            lightmapCompression = LightmapCompression.None,            // Android RGBM + ASTC broke walls into pink/green blocks; ~16 MB per 2048 map
            lightmapResolution = TexelsPerUnit,
            lightmapMaxSize = 2048,
            lightmapPadding = 4,
            directionalityMode = LightmapsMode.CombinedDirectional,
            mixedBakeMode = MixedLightingMode.Shadowmask,
            ao = true,
            aoMaxDistance = 0.5f,
            directSampleCount = 32,
            indirectSampleCount = 192,                                  // + denoiser
            environmentSampleCount = 128,
            maxBounces = 3,
            autoGenerate = false,
        };
        Save(s, Settings + "/OrangeRoom.lighting");
        Lightmapping.lightingSettings = s;
    }

    static void XRRig(Transform floor)
    {
        // XRI 3.x Starter Assets ship "XR Origin (XR Rig)" (with its Input Action Manager); "XR Interaction Setup" was the 2.x name.
        // The Hands Interaction Demo's "XR Origin Hands (XR Rig)" is a variant of it that adds tracked hands (pinch/poke), so prefer it
        var rigs = AssetDatabase.FindAssets("XR Origin t:Prefab").Select(AssetDatabase.GUIDToAssetPath).ToList();
        var path = rigs.FirstOrDefault(p => Path.GetFileName(p) == "XR Origin Hands (XR Rig).prefab")
                ?? rigs.FirstOrDefault(p => Path.GetFileName(p) == "XR Origin (XR Rig).prefab");
        if (path == null)
        {
            Debug.LogError("[OrangeRoom] XRI Starter Assets not imported (Package Manager > XR Interaction Toolkit > Samples > Starter Assets). Re-run after.");
            return;
        }
        new GameObject("XR Interaction Manager").AddComponent<XRInteractionManager>();
        var rig = (GameObject)PrefabUtility.InstantiatePrefab(AssetDatabase.LoadAssetAtPath<GameObject>(path));
        if (floor)
        {
            var b = floor.GetComponent<Renderer>().bounds;
            rig.transform.position = new Vector3(b.center.x, b.max.y, b.center.z);
        }
        ConfigureRig(rig);
    }

    public static void ConfigureRig(GameObject rig)
    {
        foreach (var cam in rig.GetComponentsInChildren<Camera>(true))
        {
            cam.nearClipPlane = 0.05f;
            // ponytail: no post on Quest (HDR off + MSAA: ACES/bloom only cost GPU and clip whites). Want the AgX look back?
            // supportsHDR + HDR colour grading on the URP asset, a Volume with Tonemapping, and profile it on the device.
            cam.GetUniversalAdditionalCameraData().renderPostProcessing = false;
        }
        // the IoT devices' hit zones are trigger colliders (XRDeviceInput); XRI rays ignore triggers by default
        foreach (var c in rig.GetComponentsInChildren<UnityEngine.XR.Interaction.Toolkit.Interactors.Casters.CurveInteractionCaster>(true))
            c.raycastTriggerInteraction = QueryTriggerInteraction.Collide;
        foreach (var r in rig.GetComponentsInChildren<UnityEngine.XR.Interaction.Toolkit.Interactors.XRRayInteractor>(true))
            r.raycastTriggerInteraction = QueryTriggerInteraction.Collide;
    }

    // ---------- helpers ----------

    static bool Ext(Renderer r) => r.name.Contains("_Ext_");   // Room3_Ext_Backdrop/Lawn/Treeline: outside, under a room root

    static bool UnderAny(Transform t, HashSet<Transform> set)
    {
        for (; t; t = t.parent) if (set.Contains(t)) return true;
        return false;
    }

    static Bounds WorldBounds(GameObject root, System.Func<Renderer, bool> keep)
    {
        var rs = root.GetComponentsInChildren<Renderer>(true).Where(keep).ToList();
        if (rs.Count == 0) return default;
        var b = rs[0].bounds;
        foreach (var r in rs) b.Encapsulate(r.bounds);
        return b;
    }

    static void Folder(string path)
    {
        if (!AssetDatabase.IsValidFolder(path)) AssetDatabase.CreateFolder("Assets", Path.GetFileName(path));
    }

    static void Save(Object o, string path)
    {
        AssetDatabase.DeleteAsset(path);   // idempotent re-run
        AssetDatabase.CreateAsset(o, path);
    }
}
