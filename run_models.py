from poetry_core import *
from prepare_data import peak_memory
import warnings, joblib, sys, platform
from sklearn.dummy import DummyClassifier
from threadpoolctl import threadpool_limits
import sklearn, scipy

def check_freeze():
 f=json.loads((BASE/'SOURCE_FREEZE_v02.json').read_text(encoding='utf-8'))
 for name,h in f['source_sha256'].items():
  if digest((BASE/name).read_bytes())!=h:raise RuntimeError('changed frozen source: '+name)
 for name,key in [('dataset_local.json','dataset_local_sha256'),('split_manifest.json','split_sha256'),('corpus_manifest.json','corpus_manifest_sha256')]:
  if digest((BASE/name).read_bytes())!=f[key]:raise RuntimeError('changed frozen data: '+name)
 return f

def load_models():
 reg=json.loads((BASE/'model_registry.json').read_text(encoding='utf-8'))
 result={}
 for name,meta in reg['models'].items():
  p=BASE/'models'/f'{name}.joblib'
  if digest(p.read_bytes())!=meta['sha256']:raise RuntimeError('model hash: '+name)
  result[name]=joblib.load(p)
 return result

def evaluate(rows,models,seeds):
 y=[r['poet'] for r in rows];ids=[r['id'] for r in rows];results=[]
 for name,model in models.items():
  if name=='majority':texts=['']*len(rows)
  else:
   family,norm,masked=name.split('__');texts=[prepare(r['text'],norm,masked=='masked') for r in rows]
  pred=model.predict(texts).tolist()
  results.append({'model':name,'percent':0,'seed':None,'metrics':metrics(y,pred),'predictions':pred,'ids':ids})
 clean=[prepare(r['text']) for r in rows]
 for seed in seeds:
  for percent in [2,5,10]:
   queries=[];totals=Counter()
   for r,s in zip(rows,clean):
    q,meta=corrupt(s,r['id'],seed,percent);queries.append(q);totals.update(errors(s,q));totals.update({'eligible':meta['eligible'],'selected':meta['selected']})
   error_stats=dict(totals);error_stats['cer']=totals['char_edits']/totals['chars'];error_stats['wer']=totals['word_edits']/totals['words']
   for name in ['word__canonical__masked','char__canonical__masked','majority']:
    pred=models[name].predict(queries).tolist()
    results.append({'model':name,'percent':percent,'seed':seed,'metrics':metrics(y,pred),'predictions':pred,'ids':ids,'measured_errors':error_stats})
 return results

def main():
 check_freeze();(BASE/'models').mkdir(exist_ok=True)
 marker=BASE/'FIT_STARTED.json'
 with marker.open('x',encoding='utf-8') as f:json.dump({'time':time.time(),'scope':'nine study classifiers plus two audit-only timing fits'},f)
 data=json.loads((BASE/'dataset_local.json').read_text(encoding='utf-8'))
 train=[r for r in data if r['split']=='train'];val=[r for r in data if r['split']=='validation']
                                                                                       
 auditmeta=json.loads((BASE/'acquisition.json').read_text(encoding='utf-8'))['files'];audit=[]
 for x in auditmeta:
  obj=json.loads((BASE/'raw'/f"{x['id']}.json").read_text(encoding='utf-8'))
  audit.append(extract(obj,x['id'],x['poet_id'],x['category_id']))
 benchmark=[];fit_start=time.perf_counter()
 with threadpool_limits(limits=1):
  for family in ['word','char']:
   t=time.perf_counter()
   with warnings.catch_warnings(record=True) as ws:
    warnings.simplefilter('always');model=build_model(family);model.fit([prepare(r['text']) for r in audit],[r['poet'] for r in audit])
   benchmark.append({'family':family,'seconds':time.perf_counter()-t,'features':len(model['tfidf'].vocabulary_),'warnings':[str(w.message) for w in ws]})
  save('development_benchmark.json',{'fits':benchmark,'performance_not_evaluated':True,'peak_memory':peak_memory()})
  if peak_memory()>1073741824:raise RuntimeError('benchmark memory cap')
  models={};registry={};y=[r['poet'] for r in train]
  for family in ['word','char']:
   for norm in ['minimal','canonical']:
    for masked in [False,True]:
     name=family+'__'+norm+'__'+('masked' if masked else 'unmasked')
     texts=[prepare(r['text'],norm,masked) for r in train];m=build_model(family);t=time.perf_counter()
     with warnings.catch_warnings(record=True) as ws:
      warnings.simplefilter('always');m.fit(texts,y)
     path=BASE/'models'/f'{name}.joblib';joblib.dump(m,path,compress=3)
     registry[name]={'seconds':time.perf_counter()-t,'feature_count':len(m['tfidf'].vocabulary_),'iterations':np.asarray(m['classifier'].n_iter_).tolist(),'warnings':[str(w.message) for w in ws],'sha256':digest(path.read_bytes())}
     models[name]=m;print('FIT',name,registry[name]['feature_count'],round(registry[name]['seconds'],3),flush=True)
     if time.perf_counter()-fit_start>900 or peak_memory()>1073741824:raise RuntimeError('fit resource cap')
  m=DummyClassifier(strategy='most_frequent');t=time.perf_counter();m.fit(['']*len(y),y);path=BASE/'models'/'majority.joblib';joblib.dump(m,path)
  registry['majority']={'seconds':time.perf_counter()-t,'feature_count':0,'warnings':[],'sha256':digest(path.read_bytes())};models['majority']=m
  save('model_registry.json',{'models':registry,'training_ids':[r['id'] for r in train],'validation_refit':False,'environment':{'python':sys.version,'numpy':np.__version__,'sklearn':sklearn.__version__,'scipy':scipy.__version__,'platform':platform.platform()},'threads':1,'peak_memory':peak_memory(),'total_fit_wall_seconds':time.perf_counter()-fit_start})
  readouts=evaluate(val,models,CONFIG['corruption']['development_seeds'])
  save('validation_results.json',{'version':CONFIG['version'],'labels':LABELS,'truth':[r['poet'] for r in val],'readouts':readouts,'test_evaluated':False})
  print('VALIDATION',json.dumps({r['model']:r['metrics']['macro_f1'] for r in readouts if r['percent']==0}),flush=True)
if __name__=='__main__':main()
