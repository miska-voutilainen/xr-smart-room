// Batch-mode pipeline for the Meta Quest 3S build (Android, OpenXR). Unity 2022.3.62f3 (Personal), URP 14, OpenXR 1.17, XRI 3.5.
// Each step is its own editor launch (the input backend switch needs a restart). Needs the XRI Starter Assets sample
// in Assets/Samples (committed). Each step throws on failure so the batch run exits non-zero:
//   unity run <unity dir> -- -buildTarget Android -executeMethod OrangeRoomQuest.<Step> -logFile <log>
//   Setup -> Scene -> Bake -> Snapshots -> Apk
// Same steps by hand: menu OrangeRoom > Quest > ...
using System;
using System.IO;
using System.Linq;
using System.Reflection;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEditor.XR.Management;
using UnityEditor.XR.Management.Metadata;
using UnityEditor.XR.OpenXR.Features;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;
using UnityEngine.XR.Interaction.Toolkit;
using UnityEngine.XR.Management;
using UnityEngine.XR.OpenXR;
using UnityEngine.XR.OpenXR.Features;

public static class OrangeRoomQuest
{
    const BuildTargetGroup Android = BuildTargetGroup.Android;
    const string ScenePath = "Assets/Scenes/OrangeRoom.unity";
    const string ApkPath = "Build/OrangeRoom-Quest3S.apk";
    const string SnapDir = "Build/Snapshots";
    // hands: XR Hands' HandTracking subsystem + MetaHandTrackingAim (pinch/aim), OpenXR Hand Interaction Profile
    static readonly string[] QuestFeatures = { "MetaQuestFeature", "OculusTouchControllerProfile", "MetaQuestTouchPlusControllerProfile",
        "HandTracking", "MetaHandTrackingAim", "HandInteractionProfile" };

    [MenuItem("OrangeRoom/Quest/1 Setup")]
    public static void Setup()
    {
        PlayerSettings.companyName = "OrangeTeam";
        PlayerSettings.productName = "OrangeRoom";
        PlayerSettings.SetApplicationIdentifier(Android, "com.orangeteam.orangeroom");
        PlayerSettings.colorSpace = ColorSpace.Linear;
        PlayerSettings.SetScriptingBackend(Android, ScriptingImplementation.IL2CPP);
        PlayerSettings.Android.targetArchitectures = AndroidArchitecture.ARM64;
        PlayerSettings.Android.minSdkVersion = AndroidSdkVersions.AndroidApiLevel32;
        PlayerSettings.SetUseDefaultGraphicsAPIs(BuildTarget.Android, false);
        PlayerSettings.SetGraphicsAPIs(BuildTarget.Android, new[] { GraphicsDeviceType.OpenGLES3 });
        PlayerSettings.defaultInterfaceOrientation = UIOrientation.LandscapeLeft;
        EditorUserBuildSettings.androidBuildSubtarget = MobileTextureSubtarget.ASTC;

        // Input handling = Both (no public API; takes effect on the next editor start)
        var so = new SerializedObject(AssetDatabase.LoadAllAssetsAtPath("ProjectSettings/ProjectSettings.asset")[0]);
        so.FindProperty("activeInputHandler").intValue = 2;
        so.ApplyModifiedProperties();

        // URP asset, Quest profile (README step 3): HDR off, MSAA 4x, no depth/opaque texture
        Folder("Assets/Settings");
        var data = ScriptableObject.CreateInstance<UniversalRendererData>();
        data.postProcessData = AssetDatabase.LoadAssetAtPath<PostProcessData>(
            "Packages/com.unity.render-pipelines.universal/Runtime/Data/PostProcessData.asset");
        Save(data, "Assets/Settings/OrangeRoom_Quest_Renderer.asset");
        ResourceReloader.ReloadAllNullIn(data, "Packages/com.unity.render-pipelines.universal");
        var rp = UniversalRenderPipelineAsset.Create(data);
        rp.supportsHDR = false;
        rp.msaaSampleCount = 4;
        rp.renderScale = 1f;
        rp.supportsCameraDepthTexture = false;
        rp.supportsCameraOpaqueTexture = false;
        Save(rp, "Assets/Settings/OrangeRoom_Quest_URP.asset");
        GraphicsSettings.defaultRenderPipeline = rp;
        for (int i = 0; i < QualitySettings.names.Length; i++)
        {
            QualitySettings.SetQualityLevel(i, false);
            QualitySettings.renderPipeline = rp;
        }
        Debug.Log($"[Quest] URP asset: shaders={data.shaders != null} xr={data.xrSystemData != null} post={data.postProcessData != null}");

        // XR Plug-in Management: OpenXR loader on Android
        Folder("Assets/XR");
        if (!EditorBuildSettings.TryGetConfigObject(XRGeneralSettings.k_SettingsKey, out XRGeneralSettingsPerBuildTarget perTarget))
        {
            perTarget = ScriptableObject.CreateInstance<XRGeneralSettingsPerBuildTarget>();
            AssetDatabase.CreateAsset(perTarget, "Assets/XR/XRGeneralSettingsPerBuildTarget.asset");
            EditorBuildSettings.AddConfigObject(XRGeneralSettings.k_SettingsKey, perTarget, true);
        }
        if (!perTarget.HasSettingsForBuildTarget(Android)) perTarget.CreateDefaultSettingsForBuildTarget(Android);
        if (!perTarget.HasManagerSettingsForBuildTarget(Android)) perTarget.CreateDefaultManagerSettingsForBuildTarget(Android);
        var general = perTarget.SettingsForBuildTarget(Android);
        general.InitManagerOnStart = true;
        bool loader = XRPackageMetadataStore.AssignLoader(general.AssignedSettings, typeof(OpenXRLoader).FullName, Android);
        Debug.Log($"[Quest] OpenXR loader on Android: {loader}");

        // OpenXR: Meta Quest support + Touch / Touch Plus controllers + hand tracking, single pass instanced
        FeatureHelpers.RefreshFeatures(Android);
        var ox = OpenXRSettings.GetSettingsForBuildTargetGroup(Android);
        ox.renderMode = OpenXRSettings.RenderMode.SinglePassInstanced;
        foreach (var f in ox.GetFeatures<OpenXRFeature>())
            if (QuestFeatures.Contains(f.GetType().Name))
            {
                f.enabled = true;
                EditorUtility.SetDirty(f);
                Debug.Log($"[Quest] OpenXR feature on: {f.GetType().Name}");
            }
        EditorUtility.SetDirty(ox);

        // XRI samples reserve interaction layer 31 for teleport (Starter Assets validation fix-it); Build Scene needs it
        // (InteractionLayerSettings is internal to XRI: reflection)
        var ils = typeof(InteractionLayerMask).Assembly.GetType("UnityEngine.XR.Interaction.Toolkit.InteractionLayerSettings");
        var inst = ils.GetProperty("Instance", BindingFlags.Static | BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.FlattenHierarchy).GetValue(null);
        ils.GetMethod("SetLayerNameAt", BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic).Invoke(inst, new object[] { 31, "Teleport" });
        EditorUtility.SetDirty((UnityEngine.Object)inst);
        Debug.Log($"[Quest] Teleport interaction layer mask: {InteractionLayerMask.GetMask("Teleport")}");
        AssetDatabase.SaveAssets();

        // a first import runs before URP's shaders exist (OrangeRoomImport then leaves FBX materials as imported)
        AssetDatabase.ImportAsset("Assets/Models", ImportAssetOptions.ImportRecursive | ImportAssetOptions.ForceUpdate);
        Debug.Log("[Quest] Setup done.");
    }

    [MenuItem("OrangeRoom/Quest/2 Scene")]
    public static void Scene()
    {
        // = Tools > IoT Digital Twin > Individual Devices, one at a time so one failing device doesn't block the rest
        int failed = 0;
        for (int id = 1; id <= 9; id++)
            try { IoTDigitalTwin.Editor.IoTAssetGenerator.GenerateDevice(id); }
            catch (Exception e) { failed++; Debug.LogError($"[Quest] IoT device {id} not generated: {e.Message}"); DumpLandmarks(id); }
        if (!EditorApplication.ExecuteMenuItem("OrangeRoom/Build Scene")) throw new Exception("[Quest] menu OrangeRoom/Build Scene missing");
        if (EditorSceneManager.GetActiveScene().path != ScenePath) throw new Exception("[Quest] Build Scene did not write " + ScenePath);
        if (!EditorApplication.ExecuteMenuItem("OrangeRoom/Place IoT Devices")) throw new Exception("[Quest] menu OrangeRoom/Place IoT Devices missing");
        EditorSceneManager.SaveScene(EditorSceneManager.GetActiveScene());
        // the builder and placer only log errors; fail the batch run instead of shipping a scene without rig or devices
        var iot = GameObject.Find("IoT_Devices");
        if (UnityEngine.Object.FindObjectOfType<Unity.XR.CoreUtils.XROrigin>() == null || UnityEngine.Object.FindObjectOfType<XRInteractionManager>() == null)
            throw new Exception("[Quest] scene has no XR Origin / XRInteractionManager (XRI Starter Assets sample missing?)");
        int placed = iot ? iot.GetComponentsInChildren<IoTDigitalTwin.IoTDevice>().Length : 0;
        if (failed > 0 || placed != 8 || UnityEngine.Object.FindObjectOfType<RoomBridge>() == null)
            throw new Exception($"[Quest] IoT devices: {failed} failed to generate, {placed}/8 placed, bridge {(UnityEngine.Object.FindObjectOfType<RoomBridge>() ? "ok" : "missing")}");
        Debug.Log("[Quest] Scene done.");
    }

    static void DumpLandmarks(int id)
    {
        if (id != 1) return;
        var fbx = AssetDatabase.LoadAssetAtPath<GameObject>("Assets/IoTDigitalTwin_Modular/01_Zigbee_Dimmer/Models/01_Zigbee_Rotary_Dimmer.fbx");
        var go = (GameObject)PrefabUtility.InstantiatePrefab(fbx);
        foreach (var t in go.GetComponentsInChildren<Transform>(true))
            Debug.Log($"[Quest] dimmer {t.name} pos={t.position.ToString("F5")} local={t.localPosition.ToString("F5")} parent={t.parent?.name}");
        UnityEngine.Object.DestroyImmediate(go);
    }

    // Env BAKE_TPU overrides the lightmap density (texels/m) for a quick first bake.
    [MenuItem("OrangeRoom/Quest/3 Bake")]
    public static void Bake()
    {
        EditorSceneManager.OpenScene(ScenePath);
        var s = Lightmapping.lightingSettings;
        float res = s.lightmapResolution;
        int indirect = s.indirectSampleCount;
        if (float.TryParse(Environment.GetEnvironmentVariable("BAKE_TPU"), out var tpu))
        {
            s.lightmapResolution = tpu;
            s.indirectSampleCount = Math.Min(s.indirectSampleCount, 128);
        }
        var t = DateTime.Now;
        try
        {
            if (!Lightmapping.Bake()) throw new Exception("[Quest] Lightmapping.Bake failed");
            StaticOcclusionCulling.Compute();
            EditorSceneManager.SaveScene(EditorSceneManager.GetActiveScene());
            Debug.Log($"[Quest] Bake done in {(DateTime.Now - t).TotalMinutes:F1} min, {s.lightmapper}, {s.lightmapResolution} texels/m, {LightmapSettings.lightmaps.Length} lightmaps.");
        }
        finally
        {
            // the override is for this bake only: keep the builder's values in OrangeRoom.lighting
            s.lightmapResolution = res;
            s.indirectSampleCount = indirect;
            EditorUtility.SetDirty(s);
            AssetDatabase.SaveAssets();
        }
    }

    // ponytail: one-off migration of an already baked scene to the hands rig without Build Scene (which drops the lightmaps).
    // A fresh Build Scene picks the hands rig by itself (OrangeRoomSceneBuilder.XRRig); delete this once the scene is rebuilt.
    [MenuItem("OrangeRoom/Quest/Swap To Hands Rig")]
    public static void HandsRig()
    {
        var scene = EditorSceneManager.OpenScene(ScenePath);
        var path = AssetDatabase.FindAssets("XR Origin t:Prefab").Select(AssetDatabase.GUIDToAssetPath)
            .FirstOrDefault(p => Path.GetFileName(p) == "XR Origin Hands (XR Rig).prefab")
            ?? throw new Exception("[Quest] XR Origin Hands (XR Rig).prefab missing (XRI Hands Interaction Demo sample)");
        var old = UnityEngine.Object.FindObjectOfType<Unity.XR.CoreUtils.XROrigin>() ?? throw new Exception("[Quest] scene has no XR Origin");
        var rig = (GameObject)PrefabUtility.InstantiatePrefab(AssetDatabase.LoadAssetAtPath<GameObject>(path), scene);
        rig.transform.SetPositionAndRotation(old.transform.position, old.transform.rotation);
        rig.transform.SetSiblingIndex(old.transform.GetSiblingIndex());
        UnityEngine.Object.DestroyImmediate(old.gameObject);
        OrangeRoomSceneBuilder.ConfigureRig(rig);
        EditorSceneManager.SaveScene(scene);
        Debug.Log($"[Quest] Hands rig in scene: {path}");
    }

    // Eye-height views for a texture/lighting check without a headset: Build/Snapshots/*.png
    [MenuItem("OrangeRoom/Quest/4 Snapshots")]
    public static void Snapshots()
    {
        EditorSceneManager.OpenScene(ScenePath);
        Directory.CreateDirectory(SnapDir);
        var cam = new GameObject("SnapCam").AddComponent<Camera>();
        cam.fieldOfView = 90f;
        cam.nearClipPlane = 0.05f;
        cam.GetUniversalAdditionalCameraData().renderPostProcessing = false;   // same as the XR camera (OrangeRoomSceneBuilder.XRRig)
        var rt = new RenderTexture(1280, 720, 24, RenderTextureFormat.ARGB32, RenderTextureReadWrite.sRGB) { antiAliasing = 4 };
        cam.targetTexture = rt;
        cam.Render();   // warm-up: the first render after OpenScene missed the uncompressed lightmaps (black Room1_yaw000)

        foreach (var root in EditorSceneManager.GetActiveScene().GetRootGameObjects().Where(g => g.name.StartsWith("Room")))
        {
            var rs = root.GetComponentsInChildren<Renderer>();
            if (rs.Length == 0) continue;
            var b = rs[0].bounds;
            foreach (var r in rs) b.Encapsulate(r.bounds);
            var floor = rs.Where(r => r.name.Contains("Floor")).OrderByDescending(r => r.bounds.size.x * r.bounds.size.z).FirstOrDefault();
            if (floor) b = floor.bounds;   // room bounds can include props outside the walls
            var eye = new Vector3(b.center.x, (floor ? b.max.y : b.min.y) + 1.6f, b.center.z);
            for (int yaw = 0; yaw < 360; yaw += 90)
                Shot(cam, rt, $"{root.name}_yaw{yaw:000}", eye, Quaternion.Euler(0, yaw, 0));
        }
        // same poses as two renders/v2/best references (Blender (x,y,z) -> Unity (x,z,y)); vfov of the 4:3 render
        cam.fieldOfView = 55f;
        Shot(cam, rt, "Ref_10_Cam_hall_02", new Vector3(-0.997f, 1.333f, 0.6f), Quaternion.LookRotation(new Vector3(-0.974f, -0.084f, 0.21f)));
        Shot(cam, rt, "Ref_07_Cam_150435", new Vector3(0.407f, 1.57f, 1.312f), Quaternion.LookRotation(new Vector3(0.603f, -0.072f, 0.795f)));
        Shot(cam, rt, "Ref_02_Cam_122209", new Vector3(0.166f, 1.498f, 1.817f), Quaternion.LookRotation(new Vector3(0.993f, -0.067f, -0.094f)));   // Room1 lighting reference
        cam.fieldOfView = 90f;
        var iot = GameObject.Find("IoT_Devices");
        if (iot)
            foreach (Transform d in iot.transform)
                if (d.name != "Bridge") Shot(cam, rt, "IoT_" + d.name, d.position + d.forward * 0.8f, Quaternion.LookRotation(-d.forward));
        // Room1 device wall (Blender y = 2.50, devices x 2.5-4.0, TV x 4.25-5.3): whole wall, then the device grid up close
        Shot(cam, rt, "Wall_devices", new Vector3(3.9f, 1.5f, 0.6f), Quaternion.LookRotation(Vector3.forward));
        Shot(cam, rt, "Wall_devices_close", new Vector3(3.3f, 1.3f, 1.7f), Quaternion.LookRotation(Vector3.forward));
        UnityEngine.Object.DestroyImmediate(cam.gameObject);
        Debug.Log($"[Quest] Snapshots in {Path.GetFullPath(SnapDir)}");
    }

    static void Shot(Camera cam, RenderTexture rt, string name, Vector3 pos, Quaternion rot)
    {
        cam.transform.SetPositionAndRotation(pos, rot);
        cam.Render();
        RenderTexture.active = rt;
        var tex = new Texture2D(rt.width, rt.height, TextureFormat.RGB24, false);
        tex.ReadPixels(new Rect(0, 0, rt.width, rt.height), 0, 0);
        RenderTexture.active = null;
        File.WriteAllBytes(Path.Combine(SnapDir, name + ".png"), tex.EncodeToPNG());
        UnityEngine.Object.DestroyImmediate(tex);
    }

    [MenuItem("OrangeRoom/Quest/5 Build APK")]
    public static void Apk()
    {
        EditorSceneManager.OpenScene(ScenePath);
        if (Lightmapping.lightingDataAsset == null || LightmapSettings.lightmaps.Length == 0)
            throw new Exception("[Quest] scene has no baked lighting (all lights are baked-only): run Bake first");
        EditorUserBuildSettings.buildAppBundle = false;
        // Store builds: release keystore from env (kept outside the repo); without it Unity signs with the debug key.
        var ks = Environment.GetEnvironmentVariable("ORANGE_KEYSTORE");
        PlayerSettings.Android.useCustomKeystore = !string.IsNullOrEmpty(ks);
        if (PlayerSettings.Android.useCustomKeystore)
        {
            PlayerSettings.Android.keystoreName = ks;
            PlayerSettings.Android.keystorePass = PlayerSettings.Android.keyaliasPass = Environment.GetEnvironmentVariable("ORANGE_KEYSTORE_PASS");
            PlayerSettings.Android.keyaliasName = Environment.GetEnvironmentVariable("ORANGE_KEY_ALIAS");
        }
        if (int.TryParse(Environment.GetEnvironmentVariable("ORANGE_VERSION_CODE"), out var vc)) PlayerSettings.Android.bundleVersionCode = vc;
        PlayerSettings.Android.targetSdkVersion = AndroidSdkVersions.AndroidApiLevel34;
        PlayerSettings.Android.forceInternetPermission = true;   // RoomBridge: WebSocket to bridge/server.py on the lab Wi-Fi
        PlayerSettings.Android.preferredInstallLocation = AndroidPreferredInstallLocation.Auto;   // store: installLocation="auto"   // Meta Horizon Store: new apps must target API 34
        Directory.CreateDirectory(Path.GetDirectoryName(ApkPath));
        UnityEditor.Build.Reporting.BuildSummary r;
        try
        {
            r = BuildPipeline.BuildPlayer(new BuildPlayerOptions
            {
                scenes = new[] { ScenePath },
                locationPathName = ApkPath,
                target = BuildTarget.Android,
                targetGroup = Android,
            }).summary;
        }
        finally
        {
            // keystore path must not end up in ProjectSettings.asset (public repo)
            PlayerSettings.Android.useCustomKeystore = false;
            PlayerSettings.Android.keystoreName = PlayerSettings.Android.keyaliasName = "";
            AssetDatabase.SaveAssets();
        }
        Debug.Log($"[Quest] Build {r.result}: {r.outputPath} {r.totalSize / 1048576} MB, {r.totalErrors} errors, {r.totalTime}");
        if (r.result != UnityEditor.Build.Reporting.BuildResult.Succeeded) throw new Exception("[Quest] APK build failed");
    }

    static void Folder(string path)
    {
        if (!AssetDatabase.IsValidFolder(path)) AssetDatabase.CreateFolder("Assets", Path.GetFileName(path));
    }

    static void Save(UnityEngine.Object o, string path)
    {
        AssetDatabase.DeleteAsset(path);
        AssetDatabase.CreateAsset(o, path);
    }
}
