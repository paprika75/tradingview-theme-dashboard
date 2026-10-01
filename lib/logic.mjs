export const clamp = (v,min=0,max=100) => Math.min(max,Math.max(min,v));
export const round = (v) => Math.round((v+1e-9)*10)/10;
export function weighted(values,weights){const keys=Object.keys(weights);if(keys.some(k=>!Number.isFinite(values[k])))return null;const total=keys.reduce((s,k)=>s+weights[k],0);if(total<=0)return null;return round(keys.reduce((s,k)=>s+clamp(values[k])*weights[k],0)/total);}
export function opportunity(t,health,config){const q=t.quantitative,s=t.scores;const components={weeklyStrength:s.weekly,dailyAcceleration:Number.isFinite(q.dailyRank)?q.dailyAcceleration:null,breadth:q.above50,leaderQuality:s.leaderQuality,setupAvailability:clamp(q.setupReady*22),marketHealth:health};let status='MATURE';const th=config.thresholds;
 if(q.extensionPct>=th.extendedPct)status='EXTENDED';
 else if(q.weeklyDelta5<=-th.activeShortScoreDrop&&q.breadthDelta5<=-th.activeBreadthDrop)status='WEAKENING';
 else if(Number.isFinite(q.dailyRank)&&Number.isFinite(s.weekly)&&s.weekly>=th.minimumWeekly&&q.setupReady>0&&health>=th.marketWatch)status=q.dailyAcceleration>=th.emergingDaily&&q.dailyRank<q.weeklyRank?'EMERGING':'ACTIONABLE';
 return {score:weighted(components,config.opportunity),components,status,eligible:['ACTIONABLE','EMERGING'].includes(status),gates:{dailyData:Number.isFinite(q.dailyRank),market:health>=th.marketWatch,weekly:s.weekly>=th.minimumWeekly,readySetup:q.setupReady>0,notExtended:q.extensionPct<th.extendedPct}};
}
export function activeHealth(t,config){const q=t.quantitative,th=config.thresholds;const short=q.weeklyDelta5<=-th.activeShortScoreDrop||q.breadthDelta5<=-th.activeBreadthDrop;const medium=q.weeklyDelta3Weeks<=-th.activeMediumScoreDrop && q.above200<50;const failed=q.breakouts>0&&q.failedBreakouts/q.breakouts>=th.failedBreakoutRate;
 const status=medium&&(short||failed)?'DETERIORATING':short||failed?'WATCH':'HEALTHY';return {status,shortWeakness:short,mediumBreak:medium,failedRate:q.breakouts?q.failedBreakouts/q.breakouts:null};}
export function confirmation(t){if(!t||!Number.isFinite(t.quantitative.dailyRank))return 'UNCONFIRMED';const q=t.quantitative;return q.dailyRank<=10&&q.weeklyRankChange>0&&q.breadthDelta5>0&&q.leaderRSDelta5>0?'CONFIRMED TAILWIND':'UNCONFIRMED';}
export function atOrBefore(entries,date){return entries.filter(e=>e.asOf<=date).sort((a,b)=>a.asOf.localeCompare(b.asOf)).at(-1)||null;}
export function dataStatus({mode,asOf,latestAsOf,lastSuccessfulUpdate,failures=[],expectedNextUpdate},now=new Date()){
 if(failures.length)return {label:'STALE DATA',tone:'warning',reason:failures.join(' / ')};
 if(asOf<latestAsOf)return {label:'ARCHIVE',tone:'neutral',reason:'選択した過去評価を表示'};
 if(mode==='mock')return {label:'MOCK DATA',tone:'warning',reason:'市場数値・AI文章・保有例は検証用サンプル'};
 if(!Number.isFinite(Date.parse(lastSuccessfulUpdate))||Date.parse(lastSuccessfulUpdate)>+now)return {label:'INVALID DATA',tone:'negative',reason:'更新時刻が未設定または未来'};
 if(expectedNextUpdate&&+now>Date.parse(expectedNextUpdate))return {label:'STALE DATA',tone:'warning',reason:'予定された更新時刻を超過'};
 return {label:'Fresh',tone:'positive',reason:'直近の成功した更新を表示'};
}
export function marketTrend(a){const limit=a.changeUnit==='bp'?15:6;if(a.change1M>=limit&&a.price>a.ma50&&a.slope50>0)return {label:'↑↑ Strong Up',tone:'positive'};if(a.price>a.ma50&&a.slope50>0)return {label:'↑ Up',tone:'positive'};if(a.change1M<=-limit&&a.price<a.ma50&&a.slope50<0)return {label:'↓↓ Strong Down',tone:'negative'};if(a.price<a.ma50&&a.slope50<0)return {label:'↓ Down',tone:'negative'};return {label:'→ Neutral',tone:'neutral'};}