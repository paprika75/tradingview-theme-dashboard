"""Archive deterministic action context; reuse existing Outlook/exposure inputs."""
import json
from pathlib import Path
from research_store import immutable_json, atomic_json

ROOT=Path(__file__).resolve().parents[1]
VERSION='1.0.0-market-action'
DEFINITIONS={
 'MARKET_IN_CORRECTION':('WAIT','新規Entryは待機','技術候補を監視し、指数の回復・FTDを待つ'),
 'UPTREND_UNDER_PRESSURE':('LIMIT','新規Entryは慎重に確認','候補を絞り、支持・出来高・Stop・参考投資比率を確認'),
 'CONFIRMED_UPTREND':('CHECK_ENTRY','個別Entry条件を確認','市場の上昇確認に加え、Lifecycle別のEntry・Stop・Riskを確認'),
 'UNASSESSED':('VERIFY','市場判定は未完','出来高・FTD等を確認できるまで、価格上昇だけで新規Entry可と扱わない'),
}

def build(root=ROOT):
 path=root/'data/live/latest.json'
 manifest=json.loads(path.read_text())
 saved={e['asOf']:e for e in manifest.get('marketAction',[])}
 for entry in manifest.get('marketOutlook',[]):
  outlook=json.loads((root/'data'/entry['path']).read_text())
  if outlook['asOf']!=entry['asOf'] or outlook['evaluationVersion']!=entry['evaluationVersion'] or outlook['mode']!='live':
   raise ValueError('Outlook date/version/mode mismatch')
  exposure_entry=next((e for e in manifest.get('marketExposure',[]) if e['asOf']==entry['asOf']),None)
  exposure=json.loads((root/'data'/exposure_entry['path']).read_text()) if exposure_entry else None
  if exposure and (exposure['asOf']!=outlook['asOf'] or exposure['outlookVersion']!=outlook['evaluationVersion'] or exposure['mode']!='live'):
   raise ValueError('Exposure date/version/mode mismatch')
  doc={'schemaVersion':1,'mode':'live','asOf':outlook['asOf'],'evaluationVersion':VERSION,
       'outlookVersion':outlook['evaluationVersion'],'exposureVersion':exposure['evaluationVersion'] if exposure else None,
       'sourcePaths':{'outlook':entry['path'],'exposure':exposure_entry['path'] if exposure_entry else None},
       'provenance':'Deterministic replay of saved index evaluation; not a contemporaneously published entry permission',
       'markets':{}}
  for market,value in outlook['markets'].items():
   state=value['status'] if value['status'] in DEFINITIONS else 'UNASSESSED'
   code,label,condition=DEFINITIONS[state]
   doc['markets'][market]={'state':state,'code':code,'label':label,'condition':condition,
                          'reasons':value.get('reasons',[]),'range':exposure['markets'][market]['range'] if exposure else None,
                          'automaticBuy':False}
  relative=f'live/market-action/{VERSION}/{outlook["asOf"]}.json'
  immutable_json(root/'data'/relative,doc)
  saved[outlook['asOf']]={'asOf':outlook['asOf'],'path':relative,'evaluationVersion':VERSION}
 atomic_json(path,{**manifest,'marketAction':[saved[k] for k in sorted(saved)]})
 return len(saved)

if __name__=='__main__':print('Saved market action contexts:',build())
