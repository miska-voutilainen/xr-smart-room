# Tiny node helpers shared by shaders/*.py (owner: g2_shaders_hard; others import read-only).
#   import sys, os; sys.path.insert(0, os.path.dirname(__file__)); import _lib
# Every helper takes a socket OR a constant wherever a value is expected.
import bpy

# AO dirt switch. Each material that uses AO dirt gets a Value node named DIRT_NODE holding this value;
# 1 = AO grime on (Cycles stills), 0 = off (texture baking for Unity: set every "Hard_Dirt" node to 0).
DIRT = 1.0
DIRT_NODE = "Hard_Dirt"


def reset(name):
    """Clear an EXISTING material's tree -> (mat, nt, principled, object_coords). None if absent (never creates)."""
    m = bpy.data.materials.get(name)
    if m is None:
        return None
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(b.outputs[0], out.inputs["Surface"])
    return m, nt, b, nt.nodes.new("ShaderNodeTexCoord").outputs["Object"]


def put(nt, sock, v):
    """Link a socket or set a constant (tuples of 3 get alpha appended for colour sockets)."""
    if isinstance(v, bpy.types.NodeSocket):
        nt.links.new(v, sock)
    elif isinstance(v, tuple) and len(v) == 3 and len(sock.default_value) == 4:
        sock.default_value = (*v, 1.0)
    else:
        sock.default_value = v


def math(nt, op, a, b=0.0, c=0.0, clamp=False):
    n = nt.nodes.new("ShaderNodeMath")
    n.operation, n.use_clamp = op, clamp
    for i, v in enumerate((a, b, c)):
        put(nt, n.inputs[i], v)
    return n.outputs[0]


def noise(nt, vec, scale, detail=2.0, rough=0.5, dist=0.0):
    n = nt.nodes.new("ShaderNodeTexNoise")
    put(nt, n.inputs["Vector"], vec)
    n.inputs["Scale"].default_value = scale
    n.inputs["Detail"].default_value = detail
    n.inputs["Roughness"].default_value = rough
    n.inputs["Distortion"].default_value = dist
    return n.outputs["Fac"]


def maprange(nt, v, a, b, c, d):
    """Clamped linear remap of v from a..b to c..d."""
    n = nt.nodes.new("ShaderNodeMapRange")
    put(nt, n.inputs["Value"], v)
    for i, x in zip((1, 2, 3, 4), (a, b, c, d)):
        put(nt, n.inputs[i], x)
    return n.outputs[0]


def scale_vec(nt, vec, s):
    """Per-axis stretch of a coordinate (e.g. (1, 300, 300) = streaks along x)."""
    n = nt.nodes.new("ShaderNodeVectorMath")
    n.operation = "MULTIPLY"
    put(nt, n.inputs[0], vec)
    n.inputs[1].default_value = s
    return n.outputs[0]


def mix_col(nt, f, a, b):
    n = nt.nodes.new("ShaderNodeMix")
    n.data_type = "RGBA"
    put(nt, n.inputs[0], f)
    put(nt, n.inputs[6], a)
    put(nt, n.inputs[7], b)
    return n.outputs[2]


def mix_val(nt, f, a, b):
    n = nt.nodes.new("ShaderNodeMix")
    put(nt, n.inputs[0], f)
    put(nt, n.inputs[2], a)
    put(nt, n.inputs[3], b)
    return n.outputs[0]


def bump(nt, h, strength, dist, normal=None):
    n = nt.nodes.new("ShaderNodeBump")
    put(nt, n.inputs["Height"], h)
    n.inputs["Strength"].default_value = strength
    n.inputs["Distance"].default_value = dist
    if normal is not None:
        nt.links.new(normal, n.inputs["Normal"])
    return n.outputs["Normal"]


def dirt_gate(nt):
    """The per-material DIRT switch node (created once per tree)."""
    n = nt.nodes.get(DIRT_NODE)
    if n is None:
        n = nt.nodes.new("ShaderNodeValue")
        n.name = n.label = DIRT_NODE
        n.outputs[0].default_value = DIRT
    return n.outputs[0]


def gate_ao(nt, ao_out):
    """AO -> lerp(1, AO, DIRT): with the switch at 0 the AO term is exactly 1 (no grime)."""
    return mix_val(nt, dirt_gate(nt), 1.0, ao_out)


def tidy(nt):
    """Column layout by distance from the output, so trees stay readable in the editor."""
    depth = {}
    outs = [n for n in nt.nodes if n.type == "OUTPUT_MATERIAL"]
    todo = [(n, 0) for n in outs]
    while todo:
        n, d = todo.pop()
        if depth.get(n.name, -1) >= d:
            continue
        depth[n.name] = d
        todo += [(l.from_node, d + 1) for l in nt.links if l.to_node == n]
    rows = {}
    for n in nt.nodes:
        d = depth.get(n.name, max(depth.values(), default=0) + 1)
        r = rows.get(d, 0)
        n.location = (-260 * d, -220 * r)
        rows[d] = r + 1
