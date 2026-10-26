                                                                                      
                                                                                    
                                                                     
   
import urllib.request,json,hashlib,zipfile,sys,concurrent.futures
from pathlib import Path
BASE=Path(__file__).resolve().parent
ASSETS=BASE/'media_assets';TARGET=BASE/'media_runtime';ASSETS.mkdir(exist_ok=True);TARGET.mkdir(exist_ok=True)
PACKAGES={'tesserocr':'2.12.0','vosk':'0.3.45','arabic-reshaper':'3.0.0','python-bidi':'0.6.7'}
def wheel(package,version):
 meta=json.load(urllib.request.urlopen(f'https://pypi.org/pypi/{package}/{version}/json',timeout=20))
 matches=[r for r in meta['urls'] if r['filename'].endswith('.whl') and ('cp311-cp311-win_amd64' in r['filename'] or 'py3-none-win_amd64' in r['filename'] or 'py3-none-any' in r['filename'])]
 if len(matches)!=1:raise RuntimeError((package,[r['filename'] for r in matches]))
 item=matches[0];path=ASSETS/item['filename']
 if item['size']>32*1024*1024:raise RuntimeError('wheel size cap')
 if not path.exists():
  download_url=item['url'].replace('https://files.pythonhosted.org','https://mirror-pypi.runflare.com') if package=='tesserocr' else item['url']
  with urllib.request.urlopen(download_url,timeout=45) as response:
   chunks=[];size=0
   while True:
    part=response.read(1024*1024)
    if not part:break
    chunks.append(part);size+=len(part)
    if size>32*1024*1024:raise RuntimeError('download cap')
   b=b''.join(chunks)
  path.write_bytes(b)
 b=path.read_bytes()
 if hashlib.sha256(b).hexdigest()!=item['digests']['sha256'] or len(b)!=item['size']:raise RuntimeError('registry integrity mismatch')
 with zipfile.ZipFile(path) as z:
  for info in z.infolist():
   destination=(TARGET/info.filename).resolve()
   if not destination.is_relative_to(TARGET.resolve()):raise RuntimeError('unsafe archive path')
  z.extractall(TARGET)
 return {'package':package,'version':version,'bytes':len(b),'filename':item['filename'],'sha256':item['digests']['sha256'],'source':item['url'],'transport':'configured PyPI mirror for tesserocr; bytes checked against official PyPI SHA256','install':'project-local wheel extraction; runtime import validation required'}
if __name__=='__main__':
 with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:rows=list(pool.map(lambda kv:wheel(*kv),PACKAGES.items()))
 (BASE/'MEDIA_RUNTIME_RECEIPT.json').write_text(json.dumps(rows,indent=2)+'\n',encoding='utf-8')
 print(json.dumps(rows))
