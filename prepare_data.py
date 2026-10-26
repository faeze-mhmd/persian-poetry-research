from poetry_core import *
import sys, platform, ctypes
from ctypes import wintypes

def peak_memory():
 class PMC(ctypes.Structure):
  _fields_=[('cb',wintypes.DWORD),('PageFaultCount',wintypes.DWORD),('PeakWorkingSetSize',ctypes.c_size_t),('WorkingSetSize',ctypes.c_size_t),('QuotaPeakPagedPoolUsage',ctypes.c_size_t),('QuotaPagedPoolUsage',ctypes.c_size_t),('QuotaPeakNonPagedPoolUsage',ctypes.c_size_t),('QuotaNonPagedPoolUsage',ctypes.c_size_t),('PagefileUsage',ctypes.c_size_t),('PeakPagefileUsage',ctypes.c_size_t)]
 p=PMC();p.cb=ctypes.sizeof(p)
 kernel=ctypes.WinDLL('kernel32',use_last_error=True);psapi=ctypes.WinDLL('psapi',use_last_error=True)
 kernel.GetCurrentProcess.restype=wintypes.HANDLE
 psapi.GetProcessMemoryInfo.argtypes=[wintypes.HANDLE,ctypes.POINTER(PMC),wintypes.DWORD]
 psapi.GetProcessMemoryInfo.restype=wintypes.BOOL
 if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(),ctypes.byref(p),p.cb):raise ctypes.WinError(ctypes.get_last_error())
 return int(p.PeakWorkingSetSize)

def main():
 start=time.perf_counter()
 candidates=[json.loads(s) for s in (BASE/'candidate_selection_v02.jsonl').read_text(encoding='utf-8').splitlines()]
 audits=json.loads((BASE/'acquisition.json').read_text(encoding='utf-8'))['files']
 rows=[]; manifest=[]; failures=[]
 for item in candidates+[{**x,'poet':x['poet_id'],'category':x['category_id'],'audit':True} for x in audits]:
  audit=item.get('audit',False); path=BASE/('raw' if audit else 'corpus')/f"{item['id']}.json"
  if not path.exists(): failures.append({**item,'reason':'file_missing'});continue
  b=path.read_bytes()
  if audit and digest(b)!=item['sha256']: raise RuntimeError('audit integrity')
  o=json.loads(b); r=extract(o,item['id'],item['poet'],item['category']);r['audit']=audit;rows.append(r)
  manifest.append({**item,'sha256':digest(b),'bytes':len(b),'reasons':r['reasons'],'words':r['words'],'script_fraction':r['script_fraction']})
 save('corpus_manifest.json',{'revision':REV,'raw_use':'Local research only; no raw redistribution clearance','files':manifest,'failures':failures})
 components,edges=group_records(rows)
 representatives=[]; component_log=[]
 for comp in components:
  causes=[]
  if any(r['audit'] for r in comp):causes.append('touches_development')
  if len({r['poet'] for r in comp})>1:causes.append('mixed_authors')
  eligible=[r for r in comp if not r['audit'] and not r['reasons']]
  rep=None
  if not causes and eligible:
   rep=min(eligible,key=lambda r:priority(r['poet'],r['id']));representatives.append(rep)
  component_log.append({'ids':sorted(r['id'] for r in comp),'exclusion':causes,'representative':rep['id'] if rep else None})
 save('duplicate_graph.json',{'edges':edges,'components':component_log})
 counts=Counter(r['poet'] for r in representatives)
 save('data_stage_status.json',{'eligible_representatives':dict(counts),'new_files':len(candidates)-len(failures),'elapsed_seconds':time.perf_counter()-start,'peak_memory':peak_memory()})
 if any(counts[p]<100 for p in LABELS):
  print('INSUFFICIENT',dict(counts));sys.exit(3)
 chosen=[]
 for p in LABELS: chosen+=sorted([r for r in representatives if r['poet']==p],key=lambda r:priority(p,r['id']))[:100]
 splits=make_split(chosen)
 dataset=[{'id':r['id'],'poet':r['poet'],'text':r['text'],'split':splits[r['id']]} for r in sorted(chosen,key=lambda r:r['id'])]
 save('dataset_local.json',dataset)
 ids=[{k:r[k] for k in ('id','poet','split')} for r in dataset]
 save('split_manifest.json',{'version':CONFIG['version'],'revision':REV,'records':ids})
 sources={p.name:digest(p.read_bytes()) for p in [BASE/'poetry_core.py',BASE/'test_poetry.py',BASE/'prepare_data.py',BASE/'run_models.py',BASE/'final_evaluate.py',BASE/'text_experiment_v02.json']}
 save('SOURCE_FREEZE_v02.json',{'utc':__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),'source_sha256':sources,'dataset_local_sha256':digest((BASE/'dataset_local.json').read_bytes()),'split_sha256':digest((BASE/'split_manifest.json').read_bytes()),'corpus_manifest_sha256':digest((BASE/'corpus_manifest.json').read_bytes()),'environment':{'python':sys.version,'platform':platform.platform(),'numpy':np.__version__},'raw_publication':'not cleared'})
 peak=peak_memory();elapsed=time.perf_counter()-start
 if peak>1073741824 or elapsed>1800:raise RuntimeError('resource cap exceeded')
 print(json.dumps({'status':'FROZEN','counts':dict(Counter(splits.values())),'eligible':dict(counts),'duplicate_edges':len(edges),'seconds':elapsed,'peak_MiB':peak/2**20}))
if __name__=='__main__':main()
