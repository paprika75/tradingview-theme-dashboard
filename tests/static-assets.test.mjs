import test from 'node:test';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
test('Pages staging includes every entry module and hashes nested dependencies',async()=>{
 const root=new URL('../',import.meta.url);
 execFileSync('python',['scripts/stage_static.py'],{cwd:root});
 const seen=new Set();
 async function check(url){
  const key=url.pathname;if(seen.has(key))return;seen.add(key);
  const content=await readFile(url,'utf8');
  const expected=createHash('sha256').update(content).digest('hex').slice(0,12);
  assert.equal(url.searchParams.get('v'),expected,`${key} cache version`);
  for(const match of content.matchAll(/from\s+['"](\.\/[^'"]+)['"]/g))await check(new URL(match[1],url));
 }
 for(const name of ['us.html','japan.html','theme.html']){
  const page=new URL('public/'+name,root),html=await readFile(page,'utf8');
  assert.ok(html.includes('setup-lifecycle-ui.js?v='));
  for(const m of html.matchAll(/<script type="module" src="([^"]+)"/g))await check(new URL(m[1],page));
 }
});
