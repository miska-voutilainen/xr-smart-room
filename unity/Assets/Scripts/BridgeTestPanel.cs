// Bridge screen on the Room1 TV (wall between Room1 and the lab): connection status, the bridge laptop IP editor and a
// read-only line per real lab device, filled from RoomBridge.Applied (what the bridge last sent, nothing faked).
// Built in code (uGUI) on a child "Panel", so the scene builder needs no prefab and the Bridge object keeps a plain
// Transform. At start the panel moves onto the front face of the "TV" mesh (Room1.fbx); without one it stays centred on
// the Bridge object. Clicked with the controller ray (trigger). The IP is edited with -/+ buttons per octet (no
// keyboard in the headset) and saved by RoomBridge.SetUrl.
using System;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.UI;
using UnityEngine.XR.Interaction.Toolkit.UI;

public sealed class BridgeTestPanel : MonoBehaviour
{
    [Tooltip("World size of one UI pixel in metres. 1000 x 560 px = 1.00 x 0.56 m, the TV is 1.05 x 0.60 m.")]
    public float metresPerPixel = 0.001f;

    RoomBridge bridge;
    Text status, last, live;
    Font font;
    readonly int[] ip = { 192, 168, 160, 57 };
    int port = 8765;
    readonly Dictionary<string, string> values = new Dictionary<string, string>();   // "device.property" -> last value
    static readonly Color Accent = new Color(0.2f, 0.6f, 1f), Hint = new Color(0.65f, 0.72f, 0.8f);

    void Start()
    {
        bridge = FindObjectOfType<RoomBridge>();
        font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
        if (!FindObjectOfType<EventSystem>()) new GameObject("EventSystem", typeof(EventSystem), typeof(XRUIInputModule));
        if (bridge)
        {
            bridge.Applied += (d, p, v) => values[d + "." + p] = v;
            if (Uri.TryCreate(bridge.url, UriKind.Absolute, out var u))
            {
                if (u.Port > 0) port = u.Port;
                var parts = u.Host.Split('.');
                if (parts.Length == 4)
                    for (int i = 0; i < 4; i++) if (int.TryParse(parts[i], out var o) && o >= 0 && o <= 255) ip[i] = o;
            }
        }

        var root = new GameObject("Panel", typeof(RectTransform));
        root.transform.SetParent(transform, false);
        root.AddComponent<Canvas>().renderMode = RenderMode.WorldSpace;
        root.AddComponent<TrackedDeviceGraphicRaycaster>();   // controller rays
        var rt = (RectTransform)root.transform;
        rt.sizeDelta = new Vector2(1000, 560);
        rt.localScale = Vector3.one * metresPerPixel;
        var tv = GameObject.Find("TV");
        if (tv && tv.GetComponentInChildren<Renderer>() is Renderer r)
        {
            // the TV faces Room1 = Unity -Z (Blender -Y); a world-space canvas is read from -Z with identity rotation.
            // ponytail: assumes the TV stays axis-aligned on that wall; use its transform if it ever moves
            var b = r.bounds;
            root.transform.SetPositionAndRotation(new Vector3(b.center.x, b.center.y, b.min.z - 0.005f), Quaternion.identity);
        }
        else Debug.LogWarning("[OrangeRoom] No 'TV' mesh: bridge screen stays at the Bridge object.");

        root.AddComponent<Image>().color = new Color(0.06f, 0.07f, 0.09f, 1f);
        Layout<VerticalLayoutGroup>(root, 6, 20);

        Label(root.transform, "BRIDGE", 40, FontStyle.Bold);
        status = Label(root.transform, "", 30, FontStyle.Bold);
        last = Label(root.transform, "", 20, FontStyle.Normal);
        last.color = Hint;
        last.verticalOverflow = VerticalWrapMode.Truncate;   // long errors cut off instead of pushing the layout down
        last.GetComponent<LayoutElement>().preferredHeight = 26;

        var columns = new GameObject("Columns", typeof(RectTransform));
        columns.transform.SetParent(root.transform, false);
        Layout<HorizontalLayoutGroup>(columns, 24, 0);
        var left = Column(columns.transform, $"LAPTOP IP (port {port}): set, then Apply", 520);
        var right = Column(columns.transform, "LIVE FROM THE LAB", 416);

        for (int i = 0; i < 4; i++) OctetRow(left, i);
        Button(left, "Apply & reconnect", () => { if (bridge) bridge.SetUrl($"ws://{string.Join(".", ip)}:{port}"); });
        live = Label(right, "", 24, FontStyle.Normal);
    }

    string V(string key) => values.TryGetValue(key, out var v) ? v : "-";
    string Dali(string p) => values.ContainsKey("dali1.all_" + p) ? V("dali1.all_" + p) : V("dali1.group0_" + p);

    void Update()
    {
        if (!status || !bridge) return;
        status.text = $"{bridge.State.ToUpperInvariant()}   {bridge.url}";
        status.color = bridge.State == "online" ? new Color(0.3f, 0.9f, 0.4f) : bridge.State == "connecting" ? new Color(1f, 0.8f, 0.2f) : new Color(1f, 0.35f, 0.3f);
        last.text = "Last: " + bridge.LastMessage;
        live.text =
            $"Curtain   {V("curtain1.position")} % open\n" +
            $"Dimmer    {V("dimmer1.on")}, {V("dimmer1.level")} %\n" +
            $"DALI      {Dali("on")}, {Dali("kelvin")} K\n" +
            $"Room      {V("room_sensor1.temperature")} °C, {V("room_sensor1.humidity")} %\n" +
            $"Camera    person: {V("camera1.occupied")}\n" +
            $"Motion    {V("motion1.motion")}, {V("motion1.illuminance")} lx\n" +
            $"Speaker   {V("speaker1.state")}, vol {V("speaker1.volume")}";
    }

    // one octet per row: [-10] [-1] 192 [+1] [+10]
    void OctetRow(Transform parent, int i)
    {
        var row = new GameObject("Octet" + i, typeof(RectTransform));
        row.transform.SetParent(parent, false);
        Layout<HorizontalLayoutGroup>(row, 8, 0);
        row.AddComponent<LayoutElement>().minHeight = 54;
        Text value = null;
        foreach (var d in new[] { -10, -1, 0, 1, 10 })
        {
            if (d == 0) { value = Label(row.transform, ip[i].ToString(), 32, FontStyle.Bold); value.alignment = TextAnchor.MiddleCenter; continue; }
            Button(row.transform, d > 0 ? "+" + d : d.ToString(), () => { ip[i] = Mathf.Clamp(ip[i] + d, 0, 255); value.text = ip[i].ToString(); });
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

    Transform Column(Transform parent, string title, float width)
    {
        var go = new GameObject(title, typeof(RectTransform));
        go.transform.SetParent(parent, false);
        Layout<VerticalLayoutGroup>(go, 6, 0);
        go.AddComponent<LayoutElement>().preferredWidth = width;
        Label(go.transform, title, 22, FontStyle.Bold).color = Accent;
        return go.transform;
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

    // DefaultControls with empty Resources = plain white images: blue hover/press so the ray target is obvious
    void Button(Transform parent, string text, UnityEngine.Events.UnityAction onClick)
    {
        var go = DefaultControls.CreateButton(new DefaultControls.Resources());
        go.transform.SetParent(parent, false);
        var b = go.GetComponent<Button>();
        b.onClick.AddListener(onClick);
        var c = b.colors;
        c.highlightedColor = new Color(0.65f, 0.85f, 1f);
        c.pressedColor = Accent;
        b.colors = c;
        var t = go.GetComponentInChildren<Text>();
        t.font = font; t.fontSize = 28; t.text = text;
        go.AddComponent<LayoutElement>().minHeight = 54;
    }
}
