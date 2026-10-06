import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import build_market_exposure as E

RULES = json.loads((E.ROOT/'config/market-exposure.json').read_text())
DATES = [f'2026-01-{d:02}' for d in range(1, 25)]

def fixture(status='CONFIRMED_UPTREND', age=15, count=1):
    date = DATES[age]
    index = {'symbol': 'X', 'name': 'Index', 'asOf': date, 'status': status,
             'price': 110, 'ma50': 100, 'ma200': 90, 'priceTrend': 'UP',
             'distributionCount': count, 'distributionEvents': [],
             'lastFTD': {'date': DATES[0], 'valid': True}}
    market = {'status': status, 'requiredIndices': ['X'], 'indices': [index]}
    return market, date, {'X': DATES}, copy.deepcopy(RULES)

class ExposureTests(unittest.TestCase):
    def test_ftd_boundaries(self):
        for age, expected in [(0,1),(4,1),(5,2),(9,2),(10,3),(14,3),(15,4)]:
            with self.subTest(age=age): self.assertEqual(E.evaluate(*fixture(age=age))['band'], expected)

    def test_full_exposure_needs_price_structure_and_low_distribution(self):
        for field, value in [('priceTrend','MIXED'),('ma200',120),('ma50',110),('distributionCount',3)]:
            args = fixture(); args[0]['indices'][0][field] = value
            self.assertLess(E.evaluate(*args)['band'], 4)

    def test_defensive_conditions(self):
        self.assertEqual(E.evaluate(*fixture('MARKET_IN_CORRECTION'))['band'], 0)
        self.assertEqual(E.evaluate(*fixture('UPTREND_UNDER_PRESSURE', count=5))['band'], 2)
        self.assertEqual(E.evaluate(*fixture('UPTREND_UNDER_PRESSURE', count=7))['band'], 1)
        args=fixture('UPTREND_UNDER_PRESSURE');args[0]['indices'][0]['price']=99
        self.assertEqual(E.evaluate(*args)['band'], 1)
        args=fixture('UPTREND_UNDER_PRESSURE');args[0]['indices'][0]['distributionEvents']=[{'date':d} for d in DATES[13:16]]
        self.assertEqual(E.evaluate(*args)['band'], 1)

    def test_weakest_index_wins(self):
        args=fixture();second=copy.deepcopy(args[0]['indices'][0]);second.update(symbol='Y',distributionCount=4)
        args[0]['indices'].append(second);args[0]['requiredIndices'].append('Y');args[2]['Y']=DATES
        self.assertEqual(E.evaluate(*args)['band'], 3)

    def test_missing_is_unassessed_not_zero(self):
        for field, value in [('status','UNASSESSED'),('distributionCount',None),('ma50',None),('asOf','2099-01-01')]:
            args=fixture();args[0]['indices'][0][field]=value
            self.assertIsNone(E.evaluate(*args)['range'])
        args=fixture();args[0]['indices']=[]
        self.assertIsNone(E.evaluate(*args)['range'])

    def test_invalid_or_unknown_ftd_is_unassessed(self):
        for ftd in [None, {'valid':False,'date':DATES[0]}, {'valid':True,'date':'2099-01-01'}]:
            args=fixture();args[0]['indices'][0]['lastFTD']=ftd
            self.assertIsNone(E.evaluate(*args)['range'])

    def test_future_sessions_do_not_change_result(self):
        args=fixture(age=9);before=E.evaluate(*args);args[2]['X'] += ['2099-01-01']
        self.assertEqual(E.evaluate(*args),before)
        self.assertEqual(before['inputs'][0]['ftdSessionsElapsed'],9)

    def test_unconfirmed_last_session_is_rejected(self):
        args=fixture();args[2]['X']=DATES[:15]
        self.assertIsNone(E.evaluate(*args)['range'])

    def test_watchlist_scores_have_no_effect(self):
        args=fixture();before=E.evaluate(*args);args[0]['momentumHealth']=0;args[0]['themes']=['unrelated']
        self.assertEqual(E.evaluate(*args),before)

    def test_saved_exposure_is_preserved_on_new_acquisition(self):
        original=E.ROOT
        with tempfile.TemporaryDirectory() as directory:
            try:
                E.ROOT=Path(directory)
                (E.ROOT/'config').mkdir();(E.ROOT/'data/live').mkdir(parents=True)
                (E.ROOT/'config/market-exposure.json').write_text(json.dumps(RULES))
                args=fixture();date=args[1]
                outlook={'mode':'live','asOf':date,'evaluationVersion':'outlook-v1','markets':{'US':args[0]}}
                (E.ROOT/'data/live/outlook.json').write_text(json.dumps(outlook))
                saved={'mode':'live','asOf':date,'evaluationVersion':RULES['version'],'rules':RULES,
                       'markets':{'US':{'band':2,'range':[40,60]}}}
                saved_path=E.ROOT/'data/live/exposure.json';saved_path.write_text(json.dumps(saved))
                manifest={'marketOutlook':[{'asOf':date,'path':'live/outlook.json','evaluationVersion':'outlook-v1'}],
                          'marketExposure':[{'asOf':date,'path':'live/exposure.json','evaluationVersion':RULES['version']}]}
                (E.ROOT/'data/live/latest.json').write_text(json.dumps(manifest))
                source_path=E.ROOT/'input.json';source_path.write_text(json.dumps({'fetchedAt':'2026-02-01T00:00:00Z','documents':{}}))
                E.build(source_path)
                self.assertEqual(json.loads(saved_path.read_text()),saved)
                changed=copy.deepcopy(RULES);changed['heavyDistributionCount']=8
                (E.ROOT/'config/market-exposure.json').write_text(json.dumps(changed))
                with self.assertRaisesRegex(ValueError,'version'):E.build(source_path)
            finally:E.ROOT=original

if __name__ == '__main__': unittest.main()
