// Submission videos without a headset: one play-mode session records, per IoT device (01-09), two 1920x1080 clips into
// ../submission/<device>/:
//   vr_click.mp4   a scripted XR select on the device's hit zone: the same ControlDown/Up + RoomBridge.UserControl calls
//                  XRDeviceInput makes on a controller trigger (bridge offline = local twin, except 05: online, simulator)
//   real_click.mp4 the JSON lines the bridge sends when someone operates the real device, fed through RoomBridge.Parse +
//                  Apply (the path RoomBridge.Update takes for socket messages)
// plus 1080p room screenshots in ../submission/screenshots/. Frames go straight to ffmpeg (h264_nvenc) over a pipe.
//   python3 bridge/server.py --simulate &
//   ~/Unity/Hub/Editor/2022.3.62f3/Editor/Unity -batchmode -projectPath unity -executeMethod OrangeRoomClickClip.Run -logFile -
// Same play-mode driver as OrangeRoomBridgeCheck (no -quit; exits 0, or 1 if a clip's check failed).
using System;
using System.Collections;
using System.Collections.Generic;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Linq;
using IoTDigitalTwin;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering.Universal;
using Debug = UnityEngine.Debug;
using Object = UnityEngine.Object;

[InitializeOnLoad]
public static class OrangeRoomClickClip
{
    const string ScenePath = "Assets/Scenes/OrangeRoom.unity", Out = "../submission";
    const string Active = "ClickClip.Active", Failed = "ClickClip.Failed", Started = "ClickClip.Started";
    const double Timeout = 900, Fps = 30;
    const int W = 1920, H = 1080;

    static readonly Stack<IEnumerator> steps = new Stack<IEnumerator>();
    static double Now => EditorApplication.timeSinceStartup;
    static Camera cam; static RenderTexture rt; static Texture2D tex;
    static Process ffmpeg; static double t0; static int frames;
    static RoomBridge bridge;
    static LineRenderer ray; static GameObject dot;

    static OrangeRoomClickClip() { if (SessionState.GetBool(Active, false)) Hook(); }

    public static void Run()
    {
        SessionState.SetBool(Active, true);
        SessionState.SetBool(Failed, false);
        SessionState.SetFloat(Started, (float)Now);
        Hook();
        EditorSceneManager.OpenScene(ScenePath);
        EditorApplication.EnterPlaymode();
    }

    static void Hook()
    {
        EditorApplication.playModeStateChanged += s =>
        {
            if (s == PlayModeStateChange.EnteredPlayMode) steps.Push(Steps());
            else if (s == PlayModeStateChange.EnteredEditMode) Exit();
        };
        EditorApplication.update += Tick;
    }

    static void Tick()
    {
        if (Now - SessionState.GetFloat(Started, 0) > Timeout) { steps.Clear(); Fail($"timeout {Timeout} s"); Finish(); return; }
        if (steps.Count == 0) return;
        try
        {
            Capture();
            var top = steps.Peek();
            if (!top.MoveNext()) { steps.Pop(); if (steps.Count == 0) Finish(); }
            else if (top.Current is IEnumerator inner) steps.Push(inner);
        }
        catch (Exception e) { steps.Clear(); Fail(e.ToString()); StopVideo(); Finish(); }
    }

    // ponytail: one render per tick, repeated for every 1/30 s slot it covers, so clips keep wall-clock speed
    static void Capture()
    {
        if (ffmpeg == null) return;
        int due = (int)((Now - t0) * Fps) + 1;
        if (due <= frames) return;
        Grab();
        var raw = tex.GetRawTextureData();
        var s = ffmpeg.StandardInput.BaseStream;
        while (frames < due) { s.Write(raw, 0, raw.Length); frames++; }
    }

    static void Grab()
    {
        cam.Render();
        RenderTexture.active = rt;
        tex.ReadPixels(new Rect(0, 0, W, H), 0, 0);
        RenderTexture.active = null;
    }

    static void StartVideo(string path)
    {
        Directory.CreateDirectory(Path.GetDirectoryName(path));
        ffmpeg = Process.Start(new ProcessStartInfo("ffmpeg",
            $"-loglevel error -y -f rawvideo -pix_fmt rgb24 -s {W}x{H} -r {Fps} -i - -vf vflip -c:v h264_nvenc -preset p7 -rc vbr -cq 19 -pix_fmt yuv420p -movflags +faststart \"{Path.GetFullPath(path)}\"")
            { UseShellExecute = false, RedirectStandardInput = true });
        t0 = Now; frames = 0;
    }

    static void StopVideo()
    {
        if (ffmpeg == null) return;
        ffmpeg.StandardInput.Close();
        ffmpeg.WaitForExit(60000);
        ffmpeg = null;
    }

    static void Finish()
    {
        EditorApplication.update -= Tick;
        Debug.Log($"[ClickClip] DONE: {(SessionState.GetBool(Failed, false) ? "FAILED" : "all ok")}");
        if (EditorApplication.isPlaying) EditorApplication.isPlaying = false; else Exit();
    }

    static void Exit()
    {
        int code = SessionState.GetBool(Failed, false) ? 1 : 0;
        SessionState.EraseBool(Active);
        EditorApplication.delayCall += () => EditorApplication.Exit(code);
    }

    // ---------- clips ----------

    static IEnumerator Steps()
    {
        bridge = Object.FindObjectOfType<RoomBridge>();
        yield return Wait(0.5);   // after RoomBridge.Start, so its saved url doesn't override ours
        bridge.Disconnect();

        cam = new GameObject("ClipCam").AddComponent<Camera>();
        cam.fieldOfView = 70f;
        cam.nearClipPlane = 0.03f;
        cam.GetUniversalAdditionalCameraData().renderPostProcessing = false;   // same as the XR camera
        rt = new RenderTexture(W, H, 24, RenderTextureFormat.ARGB32, RenderTextureReadWrite.sRGB) { antiAliasing = 8 };
        cam.targetTexture = rt;
        tex = new Texture2D(W, H, TextureFormat.RGB24, false);
        cam.Render();   // warm-up (lightmaps), see OrangeRoomQuest.Snapshots

        ray = new GameObject("ClipRay").AddComponent<LineRenderer>();
        ray.material = new Material(Shader.Find("Universal Render Pipeline/Unlit"));
        ray.widthCurve = AnimationCurve.Linear(0, 0.005f, 1, 0.0015f);
        dot = GameObject.CreatePrimitive(PrimitiveType.Sphere);
        Object.Destroy(dot.GetComponent<Collider>());
        dot.transform.localScale = Vector3.one * 0.01f;
        dot.GetComponent<Renderer>().material = ray.material;
        ShowRay(false, Vector3.zero);

        if (Environment.GetEnvironmentVariable("CLIP") == "curtain") { yield return CurtainShowcase(); yield break; }
        if (Environment.GetEnvironmentVariable("CLIP") == "probe") { Probe(); yield break; }
        if (Environment.GetEnvironmentVariable("CLIP") == "switch") { yield return SwitchShowcase(); yield break; }
        yield return Screenshots();

        var dimmer = Object.FindObjectOfType<RotaryDimmer>(); var thermo = Object.FindObjectOfType<TemperatureLCD>();
        var zwave = Object.FindObjectOfType<TemperatureController>(); var camDev = Object.FindObjectOfType<SecurityCameraDevice>();
        var chain = Object.FindObjectOfType<AqaraChainController>(); var blind = Object.FindObjectOfType<RollerBlindDevice>();
        var unit = Object.FindObjectOfType<SiemensBACnetDevice>(); var speaker = Object.FindObjectOfType<NestSpeakerDevice>();
        var dali = Object.FindObjectOfType<DALILightingPanel>();

        // known start: lights on, room 22 C, nobody in, curtain open, speaker idle
        Feed("dimmer1", "on", "true"); Feed("dimmer1", "level", "80"); Feed("dali1", "all_on", "true"); Feed("dali1", "all_kelvin", "4000");
        Feed("room_sensor1", "temperature", "22"); Feed("room_sensor1", "status", "online"); Feed("camera1", "occupied", "false");
        Feed("room_sensor1", "alarm", "false"); Feed("curtain1", "position", "100"); Feed("speaker1", "state", "idle"); Feed("speaker1", "volume", "30");
        yield return Wait(2);

        // the device wall from the room: shows the device and the ceiling-light spill on the wall
        var wide = (new Vector3(3.6f, 1.55f, 0.75f), new Vector3(3.5f, 1.45f, 2.5f));

        // 01 dimmer: VR click on the knob toggles power -> ceiling lights; real: someone turns the H2 dimmer
        yield return Clip("01_Zigbee_Dimmer/vr_click", dimmer, Close(dimmer), Click(dimmer, "Knob", () => !dimmer.Power));
        Feed("dimmer1", "on", "false"); yield return Wait(1);
        yield return Clip("01_Zigbee_Dimmer/real_click", dimmer, wide, Feeds(() => !dimmer.Power || dimmer.Brightness < 0.99f,
            (0, "dimmer1", "on", "true"), (0, "dimmer1", "level", "20"), (0.6, "dimmer1", "level", "45"), (0.6, "dimmer1", "level", "70"), (0.6, "dimmer1", "level", "100")),
            () => dimmer.Power && dimmer.Brightness > 0.99f);

        // 02 T/H display: VR click Pair; real: room warms up
        yield return Clip("02_Zigbee_Temperature_Sensor/vr_click", thermo, Close(thermo), ClickAll(thermo));
        yield return Clip("02_Zigbee_Temperature_Sensor/real_click", thermo, Close(thermo), Feeds(null,
            (0, "room_sensor1", "temperature", "22"), (1, "room_sensor1", "temperature", "24"), (1, "room_sensor1", "humidity", "52"), (0.5, "room_sensor1", "temperature", "26.5")),
            () => Mathf.Abs(thermo.Temperature - 26.5f) < 0.01f);

        // 03 Z-Wave thermostat (no lab device): VR click on its keys; real: room_sensor1 temperature shows as its reading
        yield return Clip("03_ZWave_Thermostat/vr_click", zwave, Close(zwave), ClickAll(zwave));
        yield return Clip("03_ZWave_Thermostat/real_click", zwave, Close(zwave), Feeds(null,
            (0, "room_sensor1", "temperature", "26.5"), (1, "room_sensor1", "temperature", "24"), (1, "room_sensor1", "temperature", "20")), null);

        // 04 camera: VR click on the head powers it; real: a person walks in (occupied) then the alarm fires (floodlight)
        Feed("camera1", "occupied", "false"); Feed("room_sensor1", "alarm", "false");
        yield return Clip("04_Security_Camera/vr_click", camDev, Close(camDev), Click(camDev, "Head", () => camDev.Power));
        Feed("camera1", "occupied", "false"); yield return Wait(0.5);
        yield return Clip("04_Security_Camera/real_click", camDev, Close(camDev), Feeds(null,
            (0, "camera1", "occupied", "true"), (2.5, "room_sensor1", "alarm", "true")), () => camDev.Power && camDev.Floodlight);
        Feed("room_sensor1", "alarm", "false"); Feed("camera1", "occupied", "false");

        // 05 chain controller: VR hold on Lower, online -> curtain1.close to the simulator -> positions come back
        var curtainView = (new Vector3(3.55f, 1.6f, 1.15f), new Vector3(3.6f, 1.85f, 2.5f));
        yield return OnlineCurtainReset();
        yield return Clip("05_Aqara_Controller/vr_click", chain, curtainView, HoldLower(chain, blind), null);
        bridge.Disconnect(); Feed("curtain1", "position", "100"); yield return Wait(3);
        var down = Enumerable.Range(1, 10).Select(i => (0.5, "curtain1", "position", (100 - i * 10).ToString())).ToArray();
        yield return Clip("05_Aqara_Controller/real_click", chain, curtainView, Feeds(null, down), () => blind.TargetOpenPercent < 1);

        // 06 roller blind: VR click on the bottom rail sets the position (sent as set_position); real: same curtain run up
        yield return Clip("06_Roller_Blind/vr_click", blind, curtainView, DragBlind(blind), null);
        Feed("curtain1", "position", "0"); yield return Wait(3);
        var up = Enumerable.Range(1, 10).Select(i => (0.5, "curtain1", "position", (i * 10).ToString())).ToArray();
        yield return Clip("06_Roller_Blind/real_click", blind, curtainView, Feeds(null, up), () => blind.TargetOpenPercent > 99);

        // 07 Siemens room unit: VR click display/status; real: temperature and status from BACnet
        yield return Clip("07_Siemens_BACnet/vr_click", unit, Close(unit), ClickAll(unit));
        yield return Clip("07_Siemens_BACnet/real_click", unit, Close(unit), Feeds(null,
            (0, "room_sensor1", "status", "online"), (0, "room_sensor1", "temperature", "21"), (1.2, "room_sensor1", "temperature", "23"), (1.2, "room_sensor1", "temperature", "25")),
            () => Mathf.Abs(unit.DisplayValue - 25) < 0.01f);

        // 08 speaker: VR click on the top toggles play; real: someone starts music and turns it up
        Feed("speaker1", "state", "idle");
        yield return Clip("08_Nest_Speaker/vr_click", speaker, Close(speaker), Click(speaker, "Volume", () => speaker.Active));
        Feed("speaker1", "state", "idle"); yield return Wait(0.5);
        yield return Clip("08_Nest_Speaker/real_click", speaker, Close(speaker), Feeds(null,
            (0, "speaker1", "state", "playing"), (1, "speaker1", "volume", "50"), (0.8, "speaker1", "volume", "80")),
            () => speaker.Active && Mathf.Abs(speaker.Volume - 0.8f) < 0.01f);

        // 09 DALI panel: VR click on the panel; real: lights off on the panel, then on with cold white
        yield return Clip("09_DALI_Touchscreen/vr_click", dali, Close(dali), ClickAll(dali));
        Feed("dali1", "all_on", "true"); Feed("dali1", "all_kelvin", "2700"); yield return Wait(1);
        yield return Clip("09_DALI_Touchscreen/real_click", dali, wide, Feeds(null,
            (0, "dali1", "all_on", "false"), (2, "dali1", "all_on", "true"), (1.5, "dali1", "all_kelvin", "6500")),
            () => dali.Power && Mathf.Abs(dali.ColorTemperature - 6500) < 1);
    }

    // VR recreation of the lab video (30 s): look at the sensor and to the right, press Lower at 0:06, turn to the
    // curtain over ~2.5 s, the curtain closes from the top to 75 % closed at 0:30. CLIP=curtain, against a bridge whose
    // curtain moves at the real motor's speed (75 % in 24 s).
    static IEnumerator CurtainShowcase()
    {
        var chain = Object.FindObjectOfType<AqaraChainController>(); var blind = Object.FindObjectOfType<RollerBlindDevice>();
        var thermo = Object.FindObjectOfType<TemperatureLCD>();
        blind.percentPerSecond = 75f / 24f;   // ponytail: the real motor's speed, so local motion matches the bridge reports
        string position = "";
        bridge.Applied += (d, p, v) => { if (d == "curtain1" && p == "position") position = v; };
        bridge.url = Environment.GetEnvironmentVariable("BRIDGE_CHECK_URL") ?? "ws://127.0.0.1:8765";
        bridge.Connect();
        yield return Until(() => bridge.State == "online" && F(position) >= 100, 10, "bridge online, curtain open");
        blind.currentOpenPercent = 100;
        yield return Wait(1);

        var lower = Zone(chain, "Lower");
        var button = At(lower);
        var sensor = Bounds(thermo).center;
        var roller = blind.transform.position;
        var eye = new Vector3(button.x - 0.35f, 1.68f, button.z - 1.25f);
        var right = button + Vector3.right * 0.7f;
        var curtain = new Vector3(roller.x + 0.1f, roller.y - 0.35f, roller.z);
        (double t, Vector3 at)[] look = { (0, sensor), (1.8, sensor + Vector3.right * 0.15f), (3.4, right), (4.4, right), (5.4, button), (6.5, button), (9, curtain), (30, curtain) };
        cam.fieldOfView = 72f;

        StartVideo(Path.Combine(Out, "curtain_recreation", "vr_curtain_close.mp4"));
        bool pressed = false;
        while (Now - t0 < 30)
        {
            double t = Now - t0;
            int i = 0;
            while (i < look.Length - 2 && t > look[i + 1].t) i++;
            float k = Mathf.SmoothStep(0, 1, (float)((t - look[i].t) / (look[i + 1].t - look[i].t)));
            var at = Vector3.Lerp(look[i].at, look[i + 1].at, k);
            var sway = new Vector3(Mathf.PerlinNoise((float)t * 0.4f, 0) - 0.5f, Mathf.PerlinNoise(0, (float)t * 0.4f) - 0.5f, 0) * 0.03f;
            cam.transform.SetPositionAndRotation(eye + sway * 0.3f, Quaternion.LookRotation(at + sway - eye));
            if (t >= 4.6) ShowRay(pressed, button);
            if (!pressed && t >= 6)
            {   // trigger down on Lower: the XRDeviceInput calls -> {"device": "curtain1", "command": "close"}
                pressed = true;
                chain.ControlDown("Lower", new Vector2(.5f, .5f));
                bridge.UserControl(chain, "Lower", true);
                Debug.Log($"[ClickClip] curtain: Lower pressed at {t:0.00} s");
            }
            yield return null;
        }
        StopVideo();
        Debug.Log($"[ClickClip] curtain: {frames} frames, curtain1.position {position}, blind {blind.OpenPercent:0.0} %");
        if (!(F(position) < 35 && F(position) > 15)) Fail($"curtain should be ~25 % open at 0:30, bridge says {position}");
        chain.ControlUp("Lower", false, new Vector2(.5f, .5f));
        bridge.UserControl(chain, "Lower", false);   // -> stop
        yield return Wait(1);
    }

    // VR twin of the lab video (30 s), in the lab where it was filmed: the rocker switch on demo board 1 sits where the
    // real one is (the board's photo, x 0.567 / y 0.89), the right hand presses it once at 0:06, the rocker springs back,
    // the head turns to window N1 (2-3 s) and its roller blind closes from the top, following curtain1.position from
    // the bridge, to 75 % closed at 0:30. Blender (x, y, z) -> Unity (x, z, y), see OrangeRoomDevicePlacer.B2U.
    static IEnumerator SwitchShowcase()
    {
        // board 1: east(6.05) -> front face x = 5.5 + 0.15, u along -y from 6.05; photo u0..u1 = 0.10..1.60, z 0.89..1.91
        var face = new Vector3(5.65f, 1.91f - 0.89f * 1.02f, 6.05f - (0.10f + 0.567f * 1.50f));
        var white = new Material(Shader.Find("Universal Render Pipeline/Lit"));
        white.SetColor("_BaseColor", new Color(0.93f, 0.93f, 0.91f)); white.SetFloat("_Smoothness", 0.35f);
        var sw = new GameObject("Board1_RockerSwitch").transform;
        sw.position = face; sw.rotation = Quaternion.LookRotation(Vector3.left);   // forward = out of the board, into the room
        var plate = GameObject.CreatePrimitive(PrimitiveType.Cube); plate.transform.SetParent(sw, false);
        plate.transform.localScale = new Vector3(0.082f, 0.082f, 0.008f); plate.transform.localPosition = new Vector3(0, 0, 0.004f);
        var pivot = new GameObject("Rocker").transform; pivot.SetParent(sw, false); pivot.localPosition = new Vector3(0, 0, 0.011f);
        var rocker = GameObject.CreatePrimitive(PrimitiveType.Cube); rocker.transform.SetParent(pivot, false);
        rocker.transform.localScale = new Vector3(0.056f, 0.056f, 0.008f); rocker.transform.localPosition = new Vector3(0, 0, 0.002f);
        foreach (var r in sw.GetComponentsInChildren<Renderer>()) r.sharedMaterial = white;
        foreach (var c in sw.GetComponentsInChildren<Collider>()) Object.Destroy(c);
        const float Rest = 7f, Pushed = -4f;   // rest: top in, bottom out; a push on the bottom tips it the other way
        pivot.localRotation = Quaternion.Euler(-Rest, 0, 0);

        // lab window N1 blind (Blender room2.py: x 0.70..2.30 on y = 9.0, fabric from z 2.76 down), rebuilt to animate
        var old = GameObject.Find("Room2_Blind_N1");
        // ponytail: unlit greys, because the rebuilt boxes get no lightmap while the baked blinds around them do
        Material Flat(Color c) { var m = new Material(Shader.Find("Universal Render Pipeline/Unlit")); m.SetColor("_BaseColor", c); return m; }
        var mats = new[] { Flat(new Color(0.60f, 0.60f, 0.58f)), Flat(new Color(0.78f, 0.78f, 0.77f)) };
        if (old) old.SetActive(false);
        Transform Box(string n, Vector3 lo, Vector3 hi, Material m)
        {
            var g = GameObject.CreatePrimitive(PrimitiveType.Cube); g.name = n; Object.Destroy(g.GetComponent<Collider>());
            g.transform.position = (lo + hi) / 2; g.transform.localScale = hi - lo; g.GetComponent<Renderer>().sharedMaterial = m;
            return g.transform;
        }
        Box("BlindN1_Cassette", new Vector3(0.64f, 2.76f, 8.90f), new Vector3(2.36f, 2.85f, 9.0f), mats[mats.Length > 1 ? 1 : 0]);
        var fabric = Box("BlindN1_Fabric", new Vector3(0.67f, 2.0f, 8.94f), new Vector3(2.33f, 2.76f, 8.945f), mats[0]);
        var bar = Box("BlindN1_Bar", new Vector3(0.67f, 2.0f, 8.935f), new Vector3(2.33f, 2.02f, 8.95f), mats[mats.Length > 1 ? 1 : 0]);
        const float Top = 2.76f, Drop = 2.76f - 0.85f;   // fabric top, top to sill = 100 % closed
        float shown = 0;   // closed fraction on screen, eased toward the bridge position
        void SetBlind(float closed)
        {
            float bottom = Top - Mathf.Max(0.015f, closed * Drop);
            fabric.position = new Vector3(1.5f, (Top + bottom) / 2, 8.9425f); fabric.localScale = new Vector3(1.66f, Top - bottom, 0.005f);
            bar.position = new Vector3(1.5f, bottom - 0.01f, 8.9425f);
        }
        SetBlind(0);

        // right hand: the XRI sample's Quest hand mesh, posed by hand (no tracking data in the Editor)
        var handPrefab = AssetDatabase.LoadAssetAtPath<GameObject>("Assets/Models/Hands/RightHand.fbx");
        var hand = Object.Instantiate(handPrefab).transform;
        foreach (var b in hand.GetComponentsInChildren<Behaviour>(true)) if (!(b is Renderer)) b.enabled = false;
        var skin = new Material(Shader.Find("Universal Render Pipeline/Lit"));
        skin.SetColor("_BaseColor", new Color(0.87f, 0.69f, 0.58f)); skin.SetFloat("_Smoothness", 0.25f);
        foreach (var r in hand.GetComponentsInChildren<Renderer>(true)) { r.enabled = true; r.gameObject.SetActive(true); r.sharedMaterial = skin; }
        hand.gameObject.SetActive(true);
        Transform Bone(string n) => hand.GetComponentsInChildren<Transform>(true).First(x => x.name.EndsWith(n));
        Transform wristB = Bone("Wrist"), tipB = Bone("IndexTip"), indexB = Bone("IndexProximal"), littleB = Bone("LittleProximal");
        // the FBX's own axes: finger direction and index-side direction in the hand root's space
        var fingerL = hand.InverseTransformDirection(tipB.position - wristB.position);
        var sideL = hand.InverseTransformDirection(indexB.position - littleB.position);
        var handBasis = Quaternion.Inverse(Quaternion.LookRotation(fingerL, sideL));
        // pose so the index tip sits at `tip`, fingers along `dir`, index side to the hand's left (+z when facing +x)
        void PoseHand(Vector3 tip, Vector3 dir)
        {
            hand.rotation = Quaternion.LookRotation(dir, Vector3.forward) * handBasis;
            hand.position += tip - tipB.position;
        }

        string position = "";
        bridge.Applied += (d, p, v) => { if (d == "curtain1" && p == "position") position = v; };
        bridge.url = Environment.GetEnvironmentVariable("BRIDGE_CHECK_URL") ?? "ws://127.0.0.1:8765";
        bridge.Connect();
        yield return Until(() => bridge.State == "online" && F(position) >= 100, 10, "bridge online, curtain open");
        yield return Wait(1);

        var eye = new Vector3(5.12f, 1.68f, 5.2f);
        var sensor = new Vector3(5.65f, 1.91f - 0.30f * 1.02f, 6.05f - (0.10f + 0.86f * 1.50f));   // PIR, photo (0.86, 0.30)
        var right = new Vector3(5.5f, 1.35f, 4.2f);
        var window = new Vector3(1.15f, 1.95f, 9.0f);
        (double t, Vector3 at)[] look = { (0, sensor), (1.5, sensor), (3.2, right), (4.2, right), (5.3, face), (6.6, face), (9.2, window), (30, window) };
        cam.fieldOfView = 70f;
        var fwd = new Vector3(1f, -0.35f, 0.15f).normalized;   // fingers toward the board, slightly up, palm down
        var rest = eye + new Vector3(0.28f, -0.62f, -0.22f);
        var touch = face + Vector3.up * 0.008f + Vector3.left * 0.02f;   // index tip on the rocker's lower half
        (double t, Vector3 p)[] reach = { (0, rest), (4.4, rest), (5.8, touch), (6.0, touch + fwd * 0.012f), (6.25, touch), (7.4, rest), (30, rest) };

        StartVideo(Path.Combine(Out, "switch_recreation", "vr_switch_curtain.mp4"));
        bool sent = false;
        while (Now - t0 < 30)
        {
            double t = Now - t0;
            cam.transform.SetPositionAndRotation(eye, Quaternion.LookRotation(Track(look, t) + Sway(t) - eye));
            PoseHand(Track(reach, t), fwd);
            // rocker: pushed while the fingers are in (6.0-6.2 s), springs back with a small overshoot
            float a = t < 5.95 ? Rest : t < 6.2 ? Pushed : Rest + (Pushed - Rest) * Mathf.Exp(-(float)(t - 6.2) * 18f) * Mathf.Cos((float)(t - 6.2) * 40f);
            pivot.localRotation = Quaternion.Euler(-a, 0, 0);
            if (!sent && t >= 6.0) { sent = true; bridge.Send("curtain1", "close"); Debug.Log($"[ClickClip] switch: pressed at {t:0.00} s -> curtain1 close"); }
            shown = Mathf.MoveTowards(shown, 1 - F(position) / 100f, Time.unscaledDeltaTime * 75f / 24f / 100f * 1.5f);
            SetBlind(shown);
            yield return null;
        }
        StopVideo();
        Debug.Log($"[ClickClip] switch: {frames} frames, curtain1.position {position}, blind closed {shown * 100:0} %");
        if (!(F(position) < 35 && F(position) > 15)) Fail($"curtain should be ~25 % open at 0:30, bridge says {position}");
        bridge.Send("curtain1", "stop");
        yield return Wait(1);
    }

    // logs the world bounds of each submesh whose material name contains "Board_" or of objects named Blind_*
    static void Probe()
    {
        foreach (var r in Object.FindObjectsOfType<Renderer>())
            if (r.name == "Room2_Demo_Boards" || r.name == "Kitchen_Board" || r.name.Contains("Blind"))
                Debug.Log($"[Probe] {r.name} min {r.bounds.min.ToString("F3")} max {r.bounds.max.ToString("F3")} pos {r.transform.position.ToString("F3")} rot {r.transform.eulerAngles.ToString("F1")} scale {r.transform.lossyScale.ToString("F3")}");
    }

    static Vector3 Track((double t, Vector3 p)[] keys, double t)
    {
        int i = 0;
        while (i < keys.Length - 2 && t > keys[i + 1].t) i++;
        return Vector3.Lerp(keys[i].p, keys[i + 1].p, Mathf.SmoothStep(0, 1, (float)((t - keys[i].t) / (keys[i + 1].t - keys[i].t))));
    }

    static Vector3 Sway(double t) => new Vector3(Mathf.PerlinNoise((float)t * 0.4f, 0) - 0.5f, Mathf.PerlinNoise(0, (float)t * 0.4f) - 0.5f, Mathf.PerlinNoise((float)t * 0.3f, 7) - 0.5f) * 0.03f;

    static (Vector3, Vector3) Close(Component d)
    {
        if (!d) return (Vector3.zero, Vector3.forward);
        var t = d.transform.root.name == "IoT_Devices" ? d.transform : d.transform;
        var c = Bounds(d).center;
        var n = Vector3.back;   // devices on the Room1 wall face -z
        return (c + n * 0.55f + Vector3.up * 0.12f + Vector3.right * 0.12f, c);
    }

    static Bounds Bounds(Component d)
    {
        var rs = d.GetComponentsInChildren<Renderer>();
        var b = rs[0].bounds;
        foreach (var r in rs) b.Encapsulate(r.bounds);
        return b;
    }

    static IEnumerator Clip(string name, IoTDevice d, (Vector3 eye, Vector3 at) view, IEnumerator body, Func<bool> check = null)
    {
        if (!d) { Fail(name + ": device not in the scene"); yield break; }
        cam.transform.SetPositionAndRotation(view.eye, Quaternion.LookRotation(view.at - view.eye));
        ShowRay(false, Vector3.zero);
        StartVideo(Path.Combine(Out, name + ".mp4"));
        yield return Wait(1.2);
        yield return body;
        yield return Wait(2.5);
        StopVideo();
        Debug.Log($"[ClickClip] {name}: {frames} frames");
        if (check != null) { if (check()) Debug.Log($"[ClickClip] PASS: {name}"); else Fail(name + " result check"); }
    }

    static Vector3 Hand => cam.transform.position + cam.transform.right * 0.18f - cam.transform.up * 0.22f + cam.transform.forward * 0.2f;

    static void ShowRay(bool pressed, Vector3 at, bool visible = true)
    {
        ray.enabled = dot.activeSelf == false ? visible : visible;
        dot.SetActive(visible && at != Vector3.zero);
        ray.enabled = visible && at != Vector3.zero;
        if (at == Vector3.zero) return;
        ray.SetPositions(new[] { Hand, at });
        dot.transform.position = at;
        ray.material.SetColor("_BaseColor", pressed ? new Color(0.2f, 0.85f, 1f) : Color.white);
    }

    static DevicePointerTarget Zone(IoTDevice d, string action) =>
        d.GetComponentsInChildren<DevicePointerTarget>(true).First(t => t.device == d && (action == null || t.action == action));

    static Vector3 At(DevicePointerTarget z) => z.GetComponent<Collider>().bounds.center;

    // aim 0.8 s, trigger 0.25 s (a click: no ray motion), result
    static IEnumerator Click(IoTDevice d, string action, Func<bool> check)
    {
        var z = Zone(d, action);
        ShowRay(false, At(z)); yield return Wait(0.8);
        ShowRay(true, At(z));
        d.ControlDown(z.action, new Vector2(.5f, .5f)); bridge.UserControl(d, z.action, true);
        yield return Wait(0.25);
        d.ControlUp(z.action, true, new Vector2(.5f, .5f)); bridge.UserControl(d, z.action, false, true);
        ShowRay(false, At(z));
        yield return Wait(1);
        ShowRay(false, Vector3.zero);
        if (check != null && !check()) Fail($"{d.name} {action} click had no effect");
    }

    // every zone of the device once, like OrangeRoomBridgeCheck step 7; fails if none changed the device
    static IEnumerator ClickAll(IoTDevice d)
    {
        int changes = 0;
        Action<IoTDevice> count = _ => changes++;
        d.StateChanged += count;
        foreach (var z in d.GetComponentsInChildren<DevicePointerTarget>(true).Where(t => t.device == d).GroupBy(t => t.action).Select(g => g.First()))
            yield return Click(d, z.action, null);
        d.StateChanged -= count;
        if (changes == 0) Fail($"{d.name}: no zone changed its state");
    }

    static IEnumerator HoldLower(AqaraChainController chain, RollerBlindDevice blind)
    {
        var z = Zone(chain, "Lower");
        float before = blind.OpenPercent;
        ShowRay(false, At(z)); yield return Wait(0.8);
        ShowRay(true, At(z));
        chain.ControlDown("Lower", new Vector2(.5f, .5f)); bridge.UserControl(chain, "Lower", true);   // -> curtain1 close
        yield return Wait(4);
        chain.ControlUp("Lower", false, new Vector2(.5f, .5f)); bridge.UserControl(chain, "Lower", false);   // -> stop
        ShowRay(false, Vector3.zero);
        yield return Wait(2);
        if (blind.OpenPercent > before - 10) Fail($"curtain did not lower ({before} -> {blind.OpenPercent})");
    }

    // grab the bottom rail and pull it down 0.25 m (XRDeviceInput's drag: 4000 px per metre)
    static IEnumerator DragBlind(RollerBlindDevice blind)
    {
        var z = Zone(blind, "Position");
        float before = blind.TargetOpenPercent;
        ShowRay(false, At(z)); yield return Wait(0.8);
        ShowRay(true, At(z));
        blind.ControlDown("Position", new Vector2(.5f, .5f)); bridge.UserControl(blind, "Position", true);
        for (int i = 0; i < 25; i++)
        {
            blind.ControlDrag("Position", new Vector2(.5f, .5f), new Vector2(0, -40));
            ShowRay(true, At(z));
            yield return Wait(0.06);
        }
        blind.ControlUp("Position", false, new Vector2(.5f, .5f)); bridge.UserControl(blind, "Position", false);   // -> set_position
        ShowRay(false, Vector3.zero);
        yield return Wait(2);
        if (Mathf.Abs(blind.TargetOpenPercent - before) < 5) Fail($"blind drag did not move it ({before} -> {blind.TargetOpenPercent})");
    }

    static IEnumerator OnlineCurtainReset()
    {
        bridge.url = Environment.GetEnvironmentVariable("BRIDGE_CHECK_URL") ?? "ws://127.0.0.1:8765";
        string position = "";
        Action<string, string, string> on = (d, p, v) => { if (d == "curtain1" && p == "position") position = v; };
        bridge.Applied += on;
        bridge.Connect();
        yield return Until(() => bridge.State == "online" && position != "", 10, "bridge online (server.py --simulate running?)");
        if (F(position) < 100) { bridge.Send("curtain1", "set_position", 100); yield return Until(() => F(position) >= 100, 15, "curtain reopened"); }
        bridge.Applied -= on;
        yield return Wait(2);
    }

    // the real device's bridge messages, on a schedule: (delay before, device, property, value)
    static IEnumerator Feeds(Func<bool> unused, params (double delay, string device, string property, string value)[] lines)
    {
        foreach (var l in lines) { yield return Wait(l.delay); Feed(l.device, l.property, l.value); }
    }

    static void Feed(string device, string property, string value)
    {
        var v = value == "true" || value == "false" || float.TryParse(value, NumberStyles.Float, CultureInfo.InvariantCulture, out _) ? value : $"\"{value}\"";
        var m = RoomBridge.Parse($"{{\"device\": \"{device}\", \"property\": \"{property}\", \"value\": {v}, \"source\": \"real\"}}");
        bridge.Apply(m.device, m.property, m.value);
    }

    // ---------- screenshots ----------

    static IEnumerator Screenshots()
    {
        var dir = Path.Combine(Out, "screenshots");
        Directory.CreateDirectory(dir);
        void Shot(string name, Vector3 pos, Quaternion rot, float fov)
        {
            cam.fieldOfView = fov;
            cam.transform.SetPositionAndRotation(pos, rot);
            Grab();
            var flipped = new Texture2D(W, H, TextureFormat.RGB24, false);
            flipped.SetPixels32(tex.GetPixels32());
            File.WriteAllBytes(Path.Combine(dir, name + ".png"), flipped.EncodeToPNG());
            Object.Destroy(flipped);
        }
        foreach (var root in EditorSceneManager.GetActiveScene().GetRootGameObjects().Where(g => g.name.StartsWith("Room")))
        {
            var rs = root.GetComponentsInChildren<Renderer>();
            if (rs.Length == 0) continue;
            var floor = rs.Where(r => r.name.Contains("Floor")).OrderByDescending(r => r.bounds.size.x * r.bounds.size.z).FirstOrDefault();
            var b = floor ? floor.bounds : rs[0].bounds;
            var eye = new Vector3(b.center.x, (floor ? b.max.y : b.min.y) + 1.6f, b.center.z);
            for (int yaw = 0; yaw < 360; yaw += 90) Shot($"{root.name}_yaw{yaw:000}", eye, Quaternion.Euler(0, yaw, 0), 90);
        }
        Shot("Ref_hall", new Vector3(-0.997f, 1.333f, 0.6f), Quaternion.LookRotation(new Vector3(-0.974f, -0.084f, 0.21f)), 55);
        Shot("Ref_lab", new Vector3(0.407f, 1.57f, 1.312f), Quaternion.LookRotation(new Vector3(0.603f, -0.072f, 0.795f)), 55);
        Shot("Ref_room1", new Vector3(0.166f, 1.498f, 1.817f), Quaternion.LookRotation(new Vector3(0.993f, -0.067f, -0.094f)), 55);
        Shot("Wall_devices", new Vector3(3.9f, 1.5f, 0.6f), Quaternion.LookRotation(Vector3.forward), 75);
        Shot("Wall_devices_close", new Vector3(3.3f, 1.3f, 1.7f), Quaternion.LookRotation(Vector3.forward), 70);
        cam.fieldOfView = 70f;
        yield return null;
    }

    // ---------- helpers ----------

    static IEnumerator Wait(double seconds) { var end = Now + seconds; while (Now < end) yield return null; }

    static IEnumerator Until(Func<bool> done, double seconds, string what)
    {
        var end = Now + seconds;
        while (!done()) { if (Now > end) throw new Exception($"timed out after {seconds} s waiting for {what}"); yield return null; }
    }

    static float F(string v) => float.TryParse(v, NumberStyles.Float, CultureInfo.InvariantCulture, out var f) ? f : float.NaN;

    static void Fail(string why) { SessionState.SetBool(Failed, true); Debug.Log("[ClickClip] FAIL: " + why); }
}
