// Connects the XR room to bridge/server.py (bridge/README.md, sections 3 and 5) and drives the IoT library devices.
// In:  {"device": "dimmer1", "property": "level", "value": 60, ...}  -> Apply(device, property, value) on the main thread.
// Out: {"device": "curtain1", "command": "open"}                     <- only from user input (XRDeviceInput), never from
//      StateChanged, so a bridge update can't echo back to the bridge.
// The in-VR test panel (BridgeTestPanel) calls Apply too, so it exercises the same path as a real message.
using System;
using System.Collections.Concurrent;
using System.Globalization;
using System.Net.WebSockets;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading;
using System.Threading.Tasks;
using IoTDigitalTwin;
using UnityEngine;

public sealed class RoomBridge : MonoBehaviour
{
    [Tooltip("ws://<bridge PC IP>:8765. Check the laptop IP with `ip addr` / `ipconfig`; it changes on Wi-Fi.")]
    public string url = "ws://192.168.160.57:8765";   // this laptop on the lab Wi-Fi; the test panel can change it in VR
    public bool connectOnStart = true;

    public string State { get; private set; } = "offline";   // offline / connecting / online
    public string LastMessage { get; private set; } = "";
    public event Action<string, string, string> Applied;     // device, property, value (for the test panel log)

    RotaryDimmer dimmer; DALILightingPanel dali; RollerBlindDevice blind; AqaraChainController curtainButtons;
    TemperatureLCD thermo; SiemensBACnetDevice roomUnit; SecurityCameraDevice cam; NestSpeakerDevice speaker; TemperatureController zwave;

    readonly ConcurrentQueue<string> inbox = new ConcurrentQueue<string>();
    ClientWebSocket ws;
    CancellationTokenSource cts;
    Task lastSend = Task.CompletedTask;
    bool daliAll, occupied, alarm;
    float bridgePosition = -1;   // last curtain1.position from the bridge, -1 = none yet

    public const string UrlKey = "OrangeRoom.BridgeUrl";

    void Awake()
    {
        // ponytail: a url saved in VR wins over the build's ORANGE_BRIDGE_URL until changed again (or app data cleared)
        url = PlayerPrefs.GetString(UrlKey, url);
        dimmer = FindObjectOfType<RotaryDimmer>(); dali = FindObjectOfType<DALILightingPanel>();
        blind = FindObjectOfType<RollerBlindDevice>(); curtainButtons = FindObjectOfType<AqaraChainController>();
        thermo = FindObjectOfType<TemperatureLCD>(); roomUnit = FindObjectOfType<SiemensBACnetDevice>();
        cam = FindObjectOfType<SecurityCameraDevice>(); speaker = FindObjectOfType<NestSpeakerDevice>();
        zwave = FindObjectOfType<TemperatureController>();
        if (curtainButtons && blind) curtainButtons.ConnectBlind(blind);   // Raise/Lower move the virtual curtain
    }

    void Start() { if (connectOnStart) Connect(); }

    public void Connect()
    {
        Disconnect();
        cts = new CancellationTokenSource();
        _ = Run(cts.Token);
    }

    public void Disconnect()
    {
        cts?.Cancel();
        cts = null;
        State = "offline";
    }

    public void SetUrl(string newUrl)
    {
        url = newUrl;
        PlayerPrefs.SetString(UrlKey, newUrl);
        PlayerPrefs.Save();
        Connect();
    }

    void OnDestroy() => Disconnect();

    // ponytail: fixed 2 s reconnect, no backoff; the bridge is one laptop on the lab Wi-Fi
    async Task Run(CancellationToken ct)
    {
        var buf = new byte[16384];
        while (!ct.IsCancellationRequested)
        {
            var sock = new ClientWebSocket();   // local: after a reconnect the old loop must not dispose the new socket
            ws = sock;
            try
            {
                State = "connecting";
                await sock.ConnectAsync(new Uri(url), ct);
                State = "online";
                var sb = new StringBuilder();
                while (sock.State == WebSocketState.Open && !ct.IsCancellationRequested)
                {
                    var r = await sock.ReceiveAsync(new ArraySegment<byte>(buf), ct);
                    if (r.MessageType == WebSocketMessageType.Close) break;
                    sb.Append(Encoding.UTF8.GetString(buf, 0, r.Count));
                    if (r.EndOfMessage) { inbox.Enqueue(sb.ToString()); sb.Clear(); }
                }
            }
            catch (Exception e) when (!(e is OperationCanceledException)) { LastMessage = e.Message; }
            catch (OperationCanceledException) { }
            finally { sock.Dispose(); if (ws == sock) ws = null; }
            if (ct.IsCancellationRequested) break;
            State = "offline";
            try { await Task.Delay(2000, ct); } catch (OperationCanceledException) { }
        }
    }

    void Update()
    {
        while (inbox.TryDequeue(out var json))
        {
            var m = Parse(json);
            if (m.device == "dali1" && m.property != null && m.property.StartsWith("all_")) daliAll = true;   // bridge only, not the test panel
            if (m.device != null) Apply(m.device, m.property, m.value);
        }
    }

    // ---------- messages ----------

    static readonly Regex Field = new Regex("\"(\\w+)\"\\s*:\\s*(\"(?:[^\"\\\\]|\\\\.)*\"|[^,}]+)");

    // server.py sends flat objects with one scalar value (bool, int, float, string); no JSON library needed
    public static (string device, string property, string value) Parse(string json)
    {
        string d = null, p = null, v = null;
        foreach (Match f in Field.Matches(json))
        {
            var raw = f.Groups[2].Value.Trim();
            var s = raw.StartsWith("\"") ? Regex.Unescape(raw.Substring(1, raw.Length - 2)) : raw;
            switch (f.Groups[1].Value) { case "device": d = s; break; case "property": p = s; break; case "value": v = s; break; }
        }
        return (d, p, v);
    }

    static float F(string v) => float.TryParse(v, NumberStyles.Float, CultureInfo.InvariantCulture, out var f) ? f : 0f;
    static bool B(string v) => v == "true" || v == "True" || v == "1";

    public void Send(string device, string command, float? value = null)
    {
        var json = value.HasValue
            ? $"{{\"device\": \"{device}\", \"command\": \"{command}\", \"value\": {Mathf.RoundToInt(value.Value).ToString(CultureInfo.InvariantCulture)}}}"
            : $"{{\"device\": \"{device}\", \"command\": \"{command}\"}}";
        LastMessage = "-> " + json;
        var sock = ws;
        if (sock == null || sock.State != WebSocketState.Open) return;   // simulation: the virtual device already moved
        lastSend = SendAfter(lastSend, sock, json);
    }

    // ClientWebSocket allows one SendAsync at a time: chain them, so two commands in one frame both go out
    async Task SendAfter(Task previous, ClientWebSocket sock, string json)
    {
        try { await previous; } catch { }
        try { await sock.SendAsync(new ArraySegment<byte>(Encoding.UTF8.GetBytes(json)), WebSocketMessageType.Text, true, CancellationToken.None); }
        catch (Exception e) { LastMessage = "send failed: " + e.Message; }
    }

    // Bridge property -> device setter. Mapping: README "Next Steps", concept.md section 3.
    public void Apply(string device, string property, string value)
    {
        if (value == "null") return;   // server.py sends None for a failed read: keep the last known state
        LastMessage = $"{device}.{property} = {value}";
        switch (device + "." + property)
        {
            // real dimmer switch: knob + on/off; CeilingLights takes the ceiling brightness from it
            case "dimmer1.on": if (dimmer) dimmer.SetPower(B(value)); break;
            case "dimmer1.level": if (dimmer) dimmer.SetBrightness(F(value) / 100f); break;
            // real DALI panel: on/off + colour (kelvin only, no RGB on the wire). all_* = broadcast zone 1, the zone the
            // ceiling follows; group0_* (G0 = lamps 0 and 9 only) is the fallback until the bridge sends all_*
            case "dali1.all_on": if (dali) dali.SetPower(B(value)); break;
            case "dali1.all_level": if (dali) dali.SetBrightness(F(value) / 100f); break;
            case "dali1.all_kelvin": if (dali) dali.SetColorTemperature(F(value)); break;
            case "dali1.group0_on": if (dali && !daliAll) dali.SetPower(B(value)); break;
            case "dali1.group0_level": if (dali && !daliAll) dali.SetBrightness(F(value) / 100f); break;
            case "dali1.group0_kelvin": if (dali && !daliAll) dali.SetColorTemperature(F(value)); break;
            // UC1 presence: last writer wins with the DALI on/off
            case "virtual_light.on": if (dali) dali.SetPower(B(value)); break;
            case "curtain1.position": bridgePosition = F(value); if (blind) blind.SetOpenPercent(bridgePosition); break;   // 0 = closed on both sides
            case "room_sensor1.temperature":
                if (thermo) { thermo.SetTemperature(F(value)); thermo.temperatureText.SetColor(Tint(F(value))); }
                if (roomUnit) roomUnit.SetDisplayValue(Mathf.Round(F(value)));
                if (zwave) zwave.SetTemperature(F(value));   // current reading only; the target stays the user's
                break;
            case "room_sensor1.humidity": if (thermo) thermo.SetHumidity(F(value)); break;
            case "room_sensor1.status": if (roomUnit) roomUnit.SetStatus(value != "offline"); break;
            // UC3 alarm = camera floodlight, presence = red recording LED. The library only lights the floodlight while the
            // camera is powered, so power = occupied || alarm.
            // ponytail: the red LED also lights during an alarm; a UC3 warning panel (concept.md) is the upgrade
            case "room_sensor1.alarm": alarm = B(value); if (cam) { cam.SetPower(occupied || alarm); cam.SetFloodlight(alarm); } break;
            case "camera1.occupied": occupied = B(value); if (cam) cam.SetPower(occupied || alarm); break;
            case "speaker1.volume": if (speaker) speaker.SetVolume(F(value) / 100f); break;
            case "speaker1.state": if (speaker) { speaker.SetActive(value == "playing"); speaker.SetMuted(false); } break;   // real state clears a pending Mute
        }
        Applied?.Invoke(device, property, value);
    }

    // docs/temperature-tint-scale.md
    static readonly (float upTo, string hex)[] Tints =
    {
        (10, "#2563EB"), (15, "#3B82F6"), (18, "#93C5FD"), (20, "#166534"), (22, "#16A34A"),
        (24, "#86EFAC"), (25, "#FCA5A5"), (26, "#EF4444"), (float.MaxValue, "#991B1B"),
    };
    public static Color Tint(float celsius)
    {
        foreach (var t in Tints)
            if (celsius < t.upTo) { ColorUtility.TryParseHtmlString(t.hex, out var c); return c; }
        return Color.red;
    }

    // Devices that only mirror the real ones while online: XRDeviceInput ignores input on them, because server.py
    // publishes on change only and a local change would never be corrected. Curtain and speaker send commands instead.
    public bool Mirrored(IoTDevice d) => State == "online" &&
        (d is RotaryDimmer || d is DALILightingPanel || d is SecurityCameraDevice || d is TemperatureLCD || d is SiemensBACnetDevice);

    // XR input on a device -> bridge command. Curtain and speaker only: concept.md says XR never drives the real lights.
    // Called after the device's own ControlDown/ControlUp, so it sees the toggled local state.
    public void UserControl(IoTDevice device, string action, bool down, bool click = false)
    {
        if (device is AqaraChainController)
        {
            if (action == "Raise" && down) Send("curtain1", "open");
            else if (action == "Lower" && down) Send("curtain1", "close");
            else if ((action == "Raise" || action == "Lower") && !down)
            {
                Send("curtain1", "stop");
                // a short tap may not change the real position, so no message would follow: show the real one again
                if (State == "online" && bridgePosition >= 0 && blind) blind.SetOpenPercent(bridgePosition);
            }
        }
        else if (device is RollerBlindDevice b && !down)
            Send("curtain1", "set_position", b.TargetOpenPercent);
        else if (device is NestSpeakerDevice s && !down)
        {
            // pause/resume from the mirrored play state, not from the local Mute flag
            if (action == "Volume" && click) Send("speaker1", s.Active ? "resume" : "pause");   // the click already toggled Active
            else if (action == "Volume") Send("speaker1", "set_volume", s.Volume * 100f);
            else if (action == "Mute") Send("speaker1", s.Active ? "pause" : "resume");
        }
    }
}
