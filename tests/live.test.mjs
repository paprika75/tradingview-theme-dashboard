import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {DataRepository} from '../lib/data.mjs';
import {weighted,activeHealth,researchStocks} from '../lib/logic.mjs';
import * as V from '../lib/views.mjs';
const root=new URL('../',import.meta.url);
const json=async p=>JSON.parse(await readFile(new URL(p,root),'utf8'));
const fetcher=async p=>{try{const data=await json(p);return {ok:true,json:async()=>data};}catch{return {ok:false,status:404};}};
test('observed mode never imports demo analysis, samples, or scoring configuration',async()=>{
 const repo=await new DataRepository(fetcher).load();
 assert.equal(repo.router.mode,'live');
 for(const market of ['US','JP'])for(const period of ['daily','weekly']){
  const ctx=await repo.context(period,repo.manifest[period].at(-1).key,market);
  assert.equal(ctx.mode,'live');assert.equal(ctx.config.version,'3.0.0-observed-technicals');
  assert.equal(ctx.analysis,null);assert.equal(ctx.analysisMeta,null);assert.deepEqual(ctx.failures,[]);
  assert.deepEqual(await repo.driverHistory(ctx.entry.asOf,market),[]);
  assert.ok(ctx.rows.every(t=>t.ai===null));
  assert.equal(ctx.health,weighted(ctx.market.scores.marketComponents,ctx.market.marketHealthWeights));
  for(const t of ctx.rows){
   if(!t.quantitative.rankEligible)assert.equal(t.quantitative[period+'Rank'],null);
   for(const s of t.stocks){if(s.quantitative.stage==='Stage 2')assert.ok(Object.values(s.quantitative.templateChecks).every(Boolean));if(!s.dataQuality.usable)assert.equal(s.scores.leader,null);}
  }
 }
});
test('observed views render missing AI / incomplete metrics and qualified coverage without exceptions',async()=>{
 const repo=await new DataRepository(fetcher).load();
 for(const market of ['US','JP']){
  const ctx=await repo.context('daily','2026-10-05',market),state={market,mode:'live',period:'daily',key:'2026-10-05',researchTheme:'all',setupFilter:'all',selected:[],filter:'all'},hist=await repo.history('daily',ctx.entry.asOf,market);
  for(const fn of ['marketHealth','institutional','translations','opportunities','activeThemes','landscape','rotation','about'])assert.ok(V[fn](ctx,state,fn==='activeThemes'?ctx.rows.slice(0,2).map(t=>t.id):hist,[]).length>100);
  for(const t of ctx.rows)assert.ok(V.detail(ctx,state,t.id,hist).length>100);
  assert.ok(V.historyView(ctx,state,hist,[]).includes('AI履歴はまだありません'));
  assert.ok(V.landscapeRows(ctx,state,[]).html.includes('有効'));
  assert.ok(V.setups(ctx,state).includes('自動確定判定は未実装'));
  assert.ok(!V.detail(ctx,state,ctx.rows[0].id,hist).includes('QUANT / MOCK'));
  assert.ok(researchStocks(ctx).filter(r=>r.eligible).every(r=>r.stock.quantitative.stage==='Stage 2'));
 }
});
test('missing active-health evidence stays unassessed',()=>{
 const t={quantitative:{weeklyDelta5:null,breadthDelta5:2,weeklyDelta3Weeks:null,above200:70}};
 assert.equal(activeHealth(t,{thresholds:{}}).status,'UNASSESSED');
});
