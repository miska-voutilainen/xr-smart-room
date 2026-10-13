# Cycles render settings for the office interior. Runs last in render/ (after light.py), standalone + idempotent.
# Owns: engine/device, sampling, denoising, light paths, film, view transform + look, persistent data,
#       render passes + light groups for the Stage-3 compositor.
# Does NOT touch exposure, world shader or lights (render/light.py owns those).
# Refs: docs.blender.org/manual/en/latest/render/cycles/render_settings/{sampling,light_paths,film,performance}.html,
#       .../render/cycles/render_settings/sampling.html#denoising, .../render/color_management.html (AgX looks),
#       .../render/layers/passes.html (light groups, cryptomatte, mist)
import re

import bpy

SAMPLES = 512                # max per pixel; adaptive sampling stops most pixels far earlier
ADAPTIVE_THRESHOLD = 0.01    # noise threshold (Blender default); finals stay well under 3 min on an L40S
ADAPTIVE_MIN = 0             # 0 = automatic (Cycles picks from the threshold)
TIME_LIMIT = 0.0             # seconds per frame, 0 = off
DENOISE = True
LOOK = 'AgX - Medium High Contrast'   # phone JPEGs are punchier than AgX base; 'None' for neutral
# Clamp: brightest things ever seen through a bounce are the LED diffusers (~5.5 W/m2/sr) and the overcast
# sky through the window (~3); 10 keeps every real highlight and only cuts caustic fireflies. Direct unclamped.
CLAMP_DIRECT, CLAMP_INDIRECT = 0.0, 10.0
# Filter glossy only roughens glossy hits AFTER a diffuse/rough bounce; first-hit glints (LED panels and the window
# in the terrazzo, chrome taps) stay crisp. 0.5 instead of 1.0 keeps reflections-of-reflections sharper too.
BLUR_GLOSSY = 0.5
RES = (1920, 1080)
# Light groups by object name, first match wins; the world is "daylight". Anything unmatched -> "panels"
# (room-1 ceiling LEDs, monitor, any new room-1 light). Non-emissive objects in a group cost nothing.
LIGHTGROUPS = (
    ("daylight", r"^Ext_|^Light_Portal|^Light_Sun"),  # portals don't emit, listed so they don't land in "lab"
    ("entrance", r"^Room3_|Corridor|Entrance"),     # space beyond the pink door (materials/room3_entrance.py)
    ("lab", r"^Room2_|_Lab"),                       # Room2 lab panels/screens, Light_LED_Lab_*
)
FALLBACK_GROUP = "panels"
MIST = (2.0, 60.0)           # mist pass start / depth in m (window haze mask for the compositor)


def set_device(scene):
    """OptiX GPU if present, else CUDA, else CPU. Prefs don't persist in -b, so set them every run."""
    c = scene.cycles
    c.device = 'CPU'
    try:
        prefs = bpy.context.preferences.addons['cycles'].preferences
        for kind in ('OPTIX', 'CUDA'):
            prefs.compute_device_type = kind
            prefs.get_devices()
            if any(d.type == kind for d in prefs.devices):
                for d in prefs.devices:
                    d.use = d.type == kind
                c.device = 'GPU'
                return kind
    except Exception as e:  # no GPU backend in this build/session
        print("render.py: GPU setup failed, CPU", e)
    return 'CPU'


def passes_and_lightgroups(s):
    vl = s.view_layers[0]
    vl.use_pass_mist = True
    vl.use_pass_cryptomatte_object = vl.use_pass_cryptomatte_material = True
    vl.pass_cryptomatte_depth = 6
    vl.cycles.denoising_store_passes = True     # albedo/normal for denoising light-group passes in the compositor
    if s.world:
        s.world.mist_settings.start, s.world.mist_settings.depth = MIST
        s.world.mist_settings.falloff = 'LINEAR'
        s.world.lightgroup = "daylight"
    names = [g for g, _ in LIGHTGROUPS] + [FALLBACK_GROUP]
    for g in list(vl.lightgroups):
        if g.name not in names:
            vl.lightgroups.remove(g)
    for n in names:
        if n not in vl.lightgroups:
            vl.lightgroups.add(name=n)
    count = dict.fromkeys(names, 0)
    for o in bpy.data.objects:
        if o.type not in ('LIGHT', 'MESH'):
            continue
        g = next((g for g, pat in LIGHTGROUPS if re.search(pat, o.name)), FALLBACK_GROUP)
        o.lightgroup = g
        count[g] += o.type == 'LIGHT'
    return count


def render_settings():
    s = bpy.context.scene
    s.render.engine = 'CYCLES'
    kind = set_device(s)
    c = s.cycles
    c.samples = SAMPLES
    c.use_adaptive_sampling = True
    c.adaptive_threshold = ADAPTIVE_THRESHOLD
    c.adaptive_min_samples = ADAPTIVE_MIN
    c.time_limit = TIME_LIMIT
    c.use_light_tree = True                  # 30+ area lights + emissive panels + sky: big win, works on GPU
    c.use_guiding = True                     # path guiding is CPU-only: ignored on the L40S, helps local CPU previews
    c.use_surface_guiding = c.use_volume_guiding = True
    # denoise: OIDN with albedo + normal guides (follow reflections on = default, keeps terrazzo reflections sharp),
    # prefiltered guides, on the GPU (L40S: ~1 s instead of ~10 s on 8 CPU threads; falls back to CPU without one)
    c.use_denoising = DENOISE
    c.denoiser = 'OPENIMAGEDENOISE'
    c.denoising_input_passes = 'RGB_ALBEDO_NORMAL'
    c.denoising_prefilter = 'ACCURATE'
    c.denoising_quality = 'HIGH'
    c.denoising_use_gpu = True
    # light paths: interiors need diffuse depth; glass is light-path transparent for shadow rays (materials), so
    # refractive caustics stay off; transparent depth covers double glazing + rain layer + door/lab glass
    c.max_bounces = 16
    c.diffuse_bounces = 6
    c.glossy_bounces = 4
    c.transmission_bounces = 8
    c.volume_bounces = 2
    c.transparent_max_bounces = 16
    c.sample_clamp_direct = CLAMP_DIRECT
    c.sample_clamp_indirect = CLAMP_INDIRECT
    c.blur_glossy = BLUR_GLOSSY
    c.caustics_reflective = True              # cheap, lets metal/glossy bounce light (radiator, worktop)
    c.caustics_refractive = False
    c.min_light_bounces = 0
    # film / performance
    c.pixel_filter_type = 'BLACKMAN_HARRIS'
    c.filter_width = 1.5
    s.render.film_transparent = False
    s.render.use_persistent_data = True       # keeps BVH/shaders between renders (multi-camera comparison runs)
    c.use_auto_tile = True
    c.tile_size = 2048
    s.render.resolution_x, s.render.resolution_y = RES
    s.render.resolution_percentage = 100
    # colour management (exposure belongs to light.py, white balance to the compositor's WB node)
    s.display_settings.display_device = 'sRGB'
    s.view_settings.view_transform = 'AgX'
    s.view_settings.look = LOOK
    s.view_settings.gamma = 1.0
    s.view_settings.use_curve_mapping = False
    s.view_settings.use_white_balance = False
    s.sequencer_colorspace_settings.name = 'sRGB'
    s.render.image_settings.file_format = 'PNG'
    s.render.image_settings.color_depth = '8'
    print("RENDER SETTINGS OK", kind, "lightgroups (lights):", passes_and_lightgroups(s))


render_settings()
