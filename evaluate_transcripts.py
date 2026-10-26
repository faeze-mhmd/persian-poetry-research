                                                                                      
from poetry_core import *
from retrieval import load_index
from media_pipeline import transcript_quality
import argparse
def evaluate_records(records,index):
 if not records:raise ValueError('no paired records')
 lookup={r['id']:i for i,r in enumerate(index.rows)};seen=set();out=[]
 for r in records:
  sid=r['sample_id']
  if sid in seen:raise ValueError('duplicate sample_id')
  seen.add(sid)
  if r['modality'] not in ['ocr','asr']:raise ValueError('modality must be ocr or asr')
  pid=int(r['poem_id'])
  if pid not in lookup:raise ValueError('target absent from gallery')
  if r.get('reference_origin')!='human_verified':raise ValueError('declare a human-verified reference; this is a declaration, not automatic verification')
  reference=r['reference_text'];transcript=r['transcript_text']
  if not prepare(reference) or prepare(reference) not in index.texts[lookup[pid]]:raise ValueError('reference does not match the target gallery text')
  hits=index.rank([transcript],'char_tfidf_cosine')[0];ids=[p for p,_ in hits]
  out.append({'sample_id':sid,'modality':r['modality'],'poem_id':pid,'transcript_metrics':transcript_quality(reference,transcript),'retrieval_rank':ids.index(pid)+1 if pid in ids else None,'human_verification':'user declared; not independently checked'})
 return out
def main():
 p=argparse.ArgumentParser();p.add_argument('--pairs',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 rows=[json.loads(s) for s in a.pairs.read_text(encoding='utf-8').splitlines() if s.strip()]
 results=evaluate_records(rows,load_index())
 with a.output.open('x',encoding='utf-8') as f:json.dump({'results':results,'raw_text_exported':False,'limits':'paired sample evaluation only; not a population benchmark'},f,ensure_ascii=False,indent=2)
 print(json.dumps({'samples':len(results),'output':str(a.output)}))
if __name__=='__main__':main()
