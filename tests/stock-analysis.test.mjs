import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
const readJSON=async path=>JSON.parse(await readFile(new URL(`../${path}`,import.meta.url),'utf8'));
const cache=new Map();
const cached=async path=>{if(!cache.has(path))cache.set(path,await readJSON(path));return cache.get(path);};

test('stock analysis index, immutable logs and coverage are consistent',async()=>{
 const manifest=await readJSON('data/stock-analysis/manifest.json');
 assert.equal(manifest.schemaVersion,2);assert.equal(manifest.mode,'live');
 assert.ok(manifest.symbols&&typeof manifest.symbols==='object');
 for(const [symbol,meta] of Object.entries(manifest.symbols)){
  assert.ok(['US','JP'].includes(meta.market));
  assert.ok(['UNANALYZED','OBSERVED','OLDER_INPUT','LEGACY_ONLY'].includes(meta.coverageStatus));
  const analyses=[];
  if(meta.path){const legacy=await cached(meta.path);assert.equal(legacy.symbol,symbol);analyses.push(...legacy.analyses);}
  const ids=new Set();
  for(const reference of meta.entries??[]){
   const doc=await cached(reference.path);assert.equal(doc.mode,'live');
   const entry=doc.symbols[symbol];assert.ok(entry);assert.equal(entry.id,reference.id);
   assert.equal(entry.generatedAt,reference.generatedAt);assert.equal(entry.marketDataAsOf,reference.marketDataAsOf);
   assert.ok(!ids.has(entry.id),'duplicate analysis ID');ids.add(entry.id);analyses.push(entry);
  }
  for(const entry of analyses){
   assert.match(entry.analysisDate,/^\d{4}-\d{2}-\d{2}$/);assert.match(entry.marketDataAsOf,/^\d{4}-\d{2}-\d{2}$/);
   assert.ok(Number.isFinite(Date.parse(entry.generatedAt)));assert.ok(entry.marketDataAsOf<=entry.analysisDate);
   assert.ok(entry.status&&entry.stage&&entry.setup&&entry.action?.code&&entry.action?.label);
   for(const field of ['idealPath','confirmation','invalidation'])assert.ok(Array.isArray(entry[field]));
  }
  if(analyses.length){const latest=analyses.sort((a,b)=>Date.parse(b.generatedAt)-Date.parse(a.generatedAt))[0];assert.equal(meta.latestAnalysisDate,latest.analysisDate);assert.equal(meta.marketDataAsOf,latest.marketDataAsOf);}
 }
});
