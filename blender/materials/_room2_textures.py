# Lab (room 2) image textures -> textures/s1_lab/. NOT run by apply_materials ("_" prefix) and NOT a Blender script:
#   python3 -I materials/_room2_textures.py        (system python3 + PIL + numpy; outputs are committed images)
# 1. board_<n>.jpg: demo-board faces rectified from the lab photos (homography from 4 hand-picked corners,
#    neutralised so the board white is sRGB ~222). Board 4 has no usable view; room2.py reuses board_3.
# 2. screen_*.png / keys.png: synthetic screen contents seen in Photos/3 (clock screensaver "3:10 PM" on the old
#    Dell, spreadsheet on the E1 dual monitors, dark editor on laptops, terminal on the bench monitor) + keycaps.
import os
import random

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PH = os.path.join(ROOT, "Photos", "3")
OUT = os.path.join(ROOT, "textures", "s1_lab")
SANS = "/usr/share/fonts/liberation-sans-fonts/LiberationSans-Regular.ttf"
MONO = "/usr/share/fonts/liberation-mono-fonts/LiberationMono-Regular.ttf"

# ---------- demo boards: (photo, corners TL TR BR BL in full-res px, board size m) ----------
BOARDS = {
    1: ("20261012_151022.jpg", [(2547, 1049), (3923, 975), (3890, 2056), (2538, 1920)], (1.42, 1.02)),
    2: ("20261012_151025.jpg", [(2226, 1150), (2640, 1098), (2635, 1651), (2228, 1640)], (1.17, 1.02)),
    3: ("20261012_151124.jpg", [(410, 1683), (1305, 1699), (1303, 2313), (413, 2330)], (1.42, 1.02)),
    5: ("20261012_151018.jpg", [(1914, 672), (2488, 848), (2475, 1752), (1908, 1883)], (1.17, 0.97)),
}


def homography(src, dst):
    A = []
    for (x, y), (u, v) in zip(src, dst):
        A += [[x, y, 1, 0, 0, 0, -u * x, -u * y], [0, 0, 0, x, y, 1, -v * x, -v * y]]
    return np.linalg.solve(np.array(A, float), np.array([c for p in dst for c in p], float))


def boards():
    for n, (ph, corners, (w, h)) in sorted(BOARDS.items()):
        im = ImageOps.exif_transpose(Image.open(os.path.join(PH, ph))).convert("RGB")
        H = 1024
        W = int(round(H * w / h))
        coeffs = homography([(0, 0), (W, 0), (W, H), (0, H)], corners)     # output px -> photo px
        a = np.asarray(im.transform((W, H), Image.PERSPECTIVE, tuple(coeffs), Image.BICUBIC)).astype(float)
        lum = a.mean(2)
        a = np.clip(a / a[lum > np.percentile(lum, 55)].mean(0) * 222.0, 0, 255).astype(np.uint8)
        if n == 2:     # a student's head covers the lower left: clone the switch row from the right
            a[700:1024, 0:380] = a[700:1024, 380:760]
        if n == 3:     # head at the lower right: borrow board 1's lower row (same product line)
            b1 = np.asarray(Image.open(os.path.join(OUT, "board_1.jpg")))
            p = b1[780:1024, 880:1426].astype(float)
            gain = np.median(a[760:780, 880:1426], (0, 1)) / np.median(p[:20], (0, 1))
            a[780:1024, 880:1426] = np.clip(p * gain, 0, 255)
        Image.fromarray(a).save(os.path.join(OUT, "board_%d.jpg" % n), quality=90)


# shelf instruments on bench 1 (151018): front panels, (corners TL TR BR BL, output px)
INSTRUMENTS = {
    "inst_scope": ([(799, 1584), (1167, 1535), (1187, 1760), (805, 1875)], (1024, 528)),
    "inst_dmm1": ([(1247, 1503), (1453, 1493), (1453, 1615), (1250, 1636)], (1024, 384)),
    "inst_dmm2": ([(1250, 1638), (1455, 1612), (1455, 1725), (1250, 1764)], (1024, 384)),
}


def instruments():
    im = ImageOps.exif_transpose(Image.open(os.path.join(PH, "20261012_151018.jpg"))).convert("RGB")
    for name, (corners, (W, H)) in INSTRUMENTS.items():
        coeffs = homography([(0, 0), (W, 0), (W, H), (0, H)], corners)
        im.transform((W, H), Image.PERSPECTIVE, tuple(coeffs), Image.BICUBIC).save(os.path.join(OUT, name + ".jpg"),
                                                                                     quality=90)


# ---------- screens ----------

def font(path, size):
    return ImageFont.truetype(path, size)


def clock():
    im = Image.new("RGB", (1280, 1024), (4, 4, 6))
    d = ImageDraw.Draw(im)
    d.text((560, 470), "3:10:23 PM", font=font(SANS, 42), fill=(215, 215, 215))
    im.save(os.path.join(OUT, "screen_clock.png"))


def sheet():
    W, H = 1920, 1080
    im = Image.new("RGB", (W, H), (255, 255, 255))
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, W, 34), fill=(33, 115, 70))                               # title bar
    d.rectangle((0, 34, W, 150), fill=(243, 243, 243))                           # ribbon
    r = random.Random(3)
    for x in range(20, W - 200, 70):
        d.rectangle((x, 60, x + 40, 120), fill=(r.choice([(200, 200, 200), (160, 190, 170), (210, 210, 220)])))
    d.rectangle((0, 150, W, 178), fill=(250, 250, 250))
    d.rectangle((0, 178, 46, H - 40), fill=(238, 238, 238))
    cols = [46] + [46 + 64 + i * 128 for i in range(15)]
    for x in cols:
        d.line((x, 178, x, H - 40), fill=(212, 212, 212))
    for y in range(178, H - 40, 22):
        d.line((0, y, W, y), fill=(218, 218, 218))
        if y > 200:
            for c, x in enumerate(cols[:-1]):
                if r.random() < (0.85 if c < 6 else 0.25):
                    wl = r.randint(18, 100 if c == 0 else 60)
                    d.rectangle((x + 6, y + 8, x + 6 + wl, y + 14), fill=(70, 70, 70) if c else (40, 40, 40))
    d.rectangle((47, 179, W, 199), fill=(198, 224, 180))                         # header row
    d.rectangle((0, H - 40, W, H), fill=(243, 243, 243))
    d.rectangle((60, H - 34, 160, H - 8), fill=(255, 255, 255), outline=(33, 115, 70))
    im.save(os.path.join(OUT, "screen_sheet.png"))


def code(name, seed):
    W, H = 1920, 1080
    im = Image.new("RGB", (W, H), (30, 30, 30))
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, 50, H), fill=(44, 44, 44))
    d.rectangle((50, 0, 330, H), fill=(37, 37, 38))
    d.rectangle((0, H - 24, W, H), fill=(0, 122, 204))
    r = random.Random(seed)
    for y in range(40, H - 40, 26):
        if r.random() < 0.85:
            d.rectangle((70, y + 8, 70 + r.randint(60, 200), y + 16), fill=(150, 150, 150))
    pal = [(86, 156, 214), (206, 145, 120), (156, 220, 254), (220, 220, 170), (106, 153, 85), (197, 134, 192),
           (212, 212, 212)]
    for y in range(50, H - 40, 26):
        x = 360 + 30 * r.choice((0, 0, 1, 1, 2, 3))
        if r.random() < 0.12:
            continue
        for _ in range(r.randint(1, 6)):
            wl = r.randint(30, 160)
            d.rectangle((x, y + 8, x + wl, y + 17), fill=r.choice(pal))
            x += wl + 12
    im.save(os.path.join(OUT, name))


def terminal():
    W, H = 1920, 1080
    im = Image.new("RGB", (W, H), (10, 10, 12))
    d = ImageDraw.Draw(im)
    f = font(MONO, 22)
    r = random.Random(5)
    logo = ["   /\\   ", "  /  \\  ", " / /\\ \\ ", "/_/  \\_\\"]
    for i, s in enumerate(logo):
        d.text((40, 40 + i * 30), s, font=font(MONO, 30), fill=(200, 200, 200))
    y = 200
    while y < H - 40:
        line = "".join(r.choice("abcdefghijklmnopqrstuvwxyz0123456789 ./-_:[]=") for _ in range(r.randint(10, 90)))
        d.text((30, y), ("$ " if r.random() < 0.2 else "") + line, font=f, fill=(190, 190, 190))
        y += 30
    im.save(os.path.join(OUT, "screen_term.png"))


def keys():
    """Keycap grid, 1024 x 340 = full-size keyboard top (440 x 140 mm, main block left, numpad right)."""
    W, H = 1024, 340
    im = Image.new("RGB", (W, H), (14, 14, 15))
    d = ImageDraw.Draw(im)
    u = 41
    rows = [[1] * 13, [1] * 13 + [2], [1.5] + [1] * 12 + [1.5], [1.75] + [1] * 11 + [2.25],
            [2.25] + [1] * 10 + [2.75], [1.25] * 3 + [6.25] + [1.25] * 4]
    for ri, row in enumerate(rows):
        x, y = 12, 14 + ri * (u + 13) if ri else 14
        for k in row:
            w = k * u
            d.rounded_rectangle((x + 2, y + 2, x + w - 3, y + u - 3), 5, fill=(30, 30, 32), outline=(48, 48, 50))
            d.rectangle((x + 9, y + 9, x + 15, y + 15), fill=(150, 150, 150))
            x += w
    for c in range(4):                                       # numpad
        for ri in range(5):
            x, y = 800 + c * u, 68 + ri * (u + 13)
            d.rounded_rectangle((x + 2, y + 2, x + u - 3, y + u - 3), 5, fill=(30, 30, 32), outline=(48, 48, 50))
    im.save(os.path.join(OUT, "keys.png"))


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    boards()
    instruments()
    clock(); sheet(); code("screen_code.png", 1); code("screen_code2.png", 2); terminal(); keys()
    print("textures ->", OUT)
