import test from 'node:test';
import assert from 'node:assert/strict';
import {analysisSelection} from '../lib/stock-analysis-state.mjs';
const old={id:'old',analysisDate:'2026-10-05',marketDataAsOf:'2026-10-05',generatedAt:'2026-10-05T19:00:00+09:00'};
const later={id:'later',analysisDate:'2026-10-07',marketDataAsOf:'2026-10-05',generatedAt:'2026-10-07T04:00:00+09:00'};
test('older input bars never make a later analysis available in the past',()=>{
 const selected=analysisSelection({analyses:[later,old]},{asOf:'2026-10-05'});
 assert.equal(selected.current.id,'old');assert.equal(selected.hidden,1);
 assert.equal(analysisSelection({analyses:[later,old]},{asOf:'2026-10-05',latest:true}).current.id,'later');
});
test('JST availability boundary, intraday revisions and invalid timestamps',()=>{
 const midnight={...old,id:'midnight',generatedAt:'2026-10-05T15:00:00Z'};
 assert.equal(analysisSelection({analyses:[midnight,old]},{asOf:'2026-10-05'}).current.id,'old');
 const revision={...later,id:'revision',generatedAt:'2026-10-07T10:00:00+09:00'};
 const selected=analysisSelection({analyses:[old,later,revision,{...old,generatedAt:'bad'}]},{asOf:'2026-10-07'});
 assert.equal(selected.current.id,'revision');assert.deepEqual(selected.history.map(e=>e.id),['later','old']);
});
test('missing analysis and Demo are distinct and do not mix observed data',()=>{
 assert.equal(analysisSelection({analyses:[later]},{asOf:'2026-10-05'}).status,'UNANALYZED');
 assert.equal(analysisSelection({analyses:[later]},{asOf:'2026-10-07',mode:'mock',latest:true}).status,'DEMO');
 assert.equal(analysisSelection({analyses:[{...old,mode:'mock'}]},{asOf:'2026-10-05'}).current,null);
 assert.equal(analysisSelection({analyses:[old]},{}).status,'INVALID_CONTEXT');
});
