from bridge_paths import ROOT, INSTALL, ENGINE, ART_PROJECT
import os,subprocess,json
from pathlib import Path
R=Path(__file__).resolve().parent;I=Path(str(INSTALL))
env=dict(os.environ,DOTNET_ROOT=str(I/'tools/dotnet'),DOTNET_ROOT_X64=str(I/'tools/dotnet'),APPDATA=str(R/'Reports/isolated-save'))
r=subprocess.run([str(I/'new-client/tools/godot_net/Godot_v4.7.2-stable_mono_win64.exe'),'--headless','--path',str(R/'Godot'),'--script','res://test_nameplates.gd'],env=env,capture_output=True,text=True,timeout=40,creationflags=subprocess.CREATE_NO_WINDOW)
print(r.stdout,r.stderr);assert r.returncode==0
x=json.loads((R/'Reports/nameplates/godot_tests.json').read_text());assert x['passed']
