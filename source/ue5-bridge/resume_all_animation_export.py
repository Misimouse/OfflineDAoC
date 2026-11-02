"""Resume only fully unexported private files after the initial batch time limit."""
from bridge_paths import ROOT, INSTALL, ENGINE, ART_PROJECT
import os,subprocess,json,re,struct
from pathlib import Path
R=Path(__file__).resolve().parent;I=Path(str(INSTALL));D=R/'Reports/pose_animations';out=R/'SourceAnimations_v02'
tasks=json.loads((out/'tasks.json').read_text());completed=set()
for path in [D/'export_all.log',D/'export_resume.log']:
 if path.exists():completed.update(re.findall(r'BRIDGE_MODEL_EXPORTED (\d+)',path.read_text(errors='replace')))
def valid(ident):
 path=out/f'model_{ident}.glb';sidecar=Path(str(path)+'.materials.json')
 if not path.exists()or not sidecar.exists():return False
 with path.open('rb')as f:header=f.read(12)
 return len(header)==12 and header[:4]==b'glTF'and struct.unpack_from('<I',header,8)[0]==path.stat().st_size
pending=[t['id']for t in tasks if t['id']not in completed or not valid(t['id'])];print('Previously complete:',len(tasks)-len(pending),'remaining:',pending,flush=True)
if pending:
 env=dict(os.environ,DOTNET_ROOT=str(I/'tools/dotnet'),DOTNET_ROOT_X64=str(I/'tools/dotnet'),APPDATA=str(R/'Reports/model-export-save'))
 with (D/'export_resume.log').open('w')as log:
  p=subprocess.run([str(I/'new-client/tools/godot_net/Godot_v4.7.2-stable_mono_win64.exe'),'--headless','--path',str(I/'new-client/godot'),'--script',str(R/'Godot/export_all_animations.gd'),'--','--only-ids='+','.join(pending)],env=env,stdout=log,stderr=subprocess.STDOUT,timeout=1200,creationflags=subprocess.CREATE_NO_WINDOW)
 assert p.returncode==0 and 'BRIDGE_MODEL_EXPORT_PASS'in(D/'export_resume.log').read_text(errors='replace')
assert all(valid(t['id'])for t in tasks)
rows=[{'id':t['id'],'file':str(out/f"model_{t['id']}.glb"),'scale':1.0 if'race'in t['info']else float(t['info'].get('scale',1.0)),'name':t['info'].get('name','')}for t in tasks]
(out/'exported.json').write_text(json.dumps(rows,indent=2));print('Complete manifest:',len(rows),flush=True)
