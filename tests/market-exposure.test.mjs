import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {DataRepository} from '../lib/data.mjs';
import * as V from '../lib/views.mjs';
const root=new URL('../',import.meta.url);
const fetcher=async p=>{try{return {ok:true,json:async()=>JSON.parse(await readFile(new URL(p,root),'utf8'))};}catch{return {ok:false,status:404};}};
test('reference ranges match the selected date and remain independent of watchlists',async()=>{
 const repo=await new DataRepository(fetcher).load();
 for(const period of ['daily','weekly'])for(const market of ['US','JP']){
  const ctx=await repo.context(period,repo.manifest[period].at(-1).key,market);
  assert.equal(ctx.exposureMeta.asOf,ctx.entry.asOf);
  assert.equal(ctx.exposureMeta.outlookVersion,ctx.outlookMeta.evaluationVersion);
  assert.deepEqual(ctx.exposure.range,market==='US'?[20,40]:null);
  assert.equal(ctx.exposure.previous?.asOf??null,period==='daily'?'2026-10-02':null);
  const state={market,mode:'live',period,key:ctx.entry.key};
  const before=V.hero(ctx,state).split('02 / NEW OPPORTUNITIES')[0];
  ctx.health=100;ctx.rows=[];
  assert.equal(V.hero(ctx,state).split('02 / NEW OPPORTUNITIES')[0],before);
  const html=V.marketHealth(ctx);
  assert.ok(html.includes('株式投資用資金'));
  assert.ok(html.includes(market==='US'?'aria-current="true"':'データ不足で未判定'));
 }
});
test('corrupt exposure data fails closed while theme data remains available',async()=>{
 for(const patch of [d=>({...d,markets:{...d.markets,US:{...d.markets.US,band:null,range:[20,40]}}}),d=>({...d,asOf:'2099-01-01'}),d=>({...d,mode:'mock'}),d=>({...d,outlookVersion:'unknown'}),d=>({...d,markets:{...d.markets,US:{...d.markets.US,band:4,range:[20,40]}}})]){
  const custom=async p=>{const r=await fetcher(p);return p.includes('/market-exposure/')?{ok:true,json:async()=>patch(await r.json())}:r;};
  const repo=await new DataRepository(custom).load(),ctx=await repo.context('daily','2026-10-05','US');
  assert.equal(ctx.exposure,null);assert.ok(ctx.exposureError);assert.ok(ctx.rows.length>0);
  assert.ok(V.marketHealth(ctx).includes('評価データを読み込めません'));
 }
});
test('an unassessed outlook cannot advertise a numeric exposure',async()=>{
 const custom=async p=>{const r=await fetcher(p);if(!p.includes('/market-exposure/'))return r;return {ok:true,json:async()=>{const d=await r.json();d.markets.JP.band=0;d.markets.JP.range=[0,20];return d;}};};
 const repo=await new DataRepository(custom).load(),ctx=await repo.context('daily','2026-10-05','JP');
 assert.equal(ctx.exposure,null);assert.ok(ctx.exposureError);
});
test('Demo does not borrow observed reference exposure',async()=>{
 const repo=await new DataRepository(fetcher).load('mock'),ctx=await repo.context('daily',repo.manifest.daily.at(-1).key,'US');
 assert.equal(ctx.exposure,null);assert.equal(ctx.exposureMeta,null);
 assert.ok(V.marketHealth(ctx).includes('Demoでは指数の参考投資比率を生成しません'));
});
