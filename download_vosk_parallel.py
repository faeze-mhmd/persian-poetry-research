                                                                    
from pathlib import Path
import urllib.request,concurrent.futures,zipfile,time,json,hashlib
B=Path(__file__).resolve().parent;A=B/'media_assets';U='https://alphacephei.com/vosk/models/vosk-model-small-fa-0.42.zip'
def main():
 with urllib.request.urlopen(urllib.request.Request(U,headers={'Range':'bytes=0-1023'}),timeout=20) as r:
  if r.status!=206:raise RuntimeError('range download not supported')
  size=int(r.headers['Content-Range'].split('/')[-1])
 if size>64*1024*1024:raise RuntimeError('size cap')
 step=(size+3)//4
 def part(i):
  start=i*step;end=min(size-1,(i+1)*step-1);p=A/f'vosk_download.part{i}';have=p.stat().st_size if p.exists() else 0
  if have>end-start+1:raise RuntimeError('bad partial size')
  if have==end-start+1:return p
  req=urllib.request.Request(U,headers={'Range':f'bytes={start+have}-{end}'})
  with urllib.request.urlopen(req,timeout=90) as response:
   expected=f'bytes {start+have}-{end}/{size}'
   if response.status!=206 or response.headers.get('Content-Range')!=expected:raise RuntimeError('range mismatch')
   with p.open('ab') as f:
    while True:
     chunk=response.read(256*1024)
     if not chunk:break
     f.write(chunk)
  if p.stat().st_size!=end-start+1:raise RuntimeError('incomplete part')
  print('PART_COMPLETE',i,p.stat().st_size,flush=True);return p
 with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:paths=list(ex.map(part,range(4)))
 p=A/'vosk-model-small-fa-0.42.zip'
 with p.open('wb') as f:
  for partfile in paths:
   with partfile.open('rb') as r:
    while True:
     chunk=r.read(1024*1024)
     if not chunk:break
     f.write(chunk)
 with zipfile.ZipFile(p) as z:
  if z.testzip():raise RuntimeError('CRC failure')
  for n in z.namelist():
   if not (A/n).resolve().is_relative_to(A.resolve()):raise RuntimeError('unsafe path')
  z.extractall(A)
 print(json.dumps({'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'official_source':U}))
if __name__=='__main__':main()
