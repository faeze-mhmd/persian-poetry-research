                                                                                       
from poetry_core import *
from pathlib import Path
import sys
RUNTIME=BASE/'media_runtime'
if RUNTIME.is_dir() and str(RUNTIME) not in sys.path:sys.path.insert(0,str(RUNTIME))
from media_pipeline import checked_file,audio_samples
class LocalEngines:
 def __init__(self):self.vosk_model=None
 def status(self):
  import importlib.util
  return {'ocr_ready':importlib.util.find_spec('tesserocr') is not None and (BASE/'media_assets'/'tessdata'/'fas.traineddata').is_file(),'asr_ready':importlib.util.find_spec('vosk') is not None and (BASE/'media_assets'/'vosk-model-small-fa-0.42'/'am'/'final.mdl').is_file(),'no_external_inference':True}
 def ocr(self,path):
  import tesserocr
  from PIL import Image,ImageOps
  p=checked_file(path)
  with Image.open(p) as source:
   if source.width*source.height>16000000:raise ValueError('image exceeds 16MP')
   gray=ImageOps.autocontrast(ImageOps.exif_transpose(source).convert('L'))
   with tesserocr.PyTessBaseAPI(path=str(BASE/'media_assets'/'tessdata'),lang='fas',psm=6) as api:
    api.SetImage(gray);text=api.GetUTF8Text()
  return {'text':text.strip(),'engine':'tesserocr2.12.0 / Tesseract','language':'fas','psm':6}
 def asr(self,path):
  return self.asr_samples(audio_samples(path))
 def asr_samples(self,audio):
  import vosk
  if self.vosk_model is None:
   vosk.SetLogLevel(-1);self.vosk_model=vosk.Model(str(BASE/'media_assets'/'vosk-model-small-fa-0.42'))
  audio=np.asarray(audio,dtype=np.float32)
  if audio.ndim!=1 or not 0<len(audio)<=16000*60 or not np.isfinite(audio).all():raise ValueError('mono finite audio up to60s required')
  pcm=(np.clip(audio,-1,1)*32767).astype('<i2').tobytes()
  recognizer=vosk.KaldiRecognizer(self.vosk_model,16000);texts=[]
  for i in range(0,len(pcm),8000):
   if recognizer.AcceptWaveform(pcm[i:i+8000]):texts.append(json.loads(recognizer.Result()).get('text',''))
  texts.append(json.loads(recognizer.FinalResult()).get('text',''))
  return {'text':' '.join(x for x in texts if x).strip(),'engine':'vosk0.3.45','model':'vosk-model-small-fa-0.42'}
