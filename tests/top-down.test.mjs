import test from 'node:test';
import assert from 'node:assert/strict';
import {peerGroupForStock,topDownDecision} from '../lib/top-down.mjs';

const config={
 thresholds:{
  marketHealthy:70,marketWatch:50,strongTheme:80,emergingDaily:75,minimumWeekly:60,
  extendedPct:10,activeShortScoreDrop:8,activeBreadthDrop:10,activeMediumScoreDrop:12,failedBreakoutRate:.4,
 },
 opportunity:{weeklyStrength:.25,dailyAcceleration:.20,breadth:.15,leaderQuality:.15,setupAvailability:.15,marketHealth:.10},
};

function stock(symbol,leader,quantitative={}){
 return {symbol,scores:{leader},quantitative:{
  stage:'Stage 2',setupReady:true,setup:'VCP',setup_type:'VCP',lifecycle:'SETUP',lifecycleSource:'REGISTRY',
  price:100,entry:101,stop:95,pivot:101,extensionPct:0,rs:90,relativeVolume:1.2,
  ...quantitative,
 }};
}

function theme(id,name,{eligible=true,stocks=null}={}){
 return {
  id,name,
  quantitative:{
   dailyRank:eligible?1:9,weeklyRank:eligible?2:8,dailyAcceleration:eligible?82:40,above50:eligible?78:45,
   setupReady:eligible?2:0,extensionPct:eligible?3:12,weeklyDelta5:eligible?2:-10,breadthDelta5:eligible?4:-12,
  },
  scores:{daily:eligible?86:55,weekly:eligible?84:52,leaderQuality:eligible?88:60},
  stocks:stocks??[
   stock('NASDAQ:AAA',94),
   stock('NASDAQ:AAB',88,{setup:null,setup_type:null,pivot:null,entry:null,stop:null,setupReady:false}),
  ],
 };
}

function context(outlookStatus='CONFIRMED_UPTREND'){
 const asOf='2026-10-05';
 return {
  mode:'live',marketCode:'US',entry:{asOf},health:72,config,
  status:{label:'OBSERVED DATA'},
  outlook:{status:outlookStatus,reasons:[],indices:[]},
  outlookMeta:{asOf,mode:'live',evaluationVersion:'1.0.0-index-outlook'},
  exposure:null,exposureMeta:null,actionMeta:null,actionError:null,
  rows:[theme('ai-infra','AI Infrastructure'),theme('weak-theme','Weak Theme',{eligible:false})],
 };
}

test('top-down path narrows theme to leaders, setup and pivot without auto-buy',()=>{
 const result=topDownDecision(context());
 assert.equal(result.action.code,'CHECK_ENTRY');
 assert.equal(result.counts.themes,1);
 assert.equal(result.counts.focusedThemes,1);
 assert.equal(result.counts.leaders,2);
 assert.equal(result.counts.setups,1);
 assert.equal(result.counts.entryCandidates,1);
 assert.equal(result.counts.pivotReady,1);
 assert.equal(result.rows[0].theme.id,'ai-infra');
 assert.equal(result.rows[0].state.setupType,'VCP');
 assert.equal(result.rows[0].state.lifecycle,'SETUP');
 assert.equal(result.automaticBuy,false);
});

test('market correction constrains action but does not erase technical shortlist',()=>{
 const result=topDownDecision(context('MARKET_IN_CORRECTION'));
 assert.equal(result.action.code,'WAIT');
 assert.equal(result.counts.themes,1);
 assert.equal(result.counts.entryCandidates,1);
 assert.equal(result.automaticBuy,false);
});

test('peer group is read only from explicit stock data and never inferred from theme narrative',()=>{
 assert.equal(peerGroupForStock({quantitative:{peerGroup:'Semiconductor Equipment'}}),'Semiconductor Equipment');
 assert.equal(peerGroupForStock({quantitative:{industry:'Electrical Equipment'}}),'Electrical Equipment');
 assert.equal(peerGroupForStock({quantitative:{}}),null);
 assert.equal(peerGroupForStock({name:'AI Semiconductor Leader',quantitative:{}}),null);
});

test('missing pivot stays missing even when entry exists',()=>{
 const ctx=context();
 ctx.rows[0].stocks[0].quantitative.pivot=null;
 const result=topDownDecision(ctx);
 assert.equal(result.counts.entryCandidates,1);
 assert.equal(result.counts.pivotReady,0);
 assert.equal(result.rows[0].stock.quantitative.entry,101);
 assert.equal(result.rows[0].stock.quantitative.pivot,null);
});
