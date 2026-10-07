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
  const badge=document.createElement('span');
  badge.className=`stock-analysis-badge ${lifecycleTone(state.lifecycle)}`;
  badge.textContent=`Lifecycle: ${state.lifecycle==='UNASSESSED'?'未判定':state.lifecycle}${state.source==='INFERRED'?'（推定）':''}`;
  group.append(badge);
  group.dataset.lifecycleDecorated='1';
 }
}
enhanceStockDialog();
new MutationObserver(enhanceStockDialog).observe(document.getElementById('candidate-dialog'),{childList:true,subtree:true});
