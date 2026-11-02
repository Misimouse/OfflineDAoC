from bridge_paths import ROOT, INSTALL, ENGINE, ART_PROJECT
import os,subprocess,json
from pathlib import Path
R=Path(__file__).resolve().parent;I=Path(str(INSTALL))
env=dict(os.environ,DOTNET_ROOT=str(I/'tools/dotnet'),DOTNET_ROOT_X64=str(I/'tools/dotnet'),APPDATA=str(R/'Reports/model-export-save'))
with (R/'Reports/player_state/animation_audit.log').open('w')as log:
 p=subprocess.run([str(I/'new-client/tools/godot_net/Godot_v4.7.2-stable_mono_win64.exe'),'--headless','--path',str(I/'new-client/godot'),'--script',str(R/'Godot/audit_combat_animations.gd')],env=env,stdout=log,stderr=subprocess.STDOUT,timeout=180,creationflags=subprocess.CREATE_NO_WINDOW)
assert p.returncode==0,(R/'Reports/player_state/animation_audit.log').read_text()[-2000:]
data=json.loads((R/'Reports/player_state/animation_audit.json').read_text());print('Models:',len(data['models']),'errors:',data['errors']);assert not data['errors']
