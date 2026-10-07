// Render saved model values only. Candidate state cannot advance a workflow here.
export function adoptedEntryPlans(journey={}){
 const plan=journey.entryPlan;
 if(!journey.lifecycle?.confirmed||!['FORMAL_SETUP','POST_BREAKOUT'].includes(journey.phase)||plan?.status!=='CONFIRMED')return [];
 return (plan.alternatives??[]).filter(p=>p.status==='CONFIRMED'&&p.lifecycle===journey.lifecycle.value&&p.episodeId===journey.episodeId&&Number.isFinite(p.entry)&&Number.isFinite(p.stop)&&p.entry>p.stop&&p.stop>0);
}
export const phaseLabel=value=>({PRE_SETUP:'Pre-Setup',FORMAL_SETUP:'Formal Setup',POST_BREAKOUT:'Post-Breakout',REFORMING:'再形成待ち',UNASSESSED:'未確認'}[value]??'未確認');
