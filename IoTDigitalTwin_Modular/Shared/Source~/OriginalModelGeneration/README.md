# Rebuilding the assets

Runtime used: Blender 4.0.2, Python 3.12, NumPy, Pillow and DejaVu Sans fonts. The final assets require no Python scripts in Unity.

Run commands from the package directory:

```sh
python Source/make_dimmer_label.py
python Source/make_textures.py
blender -b --python Source/build_approved_dimmer.py
blender -b --python Source/build_devices.py
blender -b --python Source/render_previews.py
blender -b --python Source/validate_all.py
blender -b --python Source/assemble_scene.py
blender -b --python Source/render_details.py
python Source/make_overview.py
python Source/package_assets.py
```

`build_devices.py -- 4 8` rebuilds only the specified device numbers when invoked as `blender -b --python Source/build_devices.py -- 4 8`. Device 01 uses its dedicated approved-model script. `render_previews.py -- draft` renders inexpensive inspection images outside the package; omit `draft` for deliverable images. The scripts write output files, so keep your manual edits in a separate copy before rebuilding.

Blender must have access to NumPy for its FBX/glTF exporters. Some packaged Linux installations need their Python runtime paths configured; this is an environment issue rather than a requirement of the model files.
