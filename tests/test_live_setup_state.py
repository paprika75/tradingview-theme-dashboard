import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from build_live_with_setup_state import enrich_snapshot

RULES = {
    'version':'test', 'failedPivotPct':3, 'retestPct':3,
    'pullbackEma21MinPct':-2, 'pullbackEma21MaxPct':3, 'pullbackMaxRvol':1.2,
    'extendedFromEntryPct':10, 'extendedFromEma21Pct':10,
    'tightSessions':5, 'tightRangePct':5, 'threeWeeksTightClosePct':1.5,
    'ascendingBaseWindowSessions':60, 'ascendingBaseMaxBlockRangePct':22,
    'ascendingBaseNearHighPct':5
}


def snapshot(asof='2026-10-07'):
    q={'price':101,'entry':100,'stop':94,'ema21':99,'ma50':95,'slope50':1,
       'relativeVolume':1.4,'stage':'Stage 2','setup':'Base Breakout','setupReady':True}
    return {'period':'daily','asOf':asof,'markets':{'US':{'themes':[{'quantitative':{'setupCount':1},'stocks':[{'symbol':'NASDAQ:NVDA','quantitative':q}]}]}}}


def bars():
    from datetime import date,timedelta
    d=date(2026,7,1);out=[]
    for i in range(70):
        while d.weekday()>=5:d+=timedelta(days=1)
        price=90+i*.2
        out.append({'date':d.isoformat(),'o':price,'h':price*1.01,'l':price*.99,'c':price,'v':100})
        d+=timedelta(days=1)
    return {'NASDAQ:NVDA':out}


class LiveSetupEnrichmentTests(unittest.TestCase):
    def make_root(self, registry_asof='2026-10-07'):
        td=tempfile.TemporaryDirectory();root=Path(td.name);p=root/'data/setup-state/registry';p.mkdir(parents=True)
        (p/'manifest.json').write_text(json.dumps({'entries':[{'asOf':registry_asof,'path':f'setup-state/registry/{registry_asof}.json'}]}))
        (p/f'{registry_asof}.json').write_text(json.dumps({'asOf':registry_asof,'source':{'type':'test'},'symbols':{'NASDAQ:NVDA':{'setup_type':'VCP','setupConfirmed':True,'lifecycle':'SETUP','lifecycleConfirmed':True}}}))
        return td,root

    def test_snapshot_persists_manual_and_candidate_state(self):
        td,root=self.make_root()
        try:
            data=enrich_snapshot(snapshot(),bars(),RULES,root)
            q=data['markets']['US']['themes'][0]['stocks'][0]['quantitative']
            self.assertEqual(q['setup_type'],'VCP')
            self.assertEqual(q['lifecycle'],'SETUP')
            self.assertTrue(q['lifecycleConfirmed'])
            self.assertIn(q['lifecycleCandidate'],{'BREAKOUT','RETEST','TIGHT','EXTENDED','PULLBACK','3WT','ASCENDING_BASE'})
            self.assertEqual(data['setupState']['registryAsOf'],'2026-10-07')
            self.assertEqual(data['markets']['US']['themes'][0]['quantitative']['setupCount'],1)
        finally:td.cleanup()

    def test_future_registry_is_not_backfilled(self):
        td,root=self.make_root('2026-10-08')
        try:
            data=enrich_snapshot(snapshot('2026-10-07'),bars(),RULES,root)
            q=data['markets']['US']['themes'][0]['stocks'][0]['quantitative']
            self.assertEqual(q['setup_type'],'Base Breakout')
            self.assertFalse(q['setupConfirmed'])
            self.assertIsNone(q['setupRegistryAsOf'])
            self.assertIsNone(data['setupState']['registryAsOf'])
        finally:td.cleanup()

    def test_enrichment_is_idempotent(self):
        td,root=self.make_root()
        try:
            data=snapshot()
            first=json.dumps(enrich_snapshot(data,bars(),RULES,root),sort_keys=True)
            second=json.dumps(enrich_snapshot(data,bars(),RULES,root),sort_keys=True)
            self.assertEqual(first,second)
        finally:td.cleanup()


if __name__=='__main__':
    unittest.main()
