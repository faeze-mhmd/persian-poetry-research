import urllib.request,json,zipfile,hashlib,tarfile,io,concurrent.futures,time
from pathlib import Path
BASE=Path(__file__).resolve().parent;A=BASE/'media_assets';T=BASE/'media_runtime'
def fetch(url,path,cap):
 if path.exists() and path.stat().st_size>0:return path.read_bytes()
 size=0;chunks=[];t=time.monotonic()
 with urllib.request.urlopen(url,timeout=90) as r:
  expected=int(r.headers.get('Content-Length','0'))
  if expected>cap:raise RuntimeError('declared size cap')
  while True:
   chunk=r.read(1024*1024)
   if not chunk:break
   size+=len(chunk)
   if size>cap or time.monotonic()-t>300:raise RuntimeError('download resource cap')
   chunks.append(chunk)
   if size%(8*1024*1024)==0:print('DOWNLOADED_MiB',path.name,size//1024**2,flush=True)
 if expected and size!=expected:raise RuntimeError('incomplete response')
 b=b''.join(chunks);path.write_bytes(b);return b
def srt():
 meta=json.load(urllib.request.urlopen('https://pypi.org/pypi/srt/3.5.3/json',timeout=20));row=next(r for r in meta['urls'] if r['filename'].endswith('.tar.gz'))
 b=fetch(row['url'],A/row['filename'],1024*1024)
 assert hashlib.sha256(b).hexdigest()==row['digests']['sha256']
 with tarfile.open(fileobj=io.BytesIO(b),mode='r:gz') as tar:
  m=next(x for x in tar.getmembers() if x.name.endswith('/srt.py'));(T/'srt.py').write_bytes(tar.extractfile(m).read())
 return {'asset':'srt3.5.3 pure Python module','url':row['url'],'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'extraction':'only srt.py; no setup code run'}
def tessdata():
 meta=json.load(urllib.request.urlopen('https://api.github.com/repos/tesseract-ocr/tessdata_fast/commits/main',timeout=20));rev=meta['sha']
 url=f'https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast/{rev}/fas.traineddata';p=A/'tessdata'/'fas.traineddata';p.parent.mkdir(exist_ok=True)
 b=fetch(url,p,8*1024*1024)
 return {'asset':'fas.traineddata','revision':rev,'url':url,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def vosk():
 url='https://alphacephei.com/vosk/models/vosk-model-small-fa-0.42.zip';b=fetch(url,A/'vosk-model-small-fa-0.42.zip',64*1024*1024)
 with zipfile.ZipFile(io.BytesIO(b)) as z:
  for m in z.infolist():
   if not (A/m.filename).resolve().is_relative_to(A.resolve()):raise RuntimeError('unsafe path')
  if z.testzip():raise RuntimeError('archive CRC')
  z.extractall(A)
 return {'asset':'vosk-model-small-fa-0.42','url':url,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'license':'Apache2.0 per official model page'}
if __name__=='__main__':
 with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:rows=list(pool.map(lambda f:f(),[srt,tessdata,vosk]))
 total=sum(p.stat().st_size for p in A.glob('*.whl'))+sum(x['bytes'] for x in rows)
 if total>160*1024*1024:raise RuntimeError('aggregate download cap')
 (BASE/'MEDIA_ASSET_RECEIPT.json').write_text(json.dumps({'assets':rows,'aggregate_model_wheel_bytes':total},indent=2)+'\n',encoding='utf-8');print(json.dumps(rows))
