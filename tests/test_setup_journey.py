import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from setup_journey import build_journey, validate_review_transition, load_pre_setup, risk_pct, ENTRY_KINDS
from build_live_with_setup_state import enrich_snapshot
from build_live_with_setup_state import enrich_quantitative
from setup_lifecycle import apply_setup_state

ASOF = '2026-10-07'
RULES = {'version': '1.0.0'}

def state(lifecycle='SETUP'):
    pivot = {'id':'p1','price':100,'confirmed':True,'asOf':ASOF,'source':'CHART_REVIEW'}
    kind = (ENTRY_KINDS[lifecycle] or ['STANDARD'])[0]
    return {'setup_type':'VCP','setupConfirmed':True,'setupTypeSource':'CHART_REVIEW',
            'lifecycle':lifecycle,'lifecycleConfirmed':True,'lifecycleSource':'CHART_REVIEW',
            'setupReview':{'episodeId':'episode1','setup_type':'VCP','reviewedAsOf':ASOF,
                           'originPivot':pivot,'patternChecks':{'contractionsDecreasing':True,'volumeDryUp':True,'finalContractionClear':True}},
            'entryPlans':[{'id':'plan1','episodeId':'episode1','originPivotId':'p1','pivot':pivot,
                           'lifecycle':lifecycle,'kind':kind,'asOf':ASOF,'source':'CHART_REVIEW',
                           'entry':101,'stop':96,'stopBasis':'最終収縮の安値','confirmed':True}]}

def journey(saved=None, candidate=None, target=ASOF, pre=None, meta=None):
    saved = state() if saved is None else saved
    q = {'price':99,'entry':500,'stop':400,'asOf':target}
    apply_setup_state(q, [], saved, RULES, ASOF)
    q['lifecycleCandidate'] = candidate or saved.get('lifecycle')
    return build_journey('NASDAQ:TEST',q,saved,ASOF,pre,meta,target)

class JourneyTests(unittest.TestCase):
    def test_pre_setup_readiness_does_not_promote(self):
        for readiness in ['Ready','Near','Forming']:
            pre={'candidateEligible':True,'readiness':readiness,'pivot':100,'marketDataAsOf':ASOF}
            j=journey({},pre=pre,meta={'asOf':ASOF,'evaluationVersion':'pre1'})
            self.assertEqual(j['phase'],'PRE_SETUP')
            self.assertFalse(j['promotion']['reviewComplete'])
            self.assertFalse(j['promotion']['automaticPromotion'])
            self.assertEqual(j['entryPlan']['status'],'REVIEW_REQUIRED')

    def test_reviewed_formal_setup_has_independent_entry_stop_risk(self):
        j=journey()
        self.assertEqual(j['phase'],'FORMAL_SETUP')
        self.assertTrue(j['promotion']['reviewComplete'])
        self.assertEqual(j['originPivot']['price'],100)
        self.assertEqual(j['entryPlan']['status'],'CONFIRMED')
        self.assertEqual(j['entryPlan']['alternatives'][0]['entry'],101)
        self.assertEqual(j['entryPlan']['alternatives'][0]['riskPct'],4.9505)

    def test_each_lifecycle_uses_its_own_plan(self):
        for lifecycle in ['BREAKOUT','PULLBACK','RETEST','3WT','TIGHT','ASCENDING_BASE']:
            s=state(lifecycle)
            s['entryPlans'][0].update(entry=120,stop=115,pivot={'id':'continuation1','price':119,'asOf':ASOF,'confirmed':True,'source':'CHART_REVIEW'})
            j=journey(s)
            self.assertEqual(j['phase'],'POST_BREAKOUT')
            self.assertEqual(j['entryPlan']['status'],'CONFIRMED')
            self.assertEqual(j['originPivot']['price'],100)
            self.assertEqual(j['entryPlan']['alternatives'][0]['entry'],120)

    def test_wait_and_failed_never_adopt_old_entry(self):
        for lifecycle,status,phase in [('EXTENDED','WAIT','POST_BREAKOUT'),('FAILED_BREAKOUT','INVALID','REFORMING')]:
            s=state(lifecycle);s['entryPlans'][0]['lifecycle']='SETUP'
            j=journey(s)
            self.assertEqual(j['entryPlan']['status'],status)
            self.assertEqual(j['phase'],phase)
            self.assertEqual(j['entryPlan']['alternatives'][0]['status'],'OBSOLETE')

    def test_unconfirmed_migration_and_auto_candidate_do_not_promote(self):
        s=state('BREAKOUT');s['lifecycleConfirmed']=False
        j=journey(s,candidate='RETEST')
        self.assertEqual(j['phase'],'UNASSESSED')
        self.assertNotEqual(j['entryPlan']['status'],'CONFIRMED')
        j=journey({},candidate='BREAKOUT')
        self.assertEqual(j['phase'],'UNASSESSED')

    def test_candidate_conflict_requests_review_without_changing_state(self):
        j=journey(state('RETEST'),candidate='FAILED_BREAKOUT')
        self.assertEqual(j['lifecycle']['value'],'RETEST')
        self.assertEqual(j['entryPlan']['status'],'REVIEW_REQUIRED')

    def test_old_lifecycle_episode_and_pivot_plans_are_obsolete(self):
        for field,value in [('lifecycle','BREAKOUT'),('episodeId','old'),('originPivotId','old')]:
            s=state('RETEST');s['entryPlans'][0][field]=value
            self.assertEqual(journey(s)['entryPlan']['alternatives'][0]['status'],'OBSOLETE')

    def test_future_review_and_plans_not_joined(self):
        self.assertEqual(journey(target='2026-10-06')['phase'],'UNASSESSED')
        self.assertEqual(journey(target='2026-10-06')['entryPlan']['alternatives'],[])
        s=state();s['setupReview']['reviewedAsOf']='2026-10-08'
        self.assertIsNone(journey(s)['originPivot'])
        s=state();s['entryPlans'][0]['asOf']='2026-10-08'
        self.assertEqual(journey(s)['entryPlan']['alternatives'],[])

    def test_missing_legacy_levels_and_stale_pre_are_not_reviewed(self):
        s=state();s.pop('setupReview');s.pop('entryPlans')
        j=journey(s)
        self.assertEqual(j['entryPlan']['alternatives'],[])
        self.assertIsNone(j['episodeId'])
        pre={'candidateEligible':True,'readiness':'Ready','pivot':100,'marketDataAsOf':'2026-10-06'}
        j=journey({},pre=pre,meta={'asOf':'2026-10-06','evaluationVersion':'pre1'})
        self.assertEqual(j['phase'],'UNASSESSED')
        self.assertTrue(j['preSetup']['stale'])

    def test_missing_invalid_and_zero_stops_never_produce_risk(self):
        for stop in [None,0,101,102,float('nan')]:
            self.assertIsNone(risk_pct(101,stop))
        s=state();s['entryPlans'][0]['stop']=101
        self.assertEqual(journey(s)['entryPlan']['alternatives'][0]['status'],'INVALID')

    def test_formal_promotion_requires_review_and_separate_optional_entries(self):
        self.assertEqual(validate_review_transition(None,state(),ASOF)['lifecycle'],'SETUP')
        for field in ['volumeDryUp','finalContractionClear']:
            s=state();s['setupReview']['patternChecks'][field]=False
            with self.assertRaises(ValueError):validate_review_transition(None,s,ASOF)
        s=state();s['entryPlans'][0]['kind']='EARLY'
        with self.assertRaises(ValueError):validate_review_transition(None,s,ASOF)

    def test_reformation_creates_new_episode_and_preserves_prior_origin(self):
        previous=state('FAILED_BREAKOUT');frozen=copy.deepcopy(previous)
        with self.assertRaises(ValueError):validate_review_transition(previous,state(),ASOF)
        proposed=state();proposed['setupReview'].update(episodeId='episode2',previousEpisodeId='episode1')
        proposed['entryPlans'][0]['episodeId']='episode2'
        validate_review_transition(previous,proposed,ASOF)
        self.assertEqual(previous,frozen)
        proposed=state();proposed['setupReview']['originPivot']['price']=105
        with self.assertRaises(ValueError):validate_review_transition(state(),proposed,ASOF)

    def test_promotion_rejects_future_pivot_and_below_pivot_standard_entry(self):
        s=state();s['entryPlans'][0]['pivot']=copy.deepcopy(s['entryPlans'][0]['pivot'])
        s['entryPlans'][0]['pivot']['asOf']='2026-10-08'
        with self.assertRaises(ValueError):validate_review_transition(None,s,ASOF)
        s=state();s['entryPlans'][0]['entry']=99
        with self.assertRaises(ValueError):validate_review_transition(None,s,ASOF)

    def test_saved_pre_setup_loader_filters_future_and_checks_versions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);p=root/'data/pre-setup';p.mkdir(parents=True)
            doc={'mode':'live','asOf':ASOF,'universeAsOf':ASOF,'evaluationVersion':'pre1','markets':{}}
            (p/'saved.json').write_text(json.dumps(doc))
            (p/'latest.json').write_text(json.dumps({'entries':[{'asOf':ASOF,'path':'pre-setup/saved.json','evaluationVersion':'pre1'}]}))
            self.assertIsNone(load_pre_setup(root,'2026-10-06'))
            self.assertEqual(load_pre_setup(root,ASOF),doc)
            doc['universeAsOf']='2026-10-08';(p/'saved.json').write_text(json.dumps(doc))
            with self.assertRaises(ValueError):load_pre_setup(root,ASOF)

    def test_new_version_keeps_all_market_theme_and_lifecycle_rules(self):
        old=json.loads((ROOT/'config/versions/3.2.0-setup-lifecycle-v1.json').read_text())
        new=json.loads((ROOT/'config/versions/3.3.0-setup-journey-v1.json').read_text())
        for doc in [old,new]:doc.pop('version');doc.pop('note')
        self.assertEqual(old,new)

    def test_candidate_uses_confirmed_origin_pivot_without_rewriting_legacy_entry(self):
        s=state('BREAKOUT')
        q={'price':90,'entry':500,'stop':400,'ma50':95,'asOf':ASOF}
        enrich_quantitative(q,[],s,RULES,ASOF,ASOF)
        self.assertEqual(q['entry'],500)
        self.assertEqual(q['stop'],400)
        self.assertEqual(q['lifecycle'],'BREAKOUT')
        self.assertEqual(q['lifecycleCandidate'],'FAILED_BREAKOUT')
        self.assertEqual(q['lifecycleCandidatePivot']['price'],100)

    def test_primary_and_registry_symbols_outside_theme_catalogue_are_saved(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);pre=root/'data/pre-setup';pre.mkdir(parents=True)
            pre_doc={'mode':'live','asOf':ASOF,'universeAsOf':ASOF,'evaluationVersion':'pre1',
                     'markets':{'US':{'stocks':[{'symbol':'NASDAQ:OUTSIDE','readiness':'Ready','candidateEligible':True,'pivot':100,'marketDataAsOf':ASOF}]}}}
            (pre/'saved.json').write_text(json.dumps(pre_doc))
            (pre/'latest.json').write_text(json.dumps({'entries':[{'asOf':ASOF,'path':'pre-setup/saved.json','evaluationVersion':'pre1'}]}))
            reg=root/'data/setup-state/registry';reg.mkdir(parents=True)
            s=state('RETEST');s['market']='JP'
            (reg/'saved.json').write_text(json.dumps({'asOf':ASOF,'symbols':{'TSE:9999':s}}))
            (reg/'manifest.json').write_text(json.dumps({'entries':[{'asOf':ASOF,'path':'setup-state/registry/saved.json'}]}))
            data={'asOf':ASOF,'period':'daily','markets':{'US':{'themes':[]},'JP':{'themes':[]}}}
            enriched=enrich_snapshot(data,{},RULES,root)
            self.assertEqual(enriched['markets']['US']['setupJourneys'][0]['phase'],'PRE_SETUP')
            jp=enriched['markets']['JP']['setupJourneys'][0]
            self.assertEqual(jp['phase'],'POST_BREAKOUT')
            self.assertEqual(jp['entryPlan']['status'],'REVIEW_REQUIRED')
            self.assertEqual(enriched['markets']['US']['themes'],[])
            self.assertEqual(enrich_snapshot(copy.deepcopy(enriched),{},RULES,root),enriched)

if __name__=='__main__':unittest.main()
