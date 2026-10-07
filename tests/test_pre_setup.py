import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from datetime import date,timedelta
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import build_pre_setup as P
RULES=json.loads((P.ROOT/'config/pre-setup.json').read_text())

def bars():
    result=[]
    for i in range(65):
        p=70+i*.4
        result.append({'date':(date(2026,1,1)+timedelta(days=i)).isoformat(),'o':p,'c':p,'h':p+1,'l':p-1,'v':1000})
    for b in result[-20:-10]:b.update(o=93,c=93,h=100,l=90)
    for b in result[-10:]:b.update(o=95,c=95,h=96,l=94,v=500)
    return result

class PreSetupTests(unittest.TestCase):
    def evaluate(self, series=None, rules=None):
        series=series or bars();return P.evaluate('NASDAQ:TEST',series,bars()[-1]['date'],rules or RULES)

    def test_near_and_state_axes(self):
        r=self.evaluate();self.assertTrue(r['candidateEligible']);self.assertEqual(r['readiness'],'Near')
        self.assertEqual(r['lifecycle'],'SETUP');self.assertIsNone(r['setup_type']);self.assertFalse(r['setupConfirmed'])

    def test_distance_does_not_replace_formation_conditions(self):
        series=bars();series[-1].update(c=98,o=98,h=99,l=97)
        r=self.evaluate(series);self.assertEqual(r['readiness'],'Ready')
        no_formation=copy.deepcopy(series)
        for b in no_formation[-10:]:b.update(h=99,l=80,v=2000)
        self.assertFalse(self.evaluate(no_formation)['candidateEligible'])

    def test_forming_can_remain_a_candidate(self):
        series=bars();series[-1].update(c=92,o=92,h=93,l=91)
        self.assertEqual(self.evaluate(series)['readiness'],'Forming')

    def test_confirmed_or_intraday_pivot_passage_excludes_pre_setup(self):
        for close in [101,95]:
            series=bars();series[-1].update(c=close,o=close,h=102,l=min(94,close))
            r=self.evaluate(series);self.assertFalse(r['candidateEligible']);self.assertEqual(r['readiness'],'EXCLUDED')
            self.assertEqual(r['lifecycle'],'BREAKOUT' if close>=100 else 'UNASSESSED')

    def test_missing_volume_is_not_zero(self):
        for volume in [None,0]:
            series=bars();series[-1]['v']=volume
            r=self.evaluate(series);self.assertEqual(r['readiness'],'UNASSESSED');self.assertFalse(r['candidateEligible'])

    def test_stale_or_short_history_is_unassessed(self):
        self.assertEqual(self.evaluate(bars()[:-1])['readiness'],'UNASSESSED')
        self.assertEqual(self.evaluate(bars()[-20:])['readiness'],'UNASSESSED')

    def test_no_fixed_sixty_day_depth_filter(self):
        series=bars();series[5]['l']=10
        self.assertTrue(self.evaluate(series)['candidateEligible'])

    def test_long_term_trend_missing_is_explicit_not_confirmed(self):
        r=self.evaluate();self.assertIsNone(r['trendChecks']['ma200Rising21']);self.assertFalse(r['setupConfirmed'])

    def test_unclear_pivot_and_bad_trend_exclude(self):
        series=bars()
        for b in series[-20:-10]:b['h']=99
        series[-15]['h']=102
        self.assertFalse(self.evaluate(series)['candidateEligible'])
        series=bars();series[-1].update(c=60,o=60,l=59,h=61)
        self.assertFalse(self.evaluate(series)['candidateEligible'])

    def test_future_bars_do_not_change_result(self):
        series=bars();before=self.evaluate(series);series.append({**series[-1],'date':'2099-01-01','h':200,'c':200})
        self.assertEqual(self.evaluate(series),before)

    def test_future_universe_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            source=Path(directory)/'source.json';universe=Path(directory)/'universe.json'
            source.write_text('{}');universe.write_text(json.dumps({'asOf':'2026-10-07','markets':{}}))
            with self.assertRaisesRegex(ValueError,'universe'):P.build(source,universe,'2026-10-05')

    def test_append_only_state_snapshot_and_idempotent_manifest(self):
        original=P.ROOT
        with tempfile.TemporaryDirectory() as directory:
            try:
                P.ROOT=Path(directory);(P.ROOT/'config').mkdir()
                (P.ROOT/'config/pre-setup.json').write_text(json.dumps(RULES))
                source=P.ROOT/'source.json';universe=P.ROOT/'universe.json'
                source.write_text(json.dumps({'fetchedAt':'2026-10-07T00:00:00Z','documents':{}}))
                universe.write_text(json.dumps({'asOf':'2026-10-06','markets':{'US':{'name':'🇺🇸一次スクリーナー','symbols':['NASDAQ:TEST','NASDAQ:TEST']}}}))
                P.build(source,universe,'2026-10-06');P.build(source,universe,'2026-10-06')
                manifest=json.loads((P.ROOT/'data/pre-setup/latest.json').read_text());self.assertEqual(len(manifest['entries']),1)
                doc=json.loads((P.ROOT/'data'/manifest['entries'][0]['path']).read_text());self.assertEqual(doc['markets']['US']['requested'],1)
                self.assertEqual(doc['markets']['US']['assessed'],0)
                changed=copy.deepcopy(RULES);changed['readyDistancePct']=4
                (P.ROOT/'config/pre-setup.json').write_text(json.dumps(changed))
                with self.assertRaisesRegex(ValueError,'replace'):P.build(source,universe,'2026-10-06')
            finally:P.ROOT=original

if __name__=='__main__':unittest.main()
