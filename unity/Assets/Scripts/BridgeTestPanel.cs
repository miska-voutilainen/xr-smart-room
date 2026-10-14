// In-VR test panel: fakes the real-world signals by calling RoomBridge.Apply with the same device/property/value the
// bridge would send, so every mapping can be checked in the headset without the lab. Also shows the bridge connection.
// Built in code (world-space uGUI, XRI ray clickable) so the scene builder needs no prefab.
// The bridge IP is edited with -/+ buttons per octet (no keyboard in the headset) and saved by RoomBridge.SetUrl.
using System;
using System.Globalization;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.UI;
using UnityEngine.XR.Interaction.Toolkit.UI;

public sealed class BridgeTestPanel : MonoBehaviour
{
    RoomBridge bridge;
    Text status;
    Font font;
    readonly int[] ip = { 192, 168, 160, 57 };
    int port = 8765;
    static readonly Color Accent = new Color(0.2f, 0.6f, 1f);

    void Start()
    {
        bridge = FindObjectOfType<RoomBridge>();
        font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
        if (!FindObjectOfType<EventSystem>()) new GameObject("EventSystem", typeof(EventSystem), typeof(XRUIInputModule));

        var canvas = gameObject.AddComponent<Canvas>();
        canvas.renderMode = RenderMode.WorldSpace;
        gameObject.AddComponent<TrackedDeviceGraphicRaycaster>();
        var rt = (RectTransform)transform;
        rt.sizeDelta = new Vector2(520, 700);   // height follows the content (ContentSizeFitter below), about 0.95 m
        rt.localScale = Vector3.one * 0.001f;   // 1 px = 1 mm
        gameObject.AddComponent<Image>().color = new Color(0.08f, 0.09f, 0.11f, 0.92f);
        var layout = gameObject.AddComponent<VerticalLayoutGroup>();
        layout.padding = new RectOffset(20, 20, 16, 16);
        layout.spacing = 6;
        layout.childControlHeight = layout.childControlWidth = true;
        layout.childForceExpandHeight = false;
        gameObject.AddComponent<ContentSizeFitter>().verticalFit = ContentSizeFitter.FitMode.PreferredSize;

        if (bridge && Uri.TryCreate(bridge.url, UriKind.Absolute, out var u))
        {
            if (u.Port > 0) port = u.Port;
            var parts = u.Host.Split('.');
            if (parts.Length == 4)
                for (int i = 0; i < 4; i++) if (int.TryParse(parts[i], out var o) && o >= 0 && o <= 255) ip[i] = o;
        }

        Label("Bridge test panel (fake real-world signals)", 26, FontStyle.Bold);
        status = Label("", 18, FontStyle.Normal);
        status.GetComponent<LayoutElement>().preferredHeight = 48;   // fixed 2 lines, long errors truncate instead of growing the panel
        Label($"Bridge laptop IP (port {port}): set, then Apply", 18, FontStyle.Normal);
        for (int i = 0; i < 4; i++) OctetRow(i);
        Button("Apply & reconnect", () => { if (bridge) bridge.SetUrl($"ws://{string.Join(".", ip)}:{port}"); });

        Toggle("Dimmer on (dimmer1.on)", true, v => Apply("dimmer1", "on", v));   // RotaryDimmer.power starts true
        Slider("Dimmer level % (dimmer1.level)", 0, 100, 50, v => Apply("dimmer1", "level", v));
        Toggle("DALI lamps on (dali1.all_on)", true, v => Apply("dali1", "all_on", v));
        Slider("DALI colour K (dali1.all_kelvin)", 2000, 6500, 4500, v => Apply("dali1", "all_kelvin", v));
        Toggle("Person seen, UC1 (camera1.occupied + virtual_light.on)", false, v =>
        {
            Apply("camera1", "occupied", v);
            Apply("virtual_light", "on", v);
        });
        Slider("Curtain open % (curtain1.position)", 0, 100, 100, v => Apply("curtain1", "position", v));
        Slider("Temperature C (room_sensor1.temperature)", 15, 30, 22, v => Apply("room_sensor1", "temperature", v));
        Toggle("Temperature alarm, UC3 (room_sensor1.alarm)", false, v => Apply("room_sensor1", "alarm", v));
        Slider("Speaker volume % (speaker1.volume)", 0, 100, 30, v => Apply("speaker1", "volume", v));
    }

    void Apply(string device, string property, float v) =>
        bridge?.Apply(device, property, Mathf.Round(v).ToString(CultureInfo.InvariantCulture));
    void Apply(string device, string property, bool v) => bridge?.Apply(device, property, v ? "true" : "false");

    void Update()
    {
        if (status && bridge) status.text = $"{bridge.url}: {bridge.State}\n{bridge.LastMessage}";
    }

    // [-10] [-1] 192 [+1] [+10]
    void OctetRow(int i)
    {
        var row = new GameObject("Octet" + i, typeof(RectTransform));
        row.transform.SetParent(transform, false);
        var h = row.AddComponent<HorizontalLayoutGroup>();
        h.spacing = 6;
        h.childControlHeight = h.childControlWidth = true;
        row.AddComponent<LayoutElement>().minHeight = 44;
        Text value = null;
        foreach (var d in new[] { -10, -1, 0, 1, 10 })
        {
            if (d == 0) { value = Label(ip[i].ToString(), 24, FontStyle.Bold, row.transform); value.alignment = TextAnchor.MiddleCenter; continue; }
            Button(d > 0 ? "+" + d : d.ToString(), () => { ip[i] = Mathf.Clamp(ip[i] + d, 0, 255); value.text = ip[i].ToString(); }, row.transform);
        }
    }

    // ---------- tiny uGUI builders ----------

    // DefaultControls with empty Resources = plain white images: blue hover/press so the ray target is obvious
    static void Style(Selectable s)
    {
        var c = s.colors;
        c.highlightedColor = new Color(0.65f, 0.85f, 1f);
        c.pressedColor = Accent;
        s.colors = c;
    }

    Text Label(string text, int size, FontStyle style, Transform parent = null)
    {
        var go = new GameObject("Label", typeof(RectTransform));
        go.transform.SetParent(parent ? parent : transform, false);
        var t = go.AddComponent<Text>();
        t.font = font; t.fontSize = size; t.fontStyle = style; t.text = text; t.color = Color.white;
        go.AddComponent<LayoutElement>().minHeight = size + 8;
        return t;
    }

    void Button(string text, UnityEngine.Events.UnityAction onClick, Transform parent = null)
    {
        var go = DefaultControls.CreateButton(new DefaultControls.Resources());
        go.transform.SetParent(parent ? parent : transform, false);
        var b = go.GetComponent<Button>();
        b.onClick.AddListener(onClick);
        Style(b);
        var t = go.GetComponentInChildren<Text>();
        t.font = font; t.fontSize = 20; t.text = text;
        go.AddComponent<LayoutElement>().minHeight = 44;
    }

    void Toggle(string text, bool on, System.Action<bool> changed)
    {
        var go = DefaultControls.CreateToggle(new DefaultControls.Resources());
        go.transform.SetParent(transform, false);
        var t = go.GetComponentInChildren<Text>();
        t.font = font; t.fontSize = 18; t.text = text; t.color = Color.white;
        var bg = go.transform.Find("Background");
        bg.localScale = Vector3.one * 1.6f;
        bg.Find("Checkmark").GetComponent<Image>().color = Accent;   // default is white on the white box: invisible
        var toggle = go.GetComponent<Toggle>();
        Style(toggle);
        toggle.isOn = on;
        toggle.onValueChanged.AddListener(v => changed(v));
        go.AddComponent<LayoutElement>().minHeight = 40;
    }

    void Slider(string text, float min, float max, float value, System.Action<float> changed)
    {
        var label = Label(text, 18, FontStyle.Normal);
        var go = DefaultControls.CreateSlider(new DefaultControls.Resources());
        go.transform.SetParent(transform, false);
        var s = go.GetComponent<Slider>();
        Style(s);
        go.transform.Find("Background").GetComponent<Image>().color = new Color(0.35f, 0.37f, 0.42f);
        go.transform.Find("Fill Area/Fill").GetComponent<Image>().color = Accent;   // default white fill on white track: invisible
        s.minValue = min; s.maxValue = max; s.value = value;
        s.onValueChanged.AddListener(v =>
        {
            label.text = $"{text}: {Mathf.Round(v)}";
            changed(v);
        });
        go.AddComponent<LayoutElement>().minHeight = 34;
    }
}
