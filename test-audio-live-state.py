import subprocess,struct,json
from pathlib import Path
pid=int(subprocess.check_output(['pgrep','-x','rbp-pi']))
rows=open(f'/proc/{pid}/maps').read().splitlines()
base=int(next(r.split()[0].split('-')[0] for r in rows if r.endswith('/lib/fbshim.so') and r.split()[2]=='00000000'),16)
text=subprocess.check_output(['arm-linux-gnueabi-nm',str(Path(__file__).resolve().parent/'build/fbshim-audio.so')],text=True)
syms={p[2]:int(p[0],16) for line in text.splitlines() if len(p:=line.split())==3 and p[0][0] in '0123456789abcdef'}
with open(f'/proc/{pid}/mem','rb',buffering=0) as f:
 def read(name,n):f.seek(base+syms[name]);return f.read(n)
 p=struct.unpack('<6IQi',read('pair',36));ready=struct.unpack('<2i',read('ready',8))
 print(json.dumps({'pid':pid,'ready':ready,'real_handles':list(p[3:5]),'pair_state':p[5],'next_retry_ms':p[6],'last_error':p[7],'rate':struct.unpack('<I',read('rate',4))[0]}))
