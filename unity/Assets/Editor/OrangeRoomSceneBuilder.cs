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
    const float LedIntensity = 3f, WindowIntensity = 2f;
    static readonly Color LedColor = new Color(1f, 0.94f, 0.88f);         // = Room_LED_* in Blender
    static readonly Color WindowColor = new Color(0.86f, 0.92f, 1f);      // = Room_Window_Daylight
    const float DoorMinAngle = -110f, DoorMaxAngle = 0f;                  // relative to the pose in the FBX; sign depends on hinge side
    const float TexelsPerUnit = 40f;                                      // lightmap density; hero props get x2 via scaleInLightmap
    const float SmallObject = 0.25f;                                      // static meshes smaller than this use probes, not lightmaps
    const float ProbeSpacing = 0.6f;
    static readonly float[] ProbeHeights = { 0.3f, 1.1f, 1.8f, 2.5f };
    const float PostExposure = -0.6f;                                     // EV; -0.6 = AgX curve match (unity/POSTFX.md) + your scene calibration
    const float FogDensity = 0.025f;                                      // ~2% at 6 m indoors, heavy on the trees outside

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
                r.receiveGI = small ? ReceiveGI.LightProbes : ReceiveGI.Lightmaps;
                if (!NoColliderPrefixes.Any(p => t.name.StartsWith(p)))
                    t.gameObject.AddComponent<MeshCollider>().sharedMesh = t.GetComponent<MeshFilter>().sharedMesh;
                if (t.name == "Floor" || t.name.EndsWith("_Floor"))
                {
                    MakeTeleportFloor(t.gameObject);
                    if (floor == null || t.name == "Floor") floor = t;   // spawn in room 1
                }
            }
            if (!exterior) RoomProbes(root, dynamic);
        }

        AddLights(roots);
        Environment();
        Lighting();
        PostVolume();
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
        var b = WorldBounds(root, r => !UnderAny(r.transform, dynamic));
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
        var parent = new GameObject("Lights").transform;
        foreach (var root in roots)
        {
            if (root.name.Contains(ExteriorTag)) continue;
            var center = WorldBounds(root, r => true).center;
            foreach (var r in root.GetComponentsInChildren<MeshRenderer>(true))
            {
                string n = r.name.ToLowerInvariant();
                var b = r.bounds;
                if (n.Contains("led") && (n.Contains("panel") || n.StartsWith("room3_led_")))   // Room3_LED_NN = hall fittings
                    AreaLight(parent, placed, r.name, b.center + Vector3.down * 0.02f, Vector3.down,
                         new Vector2(Mathf.Max(b.size.x, 0.3f), Mathf.Max(b.size.z, 0.3f)), LedColor, LedIntensity);
                else if ((n.Contains("window") || n.Contains("winglass")) && n.Contains("glass"))   // Room2_WinGlass_*
                {
                    var d = center - b.center;   // windows are axis aligned: snap to the dominant horizontal axis
                    var dir = Mathf.Abs(d.x) > Mathf.Abs(d.z) ? new Vector3(Mathf.Sign(d.x), 0, 0) : new Vector3(0, 0, Mathf.Sign(d.z));
                    float w = dir.x != 0 ? b.size.z : b.size.x;
                    AreaLight(parent, placed, r.name, b.center + dir * 0.05f, dir, new Vector2(w, b.size.y), WindowColor, WindowIntensity);
                }
            }
        }
        if (placed.Count == 0) Debug.LogWarning("[OrangeRoom] No '*LED*Panel*' or '*Window*Glass*' meshes found: no lights placed.");
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
        sky.SetFloat("_AtmosphereThickness", 1.6f);
        sky.SetColor("_SkyTint", new Color(0.62f, 0.64f, 0.67f));
        sky.SetColor("_GroundColor", new Color(0.30f, 0.30f, 0.28f));
        sky.SetFloat("_Exposure", 0.8f);
        Save(sky, Settings + "/OrangeRoom_Sky.mat");
        RenderSettings.skybox = sky;
        RenderSettings.sun = null;
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
            lightmapper = LightingSettings.Lightmapper.ProgressiveGPU,   // falls back to CPU if the 4 GB GPU runs out
            lightmapResolution = TexelsPerUnit,
            lightmapMaxSize = 2048,
            lightmapPadding = 4,
            directionalityMode = LightmapsMode.CombinedDirectional,
            mixedBakeMode = MixedLightingMode.Shadowmask,
            ao = true,
            aoMaxDistance = 0.5f,
            directSampleCount = 32,
            indirectSampleCount = 512,
            environmentSampleCount = 256,
            maxBounces = 3,
            autoGenerate = false,
        };
        Save(s, Settings + "/OrangeRoom.lighting");
        Lightmapping.lightingSettings = s;
    }

    static void PostVolume()
    {
        var profile = ScriptableObject.CreateInstance<VolumeProfile>();
        Save(profile, Settings + "/OrangeRoom_Post.asset");
        // unity/POSTFX.md, XR profile: ACES + exposure/contrast fitted to Blender AgX MHC, white balance fitted to the
        // Blender grade; no vignette / grain / CA in a headset.
        var tm = profile.Add<Tonemapping>();
        tm.mode.Override(TonemappingMode.ACES);
        var ca = profile.Add<ColorAdjustments>();
        ca.postExposure.Override(PostExposure);
        ca.contrast.Override(-12f);
        var wb = profile.Add<WhiteBalance>();
        wb.temperature.Override(-34f);
        wb.tint.Override(-13f);
        var bloom = profile.Add<Bloom>();
        bloom.threshold.Override(0f);
        bloom.intensity.Override(0.03f);
        bloom.scatter.Override(0.8f);
        foreach (var c in profile.components) AssetDatabase.AddObjectToAsset(c, profile);   // persist as sub-assets
        EditorUtility.SetDirty(profile);
        AssetDatabase.SaveAssets();

        var v = new GameObject("PostProcess").AddComponent<Volume>();
        v.isGlobal = true;
        v.sharedProfile = profile;
    }

    static void XRRig(Transform floor)
    {
        var path = AssetDatabase.FindAssets("XR Interaction Setup t:Prefab").Select(AssetDatabase.GUIDToAssetPath)
            .FirstOrDefault(p => Path.GetFileName(p) == "XR Interaction Setup.prefab");
        if (path == null)
        {
            Debug.LogError("[OrangeRoom] XRI Starter Assets not imported (Package Manager > XR Interaction Toolkit > Samples > Starter Assets). Re-run after.");
            return;
        }
        var rig = (GameObject)PrefabUtility.InstantiatePrefab(AssetDatabase.LoadAssetAtPath<GameObject>(path));
        if (floor)
        {
            var b = floor.GetComponent<Renderer>().bounds;
            rig.transform.position = new Vector3(b.center.x, b.max.y, b.center.z);
        }
        foreach (var cam in rig.GetComponentsInChildren<Camera>(true))
        {
            cam.nearClipPlane = 0.05f;
            cam.GetUniversalAdditionalCameraData().renderPostProcessing = true;
        }
    }

    // ---------- helpers ----------

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
