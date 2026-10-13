# Usage: python3 make_label.py akvile_peach_06l_rimi_src.png akvile_peach_label.png
# Rectify the Rimi product shot of Akvile Peach Bubbles 0.6 l into a cylindrical label wrap with alpha.
import sys
import numpy as np
from PIL import Image
src, dst = sys.argv[1], sys.argv[2]
a = np.asarray(Image.open(src).convert("RGBA")).astype(np.float32) / 255.0
R0, R1 = 445, 1222            # sleeve rows (constant-width body)
CX, RAD = 769.0, 220.5        # body centre column / radius in px
W, H = 2048, 1144
FRONT = np.radians(75)        # usable half-angle of the front view
FEATH = np.radians(12)
u = (np.arange(W) + 0.5) / W
th = (u - 0.5) * 2 * np.pi    # u = 0.5 -> front centre
x = CX + RAD * np.sin(np.clip(th, -np.pi / 2, np.pi / 2))
y = R0 + (np.arange(H) + 0.5) / H * (R1 - R0)
xi = np.clip(x, 0, a.shape[1] - 1.001)
x0 = np.floor(xi).astype(int); fx = xi - x0
rows = np.clip(np.round(y).astype(int), 0, a.shape[0] - 1)
img = a[rows][:, x0] * (1 - fx)[None, :, None] + a[rows][:, x0 + 1] * fx[None, :, None]
rgb = img[..., :3]
r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
blue = b - r
# The shot's print is exactly neutral (white blob) or warm (peaches); clear film over the blue bottle and the
# bottle's specular streaks are blue-shifted by >= 5/255. Logo ink and its antialiasing on the white blob are
# blue too, but with a lower green share ((g-r)/(b-r) ~0.28 vs ~0.6 for the bottle).
al = np.clip(1 - (blue - 0.008) / 0.012, 0, 1)
k = (g - r) / np.maximum(blue, 1e-4)
al = np.where((blue > 0.02) & (k < 0.42), 1.0, al)
edge = np.clip((FRONT - np.abs(th)) / FEATH, 0, 1)
al *= edge[None, :]
rgb = np.clip(rgb / 0.88, 0, 1)                        # undo the shot's ~0.88 grey on the white blob
out = np.dstack([rgb, al])
out[al < 0.004, :3] = 1.0
Image.fromarray((out * 255 + 0.5).astype(np.uint8), "RGBA").save(dst, optimize=True)
print("saved", dst, out.shape, "opaque frac", (al > 0.5).mean())
