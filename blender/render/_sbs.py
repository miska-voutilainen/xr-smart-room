# Photo | render | 50 % blend comparison sheets. NOT run by apply_materials. System python3 + PIL.
#   python3 render/_sbs.py DIR [ids...] [--mode cycles|lines]   (reads DIR/<id>_<mode>.png, writes DIR/<id>_<mode>_sbs.jpg)
import glob
import os
import sys

from PIL import Image, ImageDraw, ImageOps

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
args = [a for a in sys.argv[1:] if not a.startswith("--")]
mode = sys.argv[sys.argv.index("--mode") + 1] if "--mode" in sys.argv else "cycles"
if mode in args:
    args.remove(mode)
d = args[0]
ids = args[1:] or sorted(os.path.basename(p).split("_")[0] for p in glob.glob(os.path.join(d, "*_%s.png" % mode)))
for pid in ids:
    ren = Image.open(os.path.join(d, "%s_%s.png" % (pid, mode))).convert("RGB")
    photo = ImageOps.exif_transpose(Image.open(glob.glob(os.path.join(ROOT, "Photos", "*", "*%s.jpg" % pid))[0]))
    photo = photo.convert("RGB").resize(ren.size, Image.LANCZOS)
    w, h = ren.size
    sheet = Image.new("RGB", (w * 3, h + 24), (20, 20, 20))
    for i, (im, label) in enumerate(((photo, "photo " + pid), (ren, "render " + mode),
                                     (Image.blend(photo, ren, 0.5), "50 % blend"))):
        sheet.paste(im, (i * w, 24))
        ImageDraw.Draw(sheet).text((i * w + 6, 6), label, fill=(230, 230, 230))
    path = os.path.join(d, "%s_%s_sbs.jpg" % (pid, mode))
    sheet.save(path, quality=90)
    print(path)
