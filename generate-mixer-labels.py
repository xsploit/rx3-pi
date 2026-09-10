#!/usr/bin/env python3
from pathlib import Path
import subprocess
def spans(text,w,h,size,ox=0,oy=0):
 b=subprocess.check_output(['magick','-size',f'{w}x{h}','xc:black','-font','Liberation-Sans','-pointsize',str(size),'-fill','white','-gravity','center','-annotate','0',text,'-depth','8','gray:-'])
 assert len(b)==w*h
 out=[]
 for y in range(h):
  x=0
  while x<w:
   if b[y*w+x]<128:x+=1;continue
   start=x
   while x<w and b[y*w+x]>=128:x+=1
   out.append((ox+start,oy+y,x-start))
 return out
labels=['TRIM','HIGH','MID','LOW','FILTER','LEVEL','MASTER','CROSS','HP VOL','HP MIX','TRIM','HIGH','MID','LOW','FILTER','LEVEL','TEMPO %','TEMPO %']
a=[]
for i,label in enumerate(labels):
 if i==7:continue
 if i in (6,8,9):x,w={6:(480,106),8:(586,107),9:(693,107)}[i]
 else:
  col=6 if i>=16 else (i if i<6 else i-10)
  base=0 if i<6 or i==16 else 800
  x=base+col*480//7;w=(col+1)*480//7-col*480//7
 a+=spans(label,w,32,14,x,65)
for label,x,w in [('DECK 1',16,128),('CROSSFADER',480,320),('DECK 2',816,128)]:a+=spans(label,w,32,18,x,560)
for label,x,w in [('DECK 1',0,480),('OUTPUT / HEADPHONES',480,320),('DECK 2',800,480)]:a+=spans(label,w,48,20,x,6)
for label,x in [('HEADPHONE CUE 1',32),('HEADPHONE CUE 2',848)]:a+=spans(label,400,70,22,x,650)
s='/* Generated mixer labels; pixel spans in native panel coordinates. */\nstatic const unsigned short mixer_text[][3]={\n'+''.join('{%d,%d,%d},\n'%r for r in a)+'};\n'
s+='static const unsigned short mixer_digits[][4]={\n'
for d in range(10):
 for x,y,w in spans(str(d),12,26,18):s+='{%d,%d,%d,%d},\n'%(d,x,y,w)
s+='};\n'
s+='static const unsigned short tempo_text[][4]={\n'
for char in '0123456789+-.':
 for x,y,w in spans(char,8,26,13):s+='{%d,%d,%d,%d},\n'%(ord(char),x,y,w)
s+='};\n'
Path(__file__).with_name('native-mixer-glyphs.h').write_text(s)
