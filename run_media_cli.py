from media_engines import LocalEngines
from poetry_core import *
import argparse,sys
def main():
 p=argparse.ArgumentParser();group=p.add_mutually_exclusive_group(required=True);group.add_argument('--image');group.add_argument('--audio');group.add_argument('--check',action='store_true');a=p.parse_args();engine=LocalEngines()
 if a.check:print(json.dumps(engine.status()));return
 from serve_demo import DemoApp
 result=engine.ocr(a.image) if a.image else engine.asr(a.audio)
 app=DemoApp();result['analysis']=app.analyze(result['text'])
 sys.stdout.reconfigure(encoding='utf-8');print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
