const LIFECYCLES=['SETUP','BREAKOUT','EXTENDED','PULLBACK','RETEST','3WT','TIGHT','ASCENDING_BASE','FAILED_BREAKOUT'];
let selectedLifecycle='all';
let forcingAll=false;

const num=text=>{
 const n=Number(String(text??'').replace(/[^0-9+\-.]/g,''));
 return Number.isFinite(n)?n:null;
};

function tone(lifecycle){
 if(['BREAKOUT','3WT','TIGHT','ASCENDING_BASE'].includes(lifecycle))return 'positive';
 if(['PULLBACK','RETEST','SETUP'].includes(lifecycle))return 'new';
 if(lifecycle==='EXTENDED')return 'warning';
 if(lifecycle==='FAILED_BREAKOUT')return 'negative';
 return 'neutral';
}

function normalizeSetupType(raw){
 const s=String(raw??'').trim();
 if(!s)return '—';
 if(/pullback|retest/i.test(s))return '—';
 return s;
}

function deriveLifecycle({setup,status,price,entry,pivotDistance}){
 const s=String(status??'').trim().toUpperCase().replace(/\s+/g,'_');
 if(LIFECYCLES.includes(s))return s;
 if(/FAILED|INVALID/.test(s))return 'FAILED_BREAKOUT';
 if(/EXTENDED/.test(s))return 'EXTENDED';
 if(/ASCENDING/.test(s))return 'ASCENDING_BASE';
 if(/3WT|THREE.*WEEK/.test(s))return '3WT';
 if(/TIGHT/.test(s))return 'TIGHT';
 if(/RETEST/.test(s))return 'RETEST';
 if(/PULLBACK/.test(s))return 'PULLBACK';
 const setupText=String(setup??'');
 if(/pullback|retest/i.test(setupText)){
  if(Number.isFinite(pivotDistance)&&Math.abs(pivotDistance)<=3)return 'RETEST';
  if(Number.isFinite(price)&&Number.isFinite(entry)&&Math.abs(100*(price/entry-1))<=3)return 'RETEST';
  return 'PULLBACK';
 }
 if(Number.isFinite(price)&&Number.isFinite(entry)&&price>=entry)return 'BREAKOUT';
 if(Number.isFinite(pivotDistance)&&pivotDistance<0)return 'BREAKOUT';
 return 'SETUP';
}

function setBadge(cell,lifecycle){
 const span=cell?.querySelector('.badge')||cell?.firstElementChild;
 if(span){span.textContent=lifecycle;span.className=`badge ${tone(lifecycle)}`;}
 else if(cell)cell.textContent=lifecycle;
}

function applyLifecycleFilter(section){
 const rows=[...section.querySelectorAll('#setup-body tr')];
 rows.forEach(row=>{
  if(!row.dataset.lifecycle)return;
  row.hidden=selectedLifecycle!=='all'&&row.dataset.lifecycle!==selectedLifecycle;
 });
 const visible=rows.filter(r=>r.dataset.lifecycle&&!r.hidden).length;
 const count=section.querySelector('#setup-count');
 if(count){
  const base=count.dataset.baseCount||count.textContent;
  count.dataset.baseCount=base;
  count.textContent=`${base} · 表示 ${visible}`;
 }
}

function lifecycleFilter(section){
 const toolbar=section.querySelector('.research-toolbar');
 if(!toolbar||toolbar.querySelector('#lifecycle-filter-ui'))return;
 const label=document.createElement('label');
 label.className='research-picker lifecycle-picker';
 label.innerHTML=`<span>Lifecycle</span><select id="lifecycle-filter-ui" aria-label="Lifecycleの絞り込み"><option value="all">すべて</option>${LIFECYCLES.map(v=>`<option value="${v}">${v}</option>`).join('')}</select>`;
 const select=label.querySelector('select');
 select.value=selectedLifecycle;
 select.addEventListener('change',()=>{selectedLifecycle=select.value;applyLifecycleFilter(section);});
 toolbar.insertBefore(label,section.querySelector('#setup-count'));
}

function enhanceSetupTable(){
 const section=document.getElementById('setups');
 if(!section)return;
 const legacyFilter=section.querySelector('#setup-filter');
 if(legacyFilter&&legacyFilter.value!=='all'&&!forcingAll){
  forcingAll=true;
  legacyFilter.value='all';
  legacyFilter.dispatchEvent(new Event('change',{bubbles:true}));
  queueMicrotask(()=>{forcingAll=false;});
  return;
 }
 if(legacyFilter?.closest('label'))legacyFilter.closest('label').style.display='none';
 const headText=section.querySelector('.section-head p');
 if(headText)headText.textContent='Setup Type（起点のチャート型）と Lifecycle（現在状態）を分離。Setup Typeは保持し、Lifecycleだけを状態遷移させる。';
 const headers=[...section.querySelectorAll('.setup-table thead th')];
 if(headers[2])headers[2].textContent='Setup Type';
 if(headers[4])headers[4].textContent='Lifecycle';
 const rows=[...section.querySelectorAll('#setup-body tr')];
 rows.forEach(row=>{
  if(row.classList.contains('empty')||row.dataset.lifecycleDecorated==='1')return;
  const c=[...row.cells];
  if(c.length<11)return;
  const rawSetup=c[2].textContent.trim();
  const rawStatus=c[4].textContent.trim();
  const price=num(c[6].textContent);
  const entry=num(c[7].textContent);
  const distance=num(c[10].textContent);
  const lifecycle=deriveLifecycle({setup:rawSetup,status:rawStatus,price,entry,pivotDistance:distance});
  const setupType=normalizeSetupType(rawSetup);
  row.dataset.lifecycle=lifecycle;
  row.dataset.lifecycleDecorated='1';
  c[2].textContent=setupType;
  if(setupType==='—')c[2].title='Legacy snapshot: 元のsetup_typeが保存されていないため未判定';
  setBadge(c[4],lifecycle);
 });
 lifecycleFilter(section);
 let note=section.querySelector('.setup-lifecycle-note');
 if(!note){
  note=document.createElement('p');
  note.className='footnote setup-lifecycle-note';
  note.textContent='Lifecycle: SETUP → BREAKOUT → EXTENDED / PULLBACK / RETEST → 3WT / TIGHT / ASCENDING_BASE。ブレイク仮説が崩れた場合は FAILED_BREAKOUT。Legacy snapshotで元のSetup Typeを復元できない場合は「—」表示とし、推測で埋めない。';
  section.querySelector('.table-scroll')?.insertAdjacentElement('afterend',note);
 }
 applyLifecycleFilter(section);
}

function enhanceStockDialog(){
 const dialog=document.getElementById('candidate-dialog');
 if(!dialog?.classList.contains('stock-analysis-dialog'))return;
 dialog.querySelectorAll('.stock-analysis-badges').forEach(group=>{
  if(group.dataset.lifecycleDecorated==='1')return;
  const badges=[...group.querySelectorAll('.stock-analysis-badge')];
  if(badges.length<3)return;
  const rawStatus=badges[0].textContent.trim();
  const rawSetup=badges[2].textContent.trim();
  const lifecycle=deriveLifecycle({setup:rawSetup,status:rawStatus});
  badges[0].textContent=lifecycle;
  badges[0].className=`stock-analysis-badge ${tone(lifecycle)}`;
  badges[0].title='Lifecycle';
  badges[2].textContent=normalizeSetupType(rawSetup);
  badges[2].title='Setup Type';
  group.dataset.lifecycleDecorated='1';
 });
}

function addStyles(){
 if(document.getElementById('setup-lifecycle-styles'))return;
 const style=document.createElement('style');
 style.id='setup-lifecycle-styles';
 style.textContent='.setup-lifecycle-note{border-top:1px solid #273544;padding-top:10px}.lifecycle-picker select{min-width:160px}';
 document.head.append(style);
}

function enhance(){addStyles();enhanceSetupTable();enhanceStockDialog();}
enhance();
new MutationObserver(enhance).observe(document.body,{childList:true,subtree:true});
