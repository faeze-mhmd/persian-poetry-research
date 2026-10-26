import unittest, random, copy
from poetry_core import *
class PoetryTests(unittest.TestCase):
 def test_normalizer_preserves_punctuation(self):
  self.assertEqual(canonical('كِتاب\u200cيـار،  آبی!'),'کتاب یار، آبی!')
  self.assertEqual(audit_normal('كِتاب\u200cيـار،  آبی!'),'کتاب یار آبی')
  self.assertEqual(canonical(canonical('يِک  متن!')),canonical('يِک  متن!'))
 def test_aliases_marks_and_boundaries(self):
  self.assertEqual(mask('حافِظ، سعدي شمس بیدلی'),TOKEN+'، '+TOKEN+' '+TOKEN+' بیدلی')
  self.assertEqual(mask('ناحافظ حافظانه'),'ناحافظ حافظانه')
  for a in ALIASES: self.assertEqual(mask(a),TOKEN)
 def test_minimal_and_shared_mask(self):
  self.assertEqual(prepare('سعدي\r\nكِتاب','minimal',False),'سعدي\nكِتاب')
  self.assertEqual(prepare('حافِظ\r\nكِتاب','canonical',True),TOKEN+' کتاب')
 def fixture(self):
  verses=[{'VOrder':i+1,'CoupletIndex':i//2,'Text':'این یک متن فارسی برای آزمون شعر است'} for i in range(8)]
  return {'Id':1,'CatId':24,'Verses':verses,'Sections':[{'SectionType':'WholePoem','PoemFormat':'Ghazal'}]}
 def test_loader_uses_verses_only(self):
  o=self.fixture();o['PoemSummary']='NEVER_USE';o['Sections'][0]['PlainText']='NEVER_USE'
  r=extract(o,1,2,24)
  self.assertEqual(r['reasons'],[]);self.assertNotIn('NEVER_USE',r['text']);self.assertEqual(len(r['text'].splitlines()),8)
 def test_loader_rejects_schema_failures(self):
  for mutate,reason in [(lambda o:o.update(Id=9),'id_or_category'),(lambda o:o['Verses'][0].update(VOrder=3),'verse_orders'),(lambda o:o['Verses'][0].update(Text=''),'empty_verse'),(lambda o:o['Sections'][0].update(PoemFormat='MultiBand'),'not_one_whole_ghazal'),(lambda o:o['Verses'][0].update(CoupletIndex=99),'couplet_structure')]:
   o=self.fixture();mutate(o);self.assertIn(reason,extract(o,1,2,24)['reasons'])
 def test_noise_stable_nested_and_protected(self):
  s=TOKEN+' '+ALPHABET*8+' !?'
  a,da=corrupt(s,123,2101,2);b,db=corrupt(s,123,2101,10)
  self.assertEqual((a,da),corrupt(s,123,2101,2))
  self.assertTrue(set(da['positions'])<=set(db['positions']))
  self.assertEqual(da['selected'],(2*264+50)//100)
  self.assertTrue(a.startswith(TOKEN+' '));self.assertTrue(a.endswith(' !?'))
  self.assertEqual(corrupt(s,123,2101,0)[0],s)
  self.assertNotEqual(a,corrupt(s,124,2101,2)[0])
  _,half=corrupt('ا'*25,1,1,2);self.assertEqual(half['selected'],1)
 def test_distances_and_protected_marker(self):
  self.assertEqual(levenshtein('kitten','sitting'),3)
  self.assertEqual(levenshtein([],['a']),1)
  self.assertEqual(levenshtein(['a','b'],['a','c']),1)
  self.assertEqual(errors(TOKEN+' اب',TOKEN+' اب')['chars'],3)
 def test_distance_against_independent_oracle(self):
  def oracle(a,b):
   prev=list(range(len(b)+1))
   for i,x in enumerate(a,1):
    row=[i]
    for j,y in enumerate(b,1):row.append(min(row[-1]+1,prev[j]+1,prev[j-1]+(x!=y)))
    prev=row
   return prev[-1]
  rng=random.Random(41)
  for _ in range(100):
   a=''.join(rng.choices('abcد',k=rng.randrange(30)));b=''.join(rng.choices('abcد',k=rng.randrange(30)))
   self.assertEqual(levenshtein(a,b),oracle(a,b))
 def test_exact_graph_shared_and_transitive(self):
  def r(i,n,c):return {'id':i,'poet':2,'normal':n,'couplets':set(c)}
  cs=['یک دو سه چهار پنج شش','شش پنج چهار سه دو یک','الف ب ج د ه و']
  records=[r(1,'abcdefghij',cs[:2]),r(2,'totally different',cs[:2]),r(3,'third long string',[cs[0],cs[2]]),r(4,'third long string',[])]
  groups,edges=group_records(records)
  self.assertEqual(sorted(sorted(x['id'] for x in g) for g in groups),[[1,2],[3,4]])
  self.assertTrue(any(e['reason']=='two_shared_couplets' for e in edges))
  g,e=group_records([r(1,'abcdefghijklmnopqrstuvwxyz'*4,[]),r(2,'abcdefghijklmnopqrstuvwxyz'*4+'b',[])])
  self.assertEqual(len(g),1);self.assertTrue(any(x['reason']=='jaccard_ge_0.80' for x in e))
 def test_split_stable_disjoint_balanced(self):
  rows=[{'id':p*1000+i,'poet':p} for p in LABELS for i in range(100)]
  a=make_split(rows); random.Random(7).shuffle(rows)
  self.assertEqual(a,make_split(rows));self.assertEqual(Counter(a.values()),{'train':300,'validation':100,'test':100})
  for p in LABELS:
   self.assertEqual(Counter(a[r['id']] for r in rows if r['poet']==p),{'train':60,'validation':20,'test':20})
 def test_metrics_fixed_label_space(self):
  m=metrics(LABELS,LABELS);self.assertEqual(m['macro_f1'],1)
  m=metrics(LABELS,[2]*5);self.assertAlmostEqual(m['macro_f1'],1/15)
 def test_vocabulary_training_only(self):
  m=build_model('word');m.fit(['alpha common','alpha common','beta common','beta common'],[2,2,5,5])
  m.predict(['UNSEEN_VALIDATION_TOKEN']);self.assertNotIn('UNSEEN_VALIDATION_TOKEN',m['tfidf'].vocabulary_)
if __name__=='__main__': unittest.main(verbosity=2)
