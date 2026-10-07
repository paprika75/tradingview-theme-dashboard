import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {marketAction,technicalThemeCandidate,technicalResearchStocks} from '../lib/market-action.mjs';
import {DataRepository} from '../lib/data.mjs';
import {researchStocks} from '../lib/logic.mjs';
const context=state=>({mode:'live',asOf:'2026-10-05',outlook:{status:state,reasons:['index evidence'],indices:[]},outlookMeta:{mode:'live',asOf:'2026-10-05',evaluationVersion:'outlook1'},exposure:{range:[20,40]},exposureMeta:{asOf:'2026-10-05',outlookVersion:'outlook1',evaluationVersion:'exposure1'}});
test('market constraints are conditional and never grant automatic entry',()=>{
 for(const [state,code] of Object.entries({MARKET_IN_CORRECTION:'WAIT',UPTREND_UNDER_PRESSURE:'LIMIT',CONFIRMED_UPTREND:'CHECK_ENTRY',UNASSESSED:'VERIFY'})){
  const a=marketAction(context(state));assert.equal(a.code,code);assert.equal(a.automaticBuy,false);
 }
 const missing=context('CONFIRMED_UPTREND');missing.outlookMeta.asOf='2026-10-07';assert.equal(marketAction(missing).code,'VERIFY');assert.equal(marketAction(missing).range,null);
 const jp=context('UNASSESSED');jp.outlook.indices=[{status:'UNASSESSED',priceTrend:'UP'}];assert.equal(marketAction(jp).priceOnly,true);assert.equal(marketAction(jp).code,'VERIFY');assert.equal(marketAction(jp).range,null);
 const stale={...context('CONFIRMED_UPTREND'),status:{label:'STALE DATA'}};assert.equal(marketAction(stale).code,'VERIFY');
 assert.equal(marketAction({...context('CONFIRMED_UPTREND'),mode:'mock'}).range,null);
});
test('a corrupt archived action context requests verification',async()=>{
 const fetcher=async path=>{try{return {ok:true,json:async()=>{const doc=JSON.parse(await readFile(new URL('../'+path,import.meta.url),'utf8'));if(path.includes('/market-action/'))doc.outlookVersion='wrong';return doc;}};}catch{return {ok:false,status:404};}};
 const repo=await new DataRepository(fetcher).load('live'),ctx=await repo.context('daily','2026-10-05','US');
 assert.ok(ctx.actionError);assert.equal(ctx.actionMeta,null);assert.equal(marketAction({...ctx,asOf:ctx.entry.asOf}).code,'VERIFY');
});
test('chart candidates survive defensive market context without changing scores',()=>{
 const config={thresholds:{extendedPct:10,activeShortScoreDrop:8,activeBreadthDrop:10,minimumWeekly:60,marketWatch:50,emergingDaily:75},opportunity:{weeklyStrength:1}};
 const theme={quantitative:{extensionPct:2,dailyRank:2,weeklyRank:4,weeklyDelta5:3,breadthDelta5:1,setupReady:1,dailyAcceleration:80},scores:{weekly:70,leaderQuality:80},stocks:[{symbol:'NASDAQ:TEST',scores:{leader:90},quantitative:{setup:'VCP',setupReady:true,price:99,entry:100,stop:95,stage:'Stage 2'}}]};
 const frozen=JSON.stringify(theme),ctx={rows:[theme],health:0,config};
 assert.equal(researchStocks(ctx)[0].eligible,false);
 assert.equal(technicalResearchStocks(ctx,researchStocks(ctx))[0].eligible,true);
 ctx.health=null;assert.equal(technicalThemeCandidate(theme,config).eligible,true);
 assert.equal(JSON.stringify(theme),frozen);
 theme.quantitative.extensionPct=null;assert.equal(technicalThemeCandidate(theme,config).eligible,false);
});
test('saved action context uses the selected date and input versions',async()=>{
 const fetcher=async path=>{try{return {ok:true,json:async()=>JSON.parse(await readFile(new URL('../'+path,import.meta.url),'utf8'))};}catch{return {ok:false,status:404};}};
 const repo=await new DataRepository(fetcher).load('live');
 for(const market of ['US','JP']){
  const ctx=await repo.context('daily','2026-10-05',market);
  assert.equal(ctx.actionError,null);assert.equal(ctx.actionMeta.asOf,ctx.entry.asOf);
  const a=marketAction({...ctx,asOf:ctx.entry.asOf,status:{label:'ARCHIVE'}});
  assert.equal(a.state,ctx.actionMeta.markets[market].state);assert.equal(a.condition,ctx.actionMeta.markets[market].condition);
  assert.equal(a.outlookVersion,ctx.outlookMeta.evaluationVersion);
 }
});
