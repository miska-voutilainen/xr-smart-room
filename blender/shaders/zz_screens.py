# Screen front films (s2_reflect). Runs after hard.py (sorted name) and PATCHES every material whose name
# contains "Screen": the panel's own tree (base colour, emission, UV masks) is kept, the front surface becomes a
# Coat layer = the polariser/AR film or cover glass: IOR 1.5 -> F0 4 % at normal incidence (physicallybased.info
# Glass 1.52; photo 150338: the off TV mirrors the room at a few % of the wall luminance, edges slightly soft).
# The base layer's own specular is zeroed, the film does all the reflecting. Wipe smears (ambientCG Smear004,
# CC0) modulate the film roughness. Object coords (metres) -> bake-safe, nothing view-dependent.
# Glass (Window_Glass / Door_Glass / Room2_Glass) is left to hard.py: 4 mm solid panes, IOR 1.52, full
# transmission = physically right already (2 interfaces x 4 % per pane).
import os
import re

import bpy

TEX = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "textures", "s2_reflect")
TAG = "S2_ScreenFilm"

# name -> (film roughness lo, hi, emission strength or None = keep). Default for any other "*Screen*".
FILM = {
    "TV_Screen": (0.06, 0.14, None),        # semi-gloss TV film: room reflection readable but soft (150338)
    "Monitor_Screen": (0.16, 0.26, 0.0),    # anti-glare office monitor, switched off in 122209
    "Kitchen_Screen": (0.03, 0.08, None),   # small glass-fronted display
}
DEFAULT = (0.10, 0.22, None)


def film(m, lo, hi, emit):
    nt = m.node_tree
    if nt.nodes.get(TAG):
        return False
    nt.nodes.new("NodeFrame").name = TAG
    img = bpy.data.images.load(os.path.join(TEX, "screen_smear_Smear004.jpg"), check_existing=True)
    img.colorspace_settings.name = 'Non-Color'
    co = nt.nodes.new("ShaderNodeTexCoord").outputs["Object"]
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (1 / 0.6,) * 3
    mp.inputs["Rotation"].default_value = (1.2, 0.4, 0.0)   # screens are vertical: project the map off-axis
    nt.links.new(co, mp.inputs["Vector"])
    t = nt.nodes.new("ShaderNodeTexImage")
    t.image = img
    nt.links.new(mp.outputs[0], t.inputs["Vector"])
    r = nt.nodes.new("ShaderNodeMapRange")                  # Smear004 mean 0.14, sd 0.10
    r.inputs[1].default_value, r.inputs[2].default_value = 0.05, 0.45
    r.inputs[3].default_value, r.inputs[4].default_value = lo, hi
    nt.links.new(t.outputs["Color"], r.inputs[0])
    for b in [n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"]:
        b.inputs["Coat Weight"].default_value = 1.0
        b.inputs["Coat IOR"].default_value = 1.5
        b.inputs["Coat Tint"].default_value = (1, 1, 1, 1)
        for l in list(b.inputs["Coat Roughness"].links):
            nt.links.remove(l)
        nt.links.new(r.outputs[0], b.inputs["Coat Roughness"])
        b.inputs["Specular IOR Level"].default_value = 0.0
        if emit is not None:
            b.inputs["Emission Strength"].default_value = emit
    return True


done = []
for m in bpy.data.materials:
    if m.users and not m.library and m.use_nodes and re.search("screen", m.name, re.I):
        if film(m, *FILM.get(m.name, DEFAULT)):
            done.append(m.name)
print("ZZ_SCREENS film:", sorted(done))
