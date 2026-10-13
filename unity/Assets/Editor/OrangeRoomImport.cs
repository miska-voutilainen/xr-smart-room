// Import rules for the Blender export (unity/export_unity.py -> Assets/Models/*.fbx, Assets/Textures/*.png).
// Unity 2022.3 + URP 14. Editor only.
using UnityEditor;
using UnityEditor.AssetImporters;
using UnityEngine;
using UnityEngine.Rendering;

public class OrangeRoomImport : AssetPostprocessor
{
    const string Models = "Assets/Models/";
    const string Textures = "Assets/Textures/";
    const string Ext = ".png"; // ponytail: export contract is PNG only; add .exr/.tga here if g3_export changes it

    bool IsOurs(string dir) => assetPath.StartsWith(dir);

    void OnPreprocessModel()
    {
        if (!IsOurs(Models)) return;
        var m = (ModelImporter)assetImporter;
        m.globalScale = 1f;
        m.useFileScale = true;          // Blender FBX "FBX Units Scale" -> 1 unit = 1 m
        m.bakeAxisConversion = true;    // no -90 deg X on every node
        m.importCameras = false;
        m.importLights = false;         // lights are rebuilt by OrangeRoomSceneBuilder (Blender W do not map)
        m.importBlendShapes = false;
        m.importVisibility = false;
        m.animationType = ModelImporterAnimationType.None;
        m.importAnimation = false;
        m.importNormals = ModelImporterNormals.Import;   // keep Blender bevel / custom normals
        m.importTangents = ModelImporterTangents.CalculateMikk;
        m.meshCompression = ModelImporterMeshCompression.Off;
        m.isReadable = false;
        m.optimizeMeshPolygons = true;
        m.optimizeMeshVertices = true;
        m.addCollider = false;          // the scene builder decides collider type per object
        m.generateSecondaryUV = false;  // lightmap UV2 comes from g3_export; fallback in OnPostprocessModel
        m.materialImportMode = ModelImporterMaterialImportMode.ImportViaMaterialDescription;
        m.materialLocation = ModelImporterMaterialLocation.InPrefab;
    }

    // Fallback only: unwrap meshes that arrived without UV2 so baking still works.
    void OnPostprocessModel(GameObject root)
    {
        if (!IsOurs(Models)) return;
        foreach (var mf in root.GetComponentsInChildren<MeshFilter>(true))
        {
            var mesh = mf.sharedMesh;
            if (mesh == null || mesh.uv2.Length > 0) continue;
            if (Unwrapping.GenerateSecondaryUVSet(mesh))
                Debug.LogWarning($"[OrangeRoom] {assetPath}: '{mf.name}' had no UV2, generated lightmap UVs.");
            else
                Debug.LogError($"[OrangeRoom] {assetPath}: '{mf.name}' has no UV2 and unwrap failed.");
        }
    }

    void OnPreprocessTexture()
    {
        if (!IsOurs(Textures)) return;
        var t = (TextureImporter)assetImporter;
        var name = System.IO.Path.GetFileNameWithoutExtension(assetPath);
        t.maxTextureSize = 2048;
        t.mipmapEnabled = true;
        if (name.EndsWith("_Normal"))
            t.textureType = TextureImporterType.NormalMap;
        else if (name.EndsWith("_MetallicSmoothness") || name.EndsWith("_AO"))
            t.sRGBTexture = false;      // data, not colour
    }

    // FBX material -> URP/Lit, textures by name: <mat>_BaseColor/_Normal/_MetallicSmoothness/_AO/_Emission.png
    void OnPreprocessMaterialDescription(MaterialDescription d, Material mat, AnimationClip[] clips)
    {
        if (!IsOurs(Models)) return;
        var lit = Shader.Find("Universal Render Pipeline/Lit");
        if (lit == null) { Debug.LogError("[OrangeRoom] URP not installed, materials left as imported."); return; }
        mat.shader = lit;
        var n = d.materialName;

        if (d.TryGetProperty("DiffuseColor", out Vector4 c))
            mat.SetColor("_BaseColor", new Color(c.x, c.y, c.z, 1f));
        mat.SetFloat("_Smoothness", 0.5f);
        mat.SetFloat("_Metallic", 0f);

        var baseMap = Tex(n, "_BaseColor");
        if (baseMap) { mat.SetTexture("_BaseMap", baseMap); mat.SetColor("_BaseColor", Color.white); }

        var normal = Tex(n, "_Normal");
        if (normal) { mat.SetTexture("_BumpMap", normal); mat.SetFloat("_BumpScale", 1f); mat.EnableKeyword("_NORMALMAP"); }

        var ms = Tex(n, "_MetallicSmoothness");     // R = metallic, A = smoothness (1 - Blender roughness)
        if (ms)
        {
            mat.SetTexture("_MetallicGlossMap", ms);
            mat.SetFloat("_SmoothnessTextureChannel", 0f);
            mat.SetFloat("_Smoothness", 1f);         // multiplier on the map's alpha
            mat.EnableKeyword("_METALLICSPECGLOSSMAP");
        }

        var ao = Tex(n, "_AO");                      // URP reads G
        if (ao) { mat.SetTexture("_OcclusionMap", ao); mat.SetFloat("_OcclusionStrength", 1f); mat.EnableKeyword("_OCCLUSIONMAP"); }

        var em = Tex(n, "_Emission");
        if (em)
        {
            mat.SetTexture("_EmissionMap", em);
            mat.SetColor("_EmissionColor", Color.white);
            mat.EnableKeyword("_EMISSION");
            mat.globalIlluminationFlags = MaterialGlobalIlluminationFlags.BakedEmissive;  // LED panels light the bake
        }

        if (n.Contains("Glass")) MakeGlass(mat);
    }

    Texture Tex(string mat, string suffix)
    {
        var path = Textures + mat + suffix + Ext;
        context.DependsOnArtifact(path);   // registered even if missing: model reimports when the texture arrives
        return AssetDatabase.LoadAssetAtPath<Texture>(path);
    }

    // URP/Lit transparent, premultiplied (keeps specular reflections on glass).
    static void MakeGlass(Material m)
    {
        var col = m.GetColor("_BaseColor");
        m.SetColor("_BaseColor", new Color(col.r, col.g, col.b, 0.12f));   // ponytail: fixed alpha, tune per glass if needed
        m.SetFloat("_Smoothness", 0.95f);
        m.SetFloat("_Surface", 1f);
        m.SetFloat("_Blend", 1f);                                          // Premultiply
        m.SetFloat("_SrcBlend", (float)BlendMode.One);
        m.SetFloat("_DstBlend", (float)BlendMode.OneMinusSrcAlpha);
        m.SetFloat("_SrcBlendAlpha", (float)BlendMode.One);
        m.SetFloat("_DstBlendAlpha", (float)BlendMode.OneMinusSrcAlpha);
        m.SetFloat("_ZWrite", 0f);
        m.EnableKeyword("_SURFACE_TYPE_TRANSPARENT");
        m.EnableKeyword("_ALPHAPREMULTIPLY_ON");
        m.SetOverrideTag("RenderType", "Transparent");
        m.renderQueue = (int)RenderQueue.Transparent;
        m.SetShaderPassEnabled("DepthOnly", false);
    }
}
