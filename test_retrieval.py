import unittest,tempfile
from retrieval import *
class RetrievalTests(unittest.TestCase):
 def setUp(self):
  self.rows=[{'id':20,'poet':2,'text':'alpha shared beta poem'},{'id':10,'poet':5,'text':'alpha shared beta poem'},{'id':30,'poet':7,'text':'gamma shared delta poem'},{'id':40,'poet':22,'text':'gamma shared delta poem'}]
  self.index=PoetryIndex(self.rows)
 def test_ties_use_numeric_id(self):
  for method in METHODS:self.assertEqual([x[0] for x in self.index.rank(['alpha shared'],method,k=2)[0]],[10,20])
 def test_empty_and_out_of_vocabulary(self):
  for method in METHODS:
   self.assertEqual(self.index.rank([''],method),[[]])
   self.assertEqual(self.index.rank(['ZZZZZZ'],method),[[]])
 def test_rank_positive_and_no_query_fitting(self):
  voc={f:v.vocabulary_.copy() for f,v in self.index.models.items()}
  self.index.rank(['NEVER_IN_GALLERY'],METHODS[1])
  self.assertEqual(voc,{f:v.vocabulary_ for f,v in self.index.models.items()})
  self.assertEqual(self.index.rank(['gamma delta'],METHODS[2],k=1)[0][0][0],30)
 def test_gallery_order_invariance(self):
  other=PoetryIndex(list(reversed(self.rows)))
  for method in METHODS:self.assertEqual(self.index.rank(['alpha beta'],method),other.rank(['alpha beta'],method))
 def test_metric_hand_calculation(self):
  m=summarize([1,2,None,11])
  self.assertEqual(m['recall_at_1'],.25);self.assertEqual(m['recall_at_5'],.5)
  self.assertAlmostEqual(m['mrr'],(1+1/2+1/11)/4)
 def test_serialization_matches(self):
  with tempfile.TemporaryDirectory(dir=BASE) as d:
   p=Path(d)/'index.joblib';joblib.dump(self.index,p);loaded=joblib.load(p)
   for method in METHODS:self.assertEqual(loaded.rank(['alpha shared'],method),self.index.rank(['alpha shared'],method))
 def test_query_identity_and_membership(self):
  row={'id':1,'poet':2}
                                                                            
  rankings=self.index.rank(['alpha shared beta poem'],'exact_substring')
  self.assertEqual([x[0] for x in rankings[0]],[10,20])
if __name__=='__main__':unittest.main(verbosity=2)
