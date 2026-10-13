# Material setup

DeviceDefinition.json contains source material colours, metallic/roughness settings, emission and texture mappings extracted from the original Blender model. The prefab generator builds persistent Unity materials in Generated/ for Standard or URP/Lit and assigns every mesh material slot. Runtime-specific display materials also live here; the display font material is shared. Preserve generated .meta files when moving assets.
