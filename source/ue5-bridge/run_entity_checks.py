from bridge_paths import ROOT, INSTALL, ENGINE, ART_PROJECT
import json,os,subprocess
from pathlib import Path
R=Path(__file__).resolve().parent
I=Path(str(INSTALL))
env=dict(os.environ,DOTNET_ROOT=str(I/'tools/dotnet'),DOTNET_ROOT_X64=str(I/'tools/dotnet'),APPDATA=str(R/'Reports/isolated-save'))
engine=I/'new-client/tools/godot_net/Godot_v4.7.2-stable_mono_win64.exe'
result=subprocess.run([str(engine),'--headless','--path',str(R/'Godot'),'--script','res://test_entity_lifecycle.gd'],env=env,capture_output=True,text=True,timeout=45,creationflags=subprocess.CREATE_NO_WINDOW)
print(result.stdout);print(result.stderr)
assert result.returncode==0
report=json.loads((R/'Reports/entities/godot_lifecycle.json').read_text())
assert report['passed']
from protocol import validate_snapshot
for case in report['cases']:validate_snapshot(case['snapshot'])
print('All replay snapshots conform to the bridge protocol.')
