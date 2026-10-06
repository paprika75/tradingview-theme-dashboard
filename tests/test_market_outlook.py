import unittest, json, sys, copy, tempfile
from pathlib import Path
from datetime import date, timedelta
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from build_market_outlook import evaluate_index, aggregate, save_append_only
ROOT=Path(__file__).resolve().parents[1]
CONFIG=json.loads((ROOT/'config/market-outlook.json').read_text())
SPEC={'symbol':'TEST:INDEX','name':'Test index'}

def bars(values):
    start=date(2025,1,1)
    return [{'date':(start+timedelta(days=i)).isoformat(),'o':p,'h':p+.1,'l':p-.1,'c':p,'v':1000} for i,p in enumerate(values)]

def confirmed_series():
    result=bars([100]*200+[97,88,89,89.3,89.5,91]+[110]*30)
    result[200]['v']=1100;result[201]['v']=1200;result[205]['v']=1300
    return result

def run(series,asof=None):
    return evaluate_index(series,asof or series[-1]['date'],SPEC,CONFIG)

class Outlook(unittest.TestCase):
    def test_cannot_bootstrap_a_confirmed_uptrend(self):
        out=run(bars([100+i*.1 for i in range(240)]))
        self.assertEqual(out['status'],'UNASSESSED');self.assertIsNone(out['lastFTD'])

    def test_ftd_requires_day_four_and_can_be_below_moving_averages(self):
        series=confirmed_series()[:206]
        out=run(series)
        self.assertEqual(out['lastFTD']['date'],series[205]['date'])
        self.assertEqual(out['lastFTD']['rallyDay'],4)
        self.assertTrue(out['lastFTD']['valid'])
        self.assertLess(out['price'],out['ma50'])
        self.assertEqual(out['distributionCount'],0)
        premature=copy.deepcopy(series);premature[203].update(c=91,h=91.1,v=1400)
        self.assertIsNone(run(premature[:204])['lastFTD'])

    def test_ftd_requires_higher_volume(self):
        series=confirmed_series()[:206];series[-1]['v']=1000
        self.assertIsNone(run(series)['lastFTD'])

    def test_undercutting_ftd_low_invalidates_confirmation(self):
        series=confirmed_series();series[-1]['l']=90
        out=run(series)
        self.assertEqual(out['status'],'MARKET_IN_CORRECTION')
        self.assertFalse(out['lastFTD']['valid'])
        self.assertEqual(out['lastFTD']['invalidatedOn'],series[-1]['date'])

    def test_distribution_exact_threshold_and_volume(self):
        series=confirmed_series();series[-1].update(c=109.78,h=110,l=109.7,v=1100)
        self.assertEqual(run(series)['distributionCount'],1) # exactly -0.2%, no rounded comparison
        series[-1]['c']=109.781
        self.assertEqual(run(series)['distributionCount'],0)
        series[-1]['c']=109.78;series[-1]['v']=1000
        self.assertEqual(run(series)['distributionCount'],0)

    def test_distribution_expires_on_twenty_fifth_subsequent_session(self):
        series=confirmed_series();series[-1].update(c=109.78,h=110,l=109.7,v=1100)
        extras=bars([109.78]*25)
        start=date.fromisoformat(series[-1]['date'])
        for i,b in enumerate(extras):b['date']=(start+timedelta(days=i+1)).isoformat()
        self.assertEqual(run(series+extras[:24])['distributionCount'],1)
        self.assertEqual(run(series+extras)['distributionCount'],0)

    def test_intraday_recovery_removes_day_without_future_lookahead(self):
        series=confirmed_series();series[-1].update(c=109.78,h=110,l=109.7,v=1100)
        target=series[-1]['date'];future={**series[-1],'date':(date.fromisoformat(target)+timedelta(days=1)).isoformat(),'h':120,'v':1000}
        self.assertEqual(run(series+[future],target),run(series,target))
        out=run(series+[future]);self.assertEqual(out['distributionCount'],0)
        self.assertEqual(next(e for e in out['recentEvents'] if e['date']==target)['removalReason'],'PRICE_RECOVERY')

    def test_missing_zero_and_stale_volume_never_become_zero_days(self):
        for value in [None,0]:
            series=confirmed_series()
            for b in series:b['v']=value
            out=run(series)
            self.assertEqual(out['status'],'UNASSESSED');self.assertIsNone(out['distributionCount'])
            self.assertIsNone(out['lastFTD']);self.assertEqual(out['priceTrend'],'UP')
        series=confirmed_series();target=(date.fromisoformat(series[-1]['date'])+timedelta(days=1)).isoformat()
        self.assertEqual(run(series,target)['status'],'UNASSESSED')

    def test_distribution_cluster_applies_pressure(self):
        series=confirmed_series();p=110;start=date.fromisoformat(series[-1]['date'])
        for i in range(3):
            p*=.997;series.append({'date':(start+timedelta(days=i+1)).isoformat(),'o':p,'h':p+.1,'l':p-.1,'c':p,'v':1100+i*100})
        self.assertEqual(run(series)['status'],'UPTREND_UNDER_PRESSURE')

    def test_aggregation_is_defensive_and_missing_data_is_not_bullish(self):
        self.assertEqual(aggregate([{'status':'CONFIRMED_UPTREND'},{'status':'UPTREND_UNDER_PRESSURE'}]),'UPTREND_UNDER_PRESSURE')
        self.assertEqual(aggregate([{'status':'MARKET_IN_CORRECTION'},{'status':'CONFIRMED_UPTREND'}]),'MARKET_IN_CORRECTION')
        self.assertEqual(aggregate([{'status':'UNASSESSED'},{'status':'CONFIRMED_UPTREND'}]),'UNASSESSED')

    def test_saved_outlook_cannot_be_rewritten(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'saved.json';save_append_only(p,{'score':1});save_append_only(p,{'score':1})
            with self.assertRaises(ValueError):save_append_only(p,{'score':2})

if __name__=='__main__':unittest.main()
