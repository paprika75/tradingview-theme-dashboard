"""Make an offline single-file preview from the same app and data."""
from pathlib import Path
import json
root=Path(__file__).resolve().parents[1]
fixtures={str(p.relative_to(root/'data')):json.loads(p.read_text()) for p in sorted((root/'data').rglob('*.json'))}
js=(root/'app.js').read_text()
js=js.replace('const params = new URLSearchParams(location.search);',"let params = new URLSearchParams(location.hash.split('?')[1] || '');")
js=js.replace("const filename = location.pathname.split('/').pop();","let filename = location.hash.slice(1).split('?')[0];")
js=js.replace('const page = filename', 'let page = filename')
js=js.replace("=> `${file}?${new URLSearchParams", "=> `#${file}?${new URLSearchParams")
js=js.replace("history.replaceState(null,'',`${location.pathname}?${p}`)","history.replaceState(null,'',`#${page==='overview'?'index':page}.html?${p}`)")
start=js.index('async function json(path)')
end=js.index('async function start()',start)
js=js[:start]+"async function json(path){if(!FIXTURES[path])throw new Error('Missing '+path);return FIXTURES[path];}\n"+js[end:]
js=js.replace('start();',"""window.addEventListener('hashchange',()=>{
 params=new URLSearchParams(location.hash.split('?')[1]||'');
 filename=location.hash.slice(1).split('?')[0];
 page=filename==='theme.html'?'theme':filename==='history.html'?'history':filename==='about.html'?'about':'overview';
 state.market=params.get('market')==='JP'?'JP':'US';state.period=params.get('period')==='weekly'?'weekly':'daily';
 state.key=params.get('date')||manifest[state.period].at(-1).key;state.selected=[];state.search='';state.filter='all';render();window.scrollTo(0,0);
});start();""")
css=(root/'styles.css').read_text()
html=(root/'index.html').read_text().replace('<link rel="stylesheet" href="styles.css">',f'<style>{css}</style>').replace('<script type="module" src="app.js"></script>','')
payload=json.dumps(fixtures,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')
html=html.replace('</body>',f'<script>const FIXTURES={payload};\n{js}</script></body>')
(root/'preview.html').write_text(html)
print('Offline preview:',root/'preview.html')
