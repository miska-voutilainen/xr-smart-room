// The lab's RGB ceiling lights (concept.md, "Ceiling lights"): on/off and colour from the DALI panel, brightness from
// the dimmer. Reads the two virtual devices, so it follows the bridge, the test panel and local XR input alike.
// The LED area lights are baked (URP: rectangle lights are baked-only) at a reduced level, so the lab never goes
// fully dark; these realtime point lights (no shadows) add the part that changes, plus the emissive panels.
using IoTDigitalTwin;
using UnityEngine;

public sealed class CeilingLights : MonoBehaviour
{
    public Light[] lights;          // realtime, set up by OrangeRoomSceneBuilder
    public Renderer[] panels;       // Room2_LED_Panel meshes
    [Tooltip("Spot light intensity at full brightness. Build Scene overwrites it with OrangeRoomSceneBuilder.LabRealtime.")]
    public float intensity = 3f;
    public float speed = 6f;

    RotaryDimmer dimmer; DALILightingPanel dali;
    MaterialPropertyBlock block;
    int[] slots;                    // per panel: the Light_LED_Diffuser material index, -1 = none
    float shown = 1f, blockShown = -1f;
    Color shownColor = Color.white, blockColor;

    void Awake()
    {
        dimmer = FindObjectOfType<RotaryDimmer>();
        dali = FindObjectOfType<DALILightingPanel>();
        // tint only the diffuser slot: LightingOutput would also darken the Room2_Aluminium frame (second slot)
        block = new MaterialPropertyBlock();
        slots = new int[panels.Length];
        for (int i = 0; i < panels.Length; i++)
            slots[i] = System.Array.FindIndex(panels[i].sharedMaterials, m => m && m.name.StartsWith("Light_LED_Diffuser"));
    }

    void Update()
    {
        bool on = dali == null || dali.Power;
        float level = dimmer == null ? 1f : (dimmer.Power ? dimmer.Brightness : 0f);
        Color color = dali == null ? Color.white : dali.SelectedColor;
        float k = 1 - Mathf.Exp(-speed * Time.deltaTime);
        shown = Mathf.Lerp(shown, on ? level : 0f, k);
        shownColor = Color.Lerp(shownColor, color, k);
        foreach (var l in lights)
        {
            l.color = shownColor;
            l.intensity = shown * intensity;
            l.enabled = shown > 0.001f;
        }
        if (Mathf.Abs(shown - blockShown) < 0.001f && shownColor == blockColor) return;   // eased value settled
        blockShown = shown; blockColor = shownColor;
        var c = Color.Lerp(new Color(.06f, .07f, .08f), shownColor, shown);
        block.SetColor("_Color", c);
        block.SetColor("_BaseColor", c);
        block.SetColor("_EmissionColor", shownColor * shown);   // x1, not LightingOutput's x2: HDR is off, x2 clips from 50 %
        for (int i = 0; i < panels.Length; i++)
            if (slots[i] >= 0) panels[i].SetPropertyBlock(block, slots[i]);
    }
}
