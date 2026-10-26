                                                                                   
from poetry_core import *
from retrieval import load_index
from run_models import load_models
from http.server import HTTPServer,BaseHTTPRequestHandler
import secrets,argparse,base64,binascii,tempfile
from media_engines import LocalEngines
NAMES={2:'حافظ',5:'مولانا',7:'سعدی',22:'صائب',43:'بیدل'}
class DemoApp:
 def __init__(self):
  self.index=load_index();self.model=load_models()['char__canonical__masked'];self.lookup={r['id']:r for r in self.index.rows};self.engines=LocalEngines()
 def analyze_media(self,encoded,kind):
  if kind not in ['image','audio'] or not isinstance(encoded,str):raise ValueError('unsupported media')
  data=base64.b64decode(encoded,validate=True)
  if not data or len(data)>5*1024*1024:raise ValueError('file exceeds 5MiB')
  with tempfile.TemporaryDirectory(dir=BASE) as d:
   path=Path(d)/('input.png' if kind=='image' else 'input.wav');path.write_bytes(data)
   recognized=self.engines.ocr(path) if kind=='image' else self.engines.asr(path)
  if not recognized['text'].strip():return {'hits':[],'classification':None,'recognized_text':'','media_engine':recognized['engine'],'recognition_empty':True}
  result=self.analyze(recognized['text']);result['recognized_text']=recognized['text'];result['media_engine']=recognized['engine'];return result
 def analyze(self,text):
  if not isinstance(text,str) or not text.strip():raise ValueError('متن شعر را وارد کن.')
  if len(text)>20000:raise ValueError('متن بیش از حد طولانی است.')
  if sum(ud.category(c).startswith('L') and 'ARABIC' in ud.name(c,'') for c in text)<4:raise ValueError('لطفاً دست‌کم چند واژهٔ فارسی وارد کن.')
  ranked=self.index.rank([text],'char_tfidf_cosine',k=3)[0]
  hits=[{'poem_id':pid,'author':NAMES[self.lookup[pid]['poet']],'excerpt':'\n'.join(self.lookup[pid]['text'].splitlines()[:4]),'similarity':score} for pid,score in ranked]
  author=int(self.model.predict([prepare(text)])[0])
  return {'hits':hits,'classification':{'author_id':author,'author':NAMES[author],'short_input':len(canonical(text).split())<40,'calibrated_probability':None},'scope':'fixed gallery retrieval and closed-set author estimate; distinct tasks'}
class Handler(BaseHTTPRequestHandler):
 def log_message(self,*args):pass
 def send(self,status,obj,html=False):
  b=(obj if html else json.dumps(obj,ensure_ascii=False)).encode('utf-8');self.send_response(status)
  self.send_header('Content-Type',('text/html' if html else 'application/json')+'; charset=utf-8');self.send_header('Content-Length',str(len(b)));self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.end_headers();self.wfile.write(b)
 def do_GET(self):
  if self.path=='/':
   page=(BASE/'demo.html').read_text(encoding='utf-8').replace('__DEMO_TOKEN__',json.dumps(self.server.demo_token))
   self.send(200,page,True)
  elif self.path=='/api/status':self.send(200,{'ready':True,'gallery_size':len(self.server.app.index.rows),'ocr_active':self.server.app.engines.status()['ocr_ready'],'asr_active':self.server.app.engines.status()['asr_ready']})
  else:self.send(404,{'error':'یافت نشد.'})
 def do_POST(self):
  if self.path!='/api/analyze':self.send(404,{'error':'یافت نشد.'});return
  origin=self.headers.get('Origin')
  expected=f'http://127.0.0.1:{self.server.server_port}'
  if self.headers.get('X-Demo-Token')!=self.server.demo_token or (origin and origin!=expected):self.send(403,{'error':'درخواست معتبر نیست.'});return
  try:
   size=int(self.headers.get('Content-Length','0'))
   if size<1 or size>7*1024*1024:raise ValueError('اندازهٔ درخواست معتبر نیست.')
   obj=json.loads(self.rfile.read(size));result=self.server.app.analyze_media(obj.get('data_base64'),obj['media_kind']) if obj.get('media_kind') else self.server.app.analyze(obj.get('text'))
   self.send(200,result)
  except (ValueError,TypeError,AttributeError,binascii.Error):self.send(400,{'error':'ورودی معتبر نیست یا متن قابل‌خواندنی پیدا نشد.'})
  except (RuntimeError,OSError):self.send(503,{'error':'پردازش فایل انجام نشد؛ آمادگی موتور و نوع فایل را بررسی کن.'})
def make_server(port=8765):
 server=HTTPServer(('127.0.0.1',port),Handler);server.app=DemoApp();server.demo_token=secrets.token_urlsafe(32);return server
def main():
 p=argparse.ArgumentParser();p.add_argument('--port',type=int,default=8765);a=p.parse_args();server=make_server(a.port)
 print(f'Local demo: http://127.0.0.1:{server.server_port}',flush=True)
 try:server.serve_forever()
 except KeyboardInterrupt:pass
 finally:server.server_close()
if __name__=='__main__':main()
