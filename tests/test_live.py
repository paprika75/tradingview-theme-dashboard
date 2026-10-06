import unittest,sys
from pathlib import Path
from datetime import datetime,timezone
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from build_live import valid_bars,relative_return,percentile_map,weighted,ema

def bar(iso,price=100):return {'t':int(datetime.fromisoformat(iso).timestamp()),'o':price,'h':price+1,'l':price-1,'c':price,'v':100}
class Observed(unittest.TestCase):
 def test_japan_intraday_is_excluded(self):
  doc={'success':True,'bars':[bar('2026-10-05T00:00:00+00:00'),bar('2026-10-06T00:00:00+00:00')]}
  out=valid_bars(doc,'JP',datetime(2026,10,6,5,tzinfo=timezone.utc),'TSE:6525')
  self.assertEqual([x['date'] for x in out],['2026-10-05'])
 def test_forex_open_is_next_session_and_excludes_current_session(self):
  doc={'success':True,'bars':[bar('2026-10-04T21:00:00+00:00'),bar('2026-10-05T21:00:00+00:00')]}
  out=valid_bars(doc,'US',datetime(2026,10,6,5,tzinfo=timezone.utc),'FX:USDJPY')
  self.assertEqual([x['date'] for x in out],['2026-10-05'])
 def test_crypto_current_utc_day_is_excluded(self):
  doc={'success':True,'bars':[bar('2026-10-05T00:00:00+00:00'),bar('2026-10-06T00:00:00+00:00')]}
  self.assertEqual(len(valid_bars(doc,'US',datetime(2026,10,6,5,tzinfo=timezone.utc),'CRYPTO:BTCUSD')),1)
 def test_duplicate_or_invalid_prices_reject_series(self):
  b=bar('2026-10-05T00:00:00+00:00');now=datetime(2026,10,6,tzinfo=timezone.utc)
  with self.assertRaises(ValueError):valid_bars({'success':True,'bars':[b,b]},'US',now)
  with self.assertRaises(ValueError):valid_bars({'success':True,'bars':[{**b,'c':None}]},'US',now)
 def test_missing_scores_and_tied_percentiles(self):
  self.assertIsNone(weighted({'a':None},{'a':1}))
  self.assertEqual(percentile_map({'a':3,'b':3}),{'a':50.0,'b':50.0})
  self.assertIsNone(percentile_map({'a':3})['a'])
  self.assertEqual(ema([100]*25,21),100)
 def test_relative_strength_requires_date_alignment(self):
  a=[{'date':'2026-10-01','c':100},{'date':'2026-10-02','c':110}]
  b=[{'date':'2026-10-01','c':100},{'date':'2026-10-02','c':105}]
  self.assertAlmostEqual(relative_return(a,b,1),100*(1.1/1.05-1))
  self.assertIsNone(relative_return(a,b[1:],1))
if __name__=='__main__':unittest.main()
