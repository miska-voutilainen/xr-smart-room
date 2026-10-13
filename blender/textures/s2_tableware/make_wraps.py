# Authored paper-cup wraps (owner s2_tableware), printed over real CC0 paper scans (ambientCG, see SOURCES.txt).
# Not run by apply_materials. Re-run with system python3 + PIL + numpy:  python3 textures/s2_tableware/make_wraps.py
# UV convention (shaders/zz_tableware.py): u = (theta - 270 deg) / 360, so the glue seam (u = 0/1) faces the wall (-y),
# u = 0.5 faces the room (+y, Cam_122216). v = 0 bottom of the printed band, v = 1 top. Image row 0 = v = 1.
import math
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FONT = "/usr/share/fonts/julietaula-montserrat-fonts/Montserrat-Bold.otf"


def font(px):
    try:
        return ImageFont.truetype(FONT, px)
    except OSError:
        return ImageFont.load_default()


def grain(name, w, h):
    """Real paper scan, tiled to w x h, as a 0..1 luminance multiplier around 1."""
    src = Image.open(os.path.join(HERE, name)).convert("L")
    tile = Image.new("L", (w, h))
    for y in range(0, h, src.height):
        for x in range(0, w, src.width):
            tile.paste(src, (x, y))
    a = np.asarray(tile, np.float32) / 255.0
    return a / a.mean()


def u2x(u, w):
    return int(round(u * w))


def orange_wrap(W=2048, H=1024):
    """16 oz cup, yellow-orange: white bottom band, cream top band with orange beads, white star logo + text."""
    v = np.linspace(1, 0, H)[:, None] * np.ones((1, W))
    top, bot = np.array([240, 168, 58]), np.array([228, 134, 42])          # sRGB, sampled + white-balanced 122216
    img = bot + (top - bot) * v[..., None]
    img[v < 0.075] = (238, 236, 230)                                          # bottom white band
    img[v > 0.885] = (236, 226, 208)                                          # cream top band
    img[v > 0.975] = (244, 243, 239)                                          # white under the rolled rim
    im = Image.fromarray(img.astype(np.uint8))
    d = ImageDraw.Draw(im)
    y0, y1 = int((1 - 0.965) * H), int((1 - 0.895) * H)                      # bead row in the cream band
    r = (y1 - y0) / 2 - 4
    for k in range(48):                                                       # alternating dots / rounded tiles
        x, yc = (k + 0.5) * W / 48, (y0 + y1) / 2
        if k % 2:
            d.ellipse((x - r, yc - r, x + r, yc + r), fill=(224, 150, 78))
        else:
            d.rounded_rectangle((x - r * 1.3, yc - r * 0.7, x + r * 1.3, yc + r * 0.7), 6, fill=(232, 182, 128))
    # star logo: four concave arcs around a diamond, centred at u = 0.5
    cx, cy, a = u2x(0.5, W), int((1 - 0.60) * H), 70
    for sx in (-1, 1):
        for sy in (-1, 1):
            ox, oy = cx + sx * a, cy + sy * a
            start = {(1, 1): 180, (-1, 1): 270, (-1, -1): 0, (1, -1): 90}[(sx, sy)]
            d.arc((ox - a + 8, oy - a + 8, ox + a - 8, oy + a - 8), start + 8, start + 82, fill=(250, 246, 236), width=26)
    for txt, yy, sz in (("TARKVARA", 0.42, 44), ("TEEJUHT TULEVIKU", 0.36, 44)):
        f = font(sz)
        tw = d.textlength(txt, font=f)
        d.text((cx - tw / 2, (1 - yy) * H - sz / 2), txt, font=f, fill=(250, 244, 230))
    # cream side panel (122250, left of the cup seen from +x) + small mark on the bottom band
    px = u2x(0.21, W)
    d.rectangle((px - 45, int((1 - 0.47) * H), px + 45, int((1 - 0.12) * H)), fill=(238, 228, 200))
    f = font(18)
    d.text((cx - 60, (1 - 0.035) * H - 9), "Paper cup 16oz", font=f, fill=(150, 150, 150))
    return im, grain("Paper001_1K-JPG_Color.jpg", W, H)


def brown_wrap(W=2048, H=768):
    """8 oz mauve-brown cup with a cable-knit print, vertical white text, red/blue label, round badge."""
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    col_w, row_h = W / 13.0, H / 6.5                                          # ~19 x 14 mm knit stitches
    cx = (xx % col_w) / col_w - 0.5                                           # -0.5..0.5 across a column
    ry = (yy / row_h + np.abs(cx) * 0.55) % 1.0                                # V-shaped stitch rows
    stitch = np.sin(np.pi * ry) ** 0.7 * (1 - (2 * np.abs(cx)) ** 6)        # bright stitch body, dark gaps
    base = np.array([150, 116, 102], np.float32)
    dark = np.array([96, 70, 62], np.float32)
    img = dark + (base - dark) * stitch[..., None]
    img = img + (np.array([168, 134, 120]) - base) * (stitch[..., None] > 0.85) * 0.6
    im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(im)
    # plain stripe behind the vertical text (122216 front cup) + text "ole ole" rotated
    sx = u2x(0.53, W)
    d.rectangle((sx - 40, 0, sx + 40, H), fill=(146, 112, 98))
    t = Image.new("RGBA", (H - 60, 80), (0, 0, 0, 0))
    ImageDraw.Draw(t).text((10, 4), "ole ole ole", font=font(58), fill=(232, 222, 214, 255))
    t = t.rotate(90, expand=True)
    im.paste(t, (sx - 40, 30), t)
    # red / blue label at the bottom (122216, 122250)
    lx = u2x(0.42, W)
    d.rectangle((lx, int(H * 0.80), lx + 52, int(H * 0.97)), fill=(196, 40, 52))
    d.rectangle((lx + 52, int(H * 0.80), lx + 110, int(H * 0.97)), fill=(70, 160, 220))
    d.rectangle((lx, int(H * 0.60), lx + 110, int(H * 0.80)), fill=(235, 235, 232))
    for k in range(5):
        d.rectangle((lx + 8, int(H * 0.62) + k * 11, lx + 100, int(H * 0.62) + k * 11 + 5), fill=(40, 40, 40))
    # round badge: dark disc with white concentric arcs (wifi-like mark)
    bx, by, r = u2x(0.81, W), int(H * 0.45), 95
    d.ellipse((bx - r, by - r, bx + r, by + r), fill=(70, 46, 40), outline=(232, 226, 220), width=6)
    for k, rr in enumerate((70, 52, 34)):
        d.arc((bx - rr, by - rr + 20, bx + rr, by + rr + 20), 200, 340, fill=(240, 236, 230), width=10)
    d.ellipse((bx - 10, by + 10, bx + 10, by + 30), fill=(240, 236, 230))
    im = im.filter(ImageFilter.GaussianBlur(0.8))                             # print dot gain
    return im, grain("Paper006_1K-JPG_Color.jpg", W, H)


for name, (im, g) in (("cup_orange_wrap.png", orange_wrap()), ("cup_brown_wrap.png", brown_wrap())):
    a = np.asarray(im, np.float32) * (1 + (g[..., None] - 1) * 0.6)         # paper fibre shows through the ink
    Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).save(os.path.join(HERE, name))
    print("wrote", name, im.size)
