import unittest,tempfile,threading,urllib.request,urllib.error
from types import SimpleNamespace
from unittest.mock import patch
from poetry_core import *
from media_pipeline import transcript_quality,audio_samples,ocr_image
class MediaTests(unittest.TestCase):
 def test_transcription_metric_keeps_author_errors(self):
  self.assertGreater(transcript_quality('حافظ','سعدی')['cer'],0)
  self.assertEqual(transcript_quality('كِتاب يار','کتاب یار')['cer'],0)
 def test_audio_resampling_actual_wave(self):
  import soundfile as sf
  with tempfile.TemporaryDirectory(dir=BASE) as d:
   p=Path(d)/'audio.wav';sf.write(p,np.zeros((800,2),dtype='float32'),8000)
   x=audio_samples(p);self.assertEqual(x.shape,(1600,));self.assertEqual(x.dtype,np.float32)
 def test_missing_ocr_engine_is_explicit(self):
  with tempfile.TemporaryDirectory(dir=BASE) as d:
   p=Path(d)/'a.png';p.write_bytes(b'not processed')
   with patch('media_pipeline.shutil.which',return_value=None):
    with self.assertRaisesRegex(RuntimeError,'not installed'):ocr_image(p)
 def test_ocr_adapter_arguments_with_mock_engine(self):
  from PIL import Image
  with tempfile.TemporaryDirectory(dir=BASE) as d:
   p=Path(d)/'x.png';Image.new('RGB',(100,50),'white').save(p)
   with patch('media_pipeline.shutil.which',return_value='tesseract'),patch('media_pipeline.availability',return_value={'ocr_persian_ready':True}),patch('media_pipeline.subprocess.run',return_value=SimpleNamespace(stdout='متن آزمایشی')) as call:
    r=ocr_image(p);self.assertEqual(r['text'],'متن آزمایشی');args=call.call_args.args[0]
    self.assertEqual(args[-4:],['-l','fas','--psm','6'])
class DemoTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  from serve_demo import make_server
  cls.server=make_server(0);cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
  cls.url=f'http://127.0.0.1:{cls.server.server_port}'
 @classmethod
 def tearDownClass(cls):
  cls.server.shutdown();cls.server.server_close();cls.thread.join(timeout=5)
 def post(self,obj,token=True,origin=None):
  headers={'Content-Type':'application/json'}
  if token:headers['X-Demo-Token']=self.server.demo_token
  if origin:headers['Origin']=origin
  req=urllib.request.Request(self.url+'/api/analyze',data=json.dumps(obj,ensure_ascii=False).encode(),headers=headers)
  return urllib.request.urlopen(req,timeout=15)
 def test_page_and_status(self):
  with urllib.request.urlopen(self.url) as r:text=r.read().decode('utf-8')
  self.assertIn('کاوش شعر فارسی',text);self.assertNotIn('__DEMO_TOKEN__',text)
  with urllib.request.urlopen(self.url+'/api/status') as r:obj=json.loads(r.read())
  self.assertTrue(obj['ready']);self.assertEqual(obj['gallery_size'],500)
 def test_actual_models_and_retrieval(self):
  row=self.server.app.index.rows[0]
  with self.post({'text':row['text']}) as r:obj=json.loads(r.read())
  self.assertEqual(obj['hits'][0]['poem_id'],row['id'])
  self.assertIn(obj['classification']['author_id'],LABELS)
 def test_paired_transcript_checks(self):
  from evaluate_transcripts import evaluate_records
  row=self.server.app.index.rows[0];r={'sample_id':'fixture','poem_id':row['id'],'modality':'ocr','reference_origin':'human_verified','reference_text':row['text'],'transcript_text':row['text']}
  out=evaluate_records([r],self.server.app.index)
  self.assertEqual(out[0]['transcript_metrics']['cer'],0);self.assertEqual(out[0]['retrieval_rank'],1)
  with self.assertRaises(ValueError):evaluate_records([r,r],self.server.app.index)
  bad=dict(r);bad['reference_origin']='unverified'
  with self.assertRaises(ValueError):evaluate_records([bad],self.server.app.index)
 def test_empty_and_large_input(self):
  for text in ['', 'الف'*8000]:
   with self.assertRaises(urllib.error.HTTPError) as ctx:self.post({'text':text})
   self.assertEqual(ctx.exception.code,400)
 def test_wrong_origin_and_missing_token(self):
  for kwargs in [{'token':False},{'origin':'http://example.invalid'}]:
   with self.assertRaises(urllib.error.HTTPError) as ctx:self.post({'text':'این شعر آزمایشی است'},**kwargs)
   self.assertEqual(ctx.exception.code,403)
if __name__=='__main__':unittest.main(verbosity=2)
