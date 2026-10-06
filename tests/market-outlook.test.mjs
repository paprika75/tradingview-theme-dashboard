import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {DataRepository} from '../lib/data.mjs';
import * as V from '../lib/views.mjs';
const root=new URL('../',import.meta.url);
const fetcher=async p=>{try{return {ok:true,json:async()=>JSON.parse(await readFile(new URL(p,root),'utf8'))};}catch{return {ok:false,status:404};}};
test('outlook is date-specific and independent of watchlist scores',async()=>{
 const repo=await new DataRepository(fetcher).load();
 for(const period of ['daily','weekly'])for(const market of ['US','JP']){
  const ctx=await repo.context(period,repo.manifest[period].at(-1).key,market);
  assert.equal(ctx.outlookMeta.asOf,ctx.entry.asOf);
  assert.equal(ctx.outlook.indices.length,2);
  const state={market,mode:'live',period,key:ctx.entry.key};
  const html=V.marketHealth(ctx);
  assert.ok(html.indexOf('MARKET OUTLOOK')<html.indexOf('DISTRIBUTION DAYS'));
  assert.ok(html.indexOf('DISTRIBUTION DAYS')<html.indexOf('MOMENTUM HEALTH'));
  const firstCard=()=>V.hero(ctx,state).split('02 / NEW OPPORTUNITIES')[0];
  const before=firstCard();ctx.health=0;assert.equal(firstCard(),before);
  if(market==='JP'){
   assert.equal(ctx.outlook.status,'UNASSESSED');
   assert.ok(ctx.outlook.indices.every(i=>i.distributionCount===null));
   assert.ok(html.includes('出来高不足'));
  }else assert.ok(ctx.outlook.indices.every(i=>Number.isInteger(i.distributionCount)));
 }
});
test('wrong-date outlook fails closed without corrupting saved theme data',async()=>{
 const custom=async p=>{const r=await fetcher(p);if(p.includes('/market-outlook/'))return {ok:true,json:async()=>({...await r.json(),asOf:'2099-01-01'})};return r;};
 const repo=await new DataRepository(custom).load(),ctx=await repo.context('daily','2026-10-05','US');
 assert.equal(ctx.outlook,null);assert.ok(ctx.outlookError);assert.ok(ctx.rows.length>0);
 assert.ok(V.marketHealth(ctx).includes('未判定'));
});
test('Demo never borrows observed market classifications',async()=>{
 const repo=await new DataRepository(fetcher).load('mock'),ctx=await repo.context('daily',repo.manifest.daily.at(-1).key,'US');
 assert.equal(ctx.outlook,null);assert.equal(ctx.outlookMeta,null);
 assert.ok(V.marketHealth(ctx).includes('Demoでは指数市場区分を生成しません'));
});
