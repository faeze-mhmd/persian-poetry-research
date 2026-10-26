                                                                                         
                                                                   
   
from pathlib import Path
import shutil,subprocess,importlib.util,json,sys,math
from poetry_core import BASE,canonical,errors,prepare
def availability():
 exe=shutil.which('tesseract');langs=[]
 if exe:
  try:
   p=subprocess.run([exe,'--list-langs'],capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=15,check=True);langs=p.stdout.splitlines()
  except (OSError,subprocess.SubprocessError):pass
 return {'ocr_executable':exe,'ocr_persian_ready':'fas' in langs,'whisper_package':importlib.util.find_spec('whisper') is not None,'asr_checkpoint_required':True,'actual_media_evaluated':False}
def checked_file(path,max_bytes=20*1024*1024):
 p=Path(path).resolve()
 if not p.is_file():raise ValueError('input file missing')
 if p.stat().st_size>max_bytes:raise ValueError('input file exceeds 20 MiB')
 return p
def ocr_image(path):
 image=checked_file(path);exe=shutil.which('tesseract')
 if not exe:raise RuntimeError('Tesseract is not installed; OCR has not run.')
 status=availability()
 if not status['ocr_persian_ready']:raise RuntimeError('Persian fas traineddata missing; OCR has not run.')
 from PIL import Image,ImageOps
 import tempfile
 with Image.open(image) as im:
  if im.width*im.height>16000000:raise ValueError('image exceeds 16 million pixels')
  gray=ImageOps.autocontrast(ImageOps.exif_transpose(im).convert('L'))
  with tempfile.TemporaryDirectory(dir=BASE) as tmp:
   output=Path(tmp)/'prepared.png';gray.save(output)
   result=subprocess.run([exe,str(output),'stdout','-l','fas','--psm','6'],capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=120,check=True)
 return {'text':result.stdout.strip(),'source':'ocr','engine':'tesseract','preprocessing':'EXIF orientation, grayscale, autocontrast; psm6 fixed; not benchmarked'}
def audio_samples(path):
 import soundfile as sf
 import numpy as np
 from scipy.signal import resample_poly
 p=checked_file(path);info=sf.info(str(p))
 if info.duration<=0 or info.duration>60:raise ValueError('audio must be 0-60 seconds')
 audio,sr=sf.read(str(p),dtype='float32',always_2d=True)
 if audio.shape[1]>8:raise ValueError('too many audio channels')
 audio=audio.mean(axis=1)
 if not np.isfinite(audio).all():raise ValueError('non-finite audio')
 if sr!=16000:
  g=math.gcd(sr,16000);audio=resample_poly(audio,16000//g,sr//g).astype('float32')
 return audio
def transcribe_audio(path,checkpoint):
 p=checked_file(checkpoint,max_bytes=160*1024*1024)
 if importlib.util.find_spec('whisper') is None:raise RuntimeError('openai-whisper is not installed; ASR has not run.')
 import whisper,torch
 audio=audio_samples(path);torch.set_num_threads(1);model=whisper.load_model(str(p),device='cpu')
 result=model.transcribe(audio,language='fa',task='transcribe',fp16=False,temperature=0,condition_on_previous_text=False)
 return {'text':result['text'].strip(),'source':'asr','engine':'openai-whisper','checkpoint':str(p),'actual_media_benchmark':False}
def transcript_quality(reference,transcript):
                                                                                
 a=canonical(reference);b=canonical(transcript)
 if not a:raise ValueError('reference text is empty')
 from poetry_core import levenshtein
 ce=levenshtein(a,b);we=levenshtein(a.split(),b.split())
 return {'cer':ce/len(a),'wer':we/len(a.split()),'char_edits':ce,'reference_chars':len(a),'word_edits':we,'reference_words':len(a.split()),'normalization':'canonical without author masking'}
def main():
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');p.add_argument('--image');p.add_argument('--audio');p.add_argument('--checkpoint');a=p.parse_args()
 if a.check:print(json.dumps(availability(),ensure_ascii=False,indent=2));return
 if a.image:result=ocr_image(a.image)
 elif a.audio and a.checkpoint:result=transcribe_audio(a.audio,a.checkpoint)
 else:p.error('use --check, --image, or --audio plus an existing local --checkpoint')
                                                                                 
 from retrieval import load_index
 index=load_index();hits=index.rank([result['text']],'char_tfidf_cosine',k=5)[0]
 result['retrieved_poem_ids']=[pid for pid,_ in hits]
 print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
