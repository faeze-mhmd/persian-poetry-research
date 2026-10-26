                                                                               
import os
for _key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ[_key]='1'
import json, hashlib, unicodedata as ud, re, time
from pathlib import Path
from collections import defaultdict, Counter
import numpy as np
BASE=Path(__file__).resolve().parent
CONFIG=json.loads((BASE/'text_experiment_v02.json').read_text(encoding='utf-8'))
LABELS=CONFIG['split']['labels']
ALPHABET=CONFIG['corruption']['alphabet']
ALIASES=set(CONFIG['preprocessing']['aliases'])
TOKEN='MASKEDAUTHOR'
REV=CONFIG['source']['revision']
def save(name,obj):
    (BASE/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def digest(b): return hashlib.sha256(b).hexdigest()
def priority(poet,pid,split=False):
    prefix='split-v1|20261024' if split else 'poetry-text-v1|20261023'
    return hashlib.sha256(f'{prefix}|{poet}|{pid}'.encode('ascii')).digest(),pid
def canonical(s):
    s=ud.normalize('NFKC',s).translate(str.maketrans({'ي':'ی','ى':'ی','ك':'ک','\u200c':' '}))
    s=''.join(c for c in s if not ('\u064b'<=c<='\u065f' or c=='\u0670' or '\u06d6'<=c<='\u06ed' or c=='\u0640'))
    return ' '.join(s.split())
def audit_normal(s):
    return ' '.join(''.join(c if ud.category(c)[0] in 'LN' else ' ' for c in canonical(s)).split())
def mask(s):
    out=[]; i=0
    while i<len(s):
        j=i
        if ud.category(s[i])[0] in 'LM':
            while j<len(s) and ud.category(s[j])[0] in 'LM': j+=1
            run=s[i:j]; out.append(TOKEN if canonical(run) in ALIASES else run)
        else: j=i+1; out.append(s[i])
        i=j
    return ''.join(out)
def prepare(s,norm='canonical',masked=True):
    if masked: s=mask(s)
    return canonical(s) if norm=='canonical' else s.replace('\r\n','\n')
def extract(obj,pid,poet,category,check=True):
    reasons=[]; verses=sorted(obj.get('Verses',[]),key=lambda v:v.get('VOrder',0))
    if obj.get('Id')!=pid or pid<=0 or obj.get('CatId')!=category: reasons.append('id_or_category')
    if [v.get('VOrder') for v in verses]!=list(range(1,len(verses)+1)): reasons.append('verse_orders')
    if not verses or any(not isinstance(v.get('Text'),str) or not v['Text'].strip() for v in verses): reasons.append('empty_verse')
    whole=[s for s in obj.get('Sections',[]) if s.get('SectionType')=='WholePoem']
    if len(whole)!=1 or whole[0].get('PoemFormat')!='Ghazal': reasons.append('not_one_whole_ghazal')
    groups=defaultdict(list)
    for v in verses: groups[v.get('CoupletIndex')].append(v)
    if not 4<=len(groups)<=30 or any(len(x)!=2 for x in groups.values()) or None in groups: reasons.append('couplet_structure')
    text='\n'.join(v.get('Text','') for v in verses).replace('\r\n','\n')
    normal=audit_normal(text); words=len(normal.split())
    if not 40<=words<=600: reasons.append('word_count')
    letters=[c for c in normal if ud.category(c).startswith('L')]
    fraction=sum('ARABIC' in ud.name(c,'') for c in letters)/max(1,len(letters))
    if fraction<.9: reasons.append('script_fraction')
    couples={audit_normal(' '.join(v.get('Text','') for v in g)) for g in groups.values()}
    couples={s for s in couples if len(s.split())>=6}
    return {'id':pid,'poet':poet,'text':text,'normal':normal,'couplets':couples,'reasons':reasons,'words':words,'script_fraction':fraction}
def grams(s): return {s[i:i+5] for i in range(max(0,len(s)-4))}
def group_records(records):
                                                                                                   
    n=len(records); parent=list(range(n)); edges=[]
    def root(i):
        while parent[i]!=i: parent[i]=parent[parent[i]]; i=parent[i]
        return i
    def join(i,j,reason):
        a,b=root(i),root(j)
        if a!=b: parent[b]=a
        edges.append({'a':records[i]['id'],'b':records[j]['id'],'reason':reason})
    exact={}; coupleidx=defaultdict(list); gramidx=defaultdict(list); sizes=[]
    for i,r in enumerate(records):
        norm=r['normal']
        if norm in exact: join(exact[norm],i,'identical_text')
        else: exact[norm]=i
        shared=Counter()
        for c in r['couplets']:
            for j in coupleidx[c]: shared[j]+=1
            coupleidx[c].append(i)
        for j,num in shared.items():
            if num>=2: join(j,i,'two_shared_couplets')
        gs=grams(norm); size=len(gs); sizes.append(size); intersections=Counter()
        for g in gs:
            for j in gramidx[g]:
                if min(size,sizes[j])*5>=max(size,sizes[j])*4: intersections[j]+=1
            gramidx[g].append(i)
        for j,inter in intersections.items():
            if inter*5 >= (size+sizes[j]-inter)*4: join(j,i,'jaccard_ge_0.80')
    components=defaultdict(list)
    for i in range(n): components[root(i)].append(i)
    return [[records[i] for i in inds] for inds in components.values()],edges
def make_split(selected):
    result={}
    for poet in LABELS:
        rows=sorted([r for r in selected if r['poet']==poet],key=lambda r:priority(poet,r['id'],True))
        if len(rows)!=100: raise ValueError(f'expected 100 for {poet}, got {len(rows)}')
        for i,r in enumerate(rows):
            result[r['id']]='train' if i<60 else 'validation' if i<80 else 'test'
    return result
def corrupt(text,pid,seed,percent):
    positions=[i for i,c in enumerate(text) if c in ALPHABET]
    rng=np.random.default_rng(int.from_bytes(hashlib.sha256(f'noise-v1|{seed}|{pid}'.encode('ascii')).digest()[:8],'big'))
    order=rng.permutation(len(positions))
                                                                                       
    ops=rng.integers(0,3,size=len(positions))
    ins=rng.integers(0,len(ALPHABET),size=len(positions))
    sub=rng.integers(0,len(ALPHABET)-1,size=len(positions))
    k=(percent*len(positions)+50)//100
    chosen={int(x) for x in order[:k]}; edits={}
    for j,i in enumerate(positions):
        if j not in chosen: continue
        c=text[i]
        if ops[j]==0: edits[i]=ALPHABET[int(ins[j])]+c
        elif ops[j]==1: edits[i]=''
        else:
            a=ALPHABET.replace(c,''); edits[i]=a[int(sub[j])]
    return ''.join(edits.get(i,c) for i,c in enumerate(text)),{'eligible':len(positions),'selected':k,'positions':sorted(edits)}
def levenshtein(a,b):
                                                                            
    if a==b:return 0
    if len(a)>len(b):a,b=b,a
    m=len(a)
    if not m:return len(b)
    masks={}
    for i,x in enumerate(a):masks[x]=masks.get(x,0)|(1<<i)
    full=(1<<m)-1; high=1<<(m-1); positive=full; negative=0; score=m
    for x in b:
        eq=masks.get(x,0)
        d0=(((eq&positive)+positive)^positive)|eq|negative
        hp=negative|~(d0|positive); hn=positive&d0
        score+=int(bool(hp&high))-int(bool(hn&high))
        hp=(hp<<1)|1; hn=hn<<1
        positive=(hn|~(d0|hp))&full;negative=(d0&hp)&full
    return score
def errors(clean,noisy):
    a=clean.replace(TOKEN,''); b=noisy.replace(TOKEN,'')
    return {'char_edits':levenshtein(a,b),'chars':len(a),'word_edits':levenshtein(a.split(),b.split()),'words':len(a.split())}
def metrics(y,pred):
    from sklearn.metrics import accuracy_score,f1_score,precision_recall_fscore_support,confusion_matrix
    p,r,f,n=precision_recall_fscore_support(y,pred,labels=LABELS,zero_division=0)
    return {'accuracy':float(accuracy_score(y,pred)),'macro_f1':float(f1_score(y,pred,labels=LABELS,average='macro',zero_division=0)),
            'per_author':{str(l):{'precision':float(p[i]),'recall':float(r[i]),'f1':float(f[i]),'support':int(n[i])} for i,l in enumerate(LABELS)},
            'confusion':confusion_matrix(y,pred,labels=LABELS).tolist()}
def build_model(family):
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.svm import LinearSVC
    from sklearn.pipeline import Pipeline
    shared=CONFIG['features']['shared'].copy(); shared['dtype']=np.float64; shared['max_df']=float(shared['max_df'])
    feat=next(x for x in CONFIG['features']['families'] if x['id']==family).copy()
    feat.pop('id'); feat['ngram_range']=tuple(feat['ngram_range'])
    clf=CONFIG['classifier'].copy(); clf.pop('class')
    return Pipeline([('tfidf',TfidfVectorizer(**shared,**feat)),('classifier',LinearSVC(**clf))])
