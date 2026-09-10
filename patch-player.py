from pathlib import Path
import struct
b=Path(__file__).parent;p=bytearray((b/'pi-runtime/rbp').read_bytes())
def patch(a,v):p[a-0x8000:a-0x8000+len(v)]=v
def words(a,*v):patch(a,struct.pack('<'+'I'*len(v),*v))
def branch(a,b,link=False):return (0xeb000000 if link else 0xea000000)|(((b-a-8)//4)&0xffffff)
words(0x10284,0xe320f000)
patch(0x4234c,(b/'pi-clock.bin').read_bytes())
words(0x42318,branch(0x42318,0x4234c))
words(0x42330,0xe92d4010,branch(0x42334,0x4234c,True),0xe300314d,0xe0810390,0xe8bd8010)
patch(0x443454,b'debug\0')
words(0x1a3ab8,0xe3003c03)
words(0x1a3ac0,0xe3403040)
# Original GPIO interrupts do not exist on the Pi; retain emulated initial states.
words(0x28ac8,0xe12fff1e)
# Select the existing audio profile; PCM devices are redirected by fbshim.
words(0x3c6654,0xe3a00001)
(b/'rbp-pi').write_bytes(p)
