// End-to-end check of the bridge integration (RoomBridge <-> bridge/server.py) in play mode. The caller starts the simulator:
//   python3 bridge/server.py --simulate &
//   ~/Unity/Hub/Editor/2022.3.62f3/Editor/Unity -batchmode -projectPath unity -executeMethod OrangeRoomBridgeCheck.Run -logFile -
// Use the raw editor binary: `unity run` likely adds -quit. No -quit: the check enters play mode and calls EditorApplication.Exit(0 / 1) itself (global timeout 120 s).
// BRIDGE_CHECK_URL overrides ws://127.0.0.1:8765. Prints "[BridgeCheck] PASS: ..." / "[BridgeCheck] FAIL: ..." per assertion.
using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using IoTDigitalTwin;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using Object = UnityEngine.Object;

[InitializeOnLoad]
public static class OrangeRoomBridgeCheck
{
    const string ScenePath = "Assets/Scenes/OrangeRoom.unity";
    const string Active = "BridgeCheck.Active", Failed = "BridgeCheck.Failed", Started = "BridgeCheck.Started";
    const double Timeout = 120;

    static readonly Stack<IEnumerator> steps = new Stack<IEnumerator>();
    static double Now => EditorApplication.timeSinceStartup;

    // entering play mode reloads the domain; SessionState survives it and this re-hooks the check
    static OrangeRoomBridgeCheck() { if (SessionState.GetBool(Active, false)) Hook(); }

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
        EditorApplication.playModeStateChanged += OnPlayMode;
        EditorApplication.update += Tick;
    }

    static void OnPlayMode(PlayModeStateChange s)
    {
        if (s == PlayModeStateChange.EnteredPlayMode) steps.Push(Steps());
        else if (s == PlayModeStateChange.EnteredEditMode) Exit();
    }

    // runs the Steps() iterator; a yielded IEnumerator runs to the end before its caller continues
    static void Tick()
    {
        if (Now - SessionState.GetFloat(Started, 0) > Timeout) { steps.Clear(); Fail($"global timeout {Timeout} s"); Finish(); return; }
        if (steps.Count == 0) return;
        try
        {
            var top = steps.Peek();
            if (!top.MoveNext()) { steps.Pop(); if (steps.Count == 0) Finish(); }
            else if (top.Current is IEnumerator inner) steps.Push(inner);
        }
        catch (Exception e) { steps.Clear(); Fail(e.Message); Finish(); }
    }

    static void Finish()
    {
        EditorApplication.update -= Tick;
        Debug.Log(SessionState.GetBool(Failed, false) ? "[BridgeCheck] DONE: FAILED" : "[BridgeCheck] DONE: all passed");
        if (EditorApplication.isPlaying) EditorApplication.isPlaying = false;   // -> EnteredEditMode -> Exit
        else Exit();
    }

    static void Exit()
    {
        int code = SessionState.GetBool(Failed, false) ? 1 : 0;
        SessionState.EraseBool(Active);
        EditorApplication.delayCall += () => EditorApplication.Exit(code);   // not from inside the playModeStateChanged callback
    }

    // ---------- the check ----------

    static IEnumerator Steps()
    {
        // 6. Parse, on lines shaped like server.py's json.dumps output (run first: needs no bridge)
        ParseCase(@"{""device"": ""dimmer1"", ""property"": ""on"", ""value"": true, ""source"": ""simulated"", ""timestamp"": ""2026-10-14T10:00:00+00:00""}", "dimmer1", "on", "true");
        ParseCase(@"{""device"": ""dimmer1"", ""property"": ""level"", ""value"": 60}", "dimmer1", "level", "60");
        ParseCase(@"{""device"": ""room_sensor1"", ""property"": ""temperature"", ""value"": 22.5, ""source"": ""simulated""}", "room_sensor1", "temperature", "22.5");
        ParseCase(@"{""device"": ""speaker1"", ""property"": ""title"", ""value"": ""Say \""hi\"", ok.mp3""}", "speaker1", "title", "Say \"hi\", ok.mp3");

        var bridge = Object.FindObjectOfType<RoomBridge>();
        var dali = Object.FindObjectOfType<DALILightingPanel>(); var thermo = Object.FindObjectOfType<TemperatureLCD>();
        var blind = Object.FindObjectOfType<RollerBlindDevice>(); var chain = Object.FindObjectOfType<AqaraChainController>();
        var dimmer = Object.FindObjectOfType<RotaryDimmer>(); var ceiling = Object.FindObjectOfType<CeilingLights>();
        if (!Check(bridge && dali && thermo && blind && chain && dimmer && ceiling && ceiling.lights.Length > 0,
                "scene has RoomBridge, devices and CeilingLights with lights")) yield break;

        // 1. connect. Wait for Start() first, so its connectOnStart / saved url doesn't override ours
        yield return Wait(0.5);
        var last = new Dictionary<string, string>();
        var positions = new List<float>();
        bridge.Applied += (d, p, v) => { last[d + "." + p] = v; if (d == "curtain1" && p == "position") positions.Add(F(v)); };
        bridge.url = Environment.GetEnvironmentVariable("BRIDGE_CHECK_URL") ?? "ws://127.0.0.1:8765";
        bridge.Connect();

        // 2. online + the full state server.py sends on connect
        yield return Until(() => bridge.State == "online", 10, $"bridge online at {bridge.url} (is server.py --simulate running?)");
        Check(true, "bridge online at " + bridge.url);
        string[] initial = { "dali1.group0_kelvin", "room_sensor1.temperature", "curtain1.position" };
        yield return Until(() => initial.All(last.ContainsKey), 10, "initial state: " + string.Join(", ", initial));

        // 3. devices follow the real messages
        Equal("DALI colour temperature == last dali1.group0_kelvin", dali.ColorTemperature, last["dali1.group0_kelvin"]);
        Equal("TemperatureLCD == last room_sensor1.temperature", thermo.Temperature, last["room_sensor1.temperature"]);
        Equal("RollerBlind target == last curtain1.position", blind.TargetOpenPercent, last["curtain1.position"]);

        // 4. XR curtain button -> command -> simulator moves 10 % per 0.5 s -> curtain1.position comes back
        if (F(last["curtain1.position"]) < 50)
        {   // the simulator curtain is shared state; a previous run may have left it low
            bridge.Send("curtain1", "set_position", 100);
            yield return Until(() => F(last["curtain1.position"]) >= 100, 15, "curtain reopened to 100");
        }
        int n = positions.Count;
        float start = F(last["curtain1.position"]);
        bridge.UserControl(chain, "Lower", true);
        yield return Until(() => positions.Count >= n + 2, 5, "two curtain1.position updates after Lower");
        Check(positions[n] < start && positions[n + 1] < positions[n], $"Lower: curtain1.position {start} -> {positions[n]} -> {positions[n + 1]}");
        bridge.UserControl(chain, "Lower", false);
        yield return Wait(1.5);   // a tick already in flight may still land
        float held = F(last["curtain1.position"]);
        yield return Wait(1.5);
        Check(F(last["curtain1.position"]) == held && held > 0, $"Lower released -> stop: curtain1.position holds at {held}");
        Equal("RollerBlind target == curtain1.position after stop", blind.TargetOpenPercent, last["curtain1.position"]);

        // 5. test-panel path (Apply, no bridge). Offline first, so simulator dimmer1 / virtual_light messages can't interfere
        bridge.Disconnect();
        yield return Wait(0.5);   // RoomBridge.Update drains anything still queued
        bridge.Apply("dimmer1", "on", "true");
        bridge.Apply("dimmer1", "level", "70");
        bridge.Apply("dali1", "group0_on", "true");
        yield return Wait(1);
        float on = ceiling.lights.Min(l => l.intensity);
        Check(on > 0, $"dimmer on 70 % + DALI on -> ceiling lights on (min intensity {on})");
        Check(Mathf.Abs(dimmer.Brightness - 0.7f) < 0.001f, $"RotaryDimmer.Brightness {dimmer.Brightness} == 0.7");
        bridge.Apply("dimmer1", "on", "false");
        yield return Wait(1);
        float off = ceiling.lights.Max(l => l.intensity);
        Check(off < on * 0.1f, $"dimmer off -> ceiling intensity falls ({on} -> {off})");
        float kept = blind.TargetOpenPercent;
        bridge.Apply("curtain1", "position", "null");   // server.py sends None for a failed read
        Check(blind.TargetOpenPercent == kept, $"null curtain1.position ignored (target stays {kept})");

        // 7. every device: XR-clickable, and driven by its bridge messages (still offline: the test-panel path)
        var cam = Object.FindObjectOfType<SecurityCameraDevice>(); var unit = Object.FindObjectOfType<SiemensBACnetDevice>();
        var speaker = Object.FindObjectOfType<NestSpeakerDevice>();
        IoTDevice[] all = { dimmer, thermo, cam, chain, blind, unit, speaker, dali };
        if (!Check(all.All(d => d), "scene has all 8 IoT devices")) yield break;
        foreach (var d in all)
        {
            var zones = d.GetComponentsInChildren<DevicePointerTarget>(true).Where(t => t.device == d && t.GetComponent<Collider>() is Collider c && c.isTrigger).ToArray();
            Check(d.GetComponent<XRDeviceInput>() && zones.Length > 0, $"{d.name}: XRDeviceInput + {zones.Length} trigger hit zones");
            // what XRDeviceInput calls on a click, per zone: at least one must change the device
            int changes = 0;
            Action<IoTDevice> count = _ => changes++;
            d.StateChanged += count;
            foreach (var z in zones) { d.ControlDown(z.action, new Vector2(.5f, .5f)); d.ControlUp(z.action, true, new Vector2(.5f, .5f)); }
            d.StateChanged -= count;
            Check(changes > 0, $"{d.name}: clicking its zones ({string.Join(", ", zones.Select(z => z.action).Distinct())}) changes state ({changes} changes)");
        }
        yield return Wait(0.5);
        bridge.Apply("dali1", "all_on", "false");
        Check(!dali.Power, "dali1.all_on false -> DALI panel off");
        bridge.Apply("virtual_light", "on", "true");
        Check(dali.Power, "virtual_light.on true (UC1) -> DALI panel on");
        bridge.Apply("dali1", "all_kelvin", "3000");
        Equal("dali1.all_kelvin -> DALI colour temperature", dali.ColorTemperature, "3000");
        bridge.Apply("camera1", "occupied", "true");
        Check(cam.Power && !cam.Floodlight, "camera1.occupied true -> camera on, floodlight off");
        bridge.Apply("room_sensor1", "alarm", "true");
        Check(cam.Floodlight, "room_sensor1.alarm true (UC3) -> camera floodlight on");
        bridge.Apply("room_sensor1", "alarm", "false");
        bridge.Apply("camera1", "occupied", "false");
        Check(!cam.Power && !cam.Floodlight, "occupied + alarm false -> camera off");
        bridge.Apply("room_sensor1", "temperature", "27");
        Equal("room_sensor1.temperature -> TemperatureLCD", thermo.Temperature, "27");
        Equal("room_sensor1.temperature -> Siemens display", unit.DisplayValue, "27");
        bridge.Apply("room_sensor1", "status", "offline");
        Check(!unit.Status, "room_sensor1.status offline -> Siemens status off");
        bridge.Apply("speaker1", "volume", "40");
        Equal("speaker1.volume -> speaker volume", speaker.Volume, "0.4");
        bridge.Apply("speaker1", "state", "playing");
        Check(speaker.Active && !speaker.Muted, "speaker1.state playing -> speaker active, not muted");
        bridge.Apply("curtain1", "position", "30");
        Equal("curtain1.position -> roller blind target", blind.TargetOpenPercent, "30");
    }

    // ---------- helpers ----------

    static IEnumerator Wait(double seconds) { var end = Now + seconds; while (Now < end) yield return null; }

    static IEnumerator Until(Func<bool> done, double seconds, string what)
    {
        var end = Now + seconds;
        while (!done()) { if (Now > end) throw new Exception($"timed out after {seconds} s waiting for {what}"); yield return null; }
    }

    static float F(string v) => float.TryParse(v, NumberStyles.Float, CultureInfo.InvariantCulture, out var f) ? f : float.NaN;

    static void Equal(string what, float actual, string expected) =>
        Check(Mathf.Abs(actual - F(expected)) < 0.01f, $"{what} ({actual.ToString(CultureInfo.InvariantCulture)} vs {expected})");

    static void ParseCase(string json, string device, string property, string value)
    {
        var m = RoomBridge.Parse(json);
        Check(m.device == device && m.property == property && m.value == value, $"Parse {json} -> ({m.device}, {m.property}, {m.value})");
    }

    // Debug.Log, not LogError: an error log can trigger the console's Error Pause and freeze play mode
    static bool Check(bool ok, string what)
    {
        if (ok) Debug.Log("[BridgeCheck] PASS: " + what); else Fail(what);
        return ok;
    }

    static void Fail(string why)
    {
        SessionState.SetBool(Failed, true);
        Debug.Log("[BridgeCheck] FAIL: " + why);
    }
}
