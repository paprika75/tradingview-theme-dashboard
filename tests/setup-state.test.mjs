import test from 'node:test';
import assert from 'node:assert/strict';
import {setupState,LIFECYCLES} from '../lib/setup-state.mjs';
import {DataRepository} from '../lib/data.mjs';
import * as V from '../lib/views.mjs';
import {readFile} from 'node:fs/promises';
const fetcher=async p=>({ok:true,json:async()=>JSON.parse(await readFile(new URL('../'+p,import.meta.url),'utf8'))});

test('below-entry prices remain pre-breakout; reaching entry becomes breakout',()=>{
 for(const [price,lifecycle] of [[95,'SETUP'],[100,'BREAKOUT'],[101,'BREAKOUT']]){
  const result=setupState({setup:'Base Breakout',price,entry:100,pivotDistancePct:-5});
  assert.equal(result.lifecycle,lifecycle);assert.equal(result.source,'INFERRED');
 }
});
test('missing, zero and ambiguous legacy levels stay unassessed',()=>{
 for(const entry of [undefined,null,0,'—',NaN])assert.equal(setupState({setup:'Base Breakout',price:100,entry}).lifecycle,'UNASSESSED');
 assert.equal(setupState({setup:'Pullback / Retest',price:100,entry:100}).lifecycle,'UNASSESSED');
 assert.equal(setupState({setup:'Pullback / Retest'}).setupType,'—');
});
test('saved origin and lifecycle are retained without reinterpretation',()=>{
 for(const lifecycle of LIFECYCLES){const r=setupState({setup_type:'VCP',lifecycle,price:50,entry:100},true);assert.equal(r.setupType,'VCP');assert.equal(r.lifecycle,lifecycle);assert.equal(r.source,'SAVED');}
});
test('forming readiness is preserved alongside pre-breakout lifecycle',()=>{
 const r=setupState({setup:'Base / VCP forming',status:'FORMING',readiness:'Forming'});
 assert.equal(r.lifecycle,'SETUP');assert.equal(r.readiness,'Forming');assert.equal(r.setupType,'—');assert.equal(r.confirmed,false);
});
test('entry eligibility filter and lifecycle filter narrow independently',async()=>{
 const repo=await new DataRepository(fetcher).load('mock');
 const ctx=await repo.context('daily',repo.manifest.daily.at(-1).key,'US');
 const candidate=V.setupRows(ctx,{market:'US',setupFilter:'candidate'});
 const all=V.setupRows(ctx,{market:'US',setupFilter:'all'});
 assert.ok(all.count>=candidate.count);assert.equal(candidate.count,candidate.candidates);
 for(const lifecycle of LIFECYCLES){const subset=V.setupRows(ctx,{market:'US',setupFilter:'all',lifecycleFilter:lifecycle});assert.ok(subset.count<=all.count);if(subset.count)assert.ok(subset.html.includes(`data-lifecycle="${lifecycle}"`));}
 assert.ok(V.setups(ctx,{market:'US'}).includes('id="setup-filter"'));
 assert.ok(V.setups(ctx,{market:'US'}).includes('id="lifecycle-filter"'));
});
