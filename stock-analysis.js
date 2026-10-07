import {analysisSelection} from './lib/stock-analysis-state.mjs';
const MANIFEST_PATH='data/stock-analysis/manifest.json';
let manifestPromise=null;
const analysisFiles=new Map();
async function analysisFile(path){if(!analysisFiles.has(path))analysisFiles.set(path,fetch(path,{cache:'no-cache'}).then(r=>{if(!r.ok)throw new Error(`analysis file: HTTP ${r.status}`);return r.json();}));return analysisFiles.get(path);}
function displayContext(){const node=document.querySelector('[data-analysis-as-of]');return {asOf:node?.dataset.analysisAsOf,mode:node?.dataset.analysisMode??'live'};}

const esc=s=>String(s??'—').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmt=(v,d=2)=>Number.isFinite(v)?Number(v).toLocaleString('en-US',{minimumFractionDigits:d,maximumFractionDigits:d}):'—';
const tone=status=>({READY:'positive',BREAKOUT:'positive',FORMING:'warning',WATCH:'neutral',PULLBACK:'new',RETEST:'new',INVALID:'negative'}[status]||'neutral');
const formatTimestamp=s=>s?String(s).replace('T',' ').replace('+09:00',' JST'):'—';
const currencyMark=c=>c==='JPY'?'¥':c==='USD'?'$':c?`${c} `:'';
const money=(v,c)=>Number.isFinite(v)?`${currencyMark(c)}${fmt(v,c==='JPY'?0:2)}`:'—';

function addStyles(){
 if(document.getElementById('stock-analysis-styles'))return;
 const style=document.createElement('style');
 style.id='stock-analysis-styles';
 style.textContent=`
 .stock-analysis-trigger{cursor:pointer;text-decoration-style:dotted!important;text-underline-offset:3px}.stock-analysis-trigger:hover{filter:brightness(1.16)}
 #candidate-dialog.stock-analysis-dialog{width:min(920px,calc(100vw - 36px));max-width:920px;max-height:88vh;padding:0;border:1px solid #2b3949;border-radius:14px;background:#111923;color:#dbe6ef;box-shadow:0 24px 80px #0009;overflow:auto}
 #candidate-dialog.stock-analysis-dialog::backdrop{background:#05080db8;backdrop-filter:blur(2px)}
 .stock-analysis-wrap{padding:24px}.stock-analysis-top{display:flex;justify-content:space-between;gap:20px;align-items:flex-start;border-bottom:1px solid #273341;padding-bottom:16px;margin-bottom:18px}.stock-analysis-top h2{margin:3px 0 4px;font-size:28px}.stock-analysis-top p{margin:0;color:#91a2b5}.stock-analysis-close{border:1px solid #34465a;background:#172230;color:#dbe6ef;border-radius:8px;padding:8px 11px;cursor:pointer}
 .stock-analysis-meta{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:9px;margin:14px 0}.stock-analysis-meta>div{background:#151f2b;border:1px solid #273544;border-radius:9px;padding:10px}.stock-analysis-meta span{display:block;font-size:11px;color:#7f91a5;text-transform:uppercase;letter-spacing:.05em}.stock-analysis-meta b{display:block;margin-top:3px;font-size:14px}
 .stock-analysis-badges{display:flex;gap:8px;flex-wrap:wrap}.stock-analysis-badge{display:inline-flex;border:1px solid #3b4a5c;border-radius:999px;padding:4px 9px;font-size:12px}.stock-analysis-badge.positive{border-color:#356f5d;color:#99d8bd}.stock-analysis-badge.warning{border-color:#755f32;color:#e1c47d}.stock-analysis-badge.negative{border-color:#764448;color:#e6a0a5}.stock-analysis-badge.new{border-color:#3c617c;color:#9ec9e6}
 .stock-analysis-summary{font-size:15px;line-height:1.75;margin:16px 0}.stock-analysis-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}.stock-analysis-card{background:#141d27;border:1px solid #273544;border-radius:10px;padding:14px}.stock-analysis-card h3{font-size:13px;letter-spacing:.04em;text-transform:uppercase;margin:0 0 9px;color:#a9b8c7}.stock-analysis-card ul{margin:0;padding-left:20px}.stock-analysis-card li{margin:6px 0;line-height:1.55}.stock-analysis-action{margin:14px 0;padding:14px;border-left:3px solid #c5a966;background:#1a2026}.stock-analysis-action strong{display:block;margin-bottom:4px}.stock-analysis-links{display:flex;gap:10px;align-items:center;margin-top:15px}.stock-analysis-links a{color:#a8ccea}.stock-analysis-history{margin-top:22px;border-top:1px solid #273341;padding-top:18px}.stock-analysis-history h3{margin:0 0 10px}.stock-analysis-history details{border:1px solid #283645;border-radius:9px;margin:8px 0;background:#121b25}.stock-analysis-history summary{cursor:pointer;padding:11px 13px}.stock-analysis-history .history-body{padding:0 13px 13px}.stock-analysis-empty{padding:22px 2px;color:#9babbc;line-height:1.7}
 @media(max-width:700px){.stock-analysis-meta{grid-template-columns:1fr 1fr}.stock-analysis-grid{grid-template-columns:1fr}.stock-analysis-wrap{padding:17px}.stock-analysis-top h2{font-size:23px}}
 `;
 document.head.append(style);
}

async function manifest(){
 if(!manifestPromise)manifestPromise=fetch(MANIFEST_PATH,{cache:'no-cache'}).then(r=>{if(!r.ok)throw new Error(`analysis manifest: HTTP ${r.status}`);return r.json();});
 return manifestPromise;
}

async function loadAnalysis(symbol){
 const m=await manifest();
 const record=m.symbols?.[symbol];
 if(!record)return null;
 const analyses=[];
 let legacy=null;
 if(record.path){legacy=await analysisFile(record.path);if(legacy.symbol!==symbol)throw new Error('銘柄分析ファイルのsymbolが一致しません');analyses.push(...(legacy.analyses??[]));}
 for(const entry of record.entries??[]){
  const batch=await analysisFile(entry.path);
  const item=batch.symbols?.[symbol];
  if(batch.mode!=='live'||batch.schemaVersion!==2||item?.id!==entry.id||item?.generatedAt!==entry.generatedAt||item?.analysisDate!==entry.analysisDate||item?.marketDataAsOf!==entry.marketDataAsOf)throw new Error('分析履歴のID・日時・モードが不一致');
  analyses.push(item);
 }
 return {...legacy,symbol,market:record.market??legacy?.market,currency:record.market==='JP'?'JPY':legacy?.currency??'USD',name:legacy?.name??symbol,coverageStatus:record.coverageStatus,coverageReason:record.coverageReason,analyses};
}

function pivotLabel(p,currency){
 if(!p)return '—';
 if(Number.isFinite(p.low)&&Number.isFinite(p.high))return `${money(p.low,currency)} – ${money(p.high,currency)}`;
 if(Number.isFinite(p.value))return money(p.value,currency);
 return esc(p.value===null?'未保存':p.label||'—');
}

function list(items){return `<ul>${(items||[]).map(x=>`<li>${esc(x)}</li>`).join('')||'<li>未記録</li>'}</ul>`;}

function entryBody(a,defaultCurrency){
 const currency=a.currency||defaultCurrency;
 return `<div class="stock-analysis-badges" data-setup-state="${esc(JSON.stringify({setup_type:a.setup_type,lifecycle:a.lifecycle,status:a.status,setup:a.setup,price:a.price,entry:a.entry,readiness:a.readiness,setupConfirmed:a.setupConfirmed,lifecycleConfirmed:a.lifecycleConfirmed,lifecycleSource:a.lifecycleSource,lifecycleCandidate:a.lifecycleCandidate}))}"><span class="stock-analysis-badge ${tone(a.status)}">${esc(a.status)}</span><span class="stock-analysis-badge">${esc(a.stage)}</span><span class="stock-analysis-badge">${esc(a.setup)}</span></div>
 <div class="stock-analysis-meta"><div><span>Analysis Date</span><b>${esc(a.analysisDate)}</b></div><div><span>Market Data As Of</span><b>${esc(a.marketDataAsOf)}</b></div><div><span>Price</span><b>${money(a.price,currency)}</b></div><div><span>Pivot</span><b>${pivotLabel(a.pivot,currency)}</b></div></div>
 <p class="stock-analysis-summary">${esc(a.summary)}</p>
 <div class="stock-analysis-grid"><section class="stock-analysis-card"><h3>Ideal Path</h3>${list(a.idealPath)}</section><section class="stock-analysis-card"><h3>Bullish Confirmation</h3>${list(a.confirmation)}</section><section class="stock-analysis-card"><h3>Invalidation</h3>${list(a.invalidation)}</section><section class="stock-analysis-card"><h3>Levels / Readiness</h3><p>Entry Readiness: <b>${Number.isFinite(a.entryReadiness)?fmt(a.entryReadiness,0)+'/100':'—'}</b></p><p>Pivot Distance: <b>${Number.isFinite(a.distanceToPivotPct)?fmt(a.distanceToPivotPct,1)+'%':'—'}</b></p><p>Structural Stop: <b>${money(a.structuralStop,currency)}</b></p></section></div>
 <div class="stock-analysis-action"><strong>Next Action · ${esc(a.action?.label)}</strong><span>${esc(a.action?.detail)}</span></div>
 <small>分析 ${esc(a.id??'Legacy')} · ${esc(a.evaluationVersion??'手動メモ')} · ${esc(a.dataQuality?.status??'保存分析')} · 生成時刻 ${esc(formatTimestamp(a.generatedAt))} · ${esc(a.source?.label||'Source未記録')}${a.changeReason?` · ${esc(a.changeReason)}`:''}</small>`;
}

function renderDialog(symbol,doc,latestMode=false){
 const dialog=document.getElementById('candidate-dialog');
 if(!dialog)return;
 dialog.classList.add('stock-analysis-dialog');
 if(!doc){
  dialog.innerHTML=`<div class="stock-analysis-wrap"><div class="stock-analysis-top"><div><span class="eyebrow">STOCK ANALYSIS</span><h2>${esc(symbol.split(':').at(-1))}</h2><p>${esc(symbol)}</p></div><button class="stock-analysis-close">閉じる ×</button></div><div class="stock-analysis-empty">この銘柄の保存済み分析はまだありません。分析が作成されると、分析日・市場データ日・Ideal Path・無効条件・過去ログがここに追記されます。</div><div class="stock-analysis-links"><a data-external-chart target="_blank" rel="noopener" href="https://www.tradingview.com/chart/?symbol=${encodeURIComponent(symbol)}">TradingViewで開く ↗</a></div></div>`;
 }else{
  const selection=analysisSelection(doc,{...displayContext(),latest:latestMode});
  const latest=selection.current;
  const history=selection.history;
  const entries=[latest,...history].filter(Boolean);
  const context=displayContext();
  dialog.innerHTML=`<div class="stock-analysis-wrap"><div class="stock-analysis-top"><div><span class="eyebrow">STOCK ANALYSIS · ${esc(doc.market)}</span><h2>${esc(doc.symbol.split(':').at(-1))} · ${esc(doc.name)}</h2><p>${esc(latest?.theme??doc.theme??'Theme未設定')} · ${latestMode?'最新分析を表示':'表示日の時点の分析'} · ${esc(context.asOf)} · ${entries.length}件</p></div><button class="stock-analysis-close">閉じる ×</button></div><p class="stock-analysis-summary">${latestMode?'最新分析はページの市場評価日と異なる場合があります。':selection.status==='DEMO'?'DemoではObserved分析を表示しません。':'その日の終了時点（JST）までに保存された分析を表示。'} ${latestMode?esc(doc.coverageReason??''):''}</p>${context.mode==='live'?`<button class="stock-analysis-toggle outline-btn">${latestMode?'表示日の分析に戻る':'最新分析を別表示'}</button>`:''}${latest?entryBody(latest,doc.currency):`<div class="stock-analysis-empty">${selection.status==='DEMO'?'Demo分析は未保存です。':'この表示時点で利用できる保存分析はありません。'}${selection.hidden?' 後日の分析は「最新分析を別表示」で確認できます。':''}</div>`}<div class="stock-analysis-links"><a data-external-chart target="_blank" rel="noopener" href="https://www.tradingview.com/chart/?symbol=${encodeURIComponent(symbol)}">TradingViewで開く ↗</a><span>ログは上書きせず追記保存</span></div><section class="stock-analysis-history"><h3>Analysis History</h3>${history.length?history.map(a=>`<details><summary><b>${esc(a.analysisDate)}</b> · ${esc(a.status)} · ${esc(a.setup)} · Data ${esc(a.marketDataAsOf)}</summary><div class="history-body">${entryBody(a,doc.currency)}</div></details>`).join(''):'<p class="stock-analysis-empty">この表示時点の過去ログはありません。</p>'}</section></div>`;
 }
 dialog.querySelector('.stock-analysis-close')?.addEventListener('click',()=>dialog.close());
 dialog.querySelector('.stock-analysis-toggle')?.addEventListener('click',()=>renderDialog(symbol,doc,!latestMode));
 if(!dialog.open)dialog.showModal();
}

async function openAnalysis(symbol,latestMode=false){
 const dialog=document.getElementById('candidate-dialog');
 if(!dialog)return;
 dialog.classList.add('stock-analysis-dialog');
 dialog.innerHTML=`<div class="stock-analysis-wrap"><div class="stock-analysis-top"><div><span class="eyebrow">STOCK ANALYSIS</span><h2>${esc(symbol.split(':').at(-1))}</h2><p>分析履歴を読み込み中…</p></div><button class="stock-analysis-close">閉じる ×</button></div></div>`;
 dialog.querySelector('.stock-analysis-close')?.addEventListener('click',()=>dialog.close());
 if(!dialog.open)dialog.showModal();
 try{renderDialog(symbol,displayContext().mode==='mock'?{symbol,market:'Demo',analyses:[]}:await loadAnalysis(symbol),latestMode);}
 catch(err){dialog.innerHTML=`<div class="stock-analysis-wrap"><div class="stock-analysis-top"><div><span class="eyebrow">STOCK ANALYSIS</span><h2>${esc(symbol.split(':').at(-1))}</h2><p>分析履歴を読み込めませんでした</p></div><button class="stock-analysis-close">閉じる ×</button></div><div class="stock-analysis-empty">${esc(err.message)}</div></div>`;dialog.querySelector('.stock-analysis-close')?.addEventListener('click',()=>dialog.close());}
}

function symbolFromTVLink(a){
 try{return new URL(a.href,location.href).searchParams.get('symbol');}catch{return null;}
}

function addAnalysisIndex(){
 const section=document.getElementById('setups');
 if(!section||document.getElementById('monitor-analysis-index')||displayContext().mode!=='live')return;
 const holder=document.createElement('details');holder.id='monitor-analysis-index';
 holder.innerHTML='<summary>最新の監視銘柄一覧・分析を別表示</summary><p>この一覧の監視日と市場評価日は別です。</p><div class="analysis-index-body"></div>';
 section.append(holder);
 holder.addEventListener('toggle',async()=>{
  if(!holder.open||holder.dataset.loaded)return;
  holder.dataset.loaded='true';
  try{
   const m=await manifest();if(!holder.isConnected)return;
   const market=document.querySelector('[aria-current="page"][href*="japan.html"]')?'JP':'US';
   const rows=Object.entries(m.symbols??{}).filter(([,r])=>r.market===market);
   const body=holder.querySelector('.analysis-index-body');
   body.innerHTML=`<p class="footnote">監視リスト確認日 ${esc(m.universeAsOf??'未保存')} · 保存 ${esc(formatTimestamp(m.updatedAt))} · 現在の対象 ${rows.filter(([,r])=>r.coverageStatus!=='LEGACY_ONLY').length}銘柄・過去保存 ${rows.filter(([,r])=>r.coverageStatus==='LEGACY_ONLY').length}銘柄</p><label>銘柄を検索 <input class="analysis-index-search" type="search" placeholder="NVDA / 7011"></label><p class="analysis-index-count"></p><div class="table-scroll"><table><thead><tr><th>銘柄</th><th>分析の収集状況</th><th>市場データ日</th></tr></thead><tbody class="analysis-index-rows"></tbody></table></div>`;
   const drawRows=()=>{const term=body.querySelector('input').value.trim().toUpperCase();const filtered=rows.filter(([s])=>s.includes(term));body.querySelector('.analysis-index-count').textContent=`${filtered.length}件中、先頭50件を表示`;body.querySelector('tbody').innerHTML=filtered.slice(0,50).map(([s,r])=>`<tr><td><button class="text-button" data-latest-stock="${esc(s)}">${esc(s)}</button></td><td>${esc(r.coverageStatus==='LEGACY_ONLY'?'過去の保存分析（現在Universe外）':r.coverageStatus==='UNANALYZED'?'未分析・OHLCV不足':r.coverageStatus==='OLDER_INPUT'?'保存済みの旧市場データから分析':'保存分析あり')}</td><td>${esc(r.marketDataAsOf??'未取得')}</td></tr>`).join('');};
   body.querySelector('input').addEventListener('input',drawRows);drawRows();
  }catch(error){holder.querySelector('.analysis-index-body').textContent=`一覧を取得できません: ${error.message}`;delete holder.dataset.loaded;}
 });
}

function decorate(){
 addAnalysisIndex();
 document.querySelectorAll('a[href*="tradingview.com/chart/?symbol="]').forEach(a=>{if(a.dataset.externalChart)return;a.classList.add('stock-analysis-trigger');a.title='銘柄分析を見る';});
 document.querySelectorAll('td.ticker').forEach(td=>{if(td.querySelector('a'))return;const text=td.textContent.trim();if(/^[A-Z0-9_.-]+:[A-Z0-9_.-]+$/.test(text)){td.classList.add('stock-analysis-trigger');td.title='銘柄分析を見る';td.dataset.stockSymbol=text;}});
}

addStyles();
decorate();
const app=document.getElementById('app');
if(app)new MutationObserver(decorate).observe(app,{childList:true,subtree:true});

document.addEventListener('click',e=>{
 const latest=e.target.closest('[data-latest-stock]');if(latest){e.preventDefault();openAnalysis(latest.dataset.latestStock,true);return;}
 const external=e.target.closest('a[data-external-chart]');if(external)return;
 const a=e.target.closest('a[href*="tradingview.com/chart/?symbol="]');
 if(a){const symbol=symbolFromTVLink(a);if(symbol){e.preventDefault();openAnalysis(symbol);}return;}
 const td=e.target.closest('td[data-stock-symbol]');
 if(td){e.preventDefault();openAnalysis(td.dataset.stockSymbol);}
});
