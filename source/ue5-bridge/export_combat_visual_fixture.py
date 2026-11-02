from bridge_paths import ROOT, INSTALL, ENGINE, ART_PROJECT
import os,subprocess,json
from pathlib import Path
R=Path(__file__).resolve().parent;I=Path(str(INSTALL));D=R/'Reports/combat_visual';D.mkdir(exist_ok=True)
env=dict(os.environ,DOTNET_ROOT=str(I/'tools/dotnet'),DOTNET_ROOT_X64=str(I/'tools/dotnet'),APPDATA=str(D/'offline-save'))
p=subprocess.run([str(I/'new-client/tools/godot_net/Godot_v4.7.2-stable_mono_win64.exe'),'--headless','--path',str(R/'Godot'),'--script','res://export_combat_visual_fixture.gd'],env=env,capture_output=True,text=True,timeout=35,creationflags=subprocess.CREATE_NO_WINDOW)
print(p.stdout,p.stderr);assert p.returncode==0 and'SCRIPT ERROR'not in p.stderr;assert json.loads((D/'fixture.json').read_text())
