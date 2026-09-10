#!/usr/bin/env python3
"""Recover RX3 1.19 application files from the official downloads; never flash."""
from pathlib import Path
import hashlib,io,tarfile,urllib.request,zipfile,subprocess,shutil
from firmware_image import crypt,load_key,autoexec_iso_metadata
base=Path(__file__).resolve().parent
sources=[
 'https://files.microcms-assets.io/assets/3b9e29ce734e49babfedb3f8d1e728e3/f7f69f5f428841898c6d98f9976c23bb/A9BEE4F7-6932-4E11-8D9F-5288F5F79EC2.zip',
 'https://files.microcms-assets.io/assets/3b9e29ce734e49babfedb3f8d1e728e3/5b39b9d79cc747c2b31ff39e22074bad/57CB205B-D45A-4143-BC09-22D8400074C2.zip']
allowed={'6280e9e2c1c31a2d943608fde753de79c61b08f775aa063805ff84519537f484','0cb9277161e57e35d3fd84823a926ea0ba6a342c07817cf871dc5d286b5b0169'}
def download(url,path,hashes):
 if not path.exists():
  print('Downloading',path.name,flush=True)
  partial=path.with_suffix(path.suffix+'.partial')
  urllib.request.urlretrieve(url,partial);partial.replace(path)
 if hashlib.sha256(path.read_bytes()).hexdigest() not in hashes:raise ValueError('Unexpected download hash: '+str(path))
 return path
def zip_member(path,name):
 with zipfile.ZipFile(path) as z:
  try:return z.read(name)
  except NotImplementedError:
   if shutil.which('unzip'):return subprocess.check_output(['unzip','-p',str(path),name])
   if shutil.which('7z'):return subprocess.check_output(['7z','x','-so',str(path),name])
   raise RuntimeError('Source ZIP compression requires unzip or 7z')
out=base/'extracted';out.mkdir(exist_ok=True)
parts={}
for i,url in enumerate(sources):
 p=download(url,base/f'official-source-{i}.zip',allowed)
 with zipfile.ZipFile(p) as z:
  for name in z.namelist():
   leaf=Path(name).name
   if leaf in ('pioneerdj_xdj_rx3.tar.bz2.00','pioneerdj_xdj_rx3.tar.bz2.01'):
    parts[leaf]=zip_member(p,name)
if len(parts)!=2:raise ValueError('Missing source archive part')
archive=out/'rx3.tar.bz2'
with archive.open('wb') as f:
 for name in sorted(parts):f.write(parts[name])
with tarfile.open(archive) as t:
 init=t.extractfile('pioneerdj_xdj_rx3/initramfs.tar.gz').read()
with tarfile.open(fileobj=io.BytesIO(init),mode='r:gz') as t:
 members=[m for m in t if m.isfile() and m.name.endswith('/usr/local/pdj/aes256.key')]
 if len(members)!=1:raise ValueError('Expected exactly one source-package key')
 key=t.extractfile(members[0]).read()
 (base/'aes256.key').write_bytes(key)
print('Recovered source-package firmware key; no device-specific key needed.')
p=download('https://downloads.support.alphatheta.com/firmwares/all-in-one-dj-systems/XDJ-RX3/XDJ-RX3_v119.zip',base/'XDJ-RX3_v119.zip',{'ccef2b983ff9effed51bbf976d9679d3a1ba967e0474258023c6957e9e608f83'})
with zipfile.ZipFile(p) as z:
 names=[n for n in z.namelist() if Path(n).name=='XDJRX3.UPD']
 update=zip_member(p,names[0])
# Observed v1.19 layout only: encrypted sectors followed by a 16-byte trailer.
# This is extraction, not update authentication or a flashable-image builder.
assert len(update)%512==16
plain=crypt(update[:-16],load_key(base/'aes256.key'),True)
print('Decrypted ISO volume:',autoexec_iso_metadata(plain))
iso=out/'XDJRX3.iso';iso.write_bytes(plain)
(out/'update').mkdir(exist_ok=True)
if shutil.which('7z'):
 subprocess.run(['7z','x','-y','-o'+str(out/'update'),str(iso)],check=True)
elif shutil.which('bsdtar'):
 subprocess.run(['bsdtar','-xf',str(iso),'-C',str(out/'update')],check=True)
else:raise RuntimeError('Install 7z or bsdtar for ISO extraction')
for archive_name,folder in [('pdj.tar.gz','player'),('gui.tar.gz','gui')]:
 with tarfile.open(out/'update/images'/archive_name) as t:
  for m in t:
   if not m.isfile():continue
   dest=out/folder/m.name
   if not dest.resolve().is_relative_to((out/folder).resolve()):raise ValueError('Unsafe archive path')
   dest.parent.mkdir(parents=True,exist_ok=True)
   dest.write_bytes(t.extractfile(m).read());dest.chmod(m.mode&0o777)
rbp=out/'player/pdj/rbp'
assert hashlib.sha256(rbp.read_bytes()).hexdigest()=='60bcbd8876116bf09f0d8f747f95d7c7d3081ebd39d6fe14d56005a22f7f3b09'
print('Verified original player:',rbp)
print('Next: python3 extract_cramfs.py; read ASTRA-PROMPT.md before any deployment.')
