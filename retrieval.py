                                                                                  
from poetry_core import *
from prepare_data import peak_memory
from run_models import check_freeze
import joblib,warnings
from threadpoolctl import threadpool_limits
PROTOCOL=BASE/'retrieval_protocol_v01.json'
METHODS=['exact_substring','word_tfidf_cosine','char_tfidf_cosine']
class PoetryIndex:
 def __init__(self,rows):
  self.rows=sorted(rows,key=lambda r:r['id']);self.ids=np.array([r['id'] for r in self.rows])
  self.texts=[prepare(r['text']) for r in self.rows];self.models={};self.matrices={};self.fit_log=[]
  for family in ['word','char']:
   vectorizer=build_model(family)['tfidf'];t=time.perf_counter()
   with warnings.catch_warnings(record=True) as ws:
    warnings.simplefilter('always');matrix=vectorizer.fit_transform(self.texts)
   self.models[family]=vectorizer;self.matrices[family]=matrix
   self.fit_log.append({'family':family,'seconds':time.perf_counter()-t,'features':len(vectorizer.vocabulary_),'warnings':[str(w.message) for w in ws]})
 def rank(self,queries,method,k=None,prepared=False):
  texts=queries if prepared else [prepare(s) for s in queries]
  result=[]
  if method=='exact_substring':
   for q in texts:
    ids=[int(self.ids[i]) for i,s in enumerate(self.texts) if q and q in s]
    result.append([(pid,1.0) for pid in (ids if k is None else ids[:k])])
  else:
   family={'word_tfidf_cosine':'word','char_tfidf_cosine':'char'}.get(method)
   if family is None:raise ValueError('unknown retrieval method')
   scores=(self.models[family].transform(texts)@self.matrices[family].T).toarray()
   for row in scores:
    order=np.lexsort((self.ids,-row));order=[int(i) for i in order if row[i]>0]
    if k is not None:order=order[:k]
    result.append([(int(self.ids[i]),float(row[i])) for i in order])
  return result

def query_for(row):
 obj=json.loads((BASE/'corpus'/f"{row['id']}.json").read_text(encoding='utf-8'));groups=defaultdict(list)
 for v in sorted(obj['Verses'],key=lambda v:v['VOrder']):groups[v['CoupletIndex']].append(v['Text'])
 good=[(i,v) for i,v in groups.items() if len(v)==2]
 ci,verses=min(good,key=lambda t:hashlib.sha256(f"retrieval-query-v1|20261025|{row['id']}|{t[0]}".encode('ascii')).digest())
 return {'id':row['id'],'poet':row['poet'],'couplet_index':ci,'query':prepare('\n'.join(verses))}

def summarize(ranks):
 n=len(ranks)
 if n==0:raise ValueError('empty evaluation')
 return {**{f'recall_at_{k}':sum(x is not None and x<=k for x in ranks)/n for k in [1,5,10]},
         'mrr':sum(1/x if x else 0 for x in ranks)/n,'missing_target_fraction':sum(x is None for x in ranks)/n,'queries':n}
def evaluate(index,queries,seeds):
 conditions=[(0,None)]+[(p,s) for s in seeds for p in [2,5,10]];out=[]
 for percent,seed in conditions:
  strings=[];totals=Counter()
  for q in queries:
   if percent:query,meta=corrupt(q['query'],q['id'],seed,percent)
   else:query=q['query']
   strings.append(query);totals.update(errors(q['query'],query))
  for method in METHODS:
   t=time.perf_counter();rankings=index.rank(strings,method,prepared=True);ranks=[];hits=[];empty=0
   for q,ranking in zip(queries,rankings):
    ids=[x[0] for x in ranking];ranks.append(ids.index(q['id'])+1 if q['id'] in ids else None)
    hits.append(ids[:10]);empty+=not ids
   m=summarize(ranks);m['empty_query_fraction']=empty/len(queries)
   m['cer']=totals['char_edits']/max(1,totals['chars']);m['wer']=totals['word_edits']/max(1,totals['words'])
   out.append({'method':method,'percent':percent,'seed':seed,'metrics':m,'ids':[q['id'] for q in queries],'poets':[q['poet'] for q in queries],'target_ranks':ranks,'top10_ids':hits,'seconds':time.perf_counter()-t})
 return out

def fit_and_develop():
 check_freeze()
 with (BASE/'RETRIEVAL_FIT_STARTED.json').open('x') as f:json.dump({'time':time.time()},f)
 rows=json.loads((BASE/'dataset_local.json').read_text(encoding='utf-8'));t=time.perf_counter()
 with threadpool_limits(limits=1):index=PoetryIndex(rows)
 if time.perf_counter()-t>300 or peak_memory()>1073741824:raise RuntimeError('retrieval resource cap')
 path=BASE/'retrieval_index_local.joblib';joblib.dump(index,path,compress=3)
                                                                        
 reloaded=joblib.load(path)
 dev=[query_for(r) for r in rows if r['split']=='validation']
 test=[query_for(r) for r in rows if r['split']=='test']
 save('retrieval_queries_local.json',{'validation':dev,'test':test})
 ids={split:[{k:q[k] for k in ('id','poet','couplet_index')} for q in qs] for split,qs in [('validation',dev),('test',test)]}
 save('retrieval_query_manifest.json',ids)
 results=evaluate(reloaded,dev,[3101,3102,3103]);save('retrieval_validation.json',{'readouts':results,'test_evaluated':False})
 freeze={'protocol_sha256':digest(PROTOCOL.read_bytes()),'index_sha256':digest(path.read_bytes()),'dataset_sha256':digest((BASE/'dataset_local.json').read_bytes()),'query_manifest_sha256':digest((BASE/'retrieval_query_manifest.json').read_bytes()),'queries_local_sha256':digest((BASE/'retrieval_queries_local.json').read_bytes()),'source_sha256':{n:digest((BASE/n).read_bytes()) for n in ['retrieval.py','test_retrieval.py','run_retrieval_final.py']},'fit_log':index.fit_log,'peak_memory':peak_memory(),'classification_source_freeze_verified':True}
 save('RETRIEVAL_FREEZE.json',freeze)
 print(json.dumps({'status':'DEVELOPMENT_DONE','gallery':len(rows),'validation_queries':len(dev),'frozen_test_queries':len(test),'fit_log':index.fit_log,'clean_validation':{r['method']:r['metrics'] for r in results if r['percent']==0},'peak_MiB':peak_memory()/2**20}))
def load_index():
 freeze=json.loads((BASE/'RETRIEVAL_FREEZE.json').read_text(encoding='utf-8'))
 p=BASE/'retrieval_index_local.joblib'
 if digest(p.read_bytes())!=freeze['index_sha256']:raise RuntimeError('index hash mismatch')
 return joblib.load(p)
