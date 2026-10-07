// Independent action constraints. Never changes saved theme/market scores.
export const ACTION_VERSION='1.0.0-market-action';
export function marketAction({mode='live',asOf,outlook,outlookMeta,exposure,exposureMeta,status,actionMeta,actionError,marketCode}={}){
 const valid=mode==='live'&&outlookMeta?.asOf===asOf&&outlookMeta?.mode==='live';
 const state=valid?outlook?.status:'UNASSESSED';
 const definitions={
  MARKET_IN_CORRECTION:['WAIT','新規Entryは待機','技術候補を監視し、指数の回復・FTDを待つ'],
  UPTREND_UNDER_PRESSURE:['LIMIT','新規Entryは慎重に確認','候補を絞り、支持・出来高・Stop・参考投資比率を確認'],
  CONFIRMED_UPTREND:['CHECK_ENTRY','個別Entry条件を確認','市場の上昇確認に加え、Lifecycle別のEntry・Stop・Riskを確認'],
  UNASSESSED:['VERIFY','市場判定は未完','出来高・FTD等を確認できるまで、価格上昇だけで新規Entry可と扱わない'],
 };
 const archived=valid&&actionMeta?.mode==='live'&&actionMeta?.asOf===asOf&&actionMeta?.outlookVersion===outlookMeta.evaluationVersion&&actionMeta?.markets?.[marketCode]?.state===state?actionMeta.markets[marketCode]:null;
 const [code,label,condition]=archived?[archived.code,archived.label,archived.condition]:definitions[state]??definitions.UNASSESSED;
 const exposureValid=valid&&state!=='UNASSESSED'&&exposureMeta?.asOf===asOf&&exposureMeta?.outlookVersion===outlookMeta?.evaluationVersion&&Array.isArray(exposure?.range)&&exposure.range.length===2;
 const stale=status?.label==='STALE DATA'||!!actionError;
 return {evaluationVersion:archived?actionMeta.evaluationVersion:ACTION_VERSION,asOf,state,code:stale?'VERIFY':code,
  label:mode==='mock'?'Demoの候補例':stale?'市場データ更新後に再確認':label,
  condition:stale?'保存評価の入力日が古いため、直近の市場環境と個別構造を更新してから判断':condition,
  reasons:valid?(outlook?.reasons??[]):['この表示日に一致するObserved Market Outlookが未取得'],
  priceOnly:valid&&outlook?.status==='UNASSESSED'&&(outlook.indices??[]).some(i=>i.priceTrend&&i.status==='UNASSESSED'),
  range:exposureValid?exposure.range:null,outlookVersion:valid?outlookMeta.evaluationVersion:null,
  exposureVersion:exposureValid?exposureMeta.evaluationVersion:null,
  automaticBuy:false};
}

export function technicalThemeCandidate(theme,config){
 const q=theme.quantitative??{},s=theme.scores??{},th=config.thresholds;
 const extended=Number.isFinite(q.extensionPct)&&q.extensionPct>=th.extendedPct;
 const weakening=Number.isFinite(q.weeklyDelta5)&&Number.isFinite(q.breadthDelta5)&&q.weeklyDelta5<=-th.activeShortScoreDrop&&q.breadthDelta5<=-th.activeBreadthDrop;
 const gates={daily:Number.isFinite(q.dailyRank),weekly:Number.isFinite(s.weekly)&&s.weekly>=th.minimumWeekly,
  ready:Number.isFinite(q.setupReady)&&q.setupReady>0,extension:Number.isFinite(q.extensionPct)&&!extended,structure:!weakening};
 return {eligible:Object.values(gates).every(Boolean),extended,gates,label:extended?'EXTENDED':Object.values(gates).every(Boolean)?'TECHNICAL CANDIDATE':'WATCH'};
}

export function technicalSummary(ctx,records){
 const entries=ctx.rows.map(theme=>({theme,technical:technicalThemeCandidate(theme,ctx.config)})).filter(r=>r.technical.eligible).sort((a,b)=>(b.theme.scores.weekly??-1)-(a.theme.scores.weekly??-1));
 const seen=new Set();
 const entryStocks=records.filter(r=>{
  const eligible=technicalThemeCandidate(r.theme,ctx.config).eligible&&r.gates.stage2&&r.gates.ready&&r.gates.levels&&r.gates.extension&&!!r.stock.quantitative.setup;
  if(!eligible||seen.has(r.stock.symbol))return false;seen.add(r.stock.symbol);return true;
 });
 return {entries,entryStocks};
}

export function technicalResearchStocks(ctx,records){
 return records.map(r=>{
  const technical=technicalThemeCandidate(r.theme,ctx.config);
  const gates={...r.gates,theme:technical.eligible};
  return {...r,technical,gates,legacyMomentumGate:r.gates.theme,
   eligible:!!r.stock.quantitative.setup&&Object.values(gates).every(Boolean)};
 });
}
