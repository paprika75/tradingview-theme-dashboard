import {marketAction,technicalThemeCandidate,technicalResearchStocks} from './market-action.mjs';
import {researchStocks} from './logic.mjs';
import {setupState} from './setup-state.mjs';

const finite=v=>Number.isFinite(v);
const score=v=>finite(v)?v:-Infinity;
const uniqueSymbols=rows=>new Set(rows.map(r=>r.stock.symbol)).size;

export function peerGroupForStock(stock){
 const q=stock?.quantitative??{};
 const value=q.peerGroup??q.industry??q.industryGroup??null;
 return typeof value==='string'&&value.trim()?value.trim():null;
}

export function topDownDecision(ctx,{themeId='all',maxThemes=5,maxRows=12}={}){
 const action=marketAction({...ctx,asOf:ctx.entry.asOf});
 const themes=ctx.rows
  .filter(theme=>themeId==='all'||theme.id===themeId)
  .map(theme=>({theme,technical:technicalThemeCandidate(theme,ctx.config)}))
  .sort((a,b)=>Number(b.technical.eligible)-Number(a.technical.eligible)||score(b.theme.scores.weekly)-score(a.theme.scores.weekly)||score(b.theme.scores.daily)-score(a.theme.scores.daily));
 const candidateThemes=themes.filter(r=>r.technical.eligible);
 const focusThemes=candidateThemes.slice(0,maxThemes);
 const focusThemeIds=new Set(focusThemes.map(r=>r.theme.id));
 const allRecords=technicalResearchStocks(ctx,researchStocks(ctx,themeId));
 const records=allRecords.filter(r=>focusThemeIds.has(r.theme.id));
 const leaders=records
  .filter(r=>r.leaderRank<=3&&r.stock.quantitative.stage==='Stage 2')
  .sort((a,b)=>score(b.stock.scores.leader)-score(a.stock.scores.leader));
 const setups=records
  .filter(r=>r.stock.quantitative.setup||r.stock.quantitative.setup_type)
  .map(r=>({...r,state:setupState(r.stock.quantitative,r.extended),peerGroup:peerGroupForStock(r.stock)}))
  .sort((a,b)=>Number(b.eligible)-Number(a.eligible)||score(b.stock.scores.leader)-score(a.stock.scores.leader));
 const entryCandidates=setups.filter(r=>r.eligible);
 const pivotReady=entryCandidates.filter(r=>finite(r.stock.quantitative.pivot));
 const peerGroups=new Set(leaders.map(r=>peerGroupForStock(r.stock)).filter(Boolean));
 return {
  action,
  themes,
  candidateThemes,
  focusThemes,
  leaders,
  setups,
  entryCandidates,
  pivotReady,
  rows:setups.slice(0,maxRows),
  peerGroups:[...peerGroups].sort(),
  counts:{
   themes:candidateThemes.length,
   focusedThemes:focusThemes.length,
   peerGroups:peerGroups.size,
   leaders:uniqueSymbols(leaders),
   setups:uniqueSymbols(setups),
   entryCandidates:uniqueSymbols(entryCandidates),
   pivotReady:uniqueSymbols(pivotReady),
  },
  industryConnected:peerGroups.size>0,
  automaticBuy:false,
 };
}
