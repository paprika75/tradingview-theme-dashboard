import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from save_setup_review import save_review
from propose_setup_review import propose
from build_stock_analysis import build
from research_store import immutable_json
from test_setup_journey import state


class ResearchTests(unittest.TestCase):
    def review(self):
        s=state();s['market']='US'
        return {'asOf':'2026-10-07','reviewedAt':'2026-10-07T12:00:00+09:00',
                'reviewer':'test fixture','changeReason':'confirmed chart structure','symbols':{'NASDAQ:TEST':s}}

    def test_review_saves_full_registry_without_mutating_prior(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);p=root/'data/setup-state/registry'
            immutable_json(p/'2026-10-06.json',{'asOf':'2026-10-06','symbols':{'NYSE:OLD':{'setup_type':None,'lifecycle':'UNASSESSED'}}})
            immutable_json(p/'manifest.json',{'schemaVersion':1,'entries':[{'asOf':'2026-10-06','path':'setup-state/registry/2026-10-06.json'}]})
            before=(p/'2026-10-06.json').read_bytes()
            result=save_review(self.review(),root)
            self.assertTrue(result['saved']);self.assertFalse(result['watchlistsChanged'])
            self.assertIn('NYSE:OLD',json.loads((p/'2026-10-07.json').read_text())['symbols'])
            self.assertEqual((p/'2026-10-06.json').read_bytes(),before)
            save_review(self.review(),root)
            self.assertEqual(len(json.loads((p/'manifest.json').read_text())['entries']),2)
            changed=self.review();changed['symbols']['NASDAQ:TEST']['entryPlans'][0]['stop']=95
            with self.assertRaises(ValueError):save_review(changed,root)
            self.assertEqual(len(json.loads((p/'manifest.json').read_text())['entries']),2)

    def test_incomplete_candidate_cannot_be_confirmed_by_save(self):
        for change in ['candidate','stop','pattern','future']:
            with tempfile.TemporaryDirectory() as tmp:
                doc=self.review();s=doc['symbols']['NASDAQ:TEST']
                if change=='candidate':s['lifecycleSource']='RULE_CANDIDATE'
                if change=='stop':s['entryPlans'][0]['stop']=0
                if change=='pattern':s['setupReview']['patternChecks']['volumeDryUp']=False
                if change=='future':s['setupReview']['originPivot']['asOf']='2026-10-08'
                with self.assertRaises(ValueError):save_review(doc,Path(tmp))
                self.assertFalse((Path(tmp)/'data/setup-state/registry/manifest.json').exists())

    def test_structural_windows_and_extended_are_proposals_only(self):
        doc={'asOf':'2026-10-07','symbol':'NASDAQ:TEST','setup_type':'CWH',
             'completedBars':[{'date':'2026-10-05','h':100,'l':94,'c':98},{'date':'2026-10-06','h':103,'l':96,'c':100},{'date':'2026-10-07','h':120,'l':112,'c':115}],
             'pivotWindow':{'start':'2026-10-05','end':'2026-10-06','basis':'handle'},
             'stopWindow':{'start':'2026-10-05','end':'2026-10-06','basis':'handle support'}}
        draft=propose(doc)
        self.assertEqual(draft['pivot'],103);self.assertEqual(draft['stop'],94)
        self.assertTrue(draft['extendedCandidate']);self.assertFalse(draft['setupConfirmed'])
        self.assertEqual(set(draft['patternChecks']),{'cupStructure','handleStructure','handleResistanceClear'})
        doc['completedBars'][-1]['date']='2026-10-08'
        with self.assertRaises(ValueError):propose(doc)

    def analysis_root(self,root):
        snapshot={'mode':'live','asOf':'2026-10-05','generatedAt':'2026-10-06T00:00:00Z','evaluationVersion':'technical1',
                  'markets':{'US':{'themes':[{'name':'test','stocks':[{'symbol':'NASDAQ:TEST','quantitative':{'price':99,'asOf':'2026-10-05','stage':'Stage 2','entry':123,'stop':100,'holdings':'must not escape'}}]}]}}}
        immutable_json(root/'data/live/snapshot.json',snapshot)
        immutable_json(root/'data/live/latest.json',{'daily':[{'asOf':'2026-10-05','path':'live/snapshot.json'}]})
        return {'asOf':'2026-10-08','observedAt':'2026-10-07T18:00:00Z','lists':[{'name':'🇺🇸一次スクリーナー','market':'US','symbols':['NASDAQ:TEST','NASDAQ:MISSING']}]}

    def test_dated_history_idempotence_new_reanalysis_and_missing_coverage(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);universe=self.analysis_root(root)
            result=build(universe,'2026-10-07T18:20:00Z','first',root)
            self.assertEqual(result['analyzed'],1);self.assertEqual(result['universe'],2)
            build(universe,'2026-10-07T18:20:00Z','first',root)
            manifest=json.loads((root/'data/stock-analysis/manifest.json').read_text())
            self.assertEqual(manifest['symbols']['NASDAQ:MISSING']['coverageStatus'],'UNANALYZED')
            self.assertEqual(len(manifest['symbols']['NASDAQ:TEST']['entries']),1)
            saved=(root/'data'/result['path']).read_bytes()
            entry=json.loads(saved)['symbols']['NASDAQ:TEST']
            self.assertEqual(entry['analysisDate'],'2026-10-08');self.assertEqual(entry['marketDataAsOf'],'2026-10-05')
            self.assertIsNone(entry['entry']);self.assertIsNone(entry['structuralStop'])
            self.assertNotIn('holdings',str(entry));self.assertFalse(entry['setupConfirmed'])
            build(universe,'2026-10-07T18:25:00Z','new review context',root)
            self.assertEqual((root/'data'/result['path']).read_bytes(),saved)
            self.assertEqual(len(json.loads((root/'data/stock-analysis/manifest.json').read_text())['symbols']['NASDAQ:TEST']['entries']),2)

    def test_failed_or_future_build_keeps_previous_analysis(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);universe=self.analysis_root(root)
            build(universe,'2026-10-07T18:20:00Z','first',root)
            path=root/'data/stock-analysis/manifest.json';saved=path.read_bytes()
            future=copy.deepcopy(universe);future['observedAt']='2026-10-09T00:00:00Z'
            with self.assertRaises(ValueError):build(future,'2026-10-07T18:20:00Z','bad',root)
            bad=copy.deepcopy(universe);bad['lists'][0]['name']='保有銘柄'
            with self.assertRaises(ValueError):build(bad,'2026-10-07T18:20:00Z','bad',root)
            self.assertEqual(path.read_bytes(),saved)

if __name__=='__main__':unittest.main()
