// In-VR test panel: fakes the real-world signals by calling RoomBridge.Apply with the same device/property/value the
// bridge would send, so every mapping can be checked without the lab. Also shows the bridge connection.
// Built in code (uGUI) on a child "Panel", so the scene builder needs no prefab and the Bridge object keeps a plain
// Transform. Each control says which real device it fakes and what to watch in the room.
// Headset: world-space panel whose left edge sits at the Bridge object, clicked with the controller ray (trigger).
// Editor (desktop testing with the XR Interaction Simulator): the same controls as a screen overlay clicked with the
// mouse, P hides/shows it. The bridge IP is edited with -/+ buttons per octet (no keyboard in the headset) and saved
// by RoomBridge.SetUrl; the editor overlay leaves that out (set the url on the RoomBridge component instead).
using System;
using System.Globalization;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.InputSystem;
using UnityEngine.UI;
using UnityEngine.XR.Interaction.Toolkit.UI;

// Update runs after XRInteractionSimulator (-29991), which turns the UI mouse off while it drives a controller, and
// before EventSystem (-1000), so a mouse over the overlay can switch it back on in time for the click.
[DefaultExecutionOrder(-1100)]
public sealed class BridgeTestPanel : MonoBehaviour
{
    [Tooltip("In the editor show the panel as a mouse-clickable screen overlay instead of in the room.")]
    public bool screenOverlayInEditor = true;
    [Tooltip("World size of one UI pixel in metres (headset panel).")]
    public float metresPerPixel = 0.0011f;

    RoomBridge bridge;
    XRUIInputModule module;
    Transform content;
    Text status;
    Font font;
    readonly int[] ip = { 192, 168, 160, 57 };
    int port = 8765;
    const float ColumnWidth = 440;
    static readonly Color Accent = new Color(0.2f, 0.6f, 1f), Hint = new Color(0.65f, 0.72f, 0.8f);

    bool Overlay => Application.isEditor && screenOverlayInEditor;

    void Start()
    {
        bridge = FindObjectOfType<RoomBridge>();
        font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
        if (!FindObjectOfType<EventSystem>()) new GameObject("EventSystem", typeof(EventSystem), typeof(XRUIInputModule));
        if (bridge && Uri.TryCreate(bridge.url, UriKind.Absolute, out var u))
        {
            if (u.Port > 0) port = u.Port;
            var parts = u.Host.Split('.');
            if (parts.Length == 4)
                for (int i = 0; i < 4; i++) if (int.TryParse(parts[i], out var o) && o >= 0 && o <= 255) ip[i] = o;
        }

        var root = new GameObject("Panel", typeof(RectTransform));
        root.transform.SetParent(transform, false);
        var canvas = root.AddComponent<Canvas>();
        if (Overlay)
        {
            canvas.renderMode = RenderMode.ScreenSpaceOverlay;
            var scaler = root.AddComponent<CanvasScaler>();
            scaler.uiScaleMode = CanvasScaler.ScaleMode.ScaleWithScreenSize;
            scaler.referenceResolution = new Vector2(1280, 780);   // ponytail: tuning knob, the panel is ~730 px tall
            scaler.matchWidthOrHeight = 1;
            root.AddComponent<GraphicRaycaster>();                  // mouse
            content = new GameObject("Content", typeof(RectTransform)).transform;
            content.SetParent(root.transform, false);
            var rt = (RectTransform)content;
            rt.anchorMin = rt.anchorMax = rt.pivot = new Vector2(0, 1);   // top-left corner
            rt.anchoredPosition = new Vector2(8, -8);
        }
        else
        {
            canvas.renderMode = RenderMode.WorldSpace;
            root.AddComponent<TrackedDeviceGraphicRaycaster>();     // controller rays
            content = root.transform;
            var rt = (RectTransform)content;
            rt.pivot = new Vector2(0, 0.5f);                        // grows to the right of the Bridge point, beside the board
            rt.localScale = Vector3.one * metresPerPixel;
        }
        content.gameObject.AddComponent<Image>().color = new Color(0.08f, 0.09f, 0.11f, 0.95f);
        Layout<VerticalLayoutGroup>(content.gameObject, 10, 18);
        ((RectTransform)content).sizeDelta = new Vector2(2 * ColumnWidth + 24 + 36, 0);   // fixed width: long texts wrap
        content.gameObject.AddComponent<ContentSizeFitter>().verticalFit = ContentSizeFitter.FitMode.PreferredSize;

        Label(content, "TEST PANEL: pretend to be the real lab", 30, FontStyle.Bold);
        Label(content, Overlay
            ? "Click with the mouse (P hides this panel). Each control sends what the real device would send; " +
              "\"Watch\" says where to look in the room."
            : "Point a controller ray here and pull the trigger to click or drag. Each control sends what the real " +
              "device would send; \"Watch\" says where to look in the room.", 18, FontStyle.Italic).color = Hint;
        status = Label(content, "", 18, FontStyle.Normal);
        status.GetComponent<LayoutElement>().preferredHeight = 50;   // fixed 2 lines, long errors truncate instead of growing

        var columns = new GameObject("Columns", typeof(RectTransform));
        columns.transform.SetParent(content, false);
        Layout<HorizontalLayoutGroup>(columns, 24, 0);
        var lights = Column(columns.transform, "LIGHTS");
        var room = Column(columns.transform, "ROOM");

        Toggle(lights, "Wall dimmer switch ON", true, x => Apply("dimmer1", "on", x),   // RotaryDimmer.power starts true
            "lab ceiling lights on/off (dimmer: board 5)");
        Slider(lights, "Wall dimmer level %", 0, 100, 50, x => Apply("dimmer1", "level", x),
            "ceiling brighter/darker, knob on board 5 turns");
        Toggle(lights, "DALI panel: lights ON", true, x => Apply("dali1", "all_on", x),
            "ceiling lights on/off, DALI screen on board 1");
        Slider(lights, "DALI colour temperature K", 2000, 6500, 4500, x => Apply("dali1", "all_kelvin", x),
            "ceiling colour: 2000 warm orange, 6500 cool white");

        Toggle(room, "Camera sees a person (use case 1)", false, x =>
        {
            Apply("camera1", "occupied", x);
            Apply("virtual_light", "on", x);
        }, "camera on board 3 turns on, ceiling lights on");
        Slider(room, "Curtain open %", 0, 100, 100, x => Apply("curtain1", "position", x),
            "roller blind above board 5 (0 = closed)");
        Slider(room, "Room temperature C", 15, 30, 22, x => Apply("room_sensor1", "temperature", x),
            "displays on board 5 + Siemens unit on board 3");
        Toggle(room, "Temperature alarm (use case 3)", false, x => Apply("room_sensor1", "alarm", x),
            "camera floodlight on board 3");
        Slider(room, "Speaker volume %", 0, 100, 30, x => Apply("speaker1", "volume", x),
            "light ring on the speaker (board 1, bottom right)");

        if (!Overlay)
        {
            Label(content, $"BRIDGE LAPTOP IP (port {port}): set with the buttons, then Apply", 22, FontStyle.Bold).color = Accent;
            OctetRow(content, 0, 1);
            OctetRow(content, 2, 3);
            Button(content, "Apply & reconnect", () => { if (bridge) bridge.SetUrl($"ws://{string.Join(".", ip)}:{port}"); });
        }
    }

    void Apply(string device, string property, float x) =>
        bridge?.Apply(device, property, Mathf.Round(x).ToString(CultureInfo.InvariantCulture));
    void Apply(string device, string property, bool x) => bridge?.Apply(device, property, x ? "true" : "false");

    void Update()
    {
        if (status && bridge) status.text = $"Bridge {bridge.State} ({bridge.url})\nLast: {bridge.LastMessage}";
        if (!Overlay || !content) return;
        if (Keyboard.current != null && Keyboard.current.pKey.wasPressedThisFrame)
            content.gameObject.SetActive(!content.gameObject.activeSelf);
        if (!module) module = FindObjectOfType<XRUIInputModule>();
        if (module && Mouse.current != null && content.gameObject.activeSelf &&
            RectTransformUtility.RectangleContainsScreenPoint((RectTransform)content, Mouse.current.position.ReadValue()))
            module.enableMouseInput = true;   // the simulator turns it off again once the mouse leaves the panel
    }

    // two octets per row: [-10] [-1] 192 [+1] [+10]   [-10] [-1] 168 [+1] [+10]
    void OctetRow(Transform parent, params int[] octets)
    {
        var row = new GameObject("Octets", typeof(RectTransform));
        row.transform.SetParent(parent, false);
        Layout<HorizontalLayoutGroup>(row, 8, 0);
        row.AddComponent<LayoutElement>().minHeight = 54;
        foreach (var i in octets)
        {
            Text value = null;
            foreach (var d in new[] { -10, -1, 0, 1, 10 })
            {
                if (d == 0) { value = Label(row.transform, ip[i].ToString(), 28, FontStyle.Bold); value.alignment = TextAnchor.MiddleCenter; continue; }
                Button(row.transform, d > 0 ? "+" + d : d.ToString(), () => { ip[i] = Mathf.Clamp(ip[i] + d, 0, 255); value.text = ip[i].ToString(); });
            }
        }
    }

    // ---------- tiny uGUI builders ----------

    static void Layout<T>(GameObject go, float spacing, int padding) where T : HorizontalOrVerticalLayoutGroup
    {
        var l = go.AddComponent<T>();
        l.spacing = spacing;
        l.padding = new RectOffset(padding, padding, padding, padding);
        l.childControlHeight = l.childControlWidth = true;
        l.childForceExpandHeight = false;
    }

    Transform Column(Transform parent, string title)
    {
        var go = new GameObject(title, typeof(RectTransform));
        go.transform.SetParent(parent, false);
        Layout<VerticalLayoutGroup>(go, 6, 0);
        go.AddComponent<LayoutElement>().preferredWidth = ColumnWidth;
        Label(go.transform, title, 22, FontStyle.Bold).color = Accent;
        return go.transform;
    }

    // DefaultControls with empty Resources = plain white images: blue hover/press so the ray target is obvious
    static void Style(Selectable s)
    {
        var c = s.colors;
        c.highlightedColor = new Color(0.65f, 0.85f, 1f);
        c.pressedColor = Accent;
        s.colors = c;
    }

    Text Label(Transform parent, string text, int size, FontStyle style)
    {
        var go = new GameObject("Label", typeof(RectTransform));
        go.transform.SetParent(parent, false);
        var t = go.AddComponent<Text>();
        t.font = font; t.fontSize = size; t.fontStyle = style; t.text = text; t.color = Color.white;
        go.AddComponent<LayoutElement>().minHeight = size + 8;
        return t;
    }

    void Button(Transform parent, string text, UnityEngine.Events.UnityAction onClick)
    {
        var go = DefaultControls.CreateButton(new DefaultControls.Resources());
        go.transform.SetParent(parent, false);
        var b = go.GetComponent<Button>();
        b.onClick.AddListener(onClick);
        Style(b);
        var t = go.GetComponentInChildren<Text>();
        t.font = font; t.fontSize = 22; t.text = text;
        go.AddComponent<LayoutElement>().minHeight = 54;
    }

    void Toggle(Transform parent, string text, bool on, Action<bool> changed, string watch)
    {
        var go = DefaultControls.CreateToggle(new DefaultControls.Resources());
        go.transform.SetParent(parent, false);
        var t = go.GetComponentInChildren<Text>();
        t.font = font; t.fontSize = 22; t.text = text; t.color = Color.white;
        ((RectTransform)t.transform).offsetMin = new Vector2(46, 0);   // room for the bigger box
        var bg = (RectTransform)go.transform.Find("Background");
        bg.sizeDelta = new Vector2(34, 34);
        bg.anchoredPosition = new Vector2(17, -21);
        var check = (RectTransform)bg.Find("Checkmark");
        check.sizeDelta = new Vector2(30, 30);
        check.GetComponent<Image>().color = Accent;   // default is white on the white box: invisible
        var toggle = go.GetComponent<Toggle>();
        Style(toggle);
        toggle.isOn = on;
        toggle.onValueChanged.AddListener(x => changed(x));
        go.AddComponent<LayoutElement>().minHeight = 42;
        Watch(parent, watch);
    }

    void Slider(Transform parent, string text, float min, float max, float value, Action<float> changed, string watch)
    {
        var label = Label(parent, $"{text}: {value}", 22, FontStyle.Normal);
        var go = DefaultControls.CreateSlider(new DefaultControls.Resources());
        go.transform.SetParent(parent, false);
        var s = go.GetComponent<Slider>();
        Style(s);
        go.transform.Find("Background").GetComponent<Image>().color = new Color(0.35f, 0.37f, 0.42f);
        go.transform.Find("Fill Area/Fill").GetComponent<Image>().color = Accent;   // default white fill on white track: invisible
        ((RectTransform)go.transform.Find("Handle Slide Area/Handle")).sizeDelta = new Vector2(36, 0);   // bigger grab target
        s.minValue = min; s.maxValue = max; s.value = value;
        s.onValueChanged.AddListener(x =>
        {
            label.text = $"{text}: {Mathf.Round(x)}";
            changed(x);
        });
        go.AddComponent<LayoutElement>().minHeight = 40;
        Watch(parent, watch);
    }

    void Watch(Transform parent, string text) => Label(parent, "Watch: " + text, 17, FontStyle.Italic).color = Hint;
}
