// Non-browser regression checks using a small DOM stub. Does not verify layout.
const vm = require('node:vm');
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const root = path.resolve(__dirname,'..');
const elements = new Map();
const el = id => {if(!elements.has(id))elements.set(id,{innerHTML:'',textContent:'',classList:{toggle(){}},querySelector:()=>({})});return elements.get(id);};
const context = {URLSearchParams,console,location:{search:'',pathname:'/index.html'},history:{replaceState(){}},document:{querySelector:el,querySelectorAll:()=>[]},fetch:async url=>({ok:true,json:async()=>JSON.parse(fs.readFileSync(path.join(root,url),'utf8'))})};
vm.createContext(context);
const source=fs.readFileSync(path.join(root,'app.js'),'utf8').replace(/start\(\);\s*$/, 'globalThis.ready=start(); globalThis.api={state,rows,current,counterpart,render,overview,details,historyPage,about,chart,tableBody,params,esc};');
vm.runInContext(source,context);
(async()=>{
 await context.ready;
 const a=context.api;
 assert.equal(a.rows().length,33);
 assert.match(el('#app').innerHTML,/DEMO DATA/);
 assert.match(el('#ranking-body').innerHTML,/AI計算基盤/);
 a.state.search='NASDAQ:MU';a.tableBody();assert.match(el('#result-count').textContent,/1 \/ 33/);
 a.state.search='no-such-symbol';a.tableBody();assert.match(el('#ranking-body').innerHTML,/該当するテーマはありません/);
 a.state.search='';a.state.filter='strong';a.tableBody();assert.equal((el('#ranking-body').innerHTML.match(/<tr>/g)||[]).length,a.rows().filter(t=>t.score>=80).length);
 a.state.filter='improving';a.tableBody();assert.equal((el('#ranking-body').innerHTML.match(/<tr>/g)||[]).length,a.rows().filter(t=>t.rankChange>0).length);
 a.state.key='2026-09-18';assert.equal(a.counterpart().key,'2026-W38');assert.ok(!a.chart(a.rows().slice(0,3).map(t=>t.id)).includes('10-01'));
 a.state.period='weekly';a.state.key='2026-W32';assert.equal(a.counterpart(),null);assert.match(a.historyPage(),/2026-W32/);
 a.state.period='daily';a.state.key='2026-10-01';a.state.market='JP';assert.equal(a.rows().length,18);
 a.params.set('id',a.rows()[0].id);assert.match(a.details(),/構成銘柄とLeader比較/);assert.match(a.details(),/tradingview\.com\/chart/);
 a.state.selected=a.rows().slice(0,4).map(t=>t.id);assert.match(a.historyPage(),/disabled/);
 assert.match(a.about(),/厳密な固定スコアは未実装/);
 assert.equal(a.esc('<img src=x>'),'&lt;img src=x&gt;');
 // The offline HTML must retain all data and local navigation, without fetch.
 const offline=fs.readFileSync(path.join(root,'preview.html'),'utf8');
 assert.ok(offline.includes('const FIXTURES='));assert.ok(!offline.includes('await fetch('));assert.ok(offline.includes('hashchange'));
 console.log('PASS: markets, search, filters, archive date bounds, detail, history selection, escaping, offline bundle (non-browser checks).');
})().catch(e=>{console.error(e);process.exitCode=1;});
