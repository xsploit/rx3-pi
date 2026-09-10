#!/usr/bin/env python3
"""Generate original 25% label pixels, without copying firmware artwork."""
from pathlib import Path
import subprocess
w,h=47,20
b=subprocess.check_output(['magick','-size',f'{w}x{h}','xc:black','-font','Liberation-Sans','-pointsize','14','-fill','white','-gravity','center','-annotate','0','25%','-depth','8','gray:-'])
assert len(b)==w*h
# Red coverage on black matches the native WIDE slot; column47 is untouched.
s='/* Generated original 25% artwork; red-on-black RGB565, 47x20. */\nstatic const unsigned short tempo25_pixels[940]={\n'
for y in range(h):s+=','.join(str((b[y*w+x]*31//255)<<11) for x in range(w))+',\n'
Path(__file__).with_name('native-tempo25-glyphs.h').write_text(s+'};\n')
