from PIL import Image,ImageDraw,ImageFont
from pathlib import Path
import json
P=Path(__file__).resolve().parents[1]
f='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf';fb='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
def font(n,b=False):return ImageFont.truetype(fb if b else f,n)
labels=['Zigbee rotary dimmer','Zigbee LCD sensor','Z-Wave controller','Security camera','Aqara chain controller','Roller blind mechanism','Siemens BACnet device','Nest smart speaker','DALI touchscreen']
sub=['86 mm frame · shaft pivot','LCD + three separate buttons','Display + capacitive targets','Lens, sensor, light + tilt mount','Drive wheel + moving cover','Roller + cloth blend shape','Dot display + status LED','Fabric normal map + cradle','Screen + eight touch targets']
W,H=1664,1984;out=Image.new('RGB',(W,H),'#edf0f2');d=ImageDraw.Draw(out)
d.rectangle((0,0,W,180),fill='#142b35');d.text((42,29),'SMART ROOM  /  IoT DEVICE ASSETS',font=font(48,True),fill='white');d.text((44,110),'TalTech digital twin  •  9 devices  •  Blender + FBX + GLB',font=font(28),fill='#afcbd2')
for i in range(9):
 x=32+i%3*544;y=212+i//3*568
 path=next((P/'Previews').glob(f'{i+1:02d}_*.png'))
 # Prefer the principal device preview over an optional detail view.
 choices=[p for p in (P/'Previews').glob(f'{i+1:02d}_*.png') if not any(k in p.stem for k in ['Detail','Front'])]
 if choices:path=choices[0]
 im=Image.open(path).convert('RGB');im=im.resize((512,470),Image.Resampling.LANCZOS) if im.width!=im.height else im.resize((512,512),Image.Resampling.LANCZOS)
 # Keep square render proportions; each card reserves 76 px for captions.
 im=im.resize((480,480),Image.Resampling.LANCZOS)
 d.rounded_rectangle((x,y,x+512,y+548),radius=10,fill='white');out.paste(im,(x+16,y+8))
 d.text((x+18,y+491),f'{i+1:02d}  {labels[i]}',font=font(23,True),fill='#18323e');d.text((x+18,y+525),sub[i],font=font(18),fill='#60727a')
d.text((42,1935),'Actual mesh renders. Tiles are framed independently; the Blender scene preserves real-world scale.',font=font(20),fill='#526871')
out.save(P/'Previews/00_All_Devices_Overview.png')
