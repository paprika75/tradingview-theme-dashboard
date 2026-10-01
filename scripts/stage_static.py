"""Stage Pages assets with dependency-aware content hashes, avoiding mixed cached releases."""
from pathlib import Path
import hashlib,re,shutil
root=Path(__file__).resolve().parents[1]
public=root/'public';public.mkdir(exist_ok=True)
for folder in ['data','lib','config']:shutil.copytree(root/folder,public/folder,dirs_exist_ok=True)
for name in ['index.html','theme.html','history.html','about.html','app.js','styles.css']:shutil.copy2(root/name,public/name)

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()[:12]
def version_imports(path):
 def replace(match):
  prefix,relative,suffix=match.groups()
  target=path.parent/relative
  return prefix+relative+'?v='+digest(target)+suffix
 path.write_text(re.sub(r"(from\s+['\"])(\./[^'\"]+)(['\"])",replace,path.read_text()))
# Logic has no imports. Readers/views import logic, then app imports those modules.
for name in ['lib/data.mjs','lib/views.mjs','app.js']:version_imports(public/name)
for name in ['index.html','theme.html','history.html','about.html']:
 p=public/name;p.write_text(p.read_text().replace('src="app.js"',f'src="app.js?v={digest(public/"app.js")}"').replace('href="styles.css"',f'href="styles.css?v={digest(public/"styles.css")}"'))
shutil.copy2(root/'tests/browser-layout.html',public/'qa.html')
(public/'.nojekyll').touch()
print('Staged versioned static assets:',public)
