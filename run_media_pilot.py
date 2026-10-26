                                                                                                     
from poetry_core import *
from media_engines import LocalEngines
from media_pipeline import transcript_quality
from retrieval import load_index
from prepare_data import peak_memory
import sys,urllib.request,hashlib
from PIL import Image,ImageDraw,ImageFont,ImageFilter,features
from scipy.signal import resample_poly
import soundfile as sf,math
A=BASE/'media_assets'
def source_couplet(item):
 o=json.loads((BASE/'corpus'/f"{item['poem_id']}.json").read_text(encoding='utf-8'));vs=sorted([v for v in o['Verses'] if v['CoupletIndex']==item['couplet_index']],key=lambda v:v['VOrder'])
 if len(vs)!=2:raise RuntimeError('couplet structure')
 return vs,[canonical(v['Text']) for v in vs]
def draw_couplet(lines,path,degraded=False):
 import arabic_reshaper
 from bidi.algorithm import get_display
 size=36
 while True:
  font=ImageFont.truetype(r'C:\Windows\Fonts\tahoma.ttf',size)
  visual=[get_display(arabic_reshaper.reshape(x)) for x in lines]
  if max(font.getlength(x) for x in visual)<=1520 or size==20:break
  size-=1
 image=Image.new('RGB',(1600,240),'white');draw=ImageDraw.Draw(image)
 for i,line in enumerate(visual):draw.text((1540,45+i*80),line,font=font,fill='black',anchor='ra')
 if degraded:image=image.resize((800,120),Image.Resampling.BILINEAR).resize((1600,240),Image.Resampling.BILINEAR).filter(ImageFilter.GaussianBlur(1.0)).rotate(2,resample=Image.Resampling.BICUBIC,expand=True,fillcolor='white')
 image.save(path);return {'font_size':size,'sha256':digest(path.read_bytes())}
def rank(index,text,pid):
 hits=index.rank([text],'char_tfidf_cosine')[0];ids=[x[0] for x in hits]
 return ids.index(pid)+1 if pid in ids else None
def audio_segment(item):
 a=item['selection'];pid=item['poem_id'];rid=a['id']
 vs,lines=source_couplet(item);timing=json.loads((A/f'verses_{rid}.json').read_text(encoding='utf-8'));lookup={x['verseOrder']:x for x in timing}
 for v in vs:
  if v['VOrder'] not in lookup or audit_normal(v['Text'])!=audit_normal(lookup[v['VOrder']]['verseText']):raise ValueError('upstream/source verse text mismatch')
 end_order=max(v['VOrder'] for v in vs)+1
 if end_order not in lookup:raise ValueError('no next verse boundary')
 start=max(0,lookup[vs[0]['VOrder']]['audioStartMilliseconds']/1000-.25);end=lookup[end_order]['audioStartMilliseconds']/1000+.25
 if not 0<end-start<=60:raise ValueError('invalid segment duration')
 p=A/f"recitation_{rid}.mp3"
 if not p.exists():
  with urllib.request.urlopen(a['mp3Url'],timeout=30) as response:b=response.read(2*1024*1024+1)
  if len(b)>2*1024*1024 or len(b)!=a['mp3SizeInBytes']:raise ValueError('audio size mismatch')
  if hashlib.md5(b).hexdigest()!=a['mp3FileCheckSum'].lower():raise ValueError('upstream MD5 mismatch')
  p.write_bytes(b)
 cached=p.read_bytes()
 if len(cached)!=a['mp3SizeInBytes'] or hashlib.md5(cached).hexdigest()!=a['mp3FileCheckSum'].lower():raise ValueError('cached audio does not match upstream checksum')
 with sf.SoundFile(str(p)) as f:
  sr=f.samplerate
  if end>len(f)/sr+.3:raise ValueError('segment exceeds file')
  f.seek(int(start*sr));audio=f.read(frames=int((end-start)*sr),dtype='float32',always_2d=True).mean(axis=1)
 if sr!=16000:
  g=math.gcd(sr,16000);audio=resample_poly(audio,16000//g,sr//g).astype(np.float32)
 wav=A/f"clip_{rid}.wav";sf.write(wav,audio,16000,subtype='PCM_16')
 return audio,' '.join(lines),{'recitation_id':rid,'poem_id':pid,'seconds':len(audio)/16000,'start_seconds':start,'end_seconds':end,'original_mp3_sha256':digest(p.read_bytes()),'clip_sha256':digest(wav.read_bytes()),'asr_input_float32_sha256':digest(np.asarray(audio,dtype='<f4').tobytes()),'mp3_url':a['mp3Url'],'timing_url':f'https://api.ganjoor.net/api/audio/verses/{rid}','reference_origin':'upstream aligned source, not independently human verified'}
def main():
 engines=LocalEngines();status=engines.status()
 if not all(status[k] for k in ['ocr_ready','asr_ready']):raise RuntimeError(status)
 protocol=BASE/'MEDIA_PROTOCOL_v01.json'
 with (BASE/'MEDIA_PILOT_STARTED.json').open('x',encoding='utf-8') as f:json.dump({'time':time.time(),'protocol_sha256':digest(protocol.read_bytes()),'sources':{n:digest((BASE/n).read_bytes()) for n in ['media_engines.py','run_media_pilot.py']}},f)
 index=load_index();pilot=json.loads((BASE/'real_media_sample_ids.json').read_text())['ids'];out=[];local=[]
 t=time.perf_counter()
 for item in pilot:
  _,lines=source_couplet(item);reference=' '.join(lines)
  for condition in ['clean','degraded']:
   path=A/f"render_{item['poem_id']}_{condition}.png";meta=draw_couplet(lines,path,condition=='degraded');started=time.perf_counter();result=engines.ocr(path)
   out.append({'modality':'rendered_ocr','condition':condition,'poem_id':item['poem_id'],'poet_id':item['poet_id'],'metrics':transcript_quality(reference,result['text']),'target_rank':rank(index,result['text'],item['poem_id']),'seconds':time.perf_counter()-started,'image':meta,'reference_origin':'programmatic canonical source rendering'})
   local.append({'id':item['poem_id'],'condition':condition,'reference':reference,'transcript':result['text']})
  if time.perf_counter()-t>900 or peak_memory()>1073741824:raise RuntimeError('pilot resource cap')
 candidates=json.loads((A/'audio_candidate_selection.json').read_text(encoding='utf-8'));skips=[]
 for item in candidates:
  if not item.get('selection'):skips.append({'poem_id':item['poem_id'],'reason':'no eligible upstream recitation'});continue
  try:audio,reference,meta=audio_segment(item)
  except (ValueError,OSError,urllib.error.URLError) as e:skips.append({'poem_id':item['poem_id'],'reason':str(e)});continue
  started=time.perf_counter();result=engines.asr_samples(audio)
  out.append({'modality':'recitation_asr','condition':'upstream_timed','poem_id':item['poem_id'],'poet_id':item['poet_id'],'metrics':transcript_quality(reference,result['text']),'target_rank':rank(index,result['text'],item['poem_id']),'seconds':time.perf_counter()-started,'audio':meta})
  local.append({'id':item['poem_id'],'condition':'asr','reference':reference,'transcript':result['text']})
 save('media_transcripts_local.json',local)
 save('media_pilot_results.json',{'protocol_sha256':digest(protocol.read_bytes()),'results':out,'skips':skips,'seconds':time.perf_counter()-t,'peak_memory':peak_memory(),'limits':'Rendered OCR and small upstream-aligned audio pilot only; no real-image generalization, no human-verified ASR benchmark, no training or tuning'})
 save('MEDIA_PILOT_COMPLETED.json',{'results_sha256':digest((BASE/'media_pilot_results.json').read_bytes()),'rows':len(out)})
 summaries={}
 for modality,condition in [('rendered_ocr','clean'),('rendered_ocr','degraded'),('recitation_asr','upstream_timed')]:
  rows=[r for r in out if r['modality']==modality and r['condition']==condition]
  summaries[modality+'/'+condition]={'n':len(rows),'cer':sum(r['metrics']['char_edits'] for r in rows)/max(1,sum(r['metrics']['reference_chars'] for r in rows)),'wer':sum(r['metrics']['word_edits'] for r in rows)/max(1,sum(r['metrics']['reference_words'] for r in rows)),'recall_at1':sum(r['target_rank']==1 for r in rows)/max(1,len(rows))}
 save('MEDIA_PILOT_SUMMARY.json',summaries);print(json.dumps({'summary':summaries,'skips':skips,'seconds':time.perf_counter()-t,'peak_MiB':peak_memory()/2**20}),flush=True)
if __name__=='__main__':main()
