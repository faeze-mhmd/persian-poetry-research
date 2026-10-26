import unittest,tempfile,base64
from pathlib import Path
from poetry_core import BASE,np,json
from media_engines import LocalEngines
from run_media_pilot import draw_couplet,source_couplet
class ActualMediaTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.engines=LocalEngines()
 def test_actual_engines_ready(self):
  s=self.engines.status();self.assertTrue(s['ocr_ready']);self.assertTrue(s['asr_ready'])
 def test_frozen_pilot_identity(self):
  from collections import Counter
  rows=json.loads((BASE/'real_media_sample_ids.json').read_text())['ids']
  self.assertEqual(len(rows),20);self.assertEqual(sorted(Counter(x['poet_id'] for x in rows).values()),[4]*5)
  for row in rows:self.assertEqual(len(source_couplet(row)[0]),2)
 def test_actual_ocr_and_render(self):
  from PIL import Image
  with tempfile.TemporaryDirectory(dir=BASE) as d:
   path=Path(d)/'fixture.png';draw_couplet(['این یک متن آزمایشی فارسی است','سلام دنیا'],path)
   with Image.open(path) as im:self.assertEqual(im.size,(1600,240))
   result=self.engines.ocr(path);self.assertIsInstance(result['text'],str);self.assertEqual(result['psm'],6)
 def test_degraded_render_geometry(self):
  from PIL import Image
  with tempfile.TemporaryDirectory(dir=BASE) as d:
   p=Path(d)/'fixture.png';draw_couplet(['متن آزمایشی','یک جمله فارسی'],p,True)
   with Image.open(p) as im:self.assertGreater(im.height,240)
 def test_actual_asr_silence_executes(self):
  result=self.engines.asr_samples(np.zeros(8000,dtype=np.float32));self.assertIsInstance(result['text'],str);self.assertEqual(result['engine'],'vosk0.3.45')
 def test_audio_shape_and_nonfinite_rejected(self):
  for x in [np.array([np.nan]),np.zeros((2,4)),np.zeros(960001)]:
   with self.assertRaises(ValueError):self.engines.asr_samples(x)
 def test_actual_upload_pipeline(self):
  from serve_demo import DemoApp
  app=DemoApp()
  with tempfile.TemporaryDirectory(dir=BASE) as d:
   p=Path(d)/'fixture.png';draw_couplet(['این یک متن آزمایشی فارسی است','سلام دنیا'],p)
   result=app.analyze_media(base64.b64encode(p.read_bytes()).decode(),'image')
   self.assertIsInstance(result['recognized_text'],str);self.assertIn('classification',result)
   if not result['recognized_text']:self.assertIsNone(result['classification']);self.assertEqual(result['hits'],[])
  with self.assertRaises(ValueError):app.analyze_media('invalid base64','image')
if __name__=='__main__':unittest.main(verbosity=2)
