export const clamp = (v,min=0,max=100) => Math.min(max,Math.max(min,v));
export const round = (v) => Math.round((v+1e-9)*10)/10;
export function weighted(values,weights){const keys=Object.keys(weights);if(keys.some(k=>!Number.isFinite(values[k])))return null;const total=keys.reduce((s,k)=>s+weights[k],0);if(total<=0)return null;return round(keys.reduce((s,k)=>s+clamp(values[k])*weights[k],0)/total);}
export function opportunity(t,health,config){const q=t.quantitative,s=t.scores;const components={weeklyStrength:s.weekly,dailyAcceleration:Number.isFinite(q.dailyRank)?q.dailyAcceleration:null,breadth:q.above50,leaderQuality:s.leaderQuality,setupAvailability:clamp(q.setupReady*22),marketHealth:health};let status='MATURE';const th=config.thresholds;
 if(q.extensionPct>=th.extendedPct)status='EXTENDED';
 else if(q.weeklyDelta5<=-th.activeShortScoreDrop&&q.breadthDelta5<=-th.activeBreadthDrop)status='WEAKENING';
 else if(Number.isFinite(q.dailyRank)&&Number.isFinite(s.weekly)&&s.weekly>=th.minimumWeekly&&q.setupReady>0&&health>=th.marketWatch)status=q.dailyAcceleration>=th.emergingDaily&&q.dailyRank<q.weeklyRank?'EMERGING':'ACTIONABLE';
 return {score:weighted(components,config.opportunity),components,status,eligible:['ACTIONABLE','EMERGING'].includes(status),gates:{dailyData:Number.isFinite(q.dailyRank),market:health>=th.marketWatch,weekly:s.weekly>=th.minimumWeekly,readySetup:q.setupReady>0,notExtended:q.extensionPct<th.extendedPct}};
}
export function activeHealth(t,config){const q=t.quantitative,th=config.thresholds;if(!Number.isFinite(q.weeklyDelta5)||!Number.isFinite(q.breadthDelta5)||!Number.isFinite(q.weeklyDelta3Weeks)||!Number.isFinite(q.above200))return {status:'UNASSESSED',shortWeakness:null,mediumBreak:null,failedRate:null};const short=q.weeklyDelta5<=-th.activeShortScoreDrop||q.breadthDelta5<=-th.activeBreadthDrop;const medium=q.weeklyDelta3Weeks<=-th.activeMediumScoreDrop && q.above200<50;const failed=q.breakouts>0&&q.failedBreakouts/q.breakouts>=th.failedBreakoutRate;
 const status=medium&&(short||failed)?'DETERIORATING':short||failed?'WATCH':'HEALTHY';return {status,shortWeakness:short,mediumBreak:medium,failedRate:q.breakouts?q.failedBreakouts/q.breakouts:null};}
export function confirmation(t){if(!t||!Number.isFinite(t.quantitative.dailyRank))return 'UNCONFIRMED';const q=t.quantitative;return q.dailyRank<=10&&q.weeklyRankChange>0&&q.breadthDelta5>0&&q.leaderRSDelta5>0?'CONFIRMED TAILWIND':'UNCONFIRMED';}
export function atOrBefore(entries,date){return entries.filter(e=>e.asOf<=date).sort((a,b)=>a.asOf.localeCompare(b.asOf)).at(-1)||null;}
export function dataStatus({mode,asOf,latestAsOf,lastSuccessfulUpdate,failures=[],expectedNextUpdate},now=new Date()){
 if(failures.length)return {label:'STALE DATA',tone:'warning',reason:failures.join(' / ')};
 if(asOf<latestAsOf)return {label:'ARCHIVE',tone:'neutral',reason:'選択した過去評価を表示'};
 if(mode==='mock')return {label:'MOCK DATA',tone:'warning',reason:'市場数値・AI文章は検証用サンプル'};
 if(!Number.isFinite(Date.parse(lastSuccessfulUpdate))||Date.parse(lastSuccessfulUpdate)>+now)return {label:'INVALID DATA',tone:'negative',reason:'更新時刻が未設定または未来'};
 if(expectedNextUpdate&&+now>Date.parse(expectedNextUpdate))return {label:'STALE DATA',tone:'warning',reason:'予定された更新時刻を超過'};
 return {label:'OBSERVED DATA',tone:'positive',reason:'確定足の遅延データから算出・自動更新未接続'};
}
export function marketTrend(a){if(!Number.isFinite(a.price)||!Number.isFinite(a.ma50)||!Number.isFinite(a.slope50))return {label:'— 未判定',tone:'neutral'};const limit=a.changeUnit==='bp'?15:6;if(a.change1M>=limit&&a.price>a.ma50&&a.slope50>0)return {label:'↑↑ Strong Up',tone:'positive'};if(a.price>a.ma50&&a.slope50>0)return {label:'↑ Up',tone:'positive'};if(a.change1M<=-limit&&a.price<a.ma50&&a.slope50<0)return {label:'↓↓ Strong Down',tone:'negative'};if(a.price<a.ma50&&a.slope50<0)return {label:'↓ Down',tone:'negative'};return {label:'→ Neutral',tone:'neutral'};}

// Reuse saved theme evaluations; stock gates only narrow the research shortlist.
export function researchStocks(ctx,themeId='all'){
 return ctx.rows.filter(t=>themeId==='all'||t.id===themeId).flatMap(theme=>{
  const themeOpportunity=opportunity(theme,ctx.health,ctx.config);
  return [...theme.stocks].sort((a,b)=>(b.scores.leader??-1)-(a.scores.leader??-1)).map((stock,index)=>{
   const q=stock.quantitative;
   const validLevels=Number.isFinite(q.price)&&q.price>0&&Number.isFinite(q.entry)&&q.entry>0&&Number.isFinite(q.stop)&&q.stop>0&&q.stop<q.entry;
   const distance=validLevels?100*(q.price/q.entry-1):null;
   const extended=Number.isFinite(distance)&&distance>=ctx.config.thresholds.extendedPct||Number.isFinite(q.extensionPct)&&q.extensionPct>=ctx.config.thresholds.extendedPct;
   const gates={theme:themeOpportunity.eligible,stage2:q.stage==='Stage 2',ready:q.setupReady===true,levels:validLevels,extension:validLevels&&!extended};
   const eligible=!!q.setup&&Object.values(gates).every(Boolean);
   return {theme,stock,leaderRank:index+1,themeOpportunity,gates,eligible,extended,distance,risk:validLevels?100*(1-q.stop/q.entry):null};
  });
 });
}

// Public overview: independent of local watch preferences or personal positions.
export function decisionSummary(ctx){
 const healthStatus=!Number.isFinite(ctx.health)?'UNASSESSED':ctx.health>=ctx.config.thresholds.marketHealthy?'HEALTHY':ctx.health>=ctx.config.thresholds.marketWatch?'WATCH':'DETERIORATING';
 const themes=ctx.rows.map(theme=>({theme,opportunity:opportunity(theme,ctx.health,ctx.config),health:activeHealth(theme,ctx.config)}));
 const counts={HEALTHY:0,WATCH:0,DETERIORATING:0,UNASSESSED:0};
 themes.forEach(r=>counts[r.health.status]++);
 const entries=themes.filter(r=>r.opportunity.eligible).sort((a,b)=>(b.opportunity.score??-1)-(a.opportunity.score??-1));
 const records=researchStocks(ctx).sort((a,b)=>(b.stock.scores.leader??-1)-(a.stock.scores.leader??-1));
 const unique=rows=>{const seen=new Set();return rows.filter(r=>{if(seen.has(r.stock.symbol))return false;seen.add(r.stock.symbol);return true;});};
 const entryStocks=unique(records.filter(r=>r.eligible));
 const healthy=themes.filter(r=>r.health.status==='HEALTHY').sort((a,b)=>(b.theme.scores.weekly??-1)-(a.theme.scores.weekly??-1));
 const warnings=themes.filter(r=>['WATCH','DETERIORATING'].includes(r.health.status)).sort((a,b)=>Number(b.health.status==='DETERIORATING')-Number(a.health.status==='DETERIORATING'));
 const trendStocks=unique(records.filter(r=>r.leaderRank<=3&&Number.isFinite(r.theme.quantitative.dailyRank)&&r.stock.quantitative.stage==='Stage 2'&&r.stock.quantitative.above50===true));
 return {healthStatus,entries,entryStocks,healthy,warnings,trendStocks,counts};
}
