                                                                                        
from poetry_core import *
import argparse,subprocess,sys
p=argparse.ArgumentParser();p.add_argument('--stage',choices=['retrieval','integration'],required=True);a=p.parse_args()
name='test_retrieval.py' if a.stage=='retrieval' else 'test_media_demo.py'
receipt='retrieval_tests_passed.json' if a.stage=='retrieval' else 'integration_tests_passed.json'
t=time.perf_counter();proc=subprocess.run([sys.executable,'-B',str(BASE/name)],cwd=BASE)
save(receipt,{'result':'PASS' if proc.returncode==0 else 'FAIL','source_sha256':digest((BASE/name).read_bytes()),'seconds':time.perf_counter()-t,'exit_code':proc.returncode})
sys.exit(proc.returncode)
