# Compositor: phone-camera look on top of the Cycles render (Blender 5.x node-group compositor). Owner: s3_comp.
# Standalone + idempotent: rebuilds the node group "Comp_PhoneLook" and assigns it to the scene. Every stage is switchable.
# Runs in scene-linear BEFORE the view transform, and the scene exposure (light.py + per-photo EV in hpc/render.sh, 1.2-3.7)
# is applied AFTER it, so every stage is scale-invariant (no absolute thresholds, offsets or display-space sharpening):
#   Render Layers -> veiling glare -> white balance -> [local tone mapping] -> local contrast -> vignette -> sharpen
#   -> lens CA -> sensor noise.   Tone curve = AgX Medium High Contrast (render.py) + PHONE_BIAS (light.py).
# Calibrated on HPC EXRs of Cam_112212/120945/122209/122216/150435 vs the photos (s3_comp report): WB from near-neutral
# wall/ceiling pixels; LTM off because the renders' darkest 5 % already match the photos (it lifted them 1-1.5 stops).
# - Veiling glare: lens/sensor scatter is a PSF over ALL light (no threshold). out = (1-k)*img + k*(img * PSF); the Glare
#   node's "Glare" output is energy-normalised (measured: sum out == sum in), so this conserves energy. Only sources many
#   stops above their surround (panels, windows) show a visible halo.
# - Local tone mapping: phone HDR lifts large dark areas (multi-frame merge + local tone curve). Base layer = wide blur of
#   log2 luminance; areas whose base lies below (log-mean + LTM_PIVOT) are lifted by LTM_STRENGTH * distance, max LTM_MAX
#   stops. Highlights untouched. The blur is a Glare node with threshold 0 (an energy-normalised kernel whose Size is
#   relative to the frame, so it works at any resolution/PCT); log values are offset by +LOG_OFS to stay positive.
# - Local contrast: same idea at mid scale (CLARITY_SIZE), +-CLARITY_MAX stops: the phone's "clarity", clamped.
# - Sharpen: unsharp mask on log2 luminance (ratio domain), detail clamped to +-SHARP_CLAMP stops: fine texture gets the
#   phone's crispness, high-contrast edges (LED panel rims, window bars) get no dark ring.
# - Chromatic aberration: Lens Distortion dispersion is a radial channel scale, zero at the centre, ~1 px at the corners.
# - Noise: shot-noise model, relative sigma = NOISE * 2^(-(logY - logmean)/2) (variance ~ signal), capped; luminance only.
# Refs: docs.blender.org/manual/en/latest/compositing/types/filter/glare.html, .../color/adjust/color_balance.html
#       (White Point), .../distort/lens_distortion.html; Spencer et al. 1995 "Physically-based glare effects for digital
#       images"; Durand & Dorsey 2002 (base/detail tone mapping); Hasinoff et al. 2016 "Burst photography for HDR" (HDR+).
import bpy

USE_GLARE, GLARE_MIX, GLARE_TYPE, GLARE_SIZE = True, 0.04, 'Bloom', 0.8   # scattered fraction, PSF kernel, relative size
USE_WB, WB_TEMP, WB_TINT = True, 4350.0, -16.0   # scene white in K / tint (node units, 10 = neutral), mapped to D65
USE_LTM, LTM_STRENGTH, LTM_MAX, LTM_PIVOT, LTM_SIZE = False, 0.30, 1.0, 1.0, 0.6   # lift factor, max stops, pivot over log-mean
USE_CLARITY, CLARITY, CLARITY_MAX, CLARITY_SIZE = True, 0.15, 0.3, 0.15   # local contrast: gain on log detail vs mid-scale mean
USE_VIGNETTE, VIGNETTE = True, 0.08              # residual corner darkening after the phone's lens-shading correction
USE_SHARPEN, SHARPEN, SHARP_CLAMP = True, 0.6, 0.12   # unsharp amount on log2 luminance, max +-stops per pixel
USE_LENS, LENS_DISPERSION = True, 0.003          # lateral CA (phone JPEGs are CA-corrected: residual only)
USE_NOISE, NOISE = True, 0.006                   # relative luminance noise at the log-mean level (ISO 50 + phone NR)
LOG_OFS = 32.0                                   # keeps log2 luminance positive through the Glare-node blur
NAME = "Comp_PhoneLook"


def build():
    s = bpy.context.scene
    ng = bpy.data.node_groups.get(NAME)
    if ng is None:
        ng = bpy.data.node_groups.new(NAME, 'CompositorNodeTree')
    ng.nodes.clear()
    for item in list(ng.interface.items_tree):
        ng.interface.remove(item)
    ng.interface.new_socket("Image", in_out='OUTPUT', socket_type='NodeSocketColor')
    N, L = ng.nodes, ng.links
    x = [0]

    def sock(n, key):   # 5.x sockets: match identifier ("Highlights Threshold") first, then UI name ("Threshold")
        return next((i for i in n.inputs if i.identifier == key), None) or next(i for i in n.inputs if i.name == key)

    def node(kind, **inputs):
        n = N.new(kind)
        n.location = (x[0], 0)
        x[0] += 200
        for k, v in inputs.items():
            sock(n, k.replace('_', ' ')).default_value = v
        return n

    def link(a, n, key):
        L.new(a, sock(n, key))

    def mix(blend, a, b, fac=1.0):
        m = node('ShaderNodeMix')
        m.data_type, m.blend_type = 'RGBA', blend
        sock(m, 'Factor_Float').default_value = fac
        L.new(a, sock(m, 'A_Color'))
        L.new(b, sock(m, 'B_Color'))
        return next(o for o in m.outputs if o.identifier == 'Result_Color')

    def math(op, a, b=None, c=None):
        n = N.new('ShaderNodeMath')
        n.operation = op
        n.location = (x[0], -300)
        x[0] += 60
        for i, v in enumerate((a, b, c)):
            if v is None:
                continue
            if isinstance(v, bpy.types.NodeSocket):
                L.new(v, n.inputs[i])
            else:
                n.inputs[i].default_value = v
        return n.outputs[0]

    def to_value(c):        # grey colour -> float
        n = node('CompositorNodeRGBToBW')
        L.new(c, n.inputs[0])
        return n.outputs[0]

    def blur_rel(v, size):
        """Energy-normalised blur of a positive scalar, kernel size relative to the frame (Glare node, threshold 0)."""
        g = node('CompositorNodeGlare', Type='Bloom', Quality='High', Threshold=0.0, Smoothness=0.0, Strength=1.0,
                 Size=size, Saturation=1.0)
        L.new(v, g.inputs['Image'])
        return to_value(g.outputs['Glare'])

    def gain(img, stops):   # img * 2^stops
        return mix('MULTIPLY', img, math('POWER', 2.0, stops))

    rl = node('CompositorNodeRLayers')
    rl.scene = s
    img = rl.outputs['Image']

    if USE_GLARE:
        g = node('CompositorNodeGlare', Type=GLARE_TYPE, Quality='High', Threshold=0.0, Smoothness=0.0, Strength=1.0,
                 Size=GLARE_SIZE, Saturation=1.0)
        L.new(img, g.inputs['Image'])
        img = mix('MIX', img, g.outputs['Glare'], GLARE_MIX)

    if USE_WB:
        wb = node('CompositorNodeColorBalance', Type='White Point')
        sock(wb, 'Input Temperature').default_value = WB_TEMP
        sock(wb, 'Input Tint').default_value = 10.0 + WB_TINT
        sock(wb, 'Output Temperature').default_value = 6500.0
        sock(wb, 'Output Tint').default_value = 10.0
        L.new(img, wb.inputs['Image'])
        img = wb.outputs['Image']

    # log2 luminance + its frame log-mean (pivot for LTM and noise); shared by LTM, sharpen, noise
    bw = node('CompositorNodeRGBToBW')
    L.new(img, bw.inputs[0])
    logy = math('LOGARITHM', math('MAXIMUM', bw.outputs[0], 1e-6), 2.0)
    lv = node('CompositorNodeLevels')
    L.new(logy, lv.inputs['Image'])
    logmean = lv.outputs['Mean']

    if USE_LTM:
        base = math('SUBTRACT', blur_rel(math('ADD', logy, LOG_OFS), LTM_SIZE), LOG_OFS)
        below = math('SUBTRACT', math('ADD', logmean, LTM_PIVOT), base)          # stops under the pivot
        lift = math('MINIMUM', math('MAXIMUM', math('MULTIPLY', below, LTM_STRENGTH), 0.0), LTM_MAX)
        img = gain(img, lift)
        logy = math('ADD', logy, lift)

    if USE_CLARITY:
        mid = math('SUBTRACT', blur_rel(math('ADD', logy, LOG_OFS), CLARITY_SIZE), LOG_OFS)
        lc = math('MINIMUM', math('MAXIMUM', math('MULTIPLY', math('SUBTRACT', logy, mid), CLARITY), -CLARITY_MAX),
                  CLARITY_MAX)
        img = gain(img, lc)
        logy = math('ADD', logy, lc)

    if USE_VIGNETTE:
        # radial falloff from Image Coordinates (Normalized: -1..1 on the long axis): f = 1 - V * smoothstep(r)
        ic = node('CompositorNodeImageCoordinates')
        L.new(img, ic.inputs['Image'])
        vm = N.new('ShaderNodeVectorMath')
        vm.operation = 'LENGTH'
        L.new(ic.outputs['Normalized'], vm.inputs[0])
        mr = node('ShaderNodeMapRange')
        mr.interpolation_type = 'SMOOTHSTEP'
        mr.inputs['From Min'].default_value, mr.inputs['From Max'].default_value = 0.35, 1.25
        mr.inputs['To Min'].default_value, mr.inputs['To Max'].default_value = 1.0, 1.0 - VIGNETTE
        L.new(vm.outputs['Value'], mr.inputs['Value'])
        img = mix('MULTIPLY', img, mr.outputs['Result'])

    if USE_SHARPEN:
        bl = node('CompositorNodeBlur', Type='Gaussian')
        sock(bl, 'Size').default_value = (1.0, 1.0)
        L.new(math('ADD', logy, LOG_OFS), bl.inputs['Image'])                  # offset: blur input is a colour
        detail = math('SUBTRACT', math('ADD', logy, LOG_OFS), to_value(bl.outputs['Image']))
        detail = math('MINIMUM', math('MAXIMUM', math('MULTIPLY', detail, SHARPEN), -SHARP_CLAMP), SHARP_CLAMP)
        img = gain(img, detail)

    if USE_LENS:
        ld = node('CompositorNodeLensdist', Type='Radial', Distortion=0.0, Dispersion=LENS_DISPERSION,
                  Fit=False, Jitter=False)
        L.new(img, ld.inputs['Image'])
        img = ld.outputs['Image']

    if USE_NOISE:
        # sigma = NOISE * 2^(-(logY - logmean)/2), capped at 4x; zero-mean white noise per pixel, luminance only
        ic = node('CompositorNodeImageCoordinates')
        L.new(img, ic.inputs['Image'])
        wn = node('ShaderNodeTexWhiteNoise')
        wn.noise_dimensions = '2D'
        L.new(ic.outputs['Pixel'], wn.inputs['Vector'])
        sig = math('MINIMUM', math('MULTIPLY', math('POWER', 2.0, math('MULTIPLY', math('SUBTRACT', logy, logmean), -0.5)),
                                   NOISE), 4 * NOISE)
        n = math('MULTIPLY_ADD', math('SUBTRACT', wn.outputs['Value'], 0.5), math('MULTIPLY', sig, 3.464), 1.0)
        img = mix('MULTIPLY', img, n)                                          # uniform(-.5,.5)*sqrt(12) = unit sigma

    out = node('NodeGroupOutput')
    L.new(img, out.inputs[0])
    s.compositing_node_group = ng
    s.render.use_compositing = True
    print("COMPOSITOR OK", len(ng.nodes), "nodes", {k: v for k, v in globals().items() if k.startswith("USE_")})


build()
