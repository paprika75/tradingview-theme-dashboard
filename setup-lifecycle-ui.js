import {setupState,lifecycleTone} from './lib/setup-state.mjs';

// Overview rows use quantitative data directly; legacy dialogs keep readiness.
function enhanceStockDialog(){
 const dialog=document.getElementById('candidate-dialog');
 if(!dialog?.classList.contains('stock-analysis-dialog'))return;
 for(const group of dialog.querySelectorAll('.stock-analysis-badges')){
  if(group.dataset.lifecycleDecorated==='1')continue;
  const badges=[...group.querySelectorAll('.stock-analysis-badge')];
  if(badges.length<3)continue;
  const q=group.dataset.setupState?JSON.parse(group.dataset.setupState):{status:badges[0].textContent.trim(),setup:badges[2].textContent.trim()};
  const state=setupState(q);
  const origin=document.createElement('span');
  origin.className='stock-analysis-badge';
  origin.textContent=`Setup Type: ${state.setupType}${state.setupType!=='—'?(state.confirmed?'（確認済み）':'（未確認）'):''}`;
  group.append(origin);
  const badge=document.createElement('span');
  badge.className=`stock-analysis-badge ${lifecycleTone(state.lifecycle)}`;
  badge.textContent=`Lifecycle: ${state.lifecycle==='UNASSESSED'?'未判定':state.lifecycle}${state.source==='INFERRED'?'（自動候補）':state.lifecycle!=='UNASSESSED'?(state.lifecycleConfirmed?'（確認済み）':'（未確認）'):''}`;
  group.append(badge);
  if(state.readiness){const readiness=document.createElement('span');readiness.className='stock-analysis-badge';readiness.textContent=`形成度: ${state.readiness}`;group.append(readiness);}
  if(state.candidate&&state.candidate!==state.lifecycle){const candidate=document.createElement('span');candidate.className='stock-analysis-badge';candidate.textContent=`自動候補: ${state.candidate}`;group.append(candidate);}
  group.dataset.lifecycleDecorated='1';
 }
}
enhanceStockDialog();
new MutationObserver(enhanceStockDialog).observe(document.getElementById('candidate-dialog'),{childList:true,subtree:true});
