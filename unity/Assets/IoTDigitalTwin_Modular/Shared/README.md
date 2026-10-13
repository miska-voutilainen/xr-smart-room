# Shared dependencies

Import this directory once, beside the device folders. It compiles without any of the nine concrete controllers or Demo.

Scripts: IoTDevice state/events and pose helpers; DeviceMath pure clamping/capsule/blind calculations; DeviceContracts IBlindControl and IPointerInputGate; DevicePointerTarget collider/UV mapping; IoTMouseInput mouse capture/dispatch; DynamicReadout runtime glyph mesh; BeadChainMotion grouped island motion. The optional inputGate accepts a MonoBehaviour implementing IPointerInputGate; leave empty outside the demo.

Editor/IoTAssetGenerator.cs discovers its location through AssetDatabase, then searches that library root for Materials/DeviceDefinition.json. Per-device InitializeOnLoad builders register themselves. Materials and generated mesh paths come from the discovered device folder, not hard-coded Assets paths. Demo registration is optional and lives in Demo/Editor. Full-demo generation requires all nine; partial generation uses available builders only.

Shaders/DeviceDisplay.shader and Textures/Runtime_FontAtlas.png are shared by all dynamic screens. Configuration/Runtime_FontAtlas.json supplies glyph metrics; the generator serializes these into each readout, so runtime has no filesystem dependency. The font material is generated once under Materials/Generated. Keep the DejaVu font license with redistributed assets.

No networking is implemented. Editor scripts stay under Editor/ folders and are excluded from players. Verification~/ test doubles must never be moved into active Unity script folders.
