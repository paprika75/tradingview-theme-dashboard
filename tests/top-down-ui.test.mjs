import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {runInNewContext} from 'node:vm';

// Run the actual entry module against an observer-driven DOM double. Network
// timing is controlled so failures and overlapping renders stay deterministic.
const source=(await readFile(new URL('../top-down-ui.js',import.meta.url),'utf8'))
 .replace(/^import .*;\n/gm,'');
const deferred=()=>{
 let resolve,reject;
 const promise=new Promise((yes,no)=>{resolve=yes;reject=no;});
 return {promise,resolve,reject};
};

function harness({market='us',date='2026-10-05',load=async()=>{},context}={}){
 const tasks=[],loads=[],contexts=[],insertions=[];
 let notify=()=>{},panel=null,targetPresent=true;
 const root={},workspace={dataset:{analysisAsOf:'2026-10-05'}};
 const location={pathname:`/${market==='us'?'us':'japan'}.html`,search:`?data=live&date=${date}`};
 const target={insertAdjacentHTML(position,html){
  assert.equal(position,'beforebegin');
  insertions.push(html);
  panel={html,dataset:{topDownSignature:html.match(/data-top-down-signature="([^"]*)"/)?.[1]},
   remove(){panel=null;notify();}};
  notify();
 }};
 class DataRepository{
  manifest={daily:[{key:'2026-10-05'}],weekly:[{key:'2026-W40'}]};
  async load(mode){loads.push(mode);return load(mode);}
  async context(period,key,market){
   contexts.push({period,key,market});
   return context?context(period,key,market):{entry:{asOf:'2026-10-05'}};
  }
 }
 const document={querySelector(selector){
  return ({'#app':root,'.workspace':workspace,'#market-health':targetPresent?target:null,
   '#top-down-path':panel,'.section-nav':null})[selector]??null;
 }};
 runInNewContext(source,{
  document,location,URLSearchParams,DataRepository,
  marketForPage:path=>path.includes('japan')?'JP':'US',
  topDownDecision:()=>({action:{code:'WAIT',label:'WAIT',condition:'Review',state:'UNASSESSED',range:null},
   counts:{themes:0,leaders:0,setups:0,entryCandidates:0,peerGroups:0},rows:[],industryConnected:false}),
  MutationObserver:class{constructor(callback){notify=callback;}observe(){}},
  queueMicrotask:callback=>tasks.push(callback),
 });
 return {
  loads,contexts,insertions,root,target,location,workspace,
  get panel(){return panel;},
  mutate(){notify();},
  setTarget(present){targetPresent=present;notify();},
  async settle(){
   let executed=0;
   for(let turn=0;turn<30;turn++){
    await Promise.resolve();
    while(tasks.length){
     assert.ok(++executed<100,'observer must settle without a retry loop');
     tasks.shift()();
    }
   }
  },
 };
}

for(const market of ['us','jp']){
 test(`${market}: persistent load failure renders once despite observer notifications`,async()=>{
  const h=harness({market,load:async()=>{throw Error('<offline>');}});
  await h.settle();
  for(let i=0;i<5;i++){h.mutate();await h.settle();}
  assert.equal(h.loads.length,1);
  assert.equal(h.insertions.length,1);
  assert.match(h.panel.html,/&lt;offline&gt;/);
  assert.match(h.panel.dataset.topDownSignature,new RegExp(`live\\|${market==='us'?'US':'JP'}\\|daily`));
 });
}

test('pending request is shared across unrelated DOM updates',async()=>{
 const wait=deferred();
 const h=harness({load:()=>wait.promise});
 for(let i=0;i<5;i++){h.mutate();await h.settle();}
 assert.equal(h.loads.length,1);
 wait.resolve();await h.settle();
 assert.equal(h.insertions.length,1);
 assert.match(h.panel.html,/TOP-DOWN SHORTLIST/);
});

test('date/market context change retries a failed load and recovers',async()=>{
 let fail=true;
 const h=harness({load:async()=>{if(fail)throw Error('offline');}});
 await h.settle();
 fail=false;
 h.location.pathname='/japan.html';
 h.location.search='?data=live&date=2026-10-05&period=weekly';
 h.workspace.dataset.analysisAsOf='2026-10-02';
 h.mutate();await h.settle();
 assert.equal(h.loads.length,2);
 assert.equal(h.contexts[0].market,'JP');
 assert.equal(h.contexts[0].period,'weekly');
 assert.equal(h.contexts[0].key,'2026-W40');
 assert.match(h.panel.html,/TOP-DOWN SHORTLIST/);
 h.mutate();await h.settle();
 assert.equal(h.loads.length,2);
});

test('missing/invalid URL date falls back without remounting the successful panel',async()=>{
 for(const date of ['', 'not-a-snapshot']){
  const h=harness({date});
  await h.settle();h.mutate();await h.settle();
  assert.equal(h.loads.length,1);
  assert.equal(h.contexts[0].key,'2026-10-05');
  assert.equal(h.insertions.length,1);
 }
});

for(const lateFailure of [false,true]){
 test(`old ${lateFailure?'failure':'success'} cannot overwrite newer context`,async()=>{
  const old=deferred();let calls=0;
  const h=harness({context:()=>++calls===1?old.promise:{entry:{asOf:'2026-10-05'}}});
  await h.settle();
  h.location.pathname='/japan.html';h.mutate();await h.settle();
  const current=h.panel;
  if(lateFailure)old.reject(Error('old failure'));else old.resolve({entry:{asOf:'2026-10-05'}});
  await h.settle();
  assert.equal(h.panel,current);
  assert.equal(h.loads.length,2);
  assert.equal(h.insertions.length,1);
  assert.match(h.panel.dataset.topDownSignature,/live\|JP/);
 });
}

test('removing Overview invalidates in-flight work even if it returns before the request',async()=>{
 const old=deferred();let calls=0;
 const h=harness({context:()=>++calls===1?old.promise:{entry:{asOf:'2026-10-05'}}});
 await h.settle();
 h.setTarget(false);await h.settle();
 h.setTarget(true);await h.settle();
 const current=h.panel;
 old.resolve({entry:{asOf:'2026-10-05'}});await h.settle();
 assert.equal(h.panel,current);
 assert.equal(h.loads.length,2);
 assert.equal(h.insertions.length,1);
});

test('context failure remains stable and a changed visible date can retry',async()=>{
 const h=harness({context:async()=>{throw Error('context unavailable');}});
 await h.settle();h.mutate();await h.settle();
 assert.equal(h.loads.length,1);
 h.workspace.dataset.analysisAsOf='2026-10-06';h.mutate();await h.settle();
 assert.equal(h.loads.length,2);
 assert.equal(h.insertions.length,2);
 assert.match(h.panel.html,/context unavailable/);
});
