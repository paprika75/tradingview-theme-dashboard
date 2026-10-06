import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {DataRepository} from '../lib/data.mjs';
import {decisionSummary,researchStocks,activeHealth} from '../lib/logic.mjs';
import {marketForPage,marketPageURL} from '../lib/routes.mjs';
import * as V from '../lib/views.mjs';
const root=new URL('../',import.meta.url);
const json=async p=>JSON.parse(await readFile(new URL(p,root),'utf8'));
const fetcher=async p=>{try{return {ok:true,json:()=>json(p)};}catch{return {ok:false,status:404};}};

test('market pages override contradictory queries and market navigation resets theme state',()=>{
 assert.equal(marketForPage('/dashboard/us.html','jp'),'US');
 assert.equal(marketForPage('/dashboard/japan.html','us'),'JP');
 assert.equal(marketForPage('/dashboard/index.html','japan'),'JP');
 const state={market:'US',mode:'mock',period:'weekly',key:'2026-W40',researchTheme:'us-5',setupFilter:'ready'};
 const same=new URL(marketPageURL(state),'https://example.test/');
 assert.equal(same.pathname,'/us.html');assert.equal(same.searchParams.get('theme'),'us-5');
 const other=new URL(marketPageURL(state,'JP'),'https://example.test/');
 assert.equal(other.pathname,'/japan.html');assert.equal(other.searchParams.get('market'),'jp');
 assert.equal(other.searchParams.get('date'),'2026-W40');assert.equal(other.searchParams.get('data'),'mock');
 assert.equal(other.searchParams.has('theme'),false);assert.equal(other.searchParams.has('setups'),false);
});

test('public summary uses all themes and keeps missing health history separate from alerts',async()=>{
 const repo=await new DataRepository(fetcher).load('live');
 for(const market of ['US','JP'])for(const period of ['daily','weekly']){
  const ctx=await repo.context(period,repo.manifest[period].at(-1).key,market),d=decisionSummary(ctx);
  assert.equal(Object.values(d.counts).reduce((a,b)=>a+b,0),ctx.rows.length);
  assert.equal(d.counts.UNASSESSED,ctx.rows.filter(t=>activeHealth(t,ctx.config).status==='UNASSESSED').length);assert.equal(d.warnings.length,d.counts.WATCH+d.counts.DETERIORATING);assert.equal(d.healthy.length,d.counts.HEALTHY);
  assert.equal(new Set(d.entryStocks.map(r=>r.stock.symbol)).size,d.entryStocks.length);
  assert.ok(d.entryStocks.every(r=>r.eligible));
  assert.ok(d.trendStocks.every(r=>r.stock.quantitative.stage==='Stage 2'&&r.stock.quantitative.above50===true));
  const state={market,mode:'live',period,key:ctx.entry.key};
  assert.equal(V.hero(ctx,state,[]),V.hero(ctx,state,ctx.rows.map(t=>t.id)));
  assert.equal(V.activeThemes(ctx,state,[]),V.activeThemes(ctx,state,[ctx.rows[0].id]));
  const html=V.hero(ctx,state)+V.activeThemes(ctx,state);
  assert.ok(html.includes('参考投資比率'));assert.ok(html.includes(market==='US'?'20–40%':'未判定'));
  assert.ok(html.includes('履歴不足・未評価'));assert.ok(!html.includes('保有テーマ'));
  for(const t of ctx.rows)assert.ok(html.includes(V.esc(t.name)));
 }
});

test('summary distinguishes healthy themes, actual warnings, and unassessed themes',async()=>{
 const repo=await new DataRepository(fetcher).load('mock');
 const ctx=await repo.context('daily','2026-10-01','US');
 ctx.rows=ctx.rows.slice(0,3).map(t=>structuredClone(t));
 for(const t of ctx.rows)Object.assign(t.quantitative,{weeklyDelta5:0,breadthDelta5:0,weeklyDelta3Weeks:0,above200:75});
 ctx.rows[1].quantitative.weeklyDelta5=-15;
 ctx.rows[2].quantitative.weeklyDelta3Weeks=null;
 const d=decisionSummary(ctx);
 assert.deepEqual(d.counts,{HEALTHY:1,WATCH:1,DETERIORATING:0,UNASSESSED:1});
 assert.equal(d.warnings[0].theme.id,ctx.rows[1].id);
 assert.equal(d.healthy[0].theme.id,ctx.rows[0].id);
 assert.equal(d.entryStocks.length,new Set(researchStocks(ctx).filter(r=>r.eligible).map(r=>r.stock.symbol)).size);
 ctx.health=null;assert.equal(decisionSummary(ctx).healthStatus,'UNASSESSED');
});
