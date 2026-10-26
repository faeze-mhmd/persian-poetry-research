from poetry_core import *
from final_evaluate import fast_f1
from run_models import check_freeze
check_freeze();r=json.loads((BASE/'test_results.json').read_text(encoding='utf-8'));receipt=json.loads((BASE/'FINAL_EVALUATION_COMPLETED.json').read_text(encoding='utf-8'))
assert digest((BASE/'test_results.json').read_bytes())==receipt['results_sha256']
assert len(r['readouts'])==36
data=json.loads((BASE/'dataset_local.json').read_text(encoding='utf-8'));test=[x for x in data if x['split']=='test']
assert r['truth']==[x['poet'] for x in test]
enc={l:i for i,l in enumerate(LABELS)}
for x in r['readouts']:
 assert x['ids']==[p['id'] for p in test]
 assert x['metrics']==metrics(r['truth'],x['predictions'])
 assert abs(x['metrics']['macro_f1']-fast_f1(np.array([enc[y] for y in r['truth']]),np.array([enc[y] for y in x['predictions']])))<1e-12
 if x['percent']:
  assert x['seed'] in CONFIG['corruption']['test_seeds']
  e=x['measured_errors'];assert e['cer']==e['char_edits']/e['chars'] and e['wer']==e['word_edits']/e['words']
f=lambda name,p:np.mean([x['metrics']['macro_f1'] for x in r['readouts'] if x['model']==name and x['percent']==p])
word='word__canonical__masked';char='char__canonical__masked'
delta=(f(word,0)-f(word,5))-(f(char,0)-f(char,5))
assert abs(delta-r['primary']['delta_drop'])<1e-12
assert np.allclose(np.percentile(r['primary']['bootstrap_values'],[2.5,97.5]),r['primary']['ci95_percentile'],rtol=0,atol=1e-12)
assert len(r['primary']['bootstrap_values'])==2000
save('FINAL_VERIFICATION.json',{'status':'PASS','source_freeze_intact':True,'test_readouts_metrics_checked':36,'fixed_label_fast_f1_matches_sklearn':True,'actual_error_rates_checked':True,'primary_contrast_and_bootstrap_percentiles_checked':True,'final_evaluations':1,'test_results_sha256':digest((BASE/'test_results.json').read_bytes())})
print(json.dumps({'status':'PASS','primary_clean_word':f(word,0),'primary_clean_char':f(char,0),'primary_noisy_5_word':f(word,5),'primary_noisy_5_char':f(char,5),'delta_drop':delta,'interval':r['primary']['ci95_percentile']}))
