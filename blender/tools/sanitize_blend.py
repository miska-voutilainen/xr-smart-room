"""Write a publishable copy of the open .blend: external paths relative, no absolute output paths.
    blender -b --factory-startup --python tools/sanitize_blend.py -- main.blend <out.blend>
Relative paths are made against the SOURCE file's folder (project root), so <out.blend> must end up in a folder with
the same layout (textures/, materials/ next to it). Save it to a neutral temp dir and move it: the file records the
path it was saved to. Saved uncompressed so `strings` can verify it. Never touches the source file."""
import os
import sys

import bpy


def isabs(p):
    return os.path.isabs(p) and not p.startswith("//")   # "//" = relative to the .blend


src, out = (os.path.abspath(a) for a in sys.argv[sys.argv.index("--") + 1:][:2])
# open without the file's UI (started with no file + factory startup): the window manager keeps last-used operator
# props such as file browser directories (home paths)
bpy.ops.wm.open_mainfile(filepath=src, load_ui=False)
for i in bpy.data.images:   # packed copies remember their absolute source path; drop the pack if the file is there
    if i.packed_file and i.filepath and os.path.isfile(bpy.path.abspath(i.filepath)):
        i.unpack(method="REMOVE")
bpy.ops.file.make_paths_relative()
for scr in bpy.data.screens:   # factory Shading workspace has a file browser that defaults to $HOME
    for sp in (sp for a in scr.areas for sp in a.spaces if sp.type == "FILE_BROWSER" and sp.params):
        sp.params.directory = b"//textures/xxxxxxxxxxxxxxxx"[:max(12, len(sp.params.directory) + 1)]  # overwrite, not truncate
for sc in bpy.data.scenes:
    if isabs(sc.render.filepath):
        sc.render.filepath = "//render_out/"
    nt = getattr(sc, "compositing_node_group", None) or getattr(sc, "node_tree", None)   # 5.x / 4.x
    if nt:
        for n in nt.nodes:
            if n.type == "OUTPUT_FILE" and isabs(getattr(n, "base_path", "") or ""):
                n.base_path = "//render_out/"
bad = [i.filepath for i in bpy.data.images if not i.packed_file and isabs(i.filepath)]
bad += [pf.filepath for i in bpy.data.images for pf in i.packed_files if isabs(pf.filepath)]
bad += [l.filepath for l in bpy.data.libraries if isabs(l.filepath)]
if bad:
    print("SANITIZE_FAIL absolute paths left:", bad)
    sys.exit(1)
bpy.ops.wm.save_as_mainfile(filepath=out, copy=True, relative_remap=False, compress=False)
print("SANITIZE_OK", out)
