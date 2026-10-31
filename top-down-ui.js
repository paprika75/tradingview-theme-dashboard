import {DataRepository} from './lib/data.mjs';
import {marketForPage} from './lib/routes.mjs';
import {topDownDecision} from './lib/top-down.mjs';

const esc=s=>String(s??'—').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmt=(v,d=1)=>Number.isFinite(v)?v.toLocaleString('en-US',{minimumFractionDigits:d,maximumFractionDigits:d}):'—';
const ticker=s=>esc(s?.split(':')[1]??s);
const badge=(text,tone='neutral')=>`<span class="badge ${tone}">${esc(text)}</span>`;
const actionTone=code=>code==='CHECK_ENTRY'?'positive':code==='WAIT'?'negative':code==='LIMIT'?'warning':'neutral';
const lifecycleTone=value=>value==='FAILED_BREAKOUT'?'negative':['EXTENDED'].includes(value)?'warning':['BREAKOUT','PULLBACK','RETEST','3WT','TIGHT','ASCENDING_BASE','SETUP'].includes(value)?'positive':'neutral';
const setupType=row=>row.state.setupType==='UNASSESSED'?'—':row.state.setupType;
const chartLink=stock=>`<a class="ticker" href="https://www.tradingview.com/chart/?symbol=${encodeURIComponent(stock.symbol)}" target="_blank" rel="noopener">${ticker(stock.symbol)} ↗</a>`;
const themeLink=(state,theme)=>`<a class="theme-link" href="theme.html?${new URLSearchParams({market:state.market.toLowerCase(),period:state.period,date:state.key,data:state.mode,id:theme.id})}">${esc(theme.name)} <span class="arrow">↗</span></a>`;

function marketState(){
 const params=new URLSearchParams(location.search);
 return {
  mode:params.get('data')==='mock'?'mock':'live',
  market:marketForPage(location.pathname,params.get('market')||''),
  period:params.get('period')==='weekly'?'weekly':'daily',
  key:params.get('date')||null,
 };
}

function stageCard(index,title,value,detail,tone='neutral'){
 return `<article class="outlook-index"><div class="outlook-title"><h3>${esc(index)} · ${esc(title)}</h3>${badge(value,tone)}</div><p>${esc(detail)}</p></article>`;
}

function renderTopDown(ctx,state){
 const d=topDownDecision(ctx);
 const action=d.action;
 const stageHTML=[
  stageCard('01','MARKET',action.label,action.condition,actionTone(action.code)),
  stageCard('02','THEME',`${d.counts.themes}候補`,d.counts.themes?'既存Theme ScoreとBreadthから技術候補を抽出':'技術条件を満たすテーマなし',d.counts.themes?'positive':'neutral'),
  stageCard('03','INDUSTRY / PEER',d.industryConnected?`${d.counts.peerGroups}群`:'未接続',d.industryConnected?'保存済み業種・Peer Groupを使用':'現行snapshotに独立Industry / Peer Groupフィールドなし',d.industryConnected?'positive':'warning'),
  stageCard('04','STOCK LEADER',`${d.counts.leaders}銘柄`,'候補テーマ内のTop 3かつStage 2を優先',d.counts.leaders?'positive':'neutral'),
  stageCard('05','SETUP',`${d.counts.setups}銘柄`,'VCP / CWH / Base Breakout等。Setup TypeとLifecycleは別軸',d.counts.setups?'positive':'neutral'),
  stageCard('06','PIVOT / ENTRY',`${d.counts.entryCandidates}候補`,'Theme × Stage 2 × Ready × Entry/Stop × 非Extended。Pivotは保存値のみ表示',d.counts.entryCandidates?'positive':'neutral'),
 ].join('');
 const rows=d.rows.map(r=>{
  const q=r.stock.quantitative;
  const risk=Number.isFinite(q.entry)&&q.entry>0&&Number.isFinite(q.stop)&&q.stop>0?100*(1-q.stop/q.entry):null;
  return `<tr><td class="sticky-theme">${themeLink(state,r.theme)}</td><td>${esc(r.peerGroup??'—')}</td><td>${chartLink(r.stock)}</td><td>${badge(r.technical.label,r.technical.eligible?'positive':r.technical.extended?'warning':'neutral')}</td><td>${fmt(r.stock.scores.leader)}</td><td>${badge(q.stage,q.stage==='Stage 2'?'positive':'neutral')}</td><td>${esc(setupType(r))}</td><td>${badge(r.state.lifecycle==='UNASSESSED'?'未判定':r.state.lifecycle,lifecycleTone(r.state.lifecycle))}</td><td>${fmt(q.pivot,2)}</td><td>${fmt(q.entry,2)}</td><td>${fmt(q.stop,2)}</td><td>${fmt(risk)}</td><td>${badge(r.eligible?'CANDIDATE':r.extended?'EXTENDED':'WATCH',r.eligible?'positive':r.extended?'warning':'neutral')}</td></tr>`;
 }).join('');
 const exposure=action.range?`${action.range[0]}–${action.range[1]}%`:'未判定';
 return `<section class="panel" id="top-down-path" data-top-down-signature="${esc([state.mode,state.market,state.period,state.key,ctx.entry.asOf].join('|'))}">
  <div class="section-head"><div><span class="section-index">00</span><h2>TOP-DOWN DECISION PATH</h2><p>Market → Theme → Industry / Peer → Stock Leader → Setup → Pivot / Entry。上位レイヤーで候補を絞り、下位レイヤーで実行条件を確認する。</p></div>${badge(action.label,actionTone(action.code))}</div>
  <div class="outlook-overview"><div><span class="eyebrow">MARKET GATE / ${esc(ctx.entry.asOf)}</span><h3>${esc(action.label)}</h3><p>${esc(action.condition)}</p><small>技術候補のランキングは市場判定で消さず、実行可否だけをMarket Gateで制約します。自動Buyは行いません。</small></div><aside><span>参考投資比率</span><strong>${esc(exposure)}</strong><small>${esc(action.state)}</small></aside></div>
  <div class="outlook-index-grid">${stageHTML}</div>
  <div class="outlook-subhead"><h3>TOP-DOWN SHORTLIST</h3><p>上位ThemeからLeader・Setupへ降りる。Industry / Peerはデータ接続後に同じ経路へ挿入する。</p></div>
  <div class="table-scroll research-scroll"><table class="research-table"><thead><tr>${['Theme','Industry / Peer','Symbol','Theme','Leader Score','Stage','Setup Type','Lifecycle','Pivot','Entry','Stop','Risk %','Technical'].map(n=>`<th>${n}</th>`).join('')}</tr></thead><tbody>${rows||'<tr><td colspan="13" class="empty">現在の技術条件を通るTop-Down候補はありません。市場判定とTheme / Setupの保存評価を確認してください。</td></tr>'}</tbody></table></div>
  <p class="footnote">Marketは行動制約、Themeは相対強度・Breadth・Ready Setup、StockはLeader ScoreとStage、Setupは確認済み状態と価格水準を別々に扱います。Industry / Peer Groupは現状未接続で、テーマ名から推測しません。Pivot未保存時もEntryをPivotとして代用しません。</p>
 </section>`;
}

let renderToken=0;
async function mount(){
 const target=document.querySelector('#market-health');
 if(!target)return;
 const state=marketState();
 const workspace=document.querySelector('.workspace');
 const visibleAsOf=workspace?.dataset.analysisAsOf??'';
 const signature=[state.mode,state.market,state.period,state.key||'',visibleAsOf].join('|');
 const existing=document.querySelector('#top-down-path');
 if(existing?.dataset.topDownSignature===signature)return;
 existing?.remove();
 const token=++renderToken;
 try{
  const repo=new DataRepository();
  await repo.load(state.mode);
  if(!state.key||!repo.manifest[state.period].some(e=>e.key===state.key))state.key=repo.manifest[state.period].at(-1).key;
  const ctx=await repo.context(state.period,state.key,state.market);
  if(token!==renderToken||!document.querySelector('#market-health'))return;
  document.querySelector('#market-health').insertAdjacentHTML('beforebegin',renderTopDown(ctx,state));
  const nav=document.querySelector('.section-nav');
  if(nav&&!nav.querySelector('a[href="#top-down-path"]'))nav.insertAdjacentHTML('afterbegin','<a href="#top-down-path"><small>00</small>Top-Down</a>');
 }catch(error){
  if(token!==renderToken||!document.querySelector('#market-health'))return;
  document.querySelector('#market-health').insertAdjacentHTML('beforebegin',`<section class="panel" id="top-down-path"><div class="padded"><h2>TOP-DOWN DECISION PATH</h2><p class="load-warning">Top-Down表示を生成できません: ${esc(error.message)}</p></div></section>`);
 }
}

const root=document.querySelector('#app');
if(root){
 const observer=new MutationObserver(()=>queueMicrotask(mount));
 observer.observe(root,{childList:true,subtree:true});
 mount();
}
