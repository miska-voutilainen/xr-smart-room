# Poster / sign crops from the hall photos (Photos/5), perspective-rectified. Coordinates in 1400-px photo space.
import numpy as np
from PIL import Image, ImageOps
import os
R = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '')
OUT = R + 'textures/s3_hall/'
def load(i):
    return ImageOps.exif_transpose(Image.open(R + 'Photos/5/hall_0%d.jpg' % i)).convert('RGB')
def quad(im, q, size, gain=1.0):
    k = im.size[0] / 1400 if im.size[0] > im.size[1] else im.size[1] / 1400
    tl, tr, br, bl = [(x * k, y * k) for x, y in q]
    out = im.transform(size, Image.QUAD, (*tl, *bl, *br, *tr), Image.BICUBIC)
    if gain != 1.0:
        a = np.asarray(out).astype(float) * gain
        out = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    return out
def level(im, pct=99.0, white=245):
    a = np.asarray(im).astype(float)
    g = white / max(np.percentile(a.max(2), pct), 1)
    return Image.fromarray(np.clip(a * g, 0, 255).astype(np.uint8))
h1, h2, h5 = load(1), load(2), load(5)
level(quad(h2, [(994.6, 303.8), (1057.7, 293.8), (1055.4, 478.5), (993.8, 475.4)], (400, 566))).save(OUT + 'poster_pg.jpg', quality=92)
level(quad(h2, [(1277, 327), (1327, 322), (1327, 417), (1277, 413)], (160, 300))).save(OUT + 'sign_405.jpg', quality=92)
level(quad(h5, [(1182, 409), (1258.3, 386.7), (1258.3, 489.6), (1182, 477)], (1400, 244)), 99.5).save(OUT + 'prints.jpg', quality=92)
level(quad(h2, [(890, 333), (918, 335), (918, 432), (890, 430)], (200, 280))).save(OUT + 'poster_a3.jpg', quality=92)
level(quad(h1, [(336, 676), (405, 676), (405, 726), (336, 726)], (280, 200))).save(OUT + 'unique_box.jpg', quality=92)
# person cut-out on the teal wall: alpha where the pixel is not teal
c = level(quad(h1, [(1140, 318), (1305, 318), (1305, 458), (1140, 458)], (660, 560)), 99.5)
a = np.asarray(c).astype(float)
teal = (a[..., 2] > a[..., 0] * 1.6) & (a[..., 1] > a[..., 0] * 1.4) & (a.max(2) < 200)
alpha = np.where(teal, 0, 255).astype(np.uint8)
from PIL import ImageFilter
al = Image.fromarray(alpha).filter(ImageFilter.MedianFilter(7))
c.putalpha(al)
c.save(OUT + 'cutout.png')
print('ok')
level(quad(h1, [(368, 692), (405, 694), (405, 726), (368, 725)], (240, 200))).save(OUT + 'unique_box.jpg', quality=92)
# one print of the framed series (hall_05, the east-most frame: glossy pink photo on white) reused for all 7
level(quad(h5, [(1243, 391), (1257, 388), (1257, 487), (1243, 485)], (120, 300)), 99.5).save(OUT + 'print_pink.jpg', quality=92)
import os; os.remove(OUT + 'prints.jpg') if os.path.exists(OUT + 'prints.jpg') else None
