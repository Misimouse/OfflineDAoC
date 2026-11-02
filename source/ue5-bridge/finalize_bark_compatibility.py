import json,hashlib
from pathlib import Path
R=Path(__file__).resolve().parent;D=R/'Reports/compatibility'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
log=(D/'build_full.log').read_text(errors='replace');targets=['UnrealEditor Win64 Development','UnrealGame Win64 Development','UnrealGame Win64 Shipping'];assert 'BUILD SUCCESSFUL' in log and all(t in log for t in targets)
files=[]
for folder in ['Binaries','Source','Content/Compatibility']:
 src=R/'Build/DAoCVisualBridge'/folder
 for p in src.rglob('*'):
  if not p.is_file():continue
  q=R/'Client/Plugins/DAoCVisualBridge'/folder/p.relative_to(src);h=hashlib.sha256(p.read_bytes()).hexdigest();assert q.is_file() and hashlib.sha256(q.read_bytes()).hexdigest()==h,str(q);files.append({'path':folder+'/'+p.relative_to(src).as_posix(),'sha256':h})
assets=read(D/'bark_assets.json');live=read(D/'live_verification.json');assert assets['complete'] and live['passed'] and live['parameters_matched'] and live['normal_logout']
for p,h in assets['original_assets_sha256'].items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h,p
(D/'installed_build.json').write_text(json.dumps({'complete':True,'targets':targets,'files':files,'originals_unchanged':True,'original_graph_copy_only':True},indent=2))
print(json.dumps({'installed':True,'originals_unchanged':True,'bindings':live['bindings'],'parameters_matched':True,'normal_logout':True,'targets':targets}))
