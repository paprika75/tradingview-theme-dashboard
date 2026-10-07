const timestamp=value=>Number.isFinite(Date.parse(value))?Date.parse(value):null;
const day=value=>/^\d{4}-\d{2}-\d{2}$/.test(value??'')?value:null;
// Market selections mean end of that day in JST. Generation time is an
// independent availability boundary, even when the input bars are older.
export function analysisSelection(doc,{asOf,mode='live',latest=false}={}){
 if(mode!=='live')return {current:null,history:[],status:'DEMO',hidden:0};
 if(!day(asOf))return {current:null,history:[],status:'INVALID_CONTEXT',hidden:0};
 const cutoff=Date.parse(`${asOf}T23:59:59.999+09:00`);
 const valid=(doc?.analyses??[]).filter(a=>a.mode!=='mock'&&day(a.analysisDate)&&day(a.marketDataAsOf)&&timestamp(a.generatedAt)!==null&&a.marketDataAsOf<=a.analysisDate);
 const all=[...valid].sort((a,b)=>timestamp(b.generatedAt)-timestamp(a.generatedAt)||String(b.id??'').localeCompare(String(a.id??'')));
 const available=latest?all:all.filter(a=>a.analysisDate<=asOf&&a.marketDataAsOf<=asOf&&timestamp(a.generatedAt)<=cutoff);
 return {current:available[0]??null,history:available.slice(1),status:available.length?(latest?'LATEST':'AS_OF'):'UNANALYZED',hidden:all.length-available.length};
}
