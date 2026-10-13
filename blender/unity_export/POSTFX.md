# Post-processing for Unity 2022.3 URP (from the Blender grade, s3_comp)

Source of truth: `render/compositor.py` (node group `Comp_PhoneLook`), `render/render.py` (view transform),
`render/light.py` (`EXPOSURE`, `PHONE_BIAS`). This file maps that grade onto one URP Global Volume.
Numbers marked *fit* were fitted numerically (scripts in the s3_comp report); verify them in Unity with the
checks at the bottom, because URP's ACES and the Neutral curve below are re-implementations, not Unity's own code.

## What the Blender grade does

| Stage (scene-linear, before the view transform) | Setting | What it models |
|---|---|---|
| Veiling glare | `out = 0.96*img + 0.04*bloom(img)`, no threshold, Bloom kernel size 0.8 | lens/sensor scatter, energy-conserving |
| White balance | White Point node, scene white 4350 K, `WB_TINT` -16 relative to the node neutral 10 (node Input Tint = -6) -> D65 / tint 10. Grey gains R 0.62 / G 1 / B 1.42 | phone AWB under 4000 K LEDs + overcast daylight |
| Local contrast | +-0.3 stop max, 0.15 x log-detail vs mid-scale mean | phone "clarity" |
| Vignette | 8 % at the frame corners, smoothstep from 35 % radius | residual lens shading |
| Sharpen | unsharp on log2 luminance, amount 0.6, 1 px, clamped to +-0.12 stop | ISP sharpening without halos on LED panel edges |
| Chromatic aberration | Lens Distortion dispersion 0.003 (0 at centre, ~1 px at corners) | residual lateral CA |
| Noise | luminance only, 0.6 % at the frame's log-mean, x2 per 2 stops darker, max 2.4 % | shot noise after phone NR |
| View transform | AgX, look `AgX - Medium High Contrast`, sRGB | tone curve |
| Exposure | +1.60 EV on radiance in W/(m2 sr) (EV100 9.34 metering + `PHONE_BIAS` 1.0) | phone exposure |

Local tone mapping (phone HDR shadow lift) exists in the compositor but is OFF: the renders' darkest 5 % already
match the photos and it lifted them 1-1.5 stops too far.

## URP Volume (Global, priority 0) — rendering 1:1 to the stills

| Override | Setting | Value | Note |
|---|---|---|---|
| Tonemapping | Mode | **ACES** | *fit*: ACES + Post Exposure -0.6 + Contrast -12 matches the AgX MHC curve to rms 0.009 (sRGB 0-1), max 0.02. Neutral is worse (best: Post Exposure -0.2, Contrast +14, rms 0.029, toe 0.07 vs 0.04). Fit used the Narkowicz ACES approximation, see checks |
| Color Adjustments | Post Exposure | **-0.6 EV + your scene calibration** | the -0.6 is only the tone-curve match; add the offset that puts the scene where Blender's exposure puts it (see Exposure below) |
| | Contrast | **-12** | |
| | Saturation | 0 (try -5 if bright LED/window areas look more saturated than in Blender: AgX desaturates highlights more than ACES) | |
| | Color Filter | white | |
| | Hue Shift | 0 | |
| White Balance | Temperature | **-34** | *fit* to the Blender grey gains with URP's LMS model: gives R 0.627 / G 1 / B 1.415 vs Blender 0.620 / 1 / 1.419 |
| | Tint | **-13** | (URP and Blender tint scales differ in sign/units; this is the numeric fit, not a conversion of -16) |
| Bloom | Threshold | **0** | physical veiling glare has no threshold; URP bloom is additive, so at threshold 0 it adds ~Intensity of energy (negligible at this level) |
| | Intensity | **0.05** | Blender mixes 4 %; start at 0.05 and compare the halo around a ceiling panel |
| | Scatter | **0.8** | wide, soft PSF |
| | Tint | white | |
| | Clamp | 65472 (default) | |
| | High Quality Filtering | on (desktop), off on mobile XR if it costs too much | |
| | Dirt | none | |
| Vignette | Intensity | **0.13** | *fit*: corner factor 0.92 as in Blender (edge-centre 0.96 vs Blender 0.935) |
| | Smoothness | **0.5** | |
| | Rounded | off | |
| Film Grain | Type | Thin1 | |
| | Intensity | 0.1 | |
| | Response | 0.8 | grain fades in highlights, like shot noise |
| Chromatic Aberration | Intensity | 0.03 | radial; corners only |
| Lift Gamma Gain | | all neutral | the grade has no lift/gamma/gain |
| Shadows Midtones Highlights | | all neutral | |
| Split Toning / Channel Mixer / Curves | | off | |
| Depth of Field / Motion Blur / Lens Distortion / Panini | | off | phone JPEGs are distortion-corrected |

No URP equivalent for: local contrast (clarity) and the edge-clamped sharpening. Closest: TAA Sharpness (not in XR
on 2022.3) or FSR 1.0 RCAS sharpening when upscaling. Leave them out rather than use an unclamped sharpen: that is
what produced the dark rings around the LED panels in Blender.

## XR (headset) profile

Lens artefacts belong to a camera, not to eyes. For the XR build use the same Volume minus:
**Vignette off, Chromatic Aberration off, Film Grain off** (they also fight with the headset's own lens correction and
are a comfort issue). Keep Tonemapping, Color Adjustments, White Balance, Bloom. Bloom Intensity can drop to 0.03:
per-eye render targets are smaller, so the same Scatter looks larger.

## Exposure

Blender: pixel = radiance [W/(m2 sr)] x 2^EXPOSURE, EXPOSURE = log2(0.18 x 683 / L_avg) + PHONE_BIAS = **+1.60 EV**,
with 1 W = 683 lm everywhere in the lights (`render/light.py`): an LED diffuser is 5120 cd/m2 = 7.5 W/(m2 sr).
In Unity the absolute offset depends on how the light intensities were imported, so calibrate it:

1. If Unity light intensities equal the Blender values (radiance/irradiance in W units, 1 W = 683 lm), set
   Post Exposure = 1.60 - 0.6 = **+1.0 EV**.
2. Otherwise (lux / nits / Unity "physical" units) set Post Exposure so that in the `Camera` (hero) view the white
   wall left of the window lands at sRGB about **175-180** and an LED panel face just clips (sRGB 250-255).
   Reference renders: `renders/hpc/s3_comp_final_Camera/frame_0001.png`.

## Checks in Unity

- Grey ramp: a quad strip with emissive values 0.01, 0.05, 0.18, 0.5, 1, 2, 4, 8 (Post Exposure 0, no bloom).
  Blender AgX MHC gives sRGB 0.041, 0.194, 0.458, 0.699, 0.813, 0.897, 0.957, 1.0. Adjust Contrast (+-4) / Post
  Exposure (+-0.1) until within 0.02.
- Grey card (albedo 0.18, lit by one 4000 K light): after White Balance it should read neutral (R=G=B within 2 %).
- LED panel edge at 1:1: no dark outline, no coloured fringe in the image centre.
