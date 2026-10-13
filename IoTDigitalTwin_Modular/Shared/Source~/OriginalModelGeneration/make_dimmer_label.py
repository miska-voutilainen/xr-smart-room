from PIL import Image,ImageDraw,ImageFont
from pathlib import Path
out=Path(__file__).resolve().parents[1]/'Textures'
im=Image.new('RGB',(2048,192),(220,220,202));d=ImageDraw.Draw(im)
f=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',34)
d.rounded_rectangle((35,31,159,155),radius=12,outline=(139,71,48),width=7)
d.line([(97,52),(97,106)],fill=(139,71,48),width=8);d.ellipse((93,123,101,131),fill=(139,71,48))
for y,t in zip((21,72,123),['1. Please remove this label before use.','2. Before installation, please remove the switch plate','   and loosen the screws to disassemble the switching unit and power unit.']): d.text((191,y),t,font=f,fill=(38,40,36))
im.save(out/'Dimmer_InstallationLabel_BaseColor.png')
