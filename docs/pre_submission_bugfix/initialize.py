"""Create a protected baseline and isolated output tree; never replace a baseline."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'reports/reproduced/pre_submission_bugfix'
if OUT.exists():
    raise SystemExit(f'Refusing to replace existing isolation directory: {OUT}')
OUT.mkdir(parents=True)
manifest={}
for folder in ['data/analysis','data/processed','reports/main','reports/thesis']:
    for p in (ROOT/folder).rglob('*'):
        if p.is_file():
            manifest[str(p.relative_to(ROOT))]={'sha256':hashlib.file_digest(p.open('rb'),'sha256').hexdigest(),'mtime_ns':p.stat().st_mtime_ns}
(OUT/'protected_before.json').write_text(json.dumps(manifest,indent=2))
(OUT/'git_status_before.txt').write_text(subprocess.check_output(['git','status','--short'],cwd=ROOT,text=True))
for folder in ['data/analysis','reports/main','reports/working/tables']:
    shutil.copytree(ROOT/folder,OUT/folder)
shutil.copytree(ROOT/'reports/main/tables',OUT/'before/tables')
shutil.copytree(ROOT/'data/analysis',OUT/'before/analysis')
for folder in ['weather','accidents','traffic']:
    (OUT/'data/processed'/folder).mkdir(parents=True)
print(OUT)
