                                                                                          
                                                                               
                                                                                     
   
import argparse,json,hashlib,time,urllib.request
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--audit-only',action='store_true');p.add_argument('--new-only',action='store_true');args=p.parse_args()
root=Path(__file__).resolve().parent;rev='86455ef602c55f64282ce9a0fba4b1084153b5a7'
meta=json.loads((root/'corpus_manifest.json').read_text(encoding='utf-8'))['files']
total=0;start=time.monotonic();downloaded=0
for r in meta:
 audit=r.get('audit',False)
 if args.audit_only and not audit:continue
 if args.new_only and audit:continue
 dest=root/('raw' if audit else 'corpus')/f"{r['id']}.json";dest.parent.mkdir(exist_ok=True)
 if dest.exists():
  if hashlib.sha256(dest.read_bytes()).hexdigest()==r['sha256']:continue
  raise RuntimeError('existing file hash mismatch: '+str(dest))
 if time.monotonic()-start>1800:raise RuntimeError('time cap')
 url=f"https://raw.githubusercontent.com/ganjoor/ganjoor-data/{rev}/{r['path']}"
 with urllib.request.urlopen(url,timeout=30) as response:b=response.read(524289)
 total+=len(b)
 if len(b)>524288 or total>31457280:raise RuntimeError('size cap')
 if hashlib.sha256(b).hexdigest()!=r['sha256']:raise RuntimeError('source hash mismatch')
 dest.write_bytes(b);downloaded+=1
print(json.dumps({'downloaded':downloaded,'bytes':total,'seconds':time.monotonic()-start}))
