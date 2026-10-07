export const LIFECYCLES=['SETUP','BREAKOUT','EXTENDED','PULLBACK','RETEST','3WT','TIGHT','ASCENDING_BASE','FAILED_BREAKOUT','UNASSESSED'];
const validPrice=v=>Number.isFinite(v)&&v>0;
const originNames={VCP:'VCP',CWH:'CWH',BASE_BREAKOUT:'Base Breakout','Base Breakout':'Base Breakout'};
export function setupState(q={},extended=false){
 const origin=q.setup_type??q.setup;
 const setupType=q.setup_type?String(q.setup_type):originNames[origin]??'—';
 const readiness=q.preSetup?.readiness??q.readiness??(q.setupReady===true?'Ready':null);
 let lifecycle='UNASSESSED',source='UNASSESSED';
 if(LIFECYCLES.includes(q.lifecycle)) {
  lifecycle=q.lifecycle;
  source=q.lifecycleSource==='RULE_CANDIDATE'?'CANDIDATE':q.lifecycleSource==='UNASSESSED'?'UNASSESSED':'SAVED';
 }
 else if(LIFECYCLES.includes(q.lifecycleCandidate)) {lifecycle=q.lifecycleCandidate;source='CANDIDATE';}
 else if(q.status==='FORMING'){lifecycle='SETUP';source='INFERRED';}
 else if(validPrice(q.price)&&validPrice(q.entry)&&setupType!=='—'){
  lifecycle=extended?'EXTENDED':q.price>=q.entry?'BREAKOUT':'SETUP';source='INFERRED';
 }
 return {
  setupType,lifecycle,source,readiness,
  confirmed:q.setupConfirmed===true,
  lifecycleConfirmed:q.lifecycleConfirmed===true,
  candidate:LIFECYCLES.includes(q.lifecycleCandidate)?q.lifecycleCandidate:null,
  candidateReasons:Array.isArray(q.lifecycleCandidateReasons)?q.lifecycleCandidateReasons:[],
  setupTypeSource:q.setupTypeSource??null,
  lifecycleSource:q.lifecycleSource??null,
  registryAsOf:q.setupRegistryAsOf??null
 };
}
export const lifecycleTone=value=>['BREAKOUT','3WT','TIGHT','ASCENDING_BASE'].includes(value)?'positive':['SETUP','PULLBACK','RETEST'].includes(value)?'new':value==='EXTENDED'?'warning':value==='FAILED_BREAKOUT'?'negative':'neutral';
