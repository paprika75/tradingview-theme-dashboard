import json, unittest
from pathlib import Path
root=Path(__file__).resolve().parents[1]
class Snapshots(unittest.TestCase):
 def test_archive_integrity(self):
  manifest=json.loads((root/'data/latest.json').read_text())
  for period,weights in [('daily',[.4,.3,.15,.15]),('weekly',[.35,.3,.2,.15])]:
   previous=None
   for entry in manifest[period]:
    doc=json.loads((root/'data'/entry['path']).read_text())
    self.assertEqual(doc['key'],entry['key'])
    self.assertEqual(doc['period'],period)
    self.assertEqual(doc['mode'],'demo')
    for market,info in doc['markets'].items():
     themes=info['themes'];self.assertEqual([t['rank'] for t in themes],list(range(1,len(themes)+1)))
     self.assertEqual(len(set(t['id'] for t in themes)),len(themes))
     for t in themes:
      self.assertAlmostEqual(t['score'],round(sum(c*w for c,w in zip(t['components'],weights)),1))
      self.assertEqual(set(t['symbols']),set(s['symbol'] for s in t['stocks']))
      self.assertIn(t['leader'],t['symbols'])
      self.assertEqual(t['leader'],t['stocks'][0]['symbol'])
      self.assertEqual(t['setups'],sum(bool(s['setup']) for s in t['stocks']))
      if previous:
       prev=next(x for x in previous['markets'][market]['themes'] if x['id']==t['id'])
       self.assertEqual(t['rankChange'],prev['rank']-t['rank'])
      else:self.assertIsNone(t['rankChange'])
    previous=doc
 def test_source_membership(self):
  cat=json.loads((root/'data/theme-catalog.json').read_text())
  for period in ['daily','weekly']:
   for file in (root/'data'/period).glob('*.json'):
    doc=json.loads(file.read_text())
    for market,info in cat['markets'].items():
     actual={t['id']:t['symbols'] for t in info['themes']}
     self.assertEqual(actual,{t['id']:t['symbols'] for t in doc['markets'][market]['themes']})
if __name__=='__main__':unittest.main()
