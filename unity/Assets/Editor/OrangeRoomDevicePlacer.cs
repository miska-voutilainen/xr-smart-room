// Menu OrangeRoom > Place IoT Devices: puts the IoT library prefabs (Assets/IoTDigitalTwin_Modular, generated with
// Tools > IoT Digital Twin > Generate Prefabs and Demo) on one wall of the open scene. Run it after
// OrangeRoom > Build Scene; re-running replaces the "IoT_Devices" root.
// Where: Room1 (two chairs, window), the partition wall to the lab, between the passage to the lab (Blender x 1.00-2.50)
// and the TV niche (x 4.07-5.50); interior face y = 2.50, facing -y into Room1 (main.blend, Blender world metres).
// The lab demo boards stay blank. Seven real lab devices (docs/README.md): dimmer, DALI panel, curtain (blind + its
// Aqara chain controller), camera, room sensor (Siemens unit), speaker, temperature display. 03 Z-Wave has no lab device.
// XR: each device root gets an XRGrabInteractable that only rotates (grab it with the grip and turn it in place) and an
// XRDeviceInput (far ray on a control = press/drag that control instead of rotating). Also adds the "Bridge" object:
// RoomBridge (WebSocket to bridge/server.py, URL from env ORANGE_BRIDGE_URL at build time) + its panel on the TV.
using System;
using IoTDigitalTwin;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.XR.Interaction.Toolkit.Interactables;

static class OrangeRoomDevicePlacer
{
    // Blender (right-handed, Z up) -> Unity for Blender's default FBX export (-Z forward, Y up) + bakeAxisConversion.
    // Calibration knob: the menu logs how far Kitchen_Board lands from this mapping; fix it here if that is not ~0.
    // Measured in 2022.3.62f3: Kitchen_Board lands at (x, z, y) (the old (-x, z, -y) was 1.913 m off).
    static Vector3 B2U(float x, float y, float z) => new Vector3(x, z, y);

    const float WallY = 2.50f;                                  // Room1 face of Wall_Top (Blender y)
    static readonly Vector3 WallNormal = B2U(0, -1, 0);         // into Room1
    // TV (manifest bbox x 4.247-5.297, y 2.475 front, z 1.138-1.738): the bridge panel's centre, 1 cm in front of the screen
    static readonly Vector3 TvCentre = B2U(4.772f, 2.465f, 1.438f);

    // prefab stem, Blender x (left = passage 2.50, right = TV niche 4.07, seen from Room1) and z of the device root, note.
    // Blind root = its roller; its bead chain hangs 0.8 m on the passage side, its cloth 0.45 m below the roller.
    static readonly (string stem, float x, float z, string note)[] Devices =
    {
        ("06_Roller_Blind_Mechanism",      3.25f, 2.30f, "curtain1: roller blind, top of the wall (cloth + chain down to ~1.5 m)"),
        ("05_Aqara_Bead_Chain_Controller", 3.95f, 1.75f, "curtain1: Aqara chain controller (Raise/Lower), right of the blind"),
        ("09_DALI_Touchscreen_Panel",      2.90f, 1.35f, "dali1: Lunatone DALI-2 Display"),
        ("07_Siemens_BACnet_Device",       3.30f, 1.35f, "room_sensor1: KNX room unit via the Siemens BACnet gateway"),
        ("02_Zigbee_Temperature_LCD",      3.65f, 1.35f, "room_sensor1 temperature/humidity: Aqara T/H display"),
        ("01_Zigbee_Rotary_Dimmer",        2.90f, 1.05f, "dimmer1: Aqara Dimmer Switch H2"),
        ("04_Security_Camera",             3.30f, 1.05f, "camera1: Aqara camera G5"),
        ("08_Nest_Smart_Speaker",          3.65f, 1.05f, "speaker1: Google Nest / Sonos"),
    };

    const float FrontOffset = 0.01f;   // m in front of the wall face

    [MenuItem("OrangeRoom/Place IoT Devices")]
    static void Place()
    {
        var old = GameObject.Find("IoT_Devices");
        if (old != null) UnityEngine.Object.DestroyImmediate(old);
        var root = new GameObject("IoT_Devices");

        var kb = GameObject.Find("Kitchen_Board");   // calibration check of B2U (Blender bbox centre 0.9425, 0.1645, 1.28)
        var r = kb != null ? kb.GetComponentInChildren<Renderer>() : null;
        if (r != null)
            Debug.Log($"[OrangeRoom] B2U check: Kitchen_Board off by {Vector3.Distance(r.bounds.center, B2U(0.9425f, 0.1645f, 1.28f)):F3} m");

        int placed = 0;
        foreach (var d in Devices)
        {
            var guids = AssetDatabase.FindAssets(d.stem + " t:Prefab");
            if (guids.Length == 0)
            {
                Debug.LogWarning($"[OrangeRoom] Prefab {d.stem} missing: run Tools > IoT Digital Twin > Generate Prefabs and Demo first.");
                continue;
            }
            var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(AssetDatabase.GUIDToAssetPath(guids[0]));
            var go = (GameObject)PrefabUtility.InstantiatePrefab(prefab, root.transform);
            go.transform.position = B2U(d.x, WallY, d.z) + WallNormal * FrontOffset;
            go.transform.rotation = Quaternion.LookRotation(WallNormal, Vector3.up);   // library prefabs: Z = front
            // body box for the hand/ray grab: the hit zones are 2 mm trigger plates, too thin to grab by hand.
            // Computed before the Rigidbody exists; the device is axis-aligned here, so the world AABB is the local box.
            var bounds = new Bounds(go.transform.position, Vector3.zero);
            foreach (var rr in go.GetComponentsInChildren<Renderer>(true)) bounds.Encapsulate(rr.bounds);
            var box = go.AddComponent<BoxCollider>();
            box.center = go.transform.InverseTransformPoint(bounds.center);
            var size = go.transform.InverseTransformVector(bounds.size);
            box.size = new Vector3(Mathf.Abs(size.x), Mathf.Abs(size.y), Mathf.Abs(size.z));
            // grab = rotate in place: kinematic, no position tracking, no throw. Dynamic attach keeps the grab offset,
            // so the device turns with the hand instead of snapping to the controller's orientation.
            var grab = go.AddComponent<XRGrabInteractable>();
            var body = go.GetComponent<Rigidbody>();
            body.isKinematic = true;
            body.useGravity = false;
            grab.movementType = XRBaseInteractable.MovementType.Kinematic;
            grab.trackPosition = false;
            grab.trackRotation = true;
            grab.trackScale = false;
            grab.throwOnDetach = false;
            grab.useDynamicAttach = true;
            grab.matchAttachPosition = true;
            grab.matchAttachRotation = true;
            // the hit zones are triggers, which XRBaseInteractable.Awake drops from an empty list: serialize them by hand
            grab.colliders.Add(box);
            foreach (var t in go.GetComponentsInChildren<DevicePointerTarget>(true))
                if (t.TryGetComponent<Collider>(out var col) && !grab.colliders.Contains(col)) grab.colliders.Add(col);
            go.AddComponent<XRDeviceInput>();
            // start the blind raised so it does not cover the wall (the bridge's curtain1.position takes over)
            var blind = go.GetComponentInChildren<IoTDigitalTwin.RollerBlindDevice>();
            if (blind)
            {
                blind.currentOpenPercent = blind.targetOpenPercent = 100;   // runtime: Awake applies the pose
                blind.cloth.SetBlendShapeWeight(blind.blendShapeIndex, blind.fullyRaisedWeight);   // edit mode (bake, snapshots)
            }
            placed++;
            Debug.Log($"[OrangeRoom] {d.stem} -> {go.transform.position}, grab box {box.size}  ({d.note})");
        }
        // plain Transform: a RectTransform under a non-UI parent lost its x/y when the scene was saved (panel on the floor).
        // BridgeTestPanel builds its canvas on a child.
        var bridge = new GameObject("Bridge");
        bridge.transform.SetParent(root.transform);
        var rb = bridge.AddComponent<RoomBridge>();
        var url = Environment.GetEnvironmentVariable("ORANGE_BRIDGE_URL");
        if (!string.IsNullOrEmpty(url)) rb.url = url;
        bridge.AddComponent<BridgeTestPanel>();
        // panel on the TV: this point = the TV screen centre (1.05 x 0.60 m), 1 cm in front of it
        bridge.transform.position = TvCentre;
        bridge.transform.rotation = Quaternion.LookRotation(-WallNormal, Vector3.up);   // uGUI faces -Z
        Debug.Log($"[OrangeRoom] Bridge {rb.url}, panel at {bridge.transform.position}");

        EditorSceneManager.MarkSceneDirty(root.scene);
        Debug.Log($"[OrangeRoom] Placed {placed}/{Devices.Length} IoT devices. Save the scene.");
    }
}
