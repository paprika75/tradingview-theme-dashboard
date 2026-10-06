import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';

const readJSON=async path=>JSON.parse(await readFile(new URL(`../${path}`,import.meta.url),'utf8'));

test('stock analysis manifest and logs are consistent',async()=>{
  const manifest=await readJSON('data/stock-analysis/manifest.json');
  assert.equal(manifest.schemaVersion,1);
  assert.ok(manifest.symbols&&typeof manifest.symbols==='object');

  for(const [symbol,meta] of Object.entries(manifest.symbols)){
    const doc=await readJSON(meta.path);
    assert.equal(doc.schemaVersion,1);
    assert.equal(doc.symbol,symbol);
    assert.ok(['USD','JPY'].includes(doc.currency));
    assert.ok(Array.isArray(doc.analyses)&&doc.analyses.length>0);

    const sorted=[...doc.analyses].sort((a,b)=>String(b.analysisDate).localeCompare(String(a.analysisDate))||String(b.generatedAt).localeCompare(String(a.generatedAt)));
    const latest=sorted[0];
    assert.equal(meta.latestAnalysisDate,latest.analysisDate);
    assert.equal(meta.marketDataAsOf,latest.marketDataAsOf);

    const ids=new Set();
    for(const entry of doc.analyses){
      assert.match(entry.analysisDate,/^\d{4}-\d{2}-\d{2}$/);
      assert.match(entry.marketDataAsOf,/^\d{4}-\d{2}-\d{2}$/);
      assert.ok(entry.generatedAt);
      assert.ok(entry.status);
      assert.ok(entry.stage);
      assert.ok(entry.setup);
      assert.ok(entry.action?.code);
      assert.ok(entry.action?.label);
      assert.ok(Array.isArray(entry.idealPath));
      assert.ok(Array.isArray(entry.confirmation));
      assert.ok(Array.isArray(entry.invalidation));
      const id=`${entry.analysisDate}|${entry.generatedAt}`;
      assert.ok(!ids.has(id),'duplicate stock analysis timestamp');
      ids.add(id);
    }
  }
});
