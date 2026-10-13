# Builds the print atlases for Kitchen_SugarBox / Kitchen_TeaBox (owner: s2_boxes). System python3 + PIL + numpy:
#   python3 -I textures/s2_boxes/_make_atlas.py
# Writes sugar_albedo.png / sugar_rough.png / tea_albedo.png / tea_rough.png next to this file.
# Panel rects (mm -> px) are mirrored in shaders/zz_boxes.py (SUGAR_RECTS / TEA_RECTS) - keep them in sync.
# Sources: UNIQUE sugar box = rectified crops of the reference photos (no flat artwork exists online) with the
# lettering re-set crisp; Greenfield = official flat front + Open Food Facts back photos (see SOURCES.txt).
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
DL = os.path.join(HERE, "dl")
FONT = "/usr/share/fonts/msttcore/"
rng = np.random.default_rng(7)

# ------------------------------------------------------------------ shared dimensions (metres in zz_boxes.py)
S_L, S_D, S_H, S_F = 170, 90, 60, 165         # sugar: length (flap side), depth, wall height, flap top (mm)
T_W, T_D, T_H = 65, 50, 130                   # tea: front width, depth, height (mm)
PX = 7                                        # sugar atlas px/mm
TPX = 8                                       # tea atlas px/mm

SUGAR_RECTS = {                               # name: (x0, y0, w, h) in atlas px, image y down
    "flap":  (0, 0, S_L * PX, S_F * PX),                       # 1190 x 1155, top of flap at y=0
    "front": (0, S_F * PX + 8, S_L * PX, S_H * PX),            # 1190 x 420
    "end":   (1200, 0, S_D * PX, S_H * PX),                    # 630 x 420
    "kraft": (1200, 540, 600, 600),                            # tiling-ish interior board (~86 mm)
    "stick": (1200, 1150, 100 * PX, 15 * PX),                  # 700 x 105 stick wrapper
}
TEA_RECTS = {
    "front": (0, 0, T_W * TPX, T_H * TPX),                     # 520 x 1040  (-x face)
    "sideA": (530, 0, T_D * TPX, T_H * TPX),                   # 400 x 1040  logo side (-y)
    "back":  (940, 0, T_W * TPX, T_H * TPX),                   # 520 x 1040  (+x)
    "sideB": (1470, 0, T_D * TPX, T_H * TPX),                  # 400 x 1040  text side (+y)
    "top":   (0, 1050, T_W * TPX, T_D * TPX),                  # 520 x 400
    "bot":   (530, 1050, T_W * TPX, T_D * TPX),
}


def photo(pid):
    import glob
    return ImageOps.exif_transpose(Image.open(glob.glob(os.path.join(ROOT, "Photos", "*", "*%s.jpg" % pid))[0])).convert("RGB")


def rectify(img, quad, size):
    """quad = TL, TR, BR, BL source px -> size (w, h). Perspective via a solved homography."""
    w, h = size
    dst = [(0, 0), (w, 0), (w, h), (0, h)]
    A, b = [], []
    for (x, y), (u, v) in zip(dst, quad):
        A += [[x, y, 1, 0, 0, 0, -u * x, -u * y], [0, 0, 0, x, y, 1, -v * x, -v * y]]
        b += [u, v]
    c = np.linalg.solve(np.array(A, float), np.array(b, float))
    return img.transform(size, Image.PERSPECTIVE, tuple(c), Image.BICUBIC)


def sharpen(im, r=2.0, p=80):
    return im.filter(ImageFilter.UnsharpMask(radius=r, percent=p, threshold=2))


def font(name, size):
    return ImageFont.truetype(FONT + name, size)


def text_c(d, xy, s, f, fill, anchor="mm", **kw):
    d.text(xy, s, font=f, fill=fill, anchor=anchor, **kw)


def fit_text(s, fname, w_px, h_px):
    """Largest font size whose text box fits w x h px."""
    size = 4
    while True:
        b = font(fname, size + 2).getbbox(s)
        if b[2] - b[0] > w_px or b[3] - b[1] > h_px:
            return font(fname, size)
        size += 2


def noise(w, h, scale, octaves=3):
    """Smooth value noise 0..1 (upsampled random grids)."""
    out = np.zeros((h, w), np.float32)
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        gw, gh = max(2, int(w / scale * 2 ** o)), max(2, int(h / scale * 2 ** o))
        g = Image.fromarray((rng.random((gh, gw)) * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC)
        out += amp * np.asarray(g, np.float32) / 255
        tot += amp
        amp *= 0.5
    return out / tot


def edge_wear(w, h, px_mm, width_mm=1.4, sides="lrtb"):
    """0..1 mask of scuffed board along the given panel edges (folds/cut edges), broken up by noise."""
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    dist = np.full((h, w), 1e9, np.float32)
    if "l" in sides: dist = np.minimum(dist, xx)
    if "r" in sides: dist = np.minimum(dist, w - 1 - xx)
    if "t" in sides: dist = np.minimum(dist, yy)
    if "b" in sides: dist = np.minimum(dist, h - 1 - yy)
    n = noise(w, h, 6 * px_mm, 4)
    m = np.clip(1 - dist / (width_mm * px_mm * (0.4 + 1.2 * n)), 0, 1) ** 1.5
    speck = (noise(w, h, 1.2 * px_mm, 2) > 0.72) * np.clip(1 - dist / (3 * px_mm), 0, 1)
    return np.clip(m + 0.5 * speck, 0, 1)


def wear(img, mask, tint=(232, 226, 214), k=0.75):
    a = np.asarray(img.convert("RGB"), np.float32)
    t = np.array(tint, np.float32)
    a = a * (1 - k * mask[..., None]) + t * (k * mask[..., None])
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def grade(img, gain=(1, 1, 1), lift=0.0, gamma=1.0):
    a = np.asarray(img.convert("RGB"), np.float32) / 255
    a = np.clip((a * np.array(gain) + lift), 0, 1) ** gamma
    return Image.fromarray((a * 255).astype(np.uint8))


def paste(atlas, rough, name, rects, img, r_img):
    x, y, w, h = rects[name]
    atlas.paste(img.resize((w, h), Image.LANCZOS), (x, y))
    rough.paste(r_img.resize((w, h), Image.BILINEAR), (x, y))


def rough_from(mask, base, worn):
    return Image.fromarray(np.clip((base + (worn - base) * mask) * 255, 0, 255).astype(np.uint8), "L")


# ================================================================== SUGAR ("UNIQUE white sugar" display box)
BLUE = (38, 144, 210)          # print blue, sampled from lit areas of 122216 / 122250 and nudged to clean CMYK cyan+
BLUE_D = (26, 112, 178)


def facets(w, h, cell):
    """Voronoi 'sugar cube' facets: per-cell shade 0..1 and an edge mask 0..1 (numpy, jittered grid)."""
    gx, gy = int(w / cell) + 3, int(h / cell) + 3
    pts = (np.stack(np.meshgrid(np.arange(gx), np.arange(gy)), -1).reshape(-1, 2) - 1 + rng.random((gx * gy, 2))) * cell
    val = rng.random(len(pts))
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    d1 = np.full((h, w), 1e9, np.float32)
    d2 = np.full((h, w), 1e9, np.float32)
    sh = np.zeros((h, w), np.float32)
    gr = np.zeros((h, w), np.float32)
    ang = rng.random(len(pts)) * 2 * np.pi
    for (px, py), v, an in zip(pts, val, ang):
        d = np.hypot(xx - px, yy - py)
        closer = d < d1
        d2 = np.where(closer, d1, np.minimum(d2, d))
        sh = np.where(closer, v, sh)
        gr = np.where(closer, ((xx - px) * np.cos(an) + (yy - py) * np.sin(an)) / cell, gr)
        d1 = np.where(closer, d, d1)
    edge = np.clip(1 - (d2 - d1) / (0.06 * cell), 0, 1)
    return sh, edge, gr


def kraft(w, h, px_mm):
    """Grey-white back of folding boxboard with fibre mottling."""
    n1, n2 = noise(w, h, 3 * px_mm, 4), noise(w, h, 0.4 * px_mm, 2)
    base = np.array((196, 188, 170), np.float32)
    a = base[None, None] * (0.93 + 0.07 * n1[..., None]) * (0.96 + 0.05 * n2[..., None])
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def blue_field(w, h, px_mm):
    n = noise(w, h, 20 * px_mm, 3)
    a = np.array(BLUE, np.float32)[None, None] * (0.97 + 0.05 * n[..., None])
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def unique_logo(d, cx, cy, w_px, h_px, fill=(250, 250, 250)):
    f = fit_text("UNIQUE", "candarab.ttf", w_px, h_px)
    text_c(d, (cx, cy), "UNIQUE", f, fill)


def sugar_flap(p216):
    W, H = S_L * PX, S_F * PX
    img = blue_field(W, H, PX)
    d = ImageDraw.Draw(img)
    mm = lambda v: int(round(v * PX))
    # tab with the logo (geometry cuts the rounded tab, so only the lettering matters here)
    unique_logo(d, W / 2, mm(16), mm(92), mm(17))
    # eyes strip: rectified from 122216 (most frontal view), photo band 295 x 62 px -> 170 x 35 mm
    eyes = rectify(p216, [(3094, 3268), (3390, 3246), (3393, 3308), (3100, 3331)], (mm(170), mm(35)))
    eyes = sharpen(grade(eyes, (1.08, 1.06, 1.04), 0.03), 3, 90)
    img.paste(eyes, (0, mm(32)))
    sugar_flap.eyes = eyes
    # torn-paper lower edge of the strip (white wedge into the blue at the right, as printed)
    d.polygon([(mm(118), mm(67)), (mm(140), mm(63.5)), (mm(170), mm(64.5)), (mm(170), mm(67))], fill=BLUE)
    d.line([(0, mm(67)), (W, mm(67))], fill=BLUE, width=mm(0.8))
    # "80" + "white sugar"
    text_c(d, (mm(24), mm(80)), "80", font("georgiab.ttf", mm(9)), (245, 245, 245))
    text_c(d, (mm(24), mm(86.5)), "sticks", font("georgia.ttf", mm(3)), (235, 240, 245))
    text_c(d, (mm(92), mm(80)), "white sugar", font("georgiab.ttf", mm(13)), (248, 248, 248))
    # faint seal at the right
    r = mm(11)
    d.ellipse([mm(150) - r, mm(80) - r, mm(150) + r, mm(80) + r], outline=(60, 150, 210), width=mm(1))
    text_c(d, (mm(150), mm(80)), "5 g", font("georgiab.ttf", mm(5)), (60, 150, 210))
    # inside part (below the box rim): a darker blue - only seen from above in shade
    img = sharpen(img, 1, 40)
    m = edge_wear(W, H, PX, 1.0, "lrt")
    return wear(img, m), rough_from(m, 0.42, 0.75)


def sugar_cubes(w, h, px_mm):
    """Macro 'sugar cube' print background: lit crystalline blocks, bright facet edges, fine grain."""
    sh, edge, grad = facets(w, h, 11.0 * px_mm)
    tone = np.clip(0.80 + 0.22 * sh + 0.16 * grad, 0, 1.2)
    warm = noise(w, h, 30 * px_mm, 2)                                     # print colour drift
    base = np.array((206, 176, 156), np.float32)[None, None] * (0.94 + 0.10 * warm[..., None])
    a = base * tone[..., None] + 38 * edge[..., None]
    a *= 0.95 + 0.08 * noise(w, h, 0.35 * px_mm, 2)[..., None]
    a += 18 * np.clip((noise(w, h, 0.5 * px_mm, 1) - 0.74) * 5, 0, 1)[..., None]    # crystal glints
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.6))


def sugar_front(eyes):
    """Front (long) wall, re-drawn from the layout in 122216 / 122209: sugar-cube photo field, white band with
    the eyes between a blue UNIQUE block and a blue 'white sugar' block, a thin blue info strip near the base."""
    W, H = S_L * PX, S_H * PX
    mm = lambda v: int(round(v * PX))
    img = sugar_cubes(W, H, PX)
    d = ImageDraw.Draw(img)
    ew, eh = eyes.size
    e = eyes.crop((int(ew * 0.12), int(eh * 0.06), int(ew * 0.88), int(eh * 0.80)))
    mid = np.asarray(e)[:, e.width // 2 - 4:e.width // 2 + 4].reshape(-1, 3)
    skin = tuple(int(c) for c in np.median(mid, 0))
    d.rectangle([0, mm(20), W, mm(38)], fill=skin)
    e = e.resize((mm(60), int(mm(60) * e.height / e.width)), Image.LANCZOS)
    img.paste(e, (mm(53), mm(29) - e.height // 2))
    d.rectangle([0, mm(21.5), mm(50), mm(36.5)], fill=BLUE)
    unique_logo(d, mm(25), mm(29), mm(40), mm(10))
    d.rectangle([mm(123), mm(21.5), mm(147), mm(36.5)], fill=BLUE)
    text_c(d, (mm(135), mm(26)), "white", font("georgiab.ttf", mm(5)), (245, 245, 245))
    text_c(d, (mm(135), mm(32.5)), "sugar", font("georgiab.ttf", mm(5)), (245, 245, 245))
    d.rectangle([mm(60), mm(49), mm(150), mm(54)], fill=BLUE_D)
    text_c(d, (mm(105), mm(51.5)), "UNIQUE  white sugar  80 x 5 g", font("verdanab.ttf", mm(3)), (235, 240, 245))
    m = edge_wear(W, H, PX, 1.3)
    return wear(img, m), rough_from(m, 0.45, 0.78)


def sugar_end(p250):
    W, H = S_D * PX, S_H * PX
    mm = lambda v: int(round(v * PX))
    img = rectify(p250, [(4407, 3765), (4647, 3774), (4647, 3911), (4405, 3897)], (W, H))
    img = sharpen(grade(img, (1.04, 1.04, 1.04), 0.02), 3, 100)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, mm(24)], fill=BLUE)
    unique_logo(d, W / 2, mm(13), mm(60), mm(12))
    d.rectangle([0, mm(38), W, H], fill=BLUE)
    text_c(d, (W / 2, mm(49.5)), "white sugar", font("georgiab.ttf", mm(8)), (245, 245, 245))
    m = edge_wear(W, H, PX, 1.3)
    return wear(img, m), rough_from(m, 0.45, 0.78)


def sugar_stick():
    W, H = 100 * PX, 15 * PX
    mm = lambda v: int(round(v * PX))
    img = Image.new("RGB", (W, H), (240, 241, 238))
    d = ImageDraw.Draw(img)
    d.rectangle([mm(8), 0, mm(38), H], fill=BLUE)
    unique_logo(d, mm(23), H / 2, mm(26), mm(7))
    text_c(d, (mm(66), H / 2), "white sugar  5 g", font("georgiab.ttf", mm(5)), BLUE_D)
    for x0 in (0, W - mm(6)):                                   # crimped seal ends
        for i in range(0, mm(6), 3):
            d.line([(x0 + i, 0), (x0 + i, H)], fill=(205, 207, 205), width=1)
    return img, Image.new("L", (W, H), 150)


def build_sugar():
    p216, p250 = photo("122216"), photo("122250")
    atlas = Image.new("RGB", (2048, 2048), BLUE)
    rough = Image.new("L", (2048, 2048), 110)
    flap = sugar_flap(p216)
    for name, (im, r) in (("flap", flap), ("front", sugar_front(sugar_flap.eyes)), ("end", sugar_end(p250)),
                          ("stick", sugar_stick())):
        paste(atlas, rough, name, SUGAR_RECTS, im, r)
    x, y, w, h = SUGAR_RECTS["kraft"]
    paste(atlas, rough, "kraft", SUGAR_RECTS, kraft(w, h, PX), Image.new("L", (w, h), 200))
    atlas.save(os.path.join(HERE, "sugar_albedo.png"))
    rough.save(os.path.join(HERE, "sugar_rough.png"))


# ================================================================== TEA (Greenfield Earl Grey Fantasy, 25 bags)
GREEN = (22, 52, 34)


def green_panel(w, h, glow=0.0):
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    g = np.exp(-(((xx - w * 0.5) / (w * 0.55)) ** 2 + ((yy - h * 0.55) / (h * 0.45)) ** 2))
    base = np.array(GREEN, np.float32)
    a = base[None, None] * (0.75 + (0.5 + glow) * g[..., None])
    a = a * (0.97 + 0.04 * noise(w, h, 40, 2)[..., None])
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def tea_front():
    f = Image.open(os.path.join(DL, "gf_86f6d7.png")).convert("RGBA")
    f = f.crop(f.getchannel("A").getbbox())
    bg = Image.new("RGBA", f.size, GREEN + (255,))
    bg.alpha_composite(f)
    return bg.convert("RGB").resize((T_W * TPX, T_H * TPX), Image.LANCZOS)


def tea_logo_side(front):
    """Side panel as on the official 3D renders: picture wrap at the top, rotated Greenfield + EGF lettering."""
    W, H = T_D * TPX, T_H * TPX
    img = green_panel(W, H)
    fw, fh = front.size
    pic = front.crop((0, 0, fw, int(fh * 0.28))).transpose(Image.FLIP_LEFT_RIGHT).resize((W, int(fh * 0.28)))
    img.paste(pic, (0, 0))
    logo = front.crop((int(fw * 0.08), int(fh * 0.37), int(fw * 0.94), int(fh * 0.47)))          # "Greenfield"
    egf = front.crop((int(fw * 0.15), int(fh * 0.53), int(fw * 0.85), int(fh * 0.72)))           # EARL GREY FANTASY
    for crop, x in ((logo, 0.30), (egf, 0.66)):
        r = crop.rotate(90, expand=True)
        k = min(W * 0.36 / r.width, H * 0.58 / r.height)
        r = r.resize((int(r.width * k), int(r.height * k)), Image.LANCZOS)
        lay(img, r, (int(W * x - r.width / 2), int(H * 0.36)))
    band = Image.new("RGB", (int(H * 0.9), 26), (0, 0, 0))
    text_c(ImageDraw.Draw(band), (band.width / 2, 13), "FINELY  SELECTED  SPECIALITY  TEA", font("georgia.ttf", 15),
           (190, 160, 90))
    band = band.rotate(90, expand=True)
    lay(img, band, (int(W * 0.9 - 13), int(H * 0.08)))
    return img


def lay(dst, src, xy):
    """Lighten-composite (bright lettering on a darker backing over the generated green)."""
    from PIL import ImageChops
    x, y = xy
    reg = dst.crop((x, y, x + src.width, y + src.height))
    dst.paste(ImageChops.lighter(reg, src), (x, y))


def tea_text_side(front):
    W, H = T_D * TPX, T_H * TPX
    img = green_panel(W, H, glow=0.5)
    d = ImageDraw.Draw(img)
    gold, cream = (200, 168, 98), (226, 222, 205)
    text_c(d, (W / 2, 40), "EARL GREY FANTASY", font("georgiab.ttf", 30), gold)
    text_c(d, (W / 2, 72), "BLACK TEA", font("georgia.ttf", 18), cream)
    t = Image.open(os.path.join(DL, "off_3.jpg")).convert("RGB")
    t = t.crop((180, 0, 3950, 2950))                                     # the printed text block
    t = grade(t, (0.85, 0.95, 0.85), -0.03)
    k = (W - 30) / t.width
    t = t.resize((W - 30, int(t.height * k)), Image.LANCZOS)
    lay(img, t, (15, 110))
    sym = Image.open(os.path.join(DL, "off_4.jpg")).convert("RGB")
    k = (W - 60) / sym.width
    sym = sym.resize((W - 60, int(sym.height * k)), Image.LANCZOS)
    lay(img, sym, (30, H - sym.height - 40))
    return img


def build_tea():
    atlas = Image.new("RGB", (2048, 2048), GREEN)
    rough = Image.new("L", (2048, 2048), 110)
    front = tea_front()
    panels = {"front": front, "sideA": tea_logo_side(front), "back": tea_logo_side(front),
              "sideB": tea_text_side(front)}
    for k in ("top", "bot"):
        w, h = TEA_RECTS[k][2:]
        im = green_panel(w, h)
        ImageDraw.Draw(im).text((w / 2, h / 2), "Greenfield", font=font("georgiaz.ttf", 60), fill=(220, 215, 200),
                                anchor="mm")
        panels[k] = im
    for name, im in panels.items():
        w, h = TEA_RECTS[name][2:]
        im = im.resize((w, h), Image.LANCZOS)
        m = edge_wear(w, h, TPX, 0.9)
        paste(atlas, rough, name, TEA_RECTS, wear(im, m, (150, 160, 140), 0.55), rough_from(m, 0.32, 0.65))
    atlas.save(os.path.join(HERE, "tea_albedo.png"))
    rough.save(os.path.join(HERE, "tea_rough.png"))


if __name__ == "__main__":
    build_sugar()
    build_tea()
    print("atlases written to", HERE)
