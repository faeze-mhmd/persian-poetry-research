from poetry_core import *
from run_models import check_freeze,load_models
from prepare_data import peak_memory
freeze=check_freeze()
assert not (BASE/'FINAL_EVALUATION_STARTED.json').exists()
data=json.loads((BASE/'dataset_local.json').read_text(encoding='utf-8'))
split=json.loads((BASE/'split_manifest.json').read_text(encoding='utf-8'))['records']
assert [{k:r[k] for k in ('id','poet','split')} for r in data]==split
assert len(data)==len({r['id'] for r in data})==500
assert not ({r['id'] for r in data}&set(CONFIG['development_exclusion']['audit_poems']))
assert Counter(r['split'] for r in data)=={'train':300,'validation':100,'test':100}
for p in LABELS:assert Counter(r['split'] for r in data if r['poet']==p)=={'train':60,'validation':20,'test':20}
graph=json.loads((BASE/'duplicate_graph.json').read_text(encoding='utf-8'));kept={r['id'] for r in data}
for comp in graph['components']:
 assert len(set(comp['ids'])&kept)<=1
 if comp['exclusion']:assert not set(comp['ids'])&kept
manifest=json.loads((BASE/'corpus_manifest.json').read_text(encoding='utf-8'))
assert not manifest['failures']; totalbytes=0
for r in manifest['files']:
 path=BASE/('raw' if r.get('audit') else 'corpus')/f"{r['id']}.json"
 assert digest(path.read_bytes())==r['sha256']
 if not r.get('audit'):totalbytes+=r['bytes']
 if r['id'] in kept:assert not r['reasons']
assert totalbytes<=31457280
val=json.loads((BASE/'validation_results.json').read_text(encoding='utf-8'))
assert len(val['readouts'])==36 and val['test_evaluated'] is False
rows=[r for r in data if r['split']=='validation'];models=load_models();checks=0
for name,m in models.items():
 if name=='majority':text=['']*len(rows)
 else:
  family,norm,masked=name.split('__');text=[prepare(r['text'],norm,masked=='masked') for r in rows]
  assert np.isfinite(m['classifier'].coef_).all()
 pred=m.predict(text).tolist();expected=next(r for r in val['readouts'] if r['model']==name and r['percent']==0)
 assert pred==expected['predictions'];checks+=1
for r in val['readouts']:
 assert r['ids']==[x['id'] for x in rows]
 assert metrics(val['truth'],r['predictions'])==r['metrics']
 if r['percent']:assert r['seed'] in CONFIG['corruption']['development_seeds']
reg=json.loads((BASE/'model_registry.json').read_text(encoding='utf-8'));assert reg['validation_refit'] is False
assert reg['training_ids']==[r['id'] for r in data if r['split']=='train']
assert reg['peak_memory']<=1073741824 and reg['total_fit_wall_seconds']<=900
tests=json.loads((BASE/'tests_passed.json').read_text(encoding='utf-8'))
assert tests['source_sha256']==digest((BASE/'test_poetry.py').read_bytes()) and tests['result']=='PASS'
save('RUN_VERIFICATION.json',{'status':'PASS','source_and_data_freeze_checked':True,'study_models_reloaded':checks,'validation_readouts_verified':36,'candidate_and_audit_files_rehashed':len(manifest['files']),'split_and_duplicate_exclusions_checked':True,'test_metrics_seen':False,'peak_memory':peak_memory(),'known_technical_repair':'Windows HANDLE signatures fixed before source freeze/model fitting; no test evaluation occurred','warnings':{n:r['warnings'] for n,r in reg['models'].items() if r['warnings']}})
save('FINAL_EVALUATION_PLAN.json',{'version':CONFIG['version'],'created_before_test':True,'primary':'Predeclared canonical/shared-mask word-versus-character DeltaDrop at 5% corruption; mean over seeds 2101/2102/2103','all_conditions':'9 clean plus primary pair and majority at 2/5/10 percent x 3 seeds = 36 readouts','no_model_selection_or_refit':True,'bootstrap':CONFIG['metrics']['bootstrap'],'validation_sha256':digest((BASE/'validation_results.json').read_bytes()),'registry_sha256':digest((BASE/'model_registry.json').read_bytes()),'freeze_sha256':digest((BASE/'SOURCE_FREEZE_v02.json').read_bytes()),'verification_sha256':digest((BASE/'RUN_VERIFICATION.json').read_bytes()),'rights_scope':'local bounded research; raw/model publication not cleared','exclusive_start_marker':'FINAL_EVALUATION_STARTED.json'})
print(json.dumps({'status':'READY_FOR_FIXED_FINAL_EVALUATION','reloaded_models':checks,'validation_clean':{r['model']:r['metrics']['macro_f1'] for r in val['readouts'] if r['percent']==0},'primary_validation_5pct':{n:np.mean([r['metrics']['macro_f1'] for r in val['readouts'] if r['model']==n and r['percent']==5]) for n in ['word__canonical__masked','char__canonical__masked']},'warnings':{n:r['warnings'] for n,r in reg['models'].items() if r['warnings']},'peak_MiB':reg['peak_memory']/2**20}))
