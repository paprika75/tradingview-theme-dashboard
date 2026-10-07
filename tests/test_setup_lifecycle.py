import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from setup_lifecycle import apply_setup_state, lifecycle_candidate, load_registry_for_date

RULES = {
    'version':'test', 'failedPivotPct':3, 'retestPct':3,
    'pullbackEma21MinPct':-2, 'pullbackEma21MaxPct':3, 'pullbackMaxRvol':1.2,
    'extendedFromEntryPct':10, 'extendedFromEma21Pct':10,
    'tightSessions':5, 'tightRangePct':5, 'threeWeeksTightClosePct':1.5,
    'ascendingBaseWindowSessions':60, 'ascendingBaseMaxBlockRangePct':22,
    'ascendingBaseNearHighPct':5
}


def bars(prices, start='2026-08-03'):
    from datetime import date, timedelta
    d=date.fromisoformat(start); out=[]
    for price in prices:
        while d.weekday()>=5:d+=timedelta(days=1)
        out.append({'date':d.isoformat(),'o':price,'h':price*1.01,'l':price*.99,'c':price,'v':100})
        d+=timedelta(days=1)
    return out


class SetupLifecycleTests(unittest.TestCase):
    def test_registry_is_point_in_time(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); p=root/'data/setup-state/registry';p.mkdir(parents=True)
            (p/'manifest.json').write_text(json.dumps({'entries':[{'asOf':'2026-10-07','path':'setup-state/registry/2026-10-07.json'}]}))
            (p/'2026-10-07.json').write_text(json.dumps({'asOf':'2026-10-07','symbols':{'NASDAQ:NVDA':{'setup_type':'VCP','lifecycle':'SETUP'}}}))
            self.assertEqual(load_registry_for_date(root,'2026-10-06')['symbols'],{})
            self.assertEqual(load_registry_for_date(root,'2026-10-07')['symbols']['NASDAQ:NVDA']['setup_type'],'VCP')

    def test_manual_state_wins_but_candidate_is_saved(self):
        q={'price':120,'entry':100,'ema21':110,'ma50':105,'slope50':1,'relativeVolume':1,'stage':'Stage 2','setup':'Base Breakout'}
        reg={'setup_type':'VCP','setupConfirmed':True,'lifecycle':'SETUP','lifecycleConfirmed':True}
        apply_setup_state(q,bars([100+i*.5 for i in range(70)]),reg,RULES,'2026-10-07')
        self.assertEqual(q['setup_type'],'VCP')
        self.assertEqual(q['lifecycle'],'SETUP')
        self.assertTrue(q['lifecycleConfirmed'])
        self.assertNotEqual(q['lifecycleCandidate'],'UNASSESSED')
        self.assertEqual(q['setupRegistryAsOf'],'2026-10-07')

    def test_rule_base_breakout_becomes_unconfirmed_origin(self):
        q={'price':99,'entry':100,'ema21':98,'ma50':95,'slope50':1,'relativeVolume':.7,'stage':'Stage 2','setup':'Base Breakout'}
        apply_setup_state(q,bars([90+i*.1 for i in range(70)]),None,RULES)
        self.assertEqual(q['setup_type'],'Base Breakout')
        self.assertFalse(q['setupConfirmed'])
        self.assertEqual(q['setupTypeSource'],'RULE_CANDIDATE')
        self.assertEqual(q['lifecycle'],'SETUP')
        self.assertEqual(q['lifecycleSource'],'RULE_CANDIDATE')

    def test_retest_extended_and_failed_candidates(self):
        base={'ema21':100,'ma50':95,'slope50':1,'relativeVolume':.8,'stage':'Stage 2','setup_type':'VCP'}
        reg={'setup_type':'VCP','lifecycle':'BREAKOUT'}
        q={**base,'price':102,'entry':100}
        self.assertEqual(lifecycle_candidate(q,bars([100]*30),reg,RULES)[0],'RETEST')
        q={**base,'price':115,'entry':100}
        self.assertEqual(lifecycle_candidate(q,bars([100,102,104,106,108,110]),reg,RULES)[0],'EXTENDED')
        q={**base,'price':90,'entry':100,'ma50':95}
        self.assertEqual(lifecycle_candidate(q,bars([100,98,95,92,90]),reg,RULES)[0],'FAILED_BREAKOUT')

    def test_pullback_candidate_without_saved_entry(self):
        q={'price':101,'entry':None,'ema21':100,'ma50':95,'slope50':1,'relativeVolume':.8,'stage':'Stage 2','setup_type':'Base Breakout'}
        reg={'setup_type':'Base Breakout','lifecycle':'BREAKOUT'}
        self.assertEqual(lifecycle_candidate(q,bars([95+i*.2 for i in range(30)]),reg,RULES)[0],'PULLBACK')


if __name__=='__main__':
    unittest.main()
