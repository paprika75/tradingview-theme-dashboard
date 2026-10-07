import test from 'node:test';
import assert from 'node:assert/strict';
import {DataRepository} from '../lib/data.mjs';
import {setupJourneyPanel} from '../lib/views.mjs';
import {adoptedEntryPlans} from '../lib/setup-journey.mjs';

const plan={status:'CONFIRMED',lifecycle:'RETEST',episodeId:'e1',kind:'REENTRY',entry:120,stop:115,riskPct:4.1667};
const journey={symbol:'NASDAQ:TEST',episodeId:'e1',phase:'POST_BREAKOUT',lifecycle:{value:'RETEST',confirmed:true},entryPlan:{status:'CONFIRMED',alternatives:[plan]}};

test('only explicitly confirmed plans for the current episode and lifecycle are adopted',()=>{
 assert.equal(adoptedEntryPlans(journey).length,1);
 for(const status of ['WAIT','INVALID','REVIEW_REQUIRED'])assert.deepEqual(adoptedEntryPlans({...journey,entryPlan:{...journey.entryPlan,status}}),[]);
 assert.deepEqual(adoptedEntryPlans({...journey,phase:'PRE_SETUP'}),[]);
 assert.deepEqual(adoptedEntryPlans({...journey,lifecycle:{value:'RETEST',confirmed:false,candidate:'RETEST'}}),[]);
 assert.deepEqual(adoptedEntryPlans({...journey,episodeId:'e2'}),[]);
});
test('Pre-Setup rendering preserves all readiness and candidate price semantics',()=>{
 const ctx={mode:'live',market:{},preSetupMeta:{asOf:'2026-10-07',evaluationVersion:'pre1'},preSetup:{stocks:['Ready','Near','Forming'].map((readiness,i)=>({symbol:'NASDAQ:TEST'+i,readiness,pivot:100,pivotDistancePct:i+1,candidateEntry:100.1,candidateStop:96,reasons:['チャート確認']}))}};
 const html=setupJourneyPanel(ctx);
 for(const value of ['Ready','Near','Forming','100.00','100.10','96.00'])assert.ok(html.includes(value));
 assert.ok(html.includes('候補抽出・REVIEW発火は正式昇格やBuyを意味しません'));
 assert.ok(html.includes('過去評価へ後から確認状態を補完しません'));
 assert.equal(setupJourneyPanel({...ctx,mode:'mock'}),'');
});
test('future Pre-Setup does not load into archive and failed loads remain explicit',async()=>{
 const docs={'data/pre-setup/latest.json':{schemaVersion:1,mode:'live',entries:[{asOf:'2026-10-07',path:'pre-setup/test.json',evaluationVersion:'pre1'}]},'data/pre-setup/test.json':{mode:'live',asOf:'2026-10-07',evaluationVersion:'pre1',universeAsOf:'2026-10-07',markets:{US:{stocks:[]},JP:{stocks:[]}}}};
 const calls=[];const repo=new DataRepository(async p=>{calls.push(p);return {ok:true,json:async()=>docs[p]};});repo.router={mode:'live'};
 const archive=await repo.preSetup('2026-10-06','US');assert.equal(archive.data,null);assert.ok(!calls.includes('data/pre-setup/test.json'));
 const current=await repo.preSetup('2026-10-07','JP');assert.equal(current.meta.stale,false);
 const older=await repo.preSetup('2026-10-08','US');assert.equal(older.meta.stale,true);
 repo.cache.clear();docs['data/pre-setup/test.json'].universeAsOf='2026-10-09';
 const invalid=await repo.preSetup('2026-10-08','US');assert.equal(invalid.data,null);assert.ok(invalid.error);
});
