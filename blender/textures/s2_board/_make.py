# One-off texture prep for shaders/zz_board.py (system python3 + Pillow/numpy/qrcode; not run by the pipeline).
#   python3 textures/s2_board/_make.py <polyhaven_8k_dir>
# OSB: crop a 0.75 m window of the Poly Haven 2.51 m scan (no tiling on the 0.53 x 0.74 m board) -> 2048 px.
# Device fronts: the board region of photo 122216 (kitchen.py crop frame), white-balanced + de-lit per device.
# QR: real QR codes (version 2, like the photo) + grey label line, 4x4 atlas in kitchen.py's tile order.
import os, sys
import numpy as np
import qrcode
from scipy.ndimage import gaussian_filter
from PIL import Image, ImageDraw, ImageFont

Image.MAX_IMAGE_PIXELS = None
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))

# ---- OSB
ph = sys.argv[1] if len(sys.argv) > 1 else None
if ph:
    win = int(round(8192 * 0.75 / 2.51))
    x0 = y0 = 2900
    for src, dst in (("diff", "osb_color.jpg"), ("nor_gl", "osb_normal.jpg"), ("rough", "osb_rough.jpg")):
        im = Image.open(os.path.join(ph, src + ".jpg")).crop((x0, y0, x0 + win, y0 + win))
        im.resize((2048, 2048), Image.LANCZOS).save(os.path.join(HERE, dst), quality=92)

# ---- device fronts: crop of 122216 = x 825..1025, y 335..600 of the 1400 px copy (kitchen.py P() frame)
ph216 = Image.open(os.path.join(ROOT, "Photos/1/20261012_122216.jpg"))
s = ph216.size[0] / 1400
crop = ph216.crop((int(825 * s), int(335 * s), int(1025 * s), int(600 * s)))
F = 2                                                  # upsample for smoother print edges
W, H = crop.size
img = np.asarray(crop.resize((W * F, H * F), Image.LANCZOS)).astype(np.float32) / 255.0
img = img ** 2.2                                        # ~linear
out = np.full_like(img, 0.78)                           # unused area = plain white plastic
K = 0.00052
# (px, py, w, h) in crop px / metres: same numbers as kitchen.py
dev = [(607, 228, 0.145, 0.090), (583, 606, 0.062, 0.062), (260, 605, 0.043, 0.043),
       (460, 550, 0.035, 0.039), (862, 651, 0.074, 0.031), (862, 607, 0.043, 0.013)]
for px, py, w, h in dev:
    hw, hh = w / K / 2 * F, h / K / 2 * F
    a0, a1 = int(px * F - hw), int(px * F + hw)
    b0, b1 = int(py * F - hh), int(py * F + hh)
    reg = img[b0:b1, a0:a1]
    sig = max(hw, hh) / 3
    lit = gaussian_filter(reg, (sig, sig, 0), mode="nearest")
    alb = reg / np.maximum(lit, 1e-3) * 0.78
    out[b0:b1, a0:a1] = np.clip(alb, 0, 0.9)
o8 = (np.clip(out, 0, 1) ** (1 / 2.2) * 255).astype(np.uint8)
X0, Y0, X1, Y1 = 200, 120, 950, 700                   # crop px window kept (zz_board.py DEV_WIN), <= 2K
Image.fromarray(o8[Y0 * F:Y1 * F, X0 * F:X1 * F]).save(os.path.join(HERE, "device_fronts.png"))

# ---- QR atlas (tile t -> column t % 4, row t // 4 from the BOTTOM of the image; stickers 40 x 46 mm)
names = ["SONOFF 4CH PRO R3", "LAMP 1 - MINI R2", "SNZB-01 BUTTON", "SNZB-03 MOTION", "ZBBRIDGE HUB",
         "SNZB-04 DOOR", "LAMP 2 - MINI R2", "7in HDMI LCD", "FAN - BASIC R2", "L1 LED STRIP"]
TP = 512
atlas = Image.new("RGB", (4 * TP, 4 * TP), (232, 232, 226))
font = ImageFont.truetype("/usr/share/fonts/liberation-sans-fonts/LiberationSans-Bold.ttf", 30)
for t, nm in enumerate(names):
    q = qrcode.QRCode(version=2, error_correction=qrcode.constants.ERROR_CORRECT_L, border=0, box_size=1)
    q.add_data("http://hub.lan/" + nm.split()[0].lower())
    q.make(fit=False)
    m = np.array(q.get_matrix(), bool)                  # 25 x 25
    tile = Image.new("RGB", (TP, TP), (236, 236, 230))
    d = ImageDraw.Draw(tile)
    # u spans 40 mm, v 46 mm on the sticker: modules are square on paper -> mod_w px = 1.15 * mod_h px
    mh = 14
    mw = int(round(mh * 46 / 40))
    qx, qy = (TP - 25 * mw) // 2, TP - 40 - 25 * mh
    for r in range(25):
        for c in range(25):
            if m[r, c]:
                d.rectangle((qx + c * mw, qy + r * mh, qx + (c + 1) * mw - 1, qy + (r + 1) * mh - 1), fill=(18, 18, 20))
    lab = Image.new("RGB", (TP * 2, 40), (236, 236, 230))
    ImageDraw.Draw(lab).text((0, 2), nm, font=font, fill=(90, 90, 92))
    lab = lab.crop((0, 0, min(TP * 2, int(font.getlength(nm)) + 4), 40))
    lab = lab.resize((int(lab.size[0] * 46 / 40 * 0.62), int(40 * 0.62 * 1.0)), Image.LANCZOS)
    if lab.size[0] > 25 * mw:
        lab = lab.resize((25 * mw, lab.size[1]), Image.LANCZOS)
    tile.paste(lab, (qx, qy - lab.size[1] - 14))
    tx, ty = t % 4, t // 4
    atlas.paste(tile, (tx * TP, (3 - ty) * TP))
atlas.save(os.path.join(HERE, "qr_atlas.png"))
print("ok")
