from retrieval import *
from threadpoolctl import threadpool_limits

def bootstrap(readouts):
 ids=readouts[0]['ids'];poets=readouts[0]['poets'];values={}
 for method in ['word_tfidf_cosine','char_tfidf_cosine']:
  values[method]=np.array([[int(rank==1) for rank in r['target_ranks']] for r in readouts if r['method']==method and r['percent']==5]).mean(axis=0)
 d=values['char_tfidf_cosine']-values['word_tfidf_cosine'];rng=np.random.default_rng(20261104);strata=[np.flatnonzero(np.array(poets)==p) for p in LABELS];samples=[]
 for _ in range(2000):
  ix=np.concatenate([rng.choice(x,size=len(x),replace=True) for x in strata]);samples.append(float(d[ix].mean()))
 return {'char_minus_word_recall_at_1_5pct':float(d.mean()),'ci95_percentile':np.percentile(samples,[2.5,97.5]).tolist(),'replicates':2000,'seed':20261104,'conditional_on_fixed_gallery_and_queries':True}
def main():
 check_freeze();freeze=json.loads((BASE/'RETRIEVAL_FREEZE.json').read_text(encoding='utf-8'))
 pairs=[('retrieval_protocol_v01.json','protocol_sha256'),('dataset_local.json','dataset_sha256'),('retrieval_query_manifest.json','query_manifest_sha256'),('retrieval_queries_local.json','queries_local_sha256')]
 for name,key in pairs:
  assert digest((BASE/name).read_bytes())==freeze[key]
 for name,h in freeze['source_sha256'].items():assert digest((BASE/name).read_bytes())==h
 tests=json.loads((BASE/'retrieval_tests_passed.json').read_text(encoding='utf-8'));assert tests['result']=='PASS';assert tests['source_sha256']==freeze['source_sha256']['test_retrieval.py']
 dev=json.loads((BASE/'retrieval_validation.json').read_text(encoding='utf-8'));assert len(dev['readouts'])==30 and not dev['test_evaluated']
 save('RETRIEVAL_FINAL_PLAN.json',{'primary':'fixed char-minus-word Recall@1 at 5%; paired stratified bootstrap','protocol_sha256':freeze['protocol_sha256'],'freeze_sha256':digest((BASE/'RETRIEVAL_FREEZE.json').read_bytes()),'validation_sha256':digest((BASE/'retrieval_validation.json').read_bytes()),'all_30_conditions':True,'no_tuning_after_test':True})
 with (BASE/'RETRIEVAL_TEST_STARTED.json').open('x') as f:json.dump({'time':time.time()},f)
 queries=json.loads((BASE/'retrieval_queries_local.json').read_text(encoding='utf-8'))['test'];assert len(queries)==100 and Counter(q['poet'] for q in queries)==Counter({p:20 for p in LABELS})
 t=time.perf_counter()
 with threadpool_limits(limits=1):result=evaluate(load_index(),queries,[4101,4102,4103])
 assert len(result)==30
 save('retrieval_test.json',{'readouts':result,'primary':bootstrap(result),'seconds':time.perf_counter()-t,'peak_memory':peak_memory(),'test_query_poems':100,'gallery_size':500})
 save('RETRIEVAL_TEST_COMPLETED.json',{'test_sha256':digest((BASE/'retrieval_test.json').read_bytes()),'readouts':30})
 print(json.dumps({'clean':{r['method']:r['metrics'] for r in result if r['percent']==0},'primary':bootstrap(result),'seconds':time.perf_counter()-t}))
if __name__=='__main__':main()
