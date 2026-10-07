"""Stage Pages assets with dependency-aware content hashes, avoiding mixed cached releases."""
from pathlib import Path
import hashlib,re,shutil
root=Path(__file__).resolve().parents[1]
public=root/'public';public.mkdir(exist_ok=True)
for folder in ['data','lib','config']:shutil.copytree(root/folder,public/folder,dirs_exist_ok=True)
for name in ['index.html','us.html','japan.html','theme.html','history.html','about.html','app.js','stock-analysis.js','setup-lifecycle-ui.js','styles.css']:shutil.copy2(root/name,public/name)

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()[:12]
def version_imports(path):
 def replace(match):
  prefix,relative,suffix=match.groups()
  target=path.parent/relative
  return prefix+relative+'?v='+digest(target)+suffix
 path.write_text(re.sub(r"(from\s+['\"])(\./[^'\"]+)(['\"])",replace,path.read_text()))
# Logic has no imports. Readers/views import logic, then app imports those modules.
for name in ['lib/data.mjs','lib/views.mjs','setup-lifecycle-ui.js','app.js']:version_imports(public/name)
for name in ['index.html','us.html','japan.html','theme.html','history.html','about.html']:
 p=public/name
 text=p.read_text().replace('src="app.js"',f'src="app.js?v={digest(public/"app.js")}"').replace('href="styles.css"',f'href="styles.css?v={digest(public/"styles.css")}"')
 if 'src="setup-lifecycle-ui.js"' in text:text=text.replace('src="setup-lifecycle-ui.js"',f'src="setup-lifecycle-ui.js?v={digest(public/"setup-lifecycle-ui.js")}"')
 if 'src="stock-analysis.js"' in text:text=text.replace('src="stock-analysis.js"',f'src="stock-analysis.js?v={digest(public/"stock-analysis.js")}"')
 p.write_text(text)
shutil.copy2(root/'tests/browser-layout.html',public/'qa.html')
(public/'.nojekyll').touch()
print('Staged versioned static assets:',public)
