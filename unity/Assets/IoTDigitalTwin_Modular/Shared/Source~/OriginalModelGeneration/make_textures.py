from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import numpy as np, colorsys
P=Path(__file__).resolve().parents[1]/'Textures';P.mkdir(exist_ok=True)
FONT='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf';BOLD='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
def font(n,b=False):return ImageFont.truetype(BOLD if b else FONT,n)
def save(im,name):im.save(P/(name+'.png'))
def text_decal(name,text,size=80,color=(85,88,84,255),w=640,h=150):
 im=Image.new('RGBA',(w,h),(0,0,0,0));d=ImageDraw.Draw(im);d.text((w/2,h/2),text,anchor='mm',font=font(size),fill=color);save(im,name)
def seven(d,x,y,n,scale=1,color=(25,36,24)):
 # Standard seven-segment digits, including small fractional digits.
 shapes=[[(12,0),(56,0),(64,7),(56,14),(12,14),(4,7)],[(58,15),(66,7),(70,13),(67,56),(60,62),(54,55)],[(59,69),(66,62),(67,69),(64,112),(56,120),(50,112)],[(8,113),(50,113),(57,121),(49,127),(6,127),(0,120)],[(0,69),(7,62),(14,69),(11,111),(3,118),(-3,111)],[(3,14),(10,7),(17,14),(14,55),(7,62),(0,55)],[(12,57),(53,57),(60,64),(52,71),(10,71),(3,64)]]
 mapping={'0':[0,1,2,3,4,5],'1':[1,2],'2':[0,1,6,4,3],'3':[0,1,6,2,3],'4':[5,6,1,2],'5':[0,5,6,2,3],'6':[0,5,6,4,2,3],'7':[0,1,2],'8':list(range(7)),'9':[0,1,2,3,5,6]}
 for i in mapping[str(n)]:d.polygon([(x+px*scale,y+py*scale) for px,py in shapes[i]],fill=color)
# Green reflective LCD, matching reference 21.7 / 48.
im=Image.new('RGB',(600,760),(115,128,96));d=ImageDraw.Draw(im)
for k in range(4):d.rectangle((480+k*17,66-k*13,490+k*17,99),fill=(37,49,31))
seven(d,95,205,'2',2.0);seven(d,255,205,'1',2.0);d.ellipse((400,435,414,449),fill=(30,43,27));seven(d,445,327,'7',.95)
d.text((452,216),'°C',font=font(48),fill=(32,44,27));seven(d,218,553,'4',1.15);seven(d,310,553,'8',1.15)
d.text((405,638),'%',font=font(27),fill=(52,65,43))
for x in (104,240):d.rounded_rectangle((x,484,x+39,511),4,outline=(63,79,49),width=3);d.line((x+8,494,x+30,494),fill=(63,79,49),width=2)
save(im,'02_LCD_BaseColor')
# Nice thermostat blue-on-black screen.
im=Image.new('RGB',(1024,660),(7,12,21));d=ImageDraw.Draw(im);blue=(48,103,193)
d.text((471,49),'FRI',font=font(29),fill=blue);d.text((640,65),'15:47',font=font(56),fill=blue)
seven(d,220,180,'2',2.4,blue);seven(d,424,180,'2',2.4,blue);d.ellipse((608,463,624,479),fill=blue);seven(d,668,275,'6',1.55,blue)
d.text((829,208),'°C',font=font(48),fill=blue);d.text((71,553),'47%',font=font(49),fill=blue);d.text((831,553),'ON',font=font(42),fill=blue)
d.line([(90,352),(125,319),(161,352)],fill=blue,width=5);d.rectangle((102,352,148,391),outline=blue,width=5);save(im,'03_Thermostat_Display')
# Printed touch-key strip.
im=Image.new('RGBA',(1200,150),(0,0,0,0));d=ImageDraw.Draw(im);c=(100,105,100,255)
d.ellipse((70,35,120,85),outline=c,width=4);d.line((95,43,95,60,111,60),fill=c,width=4)
d.rectangle((281,33,334,82),outline=c,width=4);d.line((290,45,323,45),fill=c,width=3)
d.line((521,42,546,67,571,42),fill=c,width=5);d.line((758,67,783,42,808,67),fill=c,width=5)
d.arc((1010,26,1074,89),-65,245,fill=c,width=4);d.line((1042,21,1042,57),fill=c,width=4)
d.text((600,119),'Nice',anchor='mm',font=font(37,True),fill=c);save(im,'03_Touch_Key_Legends')
text_decal('05_Aqara_Logo','Aqara',80,(73,75,70,255));text_decal('05_Open_Legend','⌃  OPEN',44,(149,148,134,255))
text_decal('07_Siemens_Logo','SIEMENS',82,(0,104,115,255),700,150)
for name,s in [('Plus','+'),('Minus','−'),('Up','⌃'),('Down','⌄')]:text_decal('Icon_'+name,s,96,(99,104,100,255),160,160)
# Fabric weave: bitmap colour and tangent-space normal, no shader-only procedural dependency.
n=1024;yy,xx=np.mgrid[0:n,0:n];u=xx/8.;v=yy/8.
a=np.sin(2*np.pi*u);b=np.sin(2*np.pi*v);checker=((np.floor(u)+np.floor(v))%2)
height=.5+.23*np.where(checker<1,a,b)+.09*np.cos(2*np.pi*(u+v))
rng=np.random.default_rng(18);shade=np.clip(.76+.18*(height-.5)+rng.normal(0,.022,(n,n)),0,1)
rgb=np.stack([shade*.99,shade,shade*.98],2);save(Image.fromarray(np.uint8(rgb*255)),'08_Fabric_BaseColor')
gy,gx=np.gradient(height);normal=np.stack([-gx*2.6,-gy*2.6,np.ones_like(gx)],2);normal/=np.linalg.norm(normal,axis=2,keepdims=True);save(Image.fromarray(np.uint8((normal*.5+.5)*255)),'08_Fabric_Normal')
# A fine faceted diffuser for the camera floodlight.
y,x=np.mgrid[0:512,0:512];fac=((x//10+y//10)%2)*.08+.57+.09*np.sin((x+y)*np.pi/10);save(Image.fromarray(np.uint8(np.stack([fac,fac,fac],2)*255)),'04_Diffuser_BaseColor')
# DALI screen: layout recreated from the supplied MEETING ROOM reference.
w,h=1600,900;im=Image.new('RGB',(w,h),(174,218,238));d=ImageDraw.Draw(im)
d.rectangle((0,0,w,102),fill=(199,234,245));d.text((800,48),'MEETING ROOM',font=font(58,True),anchor='mm',fill=(133,77,37));d.text((28,24),'10:19  ≋',font=font(29),fill=(49,83,95));d.text((211,48),'‹',font=font(55),anchor='mm',fill=(90,149,177));d.text((1330,48),'›',font=font(55),anchor='mm',fill=(90,149,177))
for x,t in [(1420,'✎'),(1520,'≡')]:d.ellipse((x-36,11,x+36,83),fill=(7,21,30));d.text((x,47),t,font=font(48),anchor='mm',fill=(160,201,220))
d.rounded_rectangle((62,158,330,669),24,fill=(185,225,239));d.text((196,295),'ON',font=font(48,True),anchor='mm',fill=(29,66,79));d.line((134,415,258,415),fill=(58,105,126),width=4);d.text((196,552),'OFF',font=font(48,True),anchor='mm',fill=(29,66,79))
d.text((420,186),'0%',font=font(32),anchor='mm',fill=(65,111,131));d.rounded_rectangle((359,621,505,663),20,fill=(61,155,208))
# Colour-temperature gradient and colour picker field.
grad=Image.new('RGB',(217,516));ar=np.empty((516,217,3),dtype=np.uint8)
for y in range(516):
 t=y/515;c=np.array((202,137,72))*(1-t)+np.array((9,30,125))*t+70*np.sin(t*np.pi);ar[y,:]=np.clip(c,0,255)
grad=Image.fromarray(ar);mask=Image.new('L',grad.size);ImageDraw.Draw(mask).rounded_rectangle((0,0,216,515),24,fill=255);im.paste(grad,(536,149),mask)
arr=np.zeros((516,686,3),dtype=np.uint8)
for x in range(686):
 hue=(.14+x/685*.59)%1
 for y in range(516):
  sat=.9- .65*np.exp(-((x-220)**2+(y-280)**2)/35000);val=1-.60*y/515;arr[y,x]=np.array(colorsys.hsv_to_rgb(hue,sat,val))*255
field=Image.fromarray(arr);mask=Image.new('L',field.size);ImageDraw.Draw(mask).rounded_rectangle((0,0,685,515),27,fill=255);im.paste(field,(793,149),mask)
d=ImageDraw.Draw(im);d.line((579,491,710,491),fill=(15,46,72),width=4);d.ellipse((631,478,657,504),outline=(14,53,73),width=4);d.ellipse((921,537,953,569),outline=(15,66,51),width=5)
for x,tag,t in [(250,'S0','task light'),(800,'S1','presentation 1'),(1325,'S2','presentation 2')]:
 d.text((x,751),tag,font=font(27),anchor='mm',fill=(86,127,148));d.text((x,795),t,font=font(34),anchor='mm',fill=(39,78,100))
save(im,'09_DALI_Touchscreen_BaseColor')
print('TEXTURES_READY',len(list(P.glob('*.png'))))
