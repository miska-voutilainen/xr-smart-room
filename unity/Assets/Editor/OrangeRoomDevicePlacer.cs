// Menu OrangeRoom > Place IoT Devices: puts the IoT library prefabs (Assets/IoTDigitalTwin_Modular, generated with
// Tools > IoT Digital Twin > Generate Prefabs and Demo) on the lab demo boards of the open scene. Run it after
// OrangeRoom > Build Scene; re-running replaces the "IoT_Devices" root.
// Positions: board face centre/normal/size measured in main.blend (Room2_Demo_Boards faces, Blender world metres),
// device spot = fraction of the board photo (textures/s1_lab/board_<n>.jpg, x from the left, y from the top), the
// same photos the board textures are made from. XR: each device root gets an XRSimpleInteractable (hover/select on
// the generator's trigger colliders); wiring select -> controller setters is the next step (README, Next Steps).
using System;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

static class OrangeRoomDevicePlacer
{
    // Blender (right-handed, Z up) -> Unity for Blender's default FBX export (-Z forward, Y up) + bakeAxisConversion.
    // Calibration knob: the menu logs how far Kitchen_Board lands from this mapping; fix it here if that is not ~0.
    static Vector3 B2U(float x, float y, float z) => new Vector3(-x, z, -y);

    struct Board { public Vector3 c, n, right; public float w, h; }

    static Board MakeBoard(Vector3 cB, Vector3 nB, float w, float h)
    {
        var n = B2U(nB.x, nB.y, nB.z);
        var c = B2U(cB.x, cB.y, cB.z);
        // seen from the front (looking along -n), "right" in the photo
        return new Board { c = c, n = n, right = Vector3.Cross(Vector3.up, -n).normalized, w = w, h = h };
    }

    // Room2_Demo_Boards front faces (Blender world): centre, normal, width, height
    static readonly Board Board1 = MakeBoard(new Vector3(5.65f, 5.20f, 1.40f), new Vector3(-1, 0, 0), 1.50f, 1.02f);
    static readonly Board Board3 = MakeBoard(new Vector3(0.60f, 8.30f, 1.40f), new Vector3(1, 0, 0), 1.30f, 1.02f);
    static readonly Board Board5 = MakeBoard(new Vector3(0.65f, 5.075f, 1.405f), new Vector3(1, 0, 0), 1.25f, 0.97f);

    // prefab stem, board, photo fraction x/y (0..1 from top-left), what / where it is
    static readonly (string stem, Board b, float fx, float fy, string note)[] Devices =
    {
        ("01_Zigbee_Rotary_Dimmer",        Board5, 0.34f, 0.88f, "dimmer1: Aqara Dimmer Switch H2, board 5 bottom row (Photos/3 151018)"),
        ("02_Zigbee_Temperature_LCD",      Board5, 0.41f, 0.88f, "Aqara T/H display next to it, board 5 bottom row (151018)"),
        ("03_ZWave_Temperature_Controller",Board5, 0.49f, 0.86f, "no bridge device; round unit on board 5 bottom row, unverified (151018)"),
        ("04_Security_Camera",             Board3, 0.26f, 0.14f, "camera1: camera on board 3 top left, label 'Kaamera' (151124)"),
        ("05_Aqara_Bead_Chain_Controller", Board5, 0.63f, 0.10f, "curtain1 actuator: Aqara driver on the rail on top of board 5 (151018)"),
        ("06_Roller_Blind_Mechanism",      Board1, 0.52f, 0.08f, "roller blind 'Mootor' on top of board 1 (151022)"),
        ("07_Siemens_BACnet_Device",       Board3, 0.79f, 0.14f, "room_sensor1: KNX room unit read through the Siemens BACnet gateway, board 3 top right (151124)"),
        ("08_Nest_Smart_Speaker",          Board1, 0.90f, 0.92f, "speaker1 alt.: Google Nest 'Dali stand WhiteNest', board 1 bottom right (151022)"),
        ("09_DALI_Touchscreen_Panel",      Board1, 0.33f, 0.72f, "dali1: Lunatone DALI-2 Display 'DALI puutepaneel', board 1 (151022)"),
    };

    const float FrontOffset = 0.02f;   // m in front of the board face

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

        var simple = Type.GetType("UnityEngine.XR.Interaction.Toolkit.Interactables.XRSimpleInteractable, Unity.XR.Interaction.Toolkit");
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
            var b = d.b;
            go.transform.position = b.c + b.right * ((d.fx - 0.5f) * b.w) + Vector3.up * ((0.5f - d.fy) * b.h) + b.n * FrontOffset;
            go.transform.rotation = Quaternion.LookRotation(b.n, Vector3.up);   // library prefabs: Z = front
            if (simple != null && go.GetComponent(simple) == null) go.AddComponent(simple);
            placed++;
            Debug.Log($"[OrangeRoom] {d.stem} -> {go.transform.position}  ({d.note})");
        }
        if (simple == null) Debug.LogWarning("[OrangeRoom] XR Interaction Toolkit 3.x not found: devices placed without interactables.");
        EditorSceneManager.MarkSceneDirty(root.scene);
        Debug.Log($"[OrangeRoom] Placed {placed}/{Devices.Length} IoT devices. Save the scene.");
    }
}
