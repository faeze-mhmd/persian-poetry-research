from poetry_core import *
from run_models import check_freeze,load_models,evaluate
from prepare_data import peak_memory
from threadpoolctl import threadpool_limits

def fast_f1(y,p):
 cm=np.bincount(y*5+p,minlength=25).reshape(5,5);den=cm.sum(0)+cm.sum(1)
 return float(np.divide(2*np.diag(cm),den,out=np.zeros(5),where=den!=0).mean())
def bootstrap(truth,readouts):
 enc={v:i for i,v in enumerate(LABELS)};y=np.array([enc[v] for v in truth])
 lookup={(r['model'],r['percent'],r['seed']):np.array([enc[v] for v in r['predictions']]) for r in readouts}
 seeds=CONFIG['corruption']['test_seeds']
 def drops(ix):
  d=[]
  for family in ['word','char']:
   name=family+'__canonical__masked'
   clean=fast_f1(y[ix],lookup[name,0,None][ix])
   noisy=np.mean([fast_f1(y[ix],lookup[name,5,s][ix]) for s in seeds])
   d.append(clean-noisy)
  return float(d[0]-d[1])
 point=drops(np.arange(len(y)));rng=np.random.default_rng(20261028);strata=[np.flatnonzero(y==i) for i in range(5)]
 values=[]
 for _ in range(2000):
  ix=np.concatenate([rng.choice(a,size=len(a),replace=True) for a in strata]);values.append(drops(ix))
 return {'delta_drop':point,'ci95_percentile':np.percentile(values,[2.5,97.5]).tolist(),'replicates':2000,'seed':20261028,'conditional_on_fixed_split_models':True,'bootstrap_values':values}
def main():
 check_freeze()
 plan=json.loads((BASE/'FINAL_EVALUATION_PLAN.json').read_text(encoding='utf-8'))
 for name,key in [('validation_results.json','validation_sha256'),('model_registry.json','registry_sha256'),('SOURCE_FREEZE_v02.json','freeze_sha256')]:
  if digest((BASE/name).read_bytes())!=plan[key]:raise RuntimeError('plan mismatch '+name)
 with (BASE/'FINAL_EVALUATION_STARTED.json').open('x',encoding='utf-8') as f:json.dump({'time':time.time(),'plan_sha256':digest((BASE/'FINAL_EVALUATION_PLAN.json').read_bytes())},f)
 t=time.perf_counter();data=json.loads((BASE/'dataset_local.json').read_text(encoding='utf-8'));rows=[r for r in data if r['split']=='test'];truth=[r['poet'] for r in rows]
 if Counter(truth)!=Counter({p:20 for p in LABELS}):raise RuntimeError('test support')
 with threadpool_limits(limits=1):
  models=load_models();readouts=evaluate(rows,models,CONFIG['corruption']['test_seeds'])
  result={'version':CONFIG['version'],'truth':truth,'labels':LABELS,'readouts':readouts,'primary':bootstrap(truth,readouts),'seconds':time.perf_counter()-t,'peak_memory':peak_memory()}
 if len(readouts)!=36:raise RuntimeError('condition count')
 if peak_memory()>1073741824:raise RuntimeError('evaluation memory cap')
 save('test_results.json',result)
 save('FINAL_EVALUATION_COMPLETED.json',{'results_sha256':digest((BASE/'test_results.json').read_bytes()),'readouts':len(readouts),'seconds':result['seconds'],'peak_memory':result['peak_memory']})
 print(json.dumps({'clean':{r['model']:r['metrics']['macro_f1'] for r in readouts if r['percent']==0},'primary':{k:v for k,v in result['primary'].items() if k!='bootstrap_values'},'seconds':result['seconds'],'peak_MiB':result['peak_memory']/2**20}),flush=True)
if __name__=='__main__':main()
