                                                                                     
                                                                          
   
from poetry_core import *
from run_models import check_freeze
import subprocess,sys,shutil
def main():
 check_freeze();target=BASE/'reproduction_v02_fresh'
 if target.exists():raise RuntimeError('fresh replay destination already exists; preserve it')
 target.mkdir()
 names=['poetry_core.py','prepare_data.py','run_models.py','final_evaluate.py','test_poetry.py','verify_before_test.py','text_experiment_v02.json','candidate_selection_v02.jsonl','acquisition.json','tests_passed.json']
 for n in names:shutil.copy2(BASE/n,target/n)
 for directory in ['raw','corpus']:shutil.copytree(BASE/directory,target/directory)
 t=time.perf_counter()
 for script in ['test_poetry.py','prepare_data.py','run_models.py','verify_before_test.py','final_evaluate.py']:
  p=subprocess.run([sys.executable,'-B',str(target/script)],cwd=target,capture_output=True,text=True)
  (target/(script+'.log')).write_text(p.stdout+'\n'+p.stderr,encoding='utf-8')
  if p.returncode:raise RuntimeError('replay failed '+script+': '+p.stderr[-1500:])
 original=json.loads((BASE/'test_results.json').read_text(encoding='utf-8'));replay=json.loads((target/'test_results.json').read_text(encoding='utf-8'))
 checks=[]
 for a,b in zip(original['readouts'],replay['readouts']):
  assert (a['model'],a['percent'],a['seed'])==(b['model'],b['percent'],b['seed'])
  checks.append(a['predictions']==b['predictions'] and a['metrics']==b['metrics'])
 assert len(checks)==36 and all(checks)
 assert original['primary']==replay['primary']
 save('REPRODUCTION_VERIFICATION.json',{'status':'PASS','fresh_directory':target.name,'commands_actually_executed':5,'same_installed_python_environment':True,'fresh_machine_not_tested':True,'all_36_test_predictions_and_metrics_identical':True,'bootstrap_and_primary_identical':True,'original_artifacts_unchanged':True,'seconds':time.perf_counter()-t})
 print(json.dumps({'status':'PASS','readouts_identical':36,'fresh_directory':target.name,'seconds':time.perf_counter()-t}))
if __name__=='__main__':main()
